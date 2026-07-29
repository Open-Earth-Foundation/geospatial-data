#!/usr/bin/env python3
"""Build flood hazard IDW COG + XYZ tiles, upload to S3, upsert catalog.

Pipeline (after ``compute_flood_hazard.py``):

  1. COG + colorized visual tiles + RGB value tiles (IDW score)
  2. Optional upload to ``s3://geo-test-api/{s3_prefix}/hazard/``
  3. Optional upsert of ``{site}_flood_hazard`` in ``catalog/datasets.yaml``

Example:
  python transformation/flood_hazard/flood_hazard_publish.py --site plymouth
  python transformation/flood_hazard/flood_hazard_publish.py --site plymouth --upload --write-catalog
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

FLOOD_HAZARD_ROOT = Path(__file__).resolve().parent
if str(FLOOD_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(FLOOD_HAZARD_ROOT))

from site_config import load_site_config  # noqa: E402

S3_BUCKET = "geo-test-api"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"
VALUE_SCALE = 10000
COG_FILENAME = "flood_hazard_score_idw_cog.tif"
COLORIZED_FILENAME = "flood_hazard_score_idw_colorized.tif"
VALUE_RGB_FILENAME = "flood_hazard_score_idw_value_encoded_rgb.tif"
PUBLISH_SUBDIR = "flood_hazard_score_idw"
COLORS_TXT = "flood_hazard_colors.txt"


def _ensure_common_cli_paths() -> None:
    """Jupyter kernels often omit Homebrew /usr/local from PATH."""
    for extra in (
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/homebrew/opt/gdal/bin",
        "/usr/local/opt/gdal/bin",
        "/opt/homebrew/sbin",
        "/usr/local/sbin",
    ):
        if Path(extra).is_dir() and extra not in os.environ.get("PATH", ""):
            os.environ["PATH"] = extra + os.pathsep + os.environ.get("PATH", "")


def require_cli(command: str) -> str:
    _ensure_common_cli_paths()
    path = shutil.which(command)
    if path:
        return path
    raise RuntimeError(
        f"{command} not found. Install GDAL (`brew install gdal`) or add it to PATH.\n"
        f"Current PATH: {os.environ.get('PATH', '')}"
    )


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


def gdal2tiles_python(gdal2tiles_path: str) -> str:
    with open(gdal2tiles_path, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline().strip()
    if first_line.startswith("#!"):
        shebang_parts = first_line[2:].split()
        if shebang_parts:
            if shebang_parts[0].endswith("env") and len(shebang_parts) > 1:
                resolved = shutil.which(shebang_parts[1])
                if resolved:
                    return resolved
            return shebang_parts[0]
    return shutil.which("python3") or shutil.which("python") or "python3"


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


def normalize_publish_cfg(site_config: dict[str, Any]) -> dict[str, Any]:
    publish = site_config.get("publish")
    if not isinstance(publish, dict):
        zoom = site_config.get("tile_zoom") or "8-15"
        site_config["publish"] = {"tile_zoom": str(zoom)}
    else:
        publish.setdefault("tile_zoom", site_config.get("tile_zoom") or "8-15")
    return site_config["publish"]


def resolve_score_tif(site_config: dict[str, Any]) -> Path:
    out_dir = Path(site_config["paths_abs"]["data_output"])
    name = site_config["outputs"]["flood_hazard_score_idw"]
    path = out_dir / name
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing IDW score GeoTIFF: {path}. "
            f"Run compute_flood_hazard.py --site {site_config.get('site_slug')} first."
        )
    return path


def publish_dir_for(site_config: dict[str, Any]) -> Path:
    return Path(site_config["paths_abs"]["out"]) / PUBLISH_SUBDIR


def resolve_publish_paths(publish_dir: Path) -> dict[str, Path]:
    publish_dir = Path(publish_dir)
    return {
        "cog": publish_dir / COG_FILENAME,
        "colorized": publish_dir / COLORIZED_FILENAME,
        "value_rgb": publish_dir / VALUE_RGB_FILENAME,
        "tiles_visual": publish_dir / "tiles_visual",
        "tiles_values": publish_dir / "tiles_values",
    }


def validate_publish_dir(publish_dir: Path) -> dict[str, Path]:
    paths = resolve_publish_paths(publish_dir)
    if not paths["cog"].is_file():
        raise FileNotFoundError(
            f"Missing IDW COG: {paths['cog']}. Run with --build first."
        )
    for name in ("tiles_visual", "tiles_values"):
        if not paths[name].is_dir():
            raise FileNotFoundError(
                f"Missing {name} dir: {paths[name]}. Run with --build first."
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


def build_cog_and_tiles(
    *,
    in_tif: Path,
    publish_dir: Path,
    tile_zoom: str = "8-15",
    colors_txt: Path | None = None,
) -> dict[str, Path]:
    """Create COG + visual XYZ + value XYZ tiles (notebook Step 2b)."""
    colors = colors_txt or (FLOOD_HAZARD_ROOT / "styles" / COLORS_TXT)
    if not colors.is_file():
        raise FileNotFoundError(f"Missing color table: {colors}")

    gdal_translate = require_cli("gdal_translate")
    gdaldem = require_cli("gdaldem")
    gdal_calc = require_cli("gdal_calc.py")
    gdal2tiles = require_cli("gdal2tiles.py")
    gdal2tiles_py = gdal2tiles_python(gdal2tiles)
    subprocess.run([gdal2tiles_py, "-c", "import numpy"], check=True, capture_output=True)

    if publish_dir.exists():
        for child in ("tiles_visual", "tiles_values"):
            d = publish_dir / child
            if d.is_dir():
                shutil.rmtree(d)
    publish_dir.mkdir(parents=True, exist_ok=True)
    paths = resolve_publish_paths(publish_dir)

    subprocess.run(
        [
            gdal_translate,
            str(in_tif),
            str(paths["cog"]),
            "-of",
            "COG",
            "-ot",
            "Float32",
            "-co",
            "COMPRESS=DEFLATE",
            "-co",
            "RESAMPLING=NEAREST",
            "-co",
            "OVERVIEWS=AUTO",
        ],
        check=True,
    )
    print(f"Created COG: {paths['cog']}")

    subprocess.run(
        [
            gdaldem,
            "color-relief",
            str(paths["cog"]),
            str(colors),
            str(paths["colorized"]),
            "-alpha",
        ],
        check=True,
    )
    print(f"Created colorized: {paths['colorized']}")

    paths["tiles_visual"].mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            gdal2tiles,
            "-r",
            "near",
            "-z",
            tile_zoom,
            "--xyz",
            "-w",
            "none",
            str(paths["colorized"]),
            str(paths["tiles_visual"]),
        ],
        check=True,
    )
    print(f"Visual tiles: {paths['tiles_visual']}")

    base_expr = (
        "numpy.where(numpy.isnan(A), 0, "
        f"numpy.rint(numpy.clip(A,0,1)*{VALUE_SCALE}).astype(numpy.int64))"
    )
    subprocess.run(
        [
            gdal_calc,
            "-A",
            str(paths["cog"]),
            "--calc",
            f"bitwise_and({base_expr},255)",
            "--calc",
            f"bitwise_and(right_shift({base_expr},8),255)",
            "--calc",
            f"bitwise_and(right_shift({base_expr},16),255)",
            "--type",
            "Byte",
            "--NoDataValue",
            "0",
            "--overwrite",
            "--outfile",
            str(paths["value_rgb"]),
        ],
        check=True,
    )

    paths["tiles_values"].mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            gdal2tiles,
            "-r",
            "near",
            "-z",
            tile_zoom,
            "--xyz",
            "-w",
            "none",
            str(paths["value_rgb"]),
            str(paths["tiles_values"]),
        ],
        check=True,
    )
    print(f"Value tiles: {paths['tiles_values']}")
    print(f"Decode: score = (R + 256*G + 65536*B) / {VALUE_SCALE}")
    return paths


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
            "scale": VALUE_SCALE,
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
            "defaults in `models/flood_hazard/config.yaml`; score CLI "
            "`transformation/flood_hazard/compute_flood_hazard.py`."
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


def run_publish(
    site: str,
    *,
    build: bool = True,
    upload: bool = False,
    write_catalog: bool = False,
) -> dict[str, str]:
    site_config = load_site_config(site, FLOOD_HAZARD_ROOT)
    publish_cfg = normalize_publish_cfg(site_config)
    tile_zoom = str(publish_cfg.get("tile_zoom", "8-15"))
    publish_dir = publish_dir_for(site_config)

    if build:
        in_tif = resolve_score_tif(site_config)
        print(f"Building publish artifacts from {in_tif}")
        build_cog_and_tiles(
            in_tif=in_tif,
            publish_dir=publish_dir,
            tile_zoom=tile_zoom,
        )
    else:
        print(f"Skipping build; using existing artifacts in {publish_dir}")

    urls = upload_flood_hazard_to_s3(site_config, publish_dir, upload=upload)
    entry = build_catalog_entry(site_config, urls)
    catalog_path = find_catalog_path(FLOOD_HAZARD_ROOT)
    upsert_datasets_yaml(entry, catalog_path, dry_run=not write_catalog)
    print(f"UPLOAD={upload} | WRITE_CATALOG={write_catalog}")
    print(f"Publish dir: {publish_dir}")
    return urls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: FLOODS_SITE)")
    parser.add_argument(
        "--build",
        action="store_true",
        default=True,
        help="Build COG + tiles (default: True)",
    )
    parser.add_argument(
        "--no-build",
        action="store_false",
        dest="build",
        help="Skip COG/tiles build; upload/catalog existing out/",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload COG + tiles to S3",
    )
    parser.add_argument(
        "--write-catalog",
        action="store_true",
        help="Write catalog/datasets.yaml (default: dry-run print)",
    )
    args = parser.parse_args(argv)
    site = args.site or os.environ.get("FLOODS_SITE", "porto_alegre")
    try:
        run_publish(
            site,
            build=args.build,
            upload=args.upload,
            write_catalog=args.write_catalog,
        )
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
