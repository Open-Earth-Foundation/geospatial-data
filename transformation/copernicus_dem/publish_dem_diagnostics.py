#!/usr/bin/env python3
"""Publish DEM diagnostic rasters (COG + tiles + catalog) for NBS flood screening (N8).

Builds web-map assets for relative elevation, depression mask, and depression depth
from ``compute_dem_diagnostics.py`` outputs in ``flood_hazard/sites/<site>/data/output/``.

Example (local build):
  python transformation/copernicus_dem/publish_dem_diagnostics.py --site richfield --build

Example (upload + catalog):
  python transformation/copernicus_dem/publish_dem_diagnostics.py \\
    --site richfield --build --upload --write-catalog

Example (Minnesota cohort):
  python transformation/copernicus_dem/publish_dem_diagnostics.py \\
    --country "United States" --build --continue-on-error
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

COPERNICUS_DEM_ROOT = Path(__file__).resolve().parent
FLOOD_HAZARD_ROOT = COPERNICUS_DEM_ROOT.parent / "flood_hazard"
NBS_ROOT = COPERNICUS_DEM_ROOT.parent / "nbs_screening"

sys.path.insert(0, str(FLOOD_HAZARD_ROOT))

from input_common import load_flood_site  # noqa: E402

try:
    import rasterio
except ImportError:  # pragma: no cover
    rasterio = None

S3_BUCKET = "geo-test-api"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"
RELEASE_PREFIX = "copernicus_dem/release/v1/2024"
DEFAULT_TILE_ZOOM = "8-15"
COPERNICUS_SOURCE_URL = (
    "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_DEM_GLO30"
)
DEFAULT_SITE = "porto_alegre"

LayerKey = Literal["relative_elevation", "depression_mask", "depression_depth"]


@dataclass(frozen=True)
class LayerSpec:
    key: LayerKey
    colors_file: str
    categorical: bool
    dataset_suffix: str
    publish_folder: str
    dataset_name: str
    raster_type: str
    accuracy: str
    limitations: str
    description_tail: str


LAYER_SPECS: tuple[LayerSpec, ...] = (
    LayerSpec(
        key="relative_elevation",
        colors_file="relative_elevation_30m_colors.txt",
        categorical=False,
        dataset_suffix="relative_elevation",
        publish_folder="relative_elevation_30m",
        dataset_name="Relative Elevation / Low-Lying Index",
        raster_type="numeric_raster",
        accuracy="Min-max normalized elevation within city AOI (1 = lowest relative elevation)",
        limitations="Screening proxy for low-lying accumulation; not hydraulic modeling or flood depth",
        description_tail="Relative low-lying index (0–1) derived from Copernicus GLO-30 DEM.",
    ),
    LayerSpec(
        key="depression_mask",
        colors_file="depression_mask_30m_colors.txt",
        categorical=True,
        dataset_suffix="depression_mask",
        publish_folder="depression_mask_30m",
        dataset_name="Topographic Depression Sink Mask",
        raster_type="categorical_raster",
        accuracy="D8 local depression mask (sink with no outlet) from priority-flood fill",
        limitations="Topographic sink only; does not account for drainage infrastructure or soil infiltration",
        description_tail="Binary topographic depression mask derived from Copernicus GLO-30 DEM using D8 flow routing and priority-flood fill.",
    ),
    LayerSpec(
        key="depression_depth",
        colors_file="depression_depth_30m_colors.txt",
        categorical=False,
        dataset_suffix="depression_depth",
        publish_folder="depression_depth_30m",
        dataset_name="Topographic Depression Depth",
        raster_type="numeric_raster",
        accuracy="Depression depth (m) = filled DEM elevation minus original DEM elevation",
        limitations="Hydrologically naive fill; urban drainage networks not represented",
        description_tail="Depression depth in meters derived from Copernicus GLO-30 DEM (filled surface minus original elevation).",
    ),
)


def _nbs_site_config():
    import importlib.util

    spec = importlib.util.spec_from_file_location("nbs_site_config", NBS_ROOT / "site_config.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load NBS site_config from {NBS_ROOT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ensure_common_cli_paths() -> None:
    for extra in (
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/homebrew/opt/gdal/bin",
        "/usr/local/opt/gdal/bin",
    ):
        if Path(extra).is_dir() and extra not in os.environ.get("PATH", ""):
            os.environ["PATH"] = extra + os.pathsep + os.environ.get("PATH", "")


def require_cli(command: str) -> str:
    _ensure_common_cli_paths()
    path = shutil.which(command)
    if path:
        return path
    raise RuntimeError(f"{command} not found. Install GDAL (`brew install gdal`) or add it to PATH.")


def resolve_aws_cli() -> str:
    _ensure_common_cli_paths()
    aws = shutil.which("aws")
    if not aws:
        raise RuntimeError("AWS CLI not found. Install awscli and configure credentials.")
    return aws


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


def public_url(key: str) -> str:
    return f"{S3_PUBLIC_BASE}/{key.lstrip('/')}"


def _s3_uri(key: str) -> str:
    return f"s3://{S3_BUCKET}/{key.lstrip('/')}"


def catalog_prefix(site_slug: str) -> str:
    return "poa" if site_slug == DEFAULT_SITE else site_slug


def dataset_id_for_layer(site_slug: str, spec: LayerSpec) -> str:
    return f"{catalog_prefix(site_slug)}_{spec.dataset_suffix}"


def s3_prefix_for_layer(site_slug: str, spec: LayerSpec) -> str:
    return f"{RELEASE_PREFIX}/{site_slug}/{spec.publish_folder}"


def resolve_input_tif(cfg: dict[str, Any], spec: LayerSpec) -> Path:
    output_dir = Path(cfg["paths_abs"]["data_output"])
    layers = cfg.get("layers") or {}
    path = output_dir / str(layers[spec.key])
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {spec.key} raster: {path}. "
            f"Run: python transformation/copernicus_dem/compute_dem_diagnostics.py --site {cfg['site_slug']}"
        )
    return path


def resolve_publish_dir(cfg: dict[str, Any], stem: str) -> Path:
    return Path(cfg["paths_abs"]["out"]) / stem


def resolve_styles_dir(cfg: dict[str, Any]) -> Path:
    return Path(cfg["paths_abs"]["styles"])


def build_dem_layer(
    *,
    in_tif: Path,
    publish_dir: Path,
    colors_txt: Path,
    stem: str,
    categorical: bool,
    tile_zoom: str = DEFAULT_TILE_ZOOM,
) -> dict[str, Path]:
    if rasterio is None:
        raise ImportError("rasterio required for DEM publish")

    gdal_translate = require_cli("gdal_translate")
    gdaldem = require_cli("gdaldem")
    gdal2tiles = require_cli("gdal2tiles.py")
    gdal2tiles_py = gdal2tiles_python(gdal2tiles)
    subprocess.run([gdal2tiles_py, "-c", "import numpy"], check=True, capture_output=True)

    publish_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "cog": publish_dir / f"{stem}_cog.tif",
        "colorized": publish_dir / f"{stem}_colorized.tif",
        "value_rgb": publish_dir / f"{stem}_value_encoded_rgb.tif",
        "value_decode": publish_dir / f"{stem}_value_tiles_decode.txt",
        "tiles_visual": publish_dir / "tiles_visual",
        "tiles_values": publish_dir / "tiles_values",
    }

    subprocess.run(
        [
            gdal_translate,
            str(in_tif),
            str(paths["cog"]),
            "-of",
            "COG",
            "-co",
            "COMPRESS=DEFLATE",
            "-co",
            "PREDICTOR=2",
        ],
        check=True,
    )
    print(f"Created COG: {paths['cog']}")

    subprocess.run(
        [
            gdaldem,
            "color-relief",
            str(in_tif),
            str(colors_txt),
            str(paths["colorized"]),
            "-alpha",
            "-co",
            "COMPRESS=LZW",
        ],
        check=True,
    )
    print(f"Created colorized raster: {paths['colorized']}")

    if paths["tiles_visual"].exists():
        shutil.rmtree(paths["tiles_visual"])
    subprocess.run(
        [
            gdal2tiles,
            "--tiledriver=PNG",
            "--webviewer=none",
            f"--zoom={tile_zoom}",
            "--resampling=near",
            "--xyz",
            str(paths["colorized"]),
            str(paths["tiles_visual"]),
        ],
        check=True,
    )
    print(f"Visual tiles: {paths['tiles_visual']}")

    with rasterio.open(in_tif) as src:
        arr = src.read(1).astype(np.float32)
        profile = src.profile.copy()

    if categorical:
        encoded = np.clip(np.nan_to_num(arr, nan=0.0), 0, 65535).astype(np.uint16)
        decode = "encoded_int = R + 256*G\nvalue = encoded_int\n"
    else:
        encoded = np.clip(np.rint(np.nan_to_num(arr, nan=0.0) * 10000), 0, 65535).astype(np.uint16)
        decode = "encoded_int = R + 256*G\nvalue = encoded_int / 10000.0\n"

    r = (encoded & 0xFF).astype(np.uint8)
    g = ((encoded >> 8) & 0xFF).astype(np.uint8)
    b = np.zeros_like(r)
    profile.update(count=3, dtype="uint8", nodata=None, compress="lzw")
    with rasterio.open(paths["value_rgb"], "w", **profile) as dst:
        dst.write(r, 1)
        dst.write(g, 2)
        dst.write(b, 3)

    if paths["tiles_values"].exists():
        shutil.rmtree(paths["tiles_values"])
    subprocess.run(
        [
            gdal2tiles,
            "--tiledriver=PNG",
            "--webviewer=none",
            f"--zoom={tile_zoom}",
            "--resampling=near",
            "--xyz",
            str(paths["value_rgb"]),
            str(paths["tiles_values"]),
        ],
        check=True,
    )
    paths["value_decode"].write_text(decode, encoding="utf-8")
    print(f"Value tiles: {paths['tiles_values']}")
    return paths


def expected_urls(site_slug: str, spec: LayerSpec, stem: str) -> dict[str, str]:
    prefix = s3_prefix_for_layer(site_slug, spec)
    return {
        "cog": public_url(f"{prefix}/{stem}_cog.tif"),
        "tiles_visual": public_url(f"{prefix}/tiles_visual"),
        "tiles_values": public_url(f"{prefix}/tiles_values"),
        "visual_tiles_template": public_url(f"{prefix}/tiles_visual/{{z}}/{{x}}/{{y}}.png"),
        "value_tiles_template": public_url(f"{prefix}/tiles_values/{{z}}/{{x}}/{{y}}.png"),
    }


def upload_dem_layer(
    site_slug: str,
    spec: LayerSpec,
    *,
    publish_dir: Path,
    stem: str,
    upload: bool,
) -> dict[str, str]:
    cog = publish_dir / f"{stem}_cog.tif"
    tiles_visual = publish_dir / "tiles_visual"
    tiles_values = publish_dir / "tiles_values"
    if not cog.is_file():
        raise FileNotFoundError(f"Missing COG: {cog}. Run with --build first.")
    if not tiles_visual.is_dir() or not tiles_values.is_dir():
        raise FileNotFoundError(f"Missing tiles under {publish_dir}. Run with --build first.")

    urls = expected_urls(site_slug, spec, stem)
    prefix = s3_prefix_for_layer(site_slug, spec)
    if not upload:
        print(f"Skipping S3 upload (upload=False). Expected prefix: s3://{S3_BUCKET}/{prefix}/")
        return urls

    aws = resolve_aws_cli()
    subprocess.run([aws, "s3", "cp", str(cog), _s3_uri(f"{prefix}/{stem}_cog.tif")], check=True)
    print(f"Uploaded COG → {urls['cog']}")
    for tiles_name in ("tiles_visual", "tiles_values"):
        subprocess.run(
            [aws, "s3", "cp", str(publish_dir / tiles_name), _s3_uri(f"{prefix}/{tiles_name}/"), "--recursive"],
            check=True,
        )
        print(f"Uploaded {tiles_name} → {urls[tiles_name]}")
    return urls


def build_catalog_entry(cfg: dict[str, Any], spec: LayerSpec, urls: dict[str, str]) -> dict[str, Any]:
    site_slug = str(cfg["site_slug"])
    display = str(cfg.get("display_name") or site_slug)
    short = "POA" if site_slug == DEFAULT_SITE else display
    dataset_id = dataset_id_for_layer(site_slug, spec)

    entry: dict[str, Any] = {
        "dataset_id": dataset_id,
        "dataset_name": f"{spec.dataset_name} ({short})",
        "publisher": "Open Earth Foundation (derived processing)",
        "license": "Copernicus open data license",
        "resolution": "30m",
        "crs": "EPSG:4326",
        "access_type": "internal_storage",
        "source_url": COPERNICUS_SOURCE_URL,
        "dataset_type": "elevation",
        "type": spec.raster_type,
        "data_quality": {
            "temporal_coverage": "Static (derived from Copernicus GLO-30 DEM)",
            "accuracy": spec.accuracy,
            "limitations": spec.limitations,
        },
        "assets": {
            "visual_tiles": {"url_template": urls["visual_tiles_template"]},
            "value_tiles": {"url_template": urls["value_tiles_template"]},
            "download": {"cog_url": urls["cog"]},
            "metadata": {"url": []},
        },
        "description": (
            f"{spec.description_tail} Diagnostic layer for flood NBS site screening in {display}. "
            "Local exports land under `transformation/flood_hazard/sites/{city}/data/output/`. "
            "Processed by `transformation/copernicus_dem/compute_dem_diagnostics.py` and "
            "`transformation/copernicus_dem/publish_dem_diagnostics.py`."
        ),
    }

    if spec.categorical:
        entry["value_encoding"] = {
            "type": "class_lookup",
            "classes": {
                0: {"name": "Not a depression", "color": "#FFFFFF"},
                1: {"name": "Depression sink", "color": "#2166AC"},
            },
        }
    else:
        unit = "score" if spec.key == "relative_elevation" else "m"
        entry["value_encoding"] = {
            "type": "single_channel",
            "scale": 1.0,
            "offset": 0.0,
            "unit": unit,
            "decode_formula": "value = R",
        }
    return entry


def _format_catalog_block(entry: dict[str, Any]) -> str:
    dq = entry["data_quality"]
    ve = entry["value_encoding"]
    assets = entry["assets"]
    desc = str(entry["description"]).strip()
    desc_lines: list[str] = []
    line = ""
    for word in desc.split():
        trial = f"{line} {word}".strip()
        if len(trial) > 100 and line:
            desc_lines.append(line)
            line = word
        else:
            line = trial
    if line:
        desc_lines.append(line)
    desc_body = "\n".join(f"      {ln}" for ln in desc_lines)

    if ve["type"] == "class_lookup":
        class_lines = []
        for code in sorted(ve["classes"]):
            cls = ve["classes"][code]
            class_lines.append(f'        {code}: {{ name: {cls["name"]}, color: "{cls["color"]}" }}')
        ve_block = (
            "    value_encoding:\n"
            "      type: class_lookup\n"
            "      classes:\n"
            + "\n".join(class_lines)
        )
    else:
        ve_block = (
            "    value_encoding:\n"
            f"      type: {ve['type']}\n"
            f"      scale: {ve['scale']}\n"
            f"      offset: {ve['offset']}\n"
            f"      unit: \"{ve['unit']}\"\n"
            f"      decode_formula: \"{ve['decode_formula']}\"\n"
        )

    download = assets["download"]
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
        f"{ve_block}"
        f"    assets:\n"
        f"      visual_tiles:\n"
        f"        url_template: {assets['visual_tiles']['url_template']}\n"
        f"      value_tiles:\n"
        f"        url_template: {assets['value_tiles']['url_template']}\n"
        f"      download:\n"
        f"        cog_url: {download['cog_url']}\n"
        f"      metadata:\n"
        f"        url: []\n"
        f"    description: >\n"
        f"{desc_body}\n"
    )


def _find_dataset_span(text: str, dataset_id: str) -> tuple[int, int] | None:
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
    return start, len(text.rstrip("\n")) + 1


def find_catalog_path() -> Path:
    for path in [COPERNICUS_DEM_ROOT, *COPERNICUS_DEM_ROOT.parents]:
        candidate = path / "catalog" / "datasets.yaml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Could not locate catalog/datasets.yaml")


def upsert_datasets_yaml(entry: dict[str, Any], catalog_path: Path, *, dry_run: bool = True) -> None:
    block = _format_catalog_block(entry)
    dataset_id = entry["dataset_id"]
    if dry_run:
        print(f"[dry-run] catalog upsert for {dataset_id} → {catalog_path}")
        print(block)
        return

    text = catalog_path.read_text(encoding="utf-8")
    span = _find_dataset_span(text, dataset_id)
    if span is None:
        body = text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
        action = "appended"
    else:
        start, end = span
        body = text[:start] + block.rstrip("\n") + "\n" + text[end:].lstrip("\n")
        action = "replaced"
    catalog_path.write_text(body, encoding="utf-8")
    print(f"Catalog {action}: {dataset_id} in {catalog_path}")


def run_publish_site(
    site: str,
    *,
    build: bool = True,
    upload: bool = False,
    write_catalog: bool = False,
    tile_zoom: str = DEFAULT_TILE_ZOOM,
    layers: tuple[LayerKey, ...] | None = None,
) -> dict[str, dict[str, str]]:
    cfg = load_flood_site(site)
    site_slug = str(cfg["site_slug"])
    display = str(cfg.get("display_name") or site_slug)
    styles_dir = resolve_styles_dir(cfg)
    selected = [spec for spec in LAYER_SPECS if layers is None or spec.key in layers]
    catalog_path = find_catalog_path()
    urls_by_layer: dict[str, dict[str, str]] = {}

    print(f"Publishing DEM diagnostics for {display} ({site_slug})")
    for spec in selected:
        in_tif = resolve_input_tif(cfg, spec)
        stem = in_tif.stem
        publish_dir = resolve_publish_dir(cfg, stem)
        colors_txt = styles_dir / spec.colors_file
        if not colors_txt.is_file():
            raise FileNotFoundError(f"Missing colors file: {colors_txt}")

        print(f"\n--- {spec.key} ---")
        print(f"  input: {in_tif}")
        print(f"  publish dir: {publish_dir}")

        if build:
            build_dem_layer(
                in_tif=in_tif,
                publish_dir=publish_dir,
                colors_txt=colors_txt,
                stem=stem,
                categorical=spec.categorical,
                tile_zoom=tile_zoom,
            )

        urls = upload_dem_layer(
            site_slug,
            spec,
            publish_dir=publish_dir,
            stem=stem,
            upload=upload,
        )
        urls_by_layer[spec.key] = urls
        entry = build_catalog_entry(cfg, spec, urls)
        upsert_datasets_yaml(entry, catalog_path, dry_run=not write_catalog)

    print(f"\nUPLOAD={upload} | WRITE_CATALOG={write_catalog} | site={site_slug}")
    return urls_by_layer


def _resolve_sites(args: argparse.Namespace) -> list[str]:
    nbs_sc = _nbs_site_config()
    resolve_site_slugs = nbs_sc.resolve_site_slugs
    exclude: list[str] = []
    for item in args.exclude:
        exclude.extend(s.strip() for s in item.split(",") if s.strip())
    args.exclude = exclude

    selection_flags = sum(
        bool(x) for x in (args.site, args.sites, args.all_configured, args.country)
    )
    if selection_flags > 1:
        raise ValueError("Use only one of --site, --sites, --all-configured, --country")

    if args.all_configured:
        return resolve_site_slugs(all_configured=True, exclude=tuple(exclude))
    if args.country:
        return resolve_site_slugs(country=args.country, exclude=tuple(exclude))
    if args.sites:
        return resolve_site_slugs(sites_csv=args.sites, exclude=tuple(exclude))
    if args.site:
        return resolve_site_slugs(site=args.site, exclude=tuple(exclude))
    return resolve_site_slugs(site="richfield", exclude=tuple(exclude))


def main(argv: list[str] | None = None) -> int:
    if rasterio is None:
        print("ERROR: rasterio required", file=sys.stderr)
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="Single city slug")
    parser.add_argument("--sites", help="Comma-separated city slugs")
    parser.add_argument("--all-configured", action="store_true")
    parser.add_argument("--country", help='Filter by NBS site YAML country (e.g. "United States")')
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument(
        "--layers",
        help="Comma-separated subset: relative_elevation,depression_mask,depression_depth",
    )
    parser.add_argument("--build", action="store_true", default=True)
    parser.add_argument("--no-build", action="store_false", dest="build")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--write-catalog", action="store_true")
    parser.add_argument("--tile-zoom", default=DEFAULT_TILE_ZOOM)
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args(argv)

    selection_flags = sum(
        bool(x) for x in (args.site, args.sites, args.all_configured, args.country)
    )
    if selection_flags > 1:
        parser.error("Use only one of --site, --sites, --all-configured, --country")

    layer_filter: tuple[LayerKey, ...] | None = None
    if args.layers:
        layer_filter = tuple(part.strip() for part in args.layers.split(",") if part.strip())  # type: ignore[assignment]

    try:
        sites = _resolve_sites(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not sites:
        print("ERROR: no sites selected.", file=sys.stderr)
        return 1

    print(f"Sites ({len(sites)}): {', '.join(sites)}")
    failures = 0
    for i, site in enumerate(sites, start=1):
        print(f"\n[{i}/{len(sites)}] {site}")
        try:
            run_publish_site(
                site,
                build=args.build,
                upload=args.upload,
                write_catalog=args.write_catalog,
                tile_zoom=args.tile_zoom,
                layers=layer_filter,
            )
        except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
            failures += 1
            print(f"ERROR: {exc}", file=sys.stderr)
            if not args.continue_on_error:
                return 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
