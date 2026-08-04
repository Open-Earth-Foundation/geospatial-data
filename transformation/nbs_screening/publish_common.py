"""Shared COG/tile publish helpers for NBS mechanism layers (heat/landslide/flood)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from grid_screening import MECHANISM_RASTER_NODATA
from site_config import DEFAULT_SITE, find_repo_root, load_site_config, site_publish_dir

S3_BUCKET = "geo-test-api"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"
DEFAULT_TILE_ZOOM = "8-15"


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def ensure_common_cli_paths() -> None:
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
    ensure_common_cli_paths()
    path = shutil.which(command)
    if path:
        return path
    raise RuntimeError(
        f"{command} not found. Install GDAL (`brew install gdal`) or add it to PATH.\n"
        f"Current PATH: {os.environ.get('PATH', '')}"
    )


def resolve_aws_cli() -> str:
    ensure_common_cli_paths()
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


def s3_uri(key: str) -> str:
    return f"s3://{S3_BUCKET}/{key.lstrip('/')}"


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


def write_mechanism_colors(
    colors_path: Path,
    *,
    header_lines: list[str],
    type_codes: Mapping[str, int],
    type_colors: Mapping[str, str],
) -> None:
    lines = header_lines + ["nv 0 0 0 0"]
    for mech_type, code in sorted(type_codes.items(), key=lambda kv: kv[1]):
        r, g, b = hex_to_rgb(type_colors[mech_type])
        lines.append(f"{code} {r} {g} {b}")
    colors_path.parent.mkdir(parents=True, exist_ok=True)
    colors_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote colors: {colors_path}")


def build_mechanism_cog_and_tiles(
    *,
    in_tif: Path,
    publish_dir: Path,
    slug: str,
    write_colors: Callable[[Path], None],
    max_code: int,
    decode_title: str,
    decode_code_name: str,
    type_codes: Mapping[str, int],
    tile_zoom: str = DEFAULT_TILE_ZOOM,
) -> dict[str, Path]:
    """EPSG:3857 COG + visual/value XYZ tiles."""
    gdalwarp = require_cli("gdalwarp")
    gdal_translate = require_cli("gdal_translate")
    gdaldem = require_cli("gdaldem")
    gdal_calc = require_cli("gdal_calc.py")
    gdal2tiles = require_cli("gdal2tiles.py")
    gdal2tiles_py = gdal2tiles_python(gdal2tiles)
    subprocess.run([gdal2tiles_py, "-c", "import numpy"], check=True, capture_output=True)

    publish_dir.mkdir(parents=True, exist_ok=True)
    paths = resolve_publish_paths(publish_dir, slug)
    write_colors(paths["colors"])

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
        f"numpy.rint(numpy.clip(A,0,{max_code})).astype(numpy.int64) + 1)"
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
        decode_title,
        "",
        f"Source raster: {in_tif}",
        f"COG (EPSG:3857): {paths['cog']}",
        f"Visual tiles: {paths['tiles_visual']}/{{z}}/{{x}}/{{y}}.png",
        f"Value tiles: {paths['tiles_values']}/{{z}}/{{x}}/{{y}}.png",
        "",
        "Value tile encoding (Terrain RGB style):",
        "encoded = R + 256 * G + 65536 * B",
        "if encoded == 0: nodata",
        f"else: {decode_code_name} = encoded - 1",
        "",
        "Mechanism codes:",
    ]
    decode_lines.extend(
        f"  {code}: {mech_type}"
        for mech_type, code in sorted(type_codes.items(), key=lambda kv: kv[1])
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


def expected_urls(site_slug: str, slug: str, s3_prefix: str) -> dict[str, str]:
    return {
        "cog": public_url(f"{s3_prefix}/{slug}_cog.tif"),
        "geojson": public_url(f"{s3_prefix}/{slug}.geojson"),
        "tiles_visual": public_url(f"{s3_prefix}/tiles_visual"),
        "tiles_values": public_url(f"{s3_prefix}/tiles_values"),
        "visual_tiles_template": public_url(f"{s3_prefix}/tiles_visual/{{z}}/{{x}}/{{y}}.png"),
        "value_tiles_template": public_url(f"{s3_prefix}/tiles_values/{{z}}/{{x}}/{{y}}.png"),
    }


def hazard_source_url(
    site_slug: str,
    *,
    hazard_dataset_id: str,
    default_hazard_key: str,
    catalog_path: Path | None = None,
) -> str:
    default = public_url(
        f"oef_calculation/release/v1/{site_slug}/climate_hazards/{default_hazard_key}"
    )
    if catalog_path is None:
        return default
    try:
        catalog_path = Path(catalog_path)
        text = catalog_path.read_text(encoding="utf-8")
        span = find_dataset_span(text, hazard_dataset_id)
        if span is None:
            return default
        block = text[span[0] : span[1]]
        match = re.search(r"cog_url:\s*(\S+)", block)
        if match:
            return match.group(1)
    except OSError:
        pass
    return default


def upload_mechanism_to_s3(
    site: str,
    hazard: str,
    *,
    slug: str,
    s3_prefix: str,
    geojson_path: Path,
    publish_dir: Path | None = None,
    upload: bool = True,
) -> dict[str, str]:
    site_cfg = load_site_config(site)
    site_slug = str(site_cfg["site_slug"])
    publish_dir = Path(publish_dir or site_publish_dir(site_slug, hazard))  # type: ignore[arg-type]
    paths = validate_publish_dir(publish_dir, slug)
    urls = expected_urls(site_slug, slug, s3_prefix)

    if not upload:
        print(f"Skipping S3 upload (upload=False). Expected prefix: s3://{S3_BUCKET}/{s3_prefix}/")
        for key, url in urls.items():
            if key.endswith("_template"):
                continue
            print(f"  {key}: {url}")
        return urls

    aws = resolve_aws_cli()
    cog_key = f"{s3_prefix}/{slug}_cog.tif"
    subprocess.run([aws, "s3", "cp", str(paths["cog"]), s3_uri(cog_key)], check=True)
    print(f"Uploaded COG → {urls['cog']}")

    for tiles_name in ("tiles_visual", "tiles_values"):
        tiles_key = f"{s3_prefix}/{tiles_name}/"
        subprocess.run(
            [aws, "s3", "cp", str(paths[tiles_name]), s3_uri(tiles_key), "--recursive"],
            check=True,
        )
        print(f"Uploaded {tiles_name} → {urls[tiles_name]}")

    geojson_key = f"{s3_prefix}/{slug}.geojson"
    subprocess.run([aws, "s3", "cp", str(geojson_path), s3_uri(geojson_key)], check=True)
    print(f"Uploaded GeoJSON → {urls['geojson']}")
    return urls


def format_catalog_block(entry: dict[str, Any]) -> str:
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


def find_dataset_span(text: str, dataset_id: str) -> tuple[int, int] | None:
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


def find_catalog_path(nbs_root: Path, start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for path in [start, *start.parents]:
        candidate = path / "catalog" / "datasets.yaml"
        if candidate.is_file():
            return candidate
        nested = path / "geospatial-data" / "catalog" / "datasets.yaml"
        if nested.is_file():
            return nested
    repo = find_repo_root(nbs_root)
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
    block = format_catalog_block(entry)
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

    span = find_dataset_span(text, dataset_id)
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


def dataset_id_for_site(site_slug: str, *, hazard: str) -> str:
    if site_slug == DEFAULT_SITE:
        return f"poa_{hazard}_mechanism_type"
    return f"{site_slug}_{hazard}_mechanism_type"


def s3_prefix_for_site(site_slug: str, *, hazard_subdir: str) -> str:
    return f"oef_calculation/release/v1/{site_slug}/climate_hazards/{hazard_subdir}"
