"""Upload heat hazard COG + XYZ tiles to S3 and upsert catalog/datasets.yaml."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

S3_BUCKET = "geo-test-api"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"
COG_FILENAME = "heat_hazard_score_cog.tif"


def _ensure_common_cli_paths() -> None:
    """Jupyter kernels often omit Homebrew /usr/local from PATH."""
    import os

    for extra in (
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/homebrew/sbin",
        "/usr/local/sbin",
    ):
        if Path(extra).is_dir() and extra not in os.environ.get("PATH", ""):
            os.environ["PATH"] = extra + os.pathsep + os.environ.get("PATH", "")


def resolve_aws_cli() -> str:
    _ensure_common_cli_paths()
    aws = shutil.which("aws")
    if not aws:
        for candidate in (Path("/usr/local/bin/aws"), Path("/opt/homebrew/bin/aws")):
            if candidate.is_file():
                return str(candidate)
        raise RuntimeError(
            "AWS CLI not found. Install awscli and configure credentials "
            "(aws configure or env vars). Ensure /usr/local/bin or "
            "/opt/homebrew/bin is on PATH for this kernel."
        )
    return aws


def require_aws_cli() -> str:
    return resolve_aws_cli()


def dataset_id_for_site(site_config: dict[str, Any]) -> str:
    """porto_alegre keeps legacy id; other cities use {site_slug}_heat_hazard."""
    slug = str(site_config.get("site_slug") or "")
    if slug == "porto_alegre":
        return "poa_heat_hazard"
    return f"{slug}_heat_hazard"


def hazard_s3_prefix(site_config: dict[str, Any]) -> str:
    base = str(site_config["s3_prefix"]).rstrip("/")
    return f"{base}/hazard"


def vector_s3_prefix(site_config: dict[str, Any]) -> str:
    base = str(site_config["s3_prefix"]).rstrip("/")
    return f"{base}/vector"


def public_url(key: str) -> str:
    return f"{S3_PUBLIC_BASE}/{key.lstrip('/')}"


def _s3_uri(key: str) -> str:
    return f"s3://{S3_BUCKET}/{key.lstrip('/')}"


def resolve_publish_paths(publish_dir: Path) -> dict[str, Path]:
    publish_dir = Path(publish_dir)
    return {
        "cog": publish_dir / COG_FILENAME,
        "tiles_visual": publish_dir / "tiles_visual",
        "tiles_values": publish_dir / "tiles_values",
    }


def validate_publish_dir(publish_dir: Path) -> dict[str, Path]:
    paths = resolve_publish_paths(publish_dir)
    if not paths["cog"].is_file():
        raise FileNotFoundError(
            f"Missing heat COG: {paths['cog']}. Run COG + Web Tiles cells first."
        )
    for name in ("tiles_visual", "tiles_values"):
        if not paths[name].is_dir():
            raise FileNotFoundError(
                f"Missing {name} dir: {paths[name]}. Run COG + Web Tiles cells first."
            )
    return paths


def expected_urls(site_config: dict[str, Any]) -> dict[str, str]:
    """Public HTTPS URLs for the hazard publish layout (no upload)."""
    prefix = hazard_s3_prefix(site_config)
    urls = {
        "cog": public_url(f"{prefix}/{COG_FILENAME}"),
        "tiles_visual": public_url(f"{prefix}/tiles_visual"),
        "tiles_values": public_url(f"{prefix}/tiles_values"),
        "visual_tiles_template": public_url(f"{prefix}/tiles_visual/{{z}}/{{x}}/{{y}}.png"),
        "value_tiles_template": public_url(f"{prefix}/tiles_values/{{z}}/{{x}}/{{y}}.png"),
    }
    bairro = site_config.get("bairro") or {}
    if bairro.get("enabled"):
        gpkg_name = Path(str(site_config["outputs"]["heat_hazard_vector"])).name
        urls["bairro_gpkg"] = public_url(f"{vector_s3_prefix(site_config)}/{gpkg_name}")
    return urls


def upload_heat_hazard_to_s3(
    site_config: dict[str, Any],
    publish_dir: Path,
    *,
    upload: bool = True,
    gpkg_path: Path | None = None,
) -> dict[str, str]:
    """Validate local heat publish artifacts; optionally upload to S3.

    Returns public HTTPS URLs (expected layout even when upload=False).
    """
    paths = validate_publish_dir(publish_dir)
    urls = expected_urls(site_config)
    prefix = hazard_s3_prefix(site_config)

    if not upload:
        print(f"Skipping S3 upload (upload=False). Expected prefix: s3://{S3_BUCKET}/{prefix}/")
        for k, v in urls.items():
            print(f"  {k}: {v}")
        return urls

    aws = require_aws_cli()

    cog_key = f"{prefix}/{COG_FILENAME}"
    subprocess.run(
        [aws, "s3", "cp", str(paths["cog"]), _s3_uri(cog_key)],
        check=True,
    )
    print(f"Uploaded COG → {urls['cog']}")

    for tiles_name in ("tiles_visual", "tiles_values"):
        tiles_key = f"{prefix}/{tiles_name}/"
        subprocess.run(
            [
                aws,
                "s3",
                "cp",
                str(paths[tiles_name]),
                _s3_uri(tiles_key),
                "--recursive",
            ],
            check=True,
        )
        print(f"Uploaded {tiles_name} → {urls[tiles_name]}")

    bairro = site_config.get("bairro") or {}
    if bairro.get("enabled") and "bairro_gpkg" in urls:
        local_gpkg = Path(gpkg_path) if gpkg_path else None
        if local_gpkg is None:
            # Prefer OUTPUT_DIR-style path if caller did not pass one
            local_gpkg = Path(site_config["paths_abs"]["data_output"]) / site_config["outputs"][
                "heat_hazard_vector"
            ]
        if local_gpkg.is_file():
            gpkg_key = f"{vector_s3_prefix(site_config)}/{local_gpkg.name}"
            subprocess.run(
                [aws, "s3", "cp", str(local_gpkg), _s3_uri(gpkg_key)],
                check=True,
            )
            print(f"Uploaded bairro GPKG → {urls['bairro_gpkg']}")
        else:
            print(f"Skipping bairro GPKG upload (missing: {local_gpkg})")

    return urls


def build_catalog_entry(
    site_config: dict[str, Any],
    urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a datasets.yaml entry mirroring poa_heat_hazard."""
    urls = urls or expected_urls(site_config)
    display = str(site_config.get("display_name") or site_config.get("site_slug"))
    dataset_id = dataset_id_for_site(site_config)
    short = "POA" if dataset_id == "poa_heat_hazard" else display
    season = str(site_config.get("season_label") or site_config.get("season") or "").upper()
    start_year = site_config.get("start_year", "")
    end_year = site_config.get("end_year", "")
    year_span = f"{start_year}–{end_year}" if start_year and end_year else "configured years"

    download: dict[str, Any] = {"cog_url": urls["cog"]}
    if urls.get("bairro_gpkg"):
        download["bairro_gpkg_url"] = urls["bairro_gpkg"]

    return {
        "dataset_id": dataset_id,
        "dataset_name": f"Heat Hazard Score ({short})",
        "publisher": "Open Earth Foundation (derived processing)",
        "license": "CC BY 4.0",
        "resolution": "~250m",
        "crs": "EPSG:4326",
        "access_type": "internal_storage",
        "source_url": "https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC08_C02_T1_L2",
        "dataset_type": "heat",
        "type": "numeric_raster",
        "data_quality": {
            "temporal_coverage": f"{season} {year_span} (Landsat 8, MODIS MOD11A2)".strip(),
            "accuracy": (
                "Arithmetic mean of normalized LST layers: Landsat 8 P90, "
                "MODIS LST daytime P90, MODIS LST nighttime P90 "
                "(ERA5 optional per site config)"
            ),
            "limitations": (
                "LST is a surface temperature proxy, not air temperature; "
                "values reflect land cover and albedo. Season-specific composite; "
                "cloud masking may reduce coverage in some years."
            ),
        },
        "value_encoding": {
            "type": "rgb_24bit_scaled",
            "scale": 10000,
            "offset": 0.0,
            "unit": "score",
            "decode_formula": "value = (R + 256*G + 65536*B) / scale",
        },
        "assets": {
            "visual_tiles": {
                "url_template": urls["visual_tiles_template"],
            },
            "value_tiles": {
                "url_template": urls["value_tiles_template"],
            },
            "download": download,
            "metadata": {
                "url": [],
            },
        },
        "description": (
            f"OEF heat hazard susceptibility index (0–1) for {display}. Ensemble of Landsat 8 LST P90, "
            "MODIS MOD11A2 daytime LST P90, and MODIS MOD11A2 nighttime LST P90 on a common ~250 m grid. "
            "Arithmetic mean of normalized layers. Methodology in `models/heat_hazard/model_card.md`; "
            "defaults in `models/heat_hazard/config.yaml`; score notebook "
            "`transformation/heat_hazard/heat_hazard_score.ipynb`."
        ),
    }


def _format_catalog_block(entry: dict[str, Any]) -> str:
    """Render one datasets.yaml list item with the repo's indent style."""
    dq = entry["data_quality"]
    ve = entry["value_encoding"]
    assets = entry["assets"]
    desc = str(entry["description"]).strip()
    desc_lines = []
    words = desc.split()
    line = ""
    for w in words:
        trial = f"{line} {w}".strip()
        if len(trial) > 100 and line:
            desc_lines.append(line)
            line = w
        else:
            line = trial
    if line:
        desc_lines.append(line)
    desc_body = "\n".join(f"      {ln}" for ln in desc_lines)

    download = assets["download"]
    download_lines = [f"        cog_url: {download['cog_url']}"]
    if download.get("bairro_gpkg_url"):
        download_lines.append(f"        bairro_gpkg_url: {download['bairro_gpkg_url']}")
    download_block = "\n".join(download_lines)

    return (
        f"  - dataset_id: {entry['dataset_id']}\n"
        f"    dataset_name: {entry['dataset_name']}\n"
        f"    publisher: {entry['publisher']}\n"
        f"    license: {entry['license']}\n"
        f"    resolution: {entry['resolution']}\n"
        f"    crs: {entry['crs']}\n"
        f"    access_type: {entry['access_type']}\n"
        f"    source_url: {entry['source_url']}\n"
        f"    dataset_type: {entry['dataset_type']}\n"
        f"    type: {entry['type']}\n"
        f"    data_quality:\n"
        f"      temporal_coverage: \"{dq['temporal_coverage']}\"\n"
        f"      accuracy: \"{dq['accuracy']}\"\n"
        f"      limitations: \"{dq['limitations']}\"\n"
        f"    value_encoding:\n"
        f"      type: {ve['type']}\n"
        f"      scale: {ve['scale']}\n"
        f"      offset: {ve['offset']}\n"
        f"      unit: \"{ve['unit']}\"\n"
        f"      decode_formula: \"{ve['decode_formula']}\"\n"
        f"    assets:\n"
        f"      visual_tiles:\n"
        f"        url_template: {assets['visual_tiles']['url_template']}\n"
        f"      value_tiles:\n"
        f"        url_template: {assets['value_tiles']['url_template']}\n"
        f"      download:\n"
        f"{download_block}\n"
        f"      metadata:\n"
        f"        url: []\n"
        f"    description: >\n"
        f"{desc_body}\n"
    )


def _find_dataset_span(text: str, dataset_id: str) -> tuple[int, int] | None:
    """Return [start, end) of the list item for dataset_id, or None."""
    pattern = re.compile(
        rf"(^|\n)(  - dataset_id: {re.escape(dataset_id)}\n)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return None
    start = match.start(2)
    next_match = re.search(r"\n  - dataset_id: ", text[match.end() :])
    if next_match:
        end = match.end() + next_match.start() + 1
        return start, end
    end = len(text.rstrip("\n")) + 1
    return start, end


def upsert_datasets_yaml(
    entry: dict[str, Any],
    catalog_path: Path,
    *,
    dry_run: bool = True,
) -> str:
    """Insert or replace a dataset block in catalog/datasets.yaml."""
    catalog_path = Path(catalog_path)
    block = _format_catalog_block(entry)
    dataset_id = entry["dataset_id"]

    if dry_run:
        print(f"[dry-run] catalog upsert for {dataset_id} → {catalog_path}")
        print(block)
        return block

    if not catalog_path.is_file():
        raise FileNotFoundError(f"Catalog not found: {catalog_path}")

    text = catalog_path.read_text(encoding="utf-8")
    if not text.startswith("datasets:"):
        raise ValueError(f"Unexpected catalog format (missing datasets:): {catalog_path}")

    span = _find_dataset_span(text, dataset_id)
    if span is None:
        body = text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
        action = "appended"
    else:
        start, end = span
        replacement = block.rstrip("\n") + "\n"
        body = text[:start] + replacement + text[end:].lstrip("\n")
        if not body.endswith("\n"):
            body += "\n"
        action = "replaced"

    catalog_path.write_text(body, encoding="utf-8")
    print(f"Catalog {action}: {dataset_id} in {catalog_path}")
    return block


def find_catalog_path(start: Path | None = None) -> Path:
    """Walk parents for geospatial-data/catalog/datasets.yaml."""
    start = (start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        candidate = path / "catalog" / "datasets.yaml"
        if candidate.is_file():
            return candidate
        nested = path / "geospatial-data" / "catalog" / "datasets.yaml"
        if nested.is_file():
            return nested
    raise FileNotFoundError(
        "Could not locate catalog/datasets.yaml from "
        f"{start}. Pass catalog_path explicitly."
    )
