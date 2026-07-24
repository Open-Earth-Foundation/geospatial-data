"""Upload flood hazard IDW COG + XYZ tiles to S3 and upsert catalog/datasets.yaml."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

S3_BUCKET = "geo-test-api"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"
COG_FILENAME = "flood_hazard_score_idw_cog.tif"


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
    """porto_alegre keeps legacy id; other cities use {site_slug}_flood_hazard."""
    slug = str(site_config.get("site_slug") or "")
    if slug == "porto_alegre":
        return "poa_flood_hazard"
    return f"{slug}_flood_hazard"


def hazard_s3_prefix(site_config: dict[str, Any]) -> str:
    base = str(site_config["s3_prefix"]).rstrip("/")
    return f"{base}/hazard"


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
            f"Missing IDW COG: {paths['cog']}. Run Step 2b (IDW COG/tiles) first."
        )
    for name in ("tiles_visual", "tiles_values"):
        if not paths[name].is_dir():
            raise FileNotFoundError(
                f"Missing {name} dir: {paths[name]}. Run Step 2b (IDW COG/tiles) first."
            )
    return paths


def expected_urls(site_config: dict[str, Any]) -> dict[str, str]:
    """Public HTTPS URLs for the hazard publish layout (no upload)."""
    prefix = hazard_s3_prefix(site_config)
    return {
        "cog": public_url(f"{prefix}/{COG_FILENAME}"),
        "tiles_visual": public_url(f"{prefix}/tiles_visual"),
        "tiles_values": public_url(f"{prefix}/tiles_values"),
        "visual_tiles_template": public_url(f"{prefix}/tiles_visual/{{z}}/{{x}}/{{y}}.png"),
        "value_tiles_template": public_url(f"{prefix}/tiles_values/{{z}}/{{x}}/{{y}}.png"),
    }


def upload_flood_hazard_to_s3(
    site_config: dict[str, Any],
    publish_dir: Path,
    *,
    upload: bool = True,
) -> dict[str, str]:
    """Validate local IDW publish artifacts; optionally upload to S3.

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

    return urls


def build_catalog_entry(
    site_config: dict[str, Any],
    urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a datasets.yaml entry mirroring poa_flood_hazard."""
    urls = urls or expected_urls(site_config)
    display = str(site_config.get("display_name") or site_config.get("site_slug"))
    dataset_id = dataset_id_for_site(site_config)
    short = "POA" if dataset_id == "poa_flood_hazard" else display

    return {
        "dataset_id": dataset_id,
        "dataset_name": f"Flood Hazard Score ({short})",
        "publisher": "Open Earth Foundation (derived processing)",
        "license": "CC BY 4.0",
        "resolution": "~250m",
        "crs": "EPSG:3857",
        "access_type": "internal_storage",
        "source_url": "https://developers.google.com/earth-engine/datasets/catalog/JRC_GLOFLOR_V2_1",
        "dataset_type": "flood",
        "type": "numeric_raster",
        "data_quality": {
            "temporal_coverage": "Static hazard layers (JRC, Aqueduct, GFD, GFPLAIN ensemble)",
            "accuracy": (
                "Weighted ensemble of normalized global fluvial hazard products; "
                "partial coverage rule (>=3/4 layers + fluvial); IDW gap-fill"
            ),
            "limitations": (
                "Hazard screening only (no exposure/vulnerability); "
                "not event-specific observed depth"
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
            "download": {
                "cog_url": urls["cog"],
            },
            "metadata": {
                "url": [],
            },
        },
        "description": (
            f"OEF flood hazard susceptibility index (0–1) for {display}. Ensemble of JRC GLOFLO v2.1, "
            "Global Flood Database, WRI Aqueduct, and GFPLAIN250m on a common ~250 m grid "
            "(IDW distance-capped fill). Methodology in `models/flood_hazard/model_card.md`; "
            "defaults in `models/flood_hazard/config.yaml`; score notebook "
            "`transformation/flood_hazard/flood_hazard_score_v2.ipynb`."
        ),
    }


def _format_catalog_block(entry: dict[str, Any]) -> str:
    """Render one datasets.yaml list item with the repo's indent style."""
    dq = entry["data_quality"]
    ve = entry["value_encoding"]
    assets = entry["assets"]
    desc = str(entry["description"]).strip()
    # Fold long description like existing entries (single folded block).
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
        f"        cog_url: {assets['download']['cog_url']}\n"
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
    # Next sibling list item or EOF
    next_match = re.search(r"\n  - dataset_id: ", text[match.end() :])
    if next_match:
        end = match.end() + next_match.start() + 1  # keep leading newline of next item
        return start, end
    # Trim trailing newlines for clean append/replace
    end = len(text.rstrip("\n")) + 1
    return start, end


def upsert_datasets_yaml(
    entry: dict[str, Any],
    catalog_path: Path,
    *,
    dry_run: bool = True,
) -> str:
    """Insert or replace a dataset block in catalog/datasets.yaml.

    When dry_run=True, prints the block and does not write the file.
    Returns the formatted YAML block.
    """
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
        # Append before final newline
        body = text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
        action = "appended"
    else:
        start, end = span
        # Ensure we leave a blank line between entries when replacing mid-file
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
