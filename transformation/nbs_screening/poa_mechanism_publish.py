"""Upload POA mechanism-type COG, XYZ tiles, and screened-cell GeoJSON to S3."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Literal

HazardKind = Literal["flood", "heat", "landslide"]

S3_BUCKET = "geo-test-api"
S3_BASE_PREFIX = "oef_calculation/release/v1/porto_alegre/climate_hazards"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"

_PUBLISH_CONFIG: dict[HazardKind, dict[str, str]] = {
    "flood": {
        "slug": "flood_mechanism_type_poa_250m",
        "geojson": "flood_mechanism_type_poa_250m.geojson",
        "subdir": "floods/flood_mechanism",
    },
    "heat": {
        "slug": "heat_mechanism_type_poa_250m",
        "geojson": "heat_mechanism_type_poa_250m.geojson",
        "subdir": "heat/heat_mechanism",
    },
    "landslide": {
        "slug": "landslide_mechanism_type_poa_90m",
        "geojson": "landslide_mechanism_type_poa_90m.geojson",
        "subdir": "landslides/landslide_mechanism",
    },
}


def require_aws_cli() -> None:
    if not shutil.which("aws"):
        raise RuntimeError(
            "AWS CLI not found. Install awscli and configure credentials "
            "(aws configure or env vars)."
        )


def _s3_uri(key: str) -> str:
    return f"s3://{S3_BUCKET}/{S3_BASE_PREFIX}/{key}"


def public_url(key: str) -> str:
    return f"{S3_PUBLIC_BASE}/{S3_BASE_PREFIX}/{key}"


def publish_config(hazard: HazardKind) -> dict[str, str]:
    return dict(_PUBLISH_CONFIG[hazard])


def upload_poa_mechanism_to_s3(
    hazard: HazardKind,
    out_dir: Path,
    *,
    publish_dir: Path | None = None,
    geojson_path: Path | None = None,
    upload_cog: bool = True,
    upload_tiles: bool = True,
    upload_geojson: bool = True,
) -> dict[str, str]:
    """Upload COG, tile pyramids, and GeoJSON. Returns public HTTPS URLs."""
    require_aws_cli()
    cfg = _PUBLISH_CONFIG[hazard]
    out_dir = Path(out_dir)
    slug = cfg["slug"]
    publish_dir = Path(publish_dir or out_dir / slug)
    geojson_path = Path(geojson_path or out_dir / cfg["geojson"])
    subdir = cfg["subdir"]
    urls: dict[str, str] = {}

    if upload_cog:
        cog_local = publish_dir / f"{slug}_cog.tif"
        if not cog_local.is_file():
            raise FileNotFoundError(f"Missing COG for upload: {cog_local}")
        cog_key = f"{subdir}/{slug}_cog.tif"
        subprocess.run(["aws", "s3", "cp", str(cog_local), _s3_uri(cog_key)], check=True)
        urls["cog"] = public_url(cog_key)
        print(f"Uploaded COG → {urls['cog']}")

    if upload_tiles:
        for tiles_name in ("tiles_visual", "tiles_values"):
            tiles_local = publish_dir / tiles_name
            if not tiles_local.is_dir():
                raise FileNotFoundError(f"Missing tiles dir: {tiles_local}")
            tiles_key = f"{subdir}/{tiles_name}/"
            subprocess.run(
                ["aws", "s3", "cp", str(tiles_local), _s3_uri(tiles_key), "--recursive"],
                check=True,
            )
            urls[tiles_name] = public_url(tiles_key)
            print(f"Uploaded {tiles_name} → {urls[tiles_name]}")

    if upload_geojson:
        if not geojson_path.is_file():
            raise FileNotFoundError(
                f"Missing GeoJSON for upload: {geojson_path}. "
                "Run the BUILD_POA_*_LAYER cell first."
            )
        geojson_key = f"{subdir}/{cfg['geojson']}"
        subprocess.run(
            ["aws", "s3", "cp", str(geojson_path), _s3_uri(geojson_key)],
            check=True,
        )
        urls["geojson"] = public_url(geojson_key)
        print(f"Uploaded GeoJSON → {urls['geojson']}")

    return urls
