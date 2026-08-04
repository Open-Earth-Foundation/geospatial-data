#!/usr/bin/env python3
"""Build flood mechanism COG + XYZ tiles, upload to S3, upsert catalog/datasets.yaml.

Pilot hazard: flood only (heat/landslide later).

Example (Richfield, build only):
  python transformation/nbs_screening/flood/publish_mechanism.py --site richfield --build

Example (upload + catalog):
  python transformation/nbs_screening/flood/publish_mechanism.py \\
    --site richfield --build --upload --write-catalog
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

FLOOD_ROOT = Path(__file__).resolve().parent
NBS_ROOT = FLOOD_ROOT.parent
for _path in (FLOOD_ROOT, NBS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from grid_screening import MECHANISM_RASTER_NODATA, flood_mechanism_layer_stem  # noqa: E402
from nbs_rules import FLOOD_MECHANISM_COLORS, FLOOD_MECHANISM_TYPE_CODES  # noqa: E402
from site_config import (  # noqa: E402
    DEFAULT_SITE,
    find_repo_root,
    load_site_config,
    resolve_site_output_dir,
    site_output_dir,
    site_publish_dir,
)

S3_BUCKET = "geo-test-api"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"
DEFAULT_TILE_ZOOM = "8-15"

FLOOD_MECHANISM_CLASS_NAMES: dict[int, str] = {
    0: "None",
    1: "Riverine",
    2: "Pluvial",
    3: "Low-lying",
    4: "Drainage constrained",
    5: "Mixed",
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _ensure_common_cli_paths() -> None:
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
            "(aws configure or env vars)."
        )
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


def dataset_id_for_site(site_slug: str) -> str:
    if site_slug == DEFAULT_SITE:
        return "poa_flood_mechanism_type"
    return f"{site_slug}_flood_mechanism_type"


def s3_prefix_for_site(site_slug: str) -> str:
    return (
        f"oef_calculation/release/v1/{site_slug}/climate_hazards/floods/flood_mechanism"
    )


def resolve_input_tif(site: str) -> Path:
    stem = flood_mechanism_layer_stem(site)
    path = resolve_site_output_dir(site, "flood") / f"{stem}.tif"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing filled mechanism raster: {path}. "
            f"Run: python transformation/nbs_screening/flood/compute_mechanism.py --site {site}"
        )
    return path


def resolve_geojson(site: str) -> Path:
    stem = flood_mechanism_layer_stem(site)
    path = resolve_site_output_dir(site, "flood") / f"{stem}.geojson"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing mechanism GeoJSON: {path}. "
            f"Run flood/compute_mechanism.py --site {site} first."
        )
    return path


def resolve_publish_paths(publish_dir: Path, slug: str) -> dict[str, Path]:
    publish_dir = Path(publish_dir)
    return {
        "colors": publish_dir / f"{slug}_colors.txt",
        "warped": publish_dir / f"{slug}_3857.tif",
        "cog": publish_dir / f"{slug}_cog.tif",
        "colorized": publish_dir / f"{slug}_colorized.tif",
        "value_rgb": publish_dir / f"{slug}_value_encoded_rgb.tif",
        "value_decode": publish_dir / f"{slug}_value_tiles_decode.txt",
        "tiles_visual": publish_dir / "tiles_visual",
        "tiles_values": publish_dir / "tiles_values",
    }


def write_flood_mechanism_colors(colors_path: Path) -> None:
    lines = [
        "# Dominant flood mechanism type. GDAL color-relief for visual tiles.",
        "# Codes from FLOOD_MECHANISM_TYPE_CODES in nbs_rules.py",
        f"# Raster nodata = {MECHANISM_RASTER_NODATA} (outside screened grid); code 0 = none",
        "nv 0 0 0 0",
    ]
    for mech_type, code in sorted(FLOOD_MECHANISM_TYPE_CODES.items(), key=lambda kv: kv[1]):
        r, g, b = _hex_to_rgb(FLOOD_MECHANISM_COLORS[mech_type])
        lines.append(f"{code} {r} {g} {b}")
    colors_path.parent.mkdir(parents=True, exist_ok=True)
    colors_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote colors: {colors_path}")


def build_flood_mechanism_cog_and_tiles(
    *,
    in_tif: Path,
    publish_dir: Path,
    slug: str,
    tile_zoom: str = DEFAULT_TILE_ZOOM,
) -> dict[str, Path]:
    """EPSG:3857 COG + visual/value XYZ tiles (notebook parity)."""
    gdalwarp = require_cli("gdalwarp")
    gdal_translate = require_cli("gdal_translate")
    gdaldem = require_cli("gdaldem")
    gdal_calc = require_cli("gdal_calc.py")
    gdal2tiles = require_cli("gdal2tiles.py")
    gdal2tiles_py = gdal2tiles_python(gdal2tiles)
    subprocess.run([gdal2tiles_py, "-c", "import numpy"], check=True, capture_output=True)

    publish_dir.mkdir(parents=True, exist_ok=True)
    paths = resolve_publish_paths(publish_dir, slug)
    write_flood_mechanism_colors(paths["colors"])

    subprocess.run(
        [
            gdalwarp,
            "-t_srs",
            "EPSG:3857",
            "-r",
            "near",
            "-overwrite",
            str(in_tif),
            str(paths["warped"]),
        ],
        check=True,
    )

    subprocess.run(
        [
            gdal_translate,
            str(paths["warped"]),
            str(paths["cog"]),
            "-of",
            "COG",
            "-ot",
            "Byte",
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
            "-nearest_color_entry",
            str(paths["cog"]),
            str(paths["colors"]),
            str(paths["colorized"]),
            "-alpha",
        ],
        check=True,
    )
    print(f"Created colorized raster: {paths['colorized']}")

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

    nodata = MECHANISM_RASTER_NODATA
    base_expr = (
        f"numpy.where((numpy.isnan(A)) | (A == {nodata}), 0, "
        "numpy.rint(numpy.clip(A,0,5)).astype(numpy.int64) + 1)"
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

    decode_lines = [
        f"Flood mechanism type value tiles ({slug})",
        "",
        f"Source raster: {in_tif}",
        f"COG (EPSG:3857): {paths['cog']}",
        f"Visual tiles: {paths['tiles_visual']}/{{z}}/{{x}}/{{y}}.png",
        f"Value tiles: {paths['tiles_values']}/{{z}}/{{x}}/{{y}}.png",
        "",
        "Value tile encoding (Terrain RGB style):",
        "encoded = R + 256 * G + 65536 * B",
        "if encoded == 0: nodata",
        "else: flood_mechanism_code = encoded - 1",
        "",
        "Mechanism codes:",
    ]
    decode_lines.extend(
        f"  {code}: {mech_type}"
        for mech_type, code in sorted(FLOOD_MECHANISM_TYPE_CODES.items(), key=lambda kv: kv[1])
    )
    paths["value_decode"].write_text("\n".join(decode_lines) + "\n", encoding="utf-8")
    print(f"Value decode notes: {paths['value_decode']}")
    return paths


def validate_publish_dir(publish_dir: Path, slug: str) -> dict[str, Path]:
    paths = resolve_publish_paths(publish_dir, slug)
    if not paths["cog"].is_file():
        raise FileNotFoundError(f"Missing COG: {paths['cog']}. Run with --build first.")
    for name in ("tiles_visual", "tiles_values"):
        if not paths[name].is_dir():
            raise FileNotFoundError(f"Missing {name} dir: {paths[name]}. Run with --build first.")
    return paths


def expected_urls(site_slug: str, slug: str) -> dict[str, str]:
    prefix = s3_prefix_for_site(site_slug)
    return {
        "cog": public_url(f"{prefix}/{slug}_cog.tif"),
        "geojson": public_url(f"{prefix}/{slug}.geojson"),
        "tiles_visual": public_url(f"{prefix}/tiles_visual"),
        "tiles_values": public_url(f"{prefix}/tiles_values"),
        "visual_tiles_template": public_url(f"{prefix}/tiles_visual/{{z}}/{{x}}/{{y}}.png"),
        "value_tiles_template": public_url(f"{prefix}/tiles_values/{{z}}/{{x}}/{{y}}.png"),
    }


def hazard_source_url(site_slug: str, catalog_path: Path | None = None) -> str:
    """Reference hazard COG URL for catalog ``source_url``."""
    hazard_id = "poa_flood_hazard" if site_slug == DEFAULT_SITE else f"{site_slug}_flood_hazard"
    default = public_url(
        f"oef_calculation/release/v1/{site_slug}/climate_hazards/floods/hazard/"
        "flood_hazard_score_idw_cog.tif"
    )
    if catalog_path is None:
        return default
    try:
        catalog_path = Path(catalog_path)
        text = catalog_path.read_text(encoding="utf-8")
        span = _find_dataset_span(text, hazard_id)
        if span is None:
            return default
        block = text[span[0] : span[1]]
        match = re.search(r"cog_url:\s*(\S+)", block)
        if match:
            return match.group(1)
    except OSError:
        pass
    return default


def upload_flood_mechanism_to_s3(
    site: str,
    *,
    publish_dir: Path | None = None,
    geojson_path: Path | None = None,
    upload: bool = True,
) -> dict[str, str]:
    site_cfg = load_site_config(site)
    site_slug = str(site_cfg["site_slug"])
    slug = flood_mechanism_layer_stem(site_slug)
    publish_dir = Path(publish_dir or site_publish_dir(site_slug, "flood"))
    geojson_path = Path(geojson_path or resolve_geojson(site_slug))
    paths = validate_publish_dir(publish_dir, slug)
    prefix = s3_prefix_for_site(site_slug)
    urls = expected_urls(site_slug, slug)

    if not upload:
        print(f"Skipping S3 upload (upload=False). Expected prefix: s3://{S3_BUCKET}/{prefix}/")
        for key, url in urls.items():
            if key.endswith("_template"):
                continue
            print(f"  {key}: {url}")
        return urls

    aws = resolve_aws_cli()
    cog_key = f"{prefix}/{slug}_cog.tif"
    subprocess.run([aws, "s3", "cp", str(paths["cog"]), _s3_uri(cog_key)], check=True)
    print(f"Uploaded COG → {urls['cog']}")

    for tiles_name in ("tiles_visual", "tiles_values"):
        tiles_key = f"{prefix}/{tiles_name}/"
        subprocess.run(
            [aws, "s3", "cp", str(paths[tiles_name]), _s3_uri(tiles_key), "--recursive"],
            check=True,
        )
        print(f"Uploaded {tiles_name} → {urls[tiles_name]}")

    geojson_key = f"{prefix}/{slug}.geojson"
    subprocess.run([aws, "s3", "cp", str(geojson_path), _s3_uri(geojson_key)], check=True)
    print(f"Uploaded GeoJSON → {urls['geojson']}")
    return urls


def build_catalog_entry(
    site_cfg: dict[str, Any],
    urls: dict[str, str],
    *,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    site_slug = str(site_cfg["site_slug"])
    display = str(site_cfg.get("display_name") or site_slug)
    short = "POA" if site_slug == DEFAULT_SITE else display
    dataset_id = dataset_id_for_site(site_slug)
    slug = flood_mechanism_layer_stem(site_slug)

    classes: dict[int, dict[str, str]] = {}
    for mech_type, code in sorted(FLOOD_MECHANISM_TYPE_CODES.items(), key=lambda kv: kv[1]):
        classes[code] = {
            "name": FLOOD_MECHANISM_CLASS_NAMES[code],
            "color": FLOOD_MECHANISM_COLORS[mech_type],
        }

    return {
        "dataset_id": dataset_id,
        "dataset_name": f"Flood Mechanism Type ({short}, 250 m)",
        "publisher": "Open Earth Foundation (derived processing)",
        "license": "CC BY 4.0",
        "resolution": "~250m",
        "crs": "EPSG:3857",
        "access_type": "internal_storage",
        "source_url": hazard_source_url(site_slug, catalog_path),
        "dataset_type": "flood",
        "type": "categorical_raster",
        "data_quality": {
            "temporal_coverage": (
                "Static screening layer from current catalog COGs and OSM waterways"
            ),
            "accuracy": (
                "Per-cell dominant mechanism from rule-based NBS screening "
                "(riverine, pluvial, low-lying, drainage proxy)"
            ),
            "limitations": (
                "Screening-level classification only; drainage_constrained is a proxy until "
                "municipal drainage data exists; not event-specific depth"
            ),
        },
        "value_encoding": {
            "type": "class_lookup",
            "decode_formula": (
                "encoded = R + 256*G + 65536*B; if encoded == 0 then nodata "
                "else mechanism_code = encoded - 1"
            ),
            "classes": classes,
        },
        "assets": {
            "visual_tiles": {"url_template": urls["visual_tiles_template"]},
            "value_tiles": {"url_template": urls["value_tiles_template"]},
            "download": {
                "cog_url": urls["cog"],
                "geojson_url": urls["geojson"],
            },
            "metadata": {"url": []},
        },
        "description": (
            f"OEF dominant flood mechanism type per 250 m cell for {display}. Integer codes: "
            "0 none, 1 riverine, 2 pluvial, 3 low_lying, 4 drainage_constrained, 5 mixed. "
            "Rules in `transformation/nbs_screening/nbs_rules.py`; produced by "
            "`transformation/nbs_screening/flood/compute_mechanism.py`. Methodology: "
            "`models/nbs_flood_mechanism_type/`. Rasterized on the OEF flood hazard 250 m grid. "
            "Value tiles use Terrain RGB with +1 offset (`mechanism_code = encoded - 1`; "
            "encoded 0 = nodata). GeoJSON (`geojson_url`) lists screened cells with mechanism "
            "strengths, boolean flags, and `is_interpolated` for analytical QA (not a map tile layer)."
        ),
        "_slug": slug,
    }


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

    class_lines = []
    for code in sorted(ve["classes"]):
        cls = ve["classes"][code]
        class_lines.append(f'        {code}: {{ name: {cls["name"]}, color: "{cls["color"]}" }}')
    classes_block = "\n".join(class_lines)

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
        f"    value_encoding:\n"
        f"      type: {ve['type']}\n"
        f"      decode_formula: \"{ve['decode_formula']}\"\n"
        f"      classes:\n"
        f"{classes_block}\n"
        f"    assets:\n"
        f"      visual_tiles:\n"
        f"        url_template: {assets['visual_tiles']['url_template']}\n"
        f"      value_tiles:\n"
        f"        url_template: {assets['value_tiles']['url_template']}\n"
        f"      download:\n"
        f"        cog_url: {download['cog_url']}\n"
        f"        geojson_url: {download['geojson_url']}\n"
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
    end = len(text.rstrip("\n")) + 1
    return start, end


def find_catalog_path(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        candidate = path / "catalog" / "datasets.yaml"
        if candidate.is_file():
            return candidate
        nested = path / "geospatial-data" / "catalog" / "datasets.yaml"
        if nested.is_file():
            return nested
    repo = find_repo_root(NBS_ROOT)
    candidate = repo / "catalog" / "datasets.yaml"
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(
        "Could not locate catalog/datasets.yaml from "
        f"{start}. Pass catalog_path explicitly."
    )


def upsert_datasets_yaml(
    entry: dict[str, Any],
    catalog_path: Path,
    *,
    dry_run: bool = True,
) -> str:
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


def run_publish(
    site: str,
    *,
    build: bool = True,
    upload: bool = False,
    write_catalog: bool = False,
    tile_zoom: str | None = None,
) -> dict[str, str]:
    site_cfg = load_site_config(site)
    site_slug = str(site_cfg["site_slug"])
    slug = flood_mechanism_layer_stem(site_slug)
    publish_dir = site_publish_dir(site_slug, "flood")
    zoom = tile_zoom or DEFAULT_TILE_ZOOM

    if build:
        in_tif = resolve_input_tif(site_slug)
        print(f"Building flood mechanism publish artifacts from {in_tif}")
        build_flood_mechanism_cog_and_tiles(
            in_tif=in_tif,
            publish_dir=publish_dir,
            slug=slug,
            tile_zoom=zoom,
        )
    else:
        print(f"Skipping build; using existing artifacts in {publish_dir}")

    urls = upload_flood_mechanism_to_s3(
        site_slug,
        publish_dir=publish_dir,
        upload=upload,
    )
    catalog_path = find_catalog_path(NBS_ROOT)
    entry = build_catalog_entry(site_cfg, urls, catalog_path=catalog_path)
    entry.pop("_slug", None)
    upsert_datasets_yaml(entry, catalog_path, dry_run=not write_catalog)
    print(f"UPLOAD={upload} | WRITE_CATALOG={write_catalog} | site={site_slug}")
    return urls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="richfield", help="City slug (default: richfield)")
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
        help="Upload COG, tiles, and GeoJSON to S3",
    )
    parser.add_argument(
        "--write-catalog",
        action="store_true",
        help="Write catalog/datasets.yaml (default: dry-run print)",
    )
    parser.add_argument(
        "--tile-zoom",
        default=DEFAULT_TILE_ZOOM,
        help=f"XYZ zoom range for gdal2tiles (default: {DEFAULT_TILE_ZOOM})",
    )
    args = parser.parse_args(argv)
    try:
        run_publish(
            args.site,
            build=args.build,
            upload=args.upload,
            write_catalog=args.write_catalog,
            tile_zoom=args.tile_zoom,
        )
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
