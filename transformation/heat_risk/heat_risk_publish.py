#!/usr/bin/env python3
"""Build heat risk COG + XYZ tiles, upload to S3, upsert catalog/datasets.yaml.

Products:
  risk           → {s3_prefix}/risk/           (dataset_id: {slug}_heat_risk)
  exposure       → {s3_prefix}/exposure/       (dataset_id: {slug}_heat_exposure)
  vulnerability  → {s3_prefix}/vulnerability/  (dataset_id: {slug}_heat_vulnerability)

Note: E/V are burned onto the heat hazard grid (may differ from flood shared E/V).

Example (Plymouth risk, dry-run catalog, no upload):
  python transformation/heat_risk/heat_risk_publish.py --site plymouth --product risk --build

Example (Rochester regional dual product):
  python transformation/heat_risk/heat_risk_publish.py \\
    --site rochester --product risk --normalization-domain regional --build

Example (upload + write catalog):
  python transformation/heat_risk/heat_risk_publish.py \\
    --site plymouth --product risk --build --upload --write-catalog
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

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

HEAT_RISK_ROOT = Path(__file__).resolve().parent
S3_BUCKET = "geo-test-api"
S3_PUBLIC_BASE = f"https://{S3_BUCKET}.s3.us-east-1.amazonaws.com"
VALUE_SCALE = 10000

# product → local naming + S3 layout + catalog metadata
PRODUCTS: dict[str, dict[str, Any]] = {
    "risk": {
        "score_glob": "heat_risk_score_{site}.tif",
        "gpkg_glob": "heat_risk_score_{site}.gpkg",
        "publish_subdir": "heat_risk_score",
        "cog_filename": "heat_risk_score_cog.tif",
        "colorized_filename": "heat_risk_score_colorized.tif",
        "value_rgb_filename": "heat_risk_score_value_encoded_rgb.tif",
        "s3_kind": "heat_risk",  # under climate_hazards/heat/risk
        "dataset_id_tpl": "{slug}_heat_risk",
        "dataset_id_poa": "poa_heat_risk",
        "dataset_name_tpl": "Heat Risk Score H×E×V ({short})",
        "dataset_type": "heat",
        "colors": "heat_risk_colors.txt",
    },
    "exposure": {
        "score_glob": "heat_exposure_score_{site}.tif",
        "gpkg_glob": None,
        "publish_subdir": "heat_exposure_score",
        "cog_filename": "heat_exposure_score_cog.tif",
        "colorized_filename": "heat_exposure_score_colorized.tif",
        "value_rgb_filename": "heat_exposure_score_value_encoded_rgb.tif",
        "s3_kind": "heat_exposure",
        "dataset_id_tpl": "{slug}_heat_exposure",
        "dataset_id_poa": "poa_heat_exposure",
        "dataset_name_tpl": "Heat Exposure Score — ACS Pop. Density ({short})",
        "dataset_type": "heat",
        "colors": "heat_risk_colors.txt",
    },
    "vulnerability": {
        "score_glob": "heat_vulnerability_score_{site}.tif",
        "gpkg_glob": None,
        "publish_subdir": "heat_vulnerability_score",
        "cog_filename": "heat_vulnerability_score_cog.tif",
        "colorized_filename": "heat_vulnerability_score_colorized.tif",
        "value_rgb_filename": "heat_vulnerability_score_value_encoded_rgb.tif",
        "s3_kind": "heat_vulnerability",
        "dataset_id_tpl": "{slug}_heat_vulnerability",
        "dataset_id_poa": "poa_heat_vulnerability",
        "dataset_name_tpl": "Heat Vulnerability Score — ACS Composite ({short})",
        "dataset_type": "heat",
        "colors": "heat_risk_colors.txt",
    },
}


def _norm_domain(domain: str | None) -> str:
    d = str(domain or "city").lower()
    if d not in {"city", "regional"}:
        raise ValueError(f"normalization_domain must be 'city' or 'regional', got {domain!r}")
    return d


def _domain_suffix(domain: str) -> str:
    return "_regional" if _norm_domain(domain) == "regional" else ""


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    out: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        key, val = line.split(":", 1)
        out[key.strip()] = val.strip().strip("'\"")
    return out


def load_site_config(site: str) -> dict[str, Any]:
    path = HEAT_RISK_ROOT / "config" / f"{site}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Missing site config: {path}")
    cfg = _load_yaml(path)
    cfg["site_slug"] = cfg.get("site_slug") or site
    cfg.setdefault(
        "s3_prefix",
        f"oef_calculation/release/v1/{cfg['site_slug']}/climate_hazards/heat",
    )
    cfg.setdefault(
        "shared_s3_prefix",
        f"oef_calculation/release/v1/{cfg['site_slug']}/shared",
    )
    # Nested `publish:` becomes "" with the naive YAML fallback when PyYAML is absent;
    # also accept a top-level tile_zoom key.
    publish = cfg.get("publish")
    if not isinstance(publish, dict):
        zoom = cfg.get("tile_zoom") or "8-15"
        cfg["publish"] = {"tile_zoom": str(zoom)}
    else:
        publish.setdefault("tile_zoom", cfg.get("tile_zoom") or "8-15")
    return cfg


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


def dataset_id_for_site(
    site_config: dict[str, Any],
    product: str,
    *,
    normalization_domain: str = "city",
) -> str:
    meta = PRODUCTS[product]
    slug = str(site_config.get("site_slug") or "")
    suf = _domain_suffix(normalization_domain)
    if slug == "porto_alegre":
        return f"{meta['dataset_id_poa']}{suf}"
    return f"{str(meta['dataset_id_tpl']).format(slug=slug)}{suf}"


def product_s3_prefix(
    site_config: dict[str, Any],
    product: str,
    *,
    normalization_domain: str = "city",
) -> str:
    kind = PRODUCTS[product]["s3_kind"]
    base = str(site_config["s3_prefix"]).rstrip("/")
    regional = _norm_domain(normalization_domain) == "regional"
    if kind == "heat_risk":
        return f"{base}/risk_regional" if regional else f"{base}/risk"
    if kind == "heat_exposure":
        return f"{base}/exposure_regional" if regional else f"{base}/exposure"
    if kind == "heat_vulnerability":
        return f"{base}/vulnerability_regional" if regional else f"{base}/vulnerability"
    raise ValueError(f"Unknown s3_kind: {kind}")


def vector_s3_prefix(site_config: dict[str, Any]) -> str:
    return f"{str(site_config['s3_prefix']).rstrip('/')}/vector"


def site_paths(site: str) -> dict[str, Path]:
    root = HEAT_RISK_ROOT / "sites" / site
    return {
        "output": root / "data" / "output",
        "out": root / "out",
    }


def resolve_score_tif(
    site: str,
    product: str,
    *,
    normalization_domain: str = "city",
) -> Path:
    pattern = PRODUCTS[product]["score_glob"].format(site=site)
    if _norm_domain(normalization_domain) == "regional":
        p = Path(pattern)
        pattern = f"{p.stem}_regional{p.suffix}"
    path = site_paths(site)["output"] / pattern
    if not path.is_file():
        hint = (
            f"Run compute_heat_risk.py --site {site} --product regional first."
            if _norm_domain(normalization_domain) == "regional"
            else f"Run compute_heat_risk.py --site {site} first."
        )
        raise FileNotFoundError(f"Missing score GeoTIFF: {path}. {hint}")
    return path


def resolve_gpkg(
    site: str,
    product: str,
    *,
    normalization_domain: str = "city",
) -> Path | None:
    glob = PRODUCTS[product].get("gpkg_glob")
    if not glob:
        return None
    name = glob.format(site=site)
    if _norm_domain(normalization_domain) == "regional":
        p = Path(name)
        name = f"{p.stem}_regional{p.suffix}"
    path = site_paths(site)["output"] / name
    return path if path.is_file() else None


def publish_dir_for(
    site: str,
    product: str,
    *,
    normalization_domain: str = "city",
) -> Path:
    return site_paths(site)["out"] / (
        PRODUCTS[product]["publish_subdir"] + _domain_suffix(normalization_domain)
    )


def resolve_publish_paths(publish_dir: Path, product: str) -> dict[str, Path]:
    meta = PRODUCTS[product]
    publish_dir = Path(publish_dir)
    return {
        "cog": publish_dir / meta["cog_filename"],
        "colorized": publish_dir / meta["colorized_filename"],
        "value_rgb": publish_dir / meta["value_rgb_filename"],
        "tiles_visual": publish_dir / "tiles_visual",
        "tiles_values": publish_dir / "tiles_values",
    }


def validate_publish_dir(publish_dir: Path, product: str) -> dict[str, Path]:
    paths = resolve_publish_paths(publish_dir, product)
    if not paths["cog"].is_file():
        raise FileNotFoundError(
            f"Missing COG: {paths['cog']}. Run with --build first."
        )
    for name in ("tiles_visual", "tiles_values"):
        if not paths[name].is_dir():
            raise FileNotFoundError(
                f"Missing {name} dir: {paths[name]}. Run with --build first."
            )
    return paths


def expected_urls(
    site_config: dict[str, Any],
    product: str,
    *,
    gpkg_name: str | None = None,
    normalization_domain: str = "city",
) -> dict[str, str]:
    prefix = product_s3_prefix(
        site_config, product, normalization_domain=normalization_domain
    )
    cog_name = PRODUCTS[product]["cog_filename"]
    urls = {
        "cog": public_url(f"{prefix}/{cog_name}"),
        "tiles_visual": public_url(f"{prefix}/tiles_visual"),
        "tiles_values": public_url(f"{prefix}/tiles_values"),
        "visual_tiles_template": public_url(f"{prefix}/tiles_visual/{{z}}/{{x}}/{{y}}.png"),
        "value_tiles_template": public_url(f"{prefix}/tiles_values/{{z}}/{{x}}/{{y}}.png"),
    }
    if product == "risk" and gpkg_name:
        urls["bairro_gpkg"] = public_url(f"{vector_s3_prefix(site_config)}/{gpkg_name}")
    return urls


def build_cog_and_tiles(
    *,
    in_tif: Path,
    publish_dir: Path,
    product: str,
    tile_zoom: str = "8-15",
    colors_txt: Path | None = None,
) -> dict[str, Path]:
    """Create COG + visual XYZ + value XYZ tiles (same pattern as flood_hazard)."""
    meta = PRODUCTS[product]
    colors = colors_txt or (HEAT_RISK_ROOT / "styles" / meta["colors"])
    if not colors.is_file():
        raise FileNotFoundError(f"Missing color table: {colors}")

    gdal_translate = require_cli("gdal_translate")
    gdaldem = require_cli("gdaldem")
    gdal_calc = require_cli("gdal_calc.py")
    gdal2tiles = require_cli("gdal2tiles.py")
    gdal2tiles_py = gdal2tiles_python(gdal2tiles)
    subprocess.run([gdal2tiles_py, "-c", "import numpy"], check=True, capture_output=True)

    publish_dir.mkdir(parents=True, exist_ok=True)
    paths = resolve_publish_paths(publish_dir, product)

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


def upload_product_to_s3(
    site_config: dict[str, Any],
    publish_dir: Path,
    product: str,
    *,
    upload: bool = True,
    gpkg_path: Path | None = None,
    normalization_domain: str = "city",
) -> dict[str, str]:
    paths = validate_publish_dir(publish_dir, product)
    gpkg_name = gpkg_path.name if gpkg_path and gpkg_path.is_file() else None
    urls = expected_urls(
        site_config,
        product,
        gpkg_name=gpkg_name,
        normalization_domain=normalization_domain,
    )
    prefix = product_s3_prefix(
        site_config, product, normalization_domain=normalization_domain
    )

    if not upload:
        print(f"Skipping S3 upload (upload=False). Expected prefix: s3://{S3_BUCKET}/{prefix}/")
        for k, v in urls.items():
            print(f"  {k}: {v}")
        return urls

    aws = resolve_aws_cli()
    cog_key = f"{prefix}/{PRODUCTS[product]['cog_filename']}"
    subprocess.run([aws, "s3", "cp", str(paths["cog"]), _s3_uri(cog_key)], check=True)
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

    if product == "risk" and gpkg_path and gpkg_path.is_file() and urls.get("bairro_gpkg"):
        gpkg_key = f"{vector_s3_prefix(site_config)}/{gpkg_path.name}"
        subprocess.run([aws, "s3", "cp", str(gpkg_path), _s3_uri(gpkg_key)], check=True)
        print(f"Uploaded block-group GPKG → {urls['bairro_gpkg']}")

    return urls


def build_catalog_entry(
    site_config: dict[str, Any],
    product: str,
    urls: dict[str, str] | None = None,
    *,
    normalization_domain: str = "city",
) -> dict[str, Any]:
    domain = _norm_domain(normalization_domain)
    urls = urls or expected_urls(site_config, product, normalization_domain=domain)
    display = str(site_config.get("display_name") or site_config.get("site_slug"))
    dataset_id = dataset_id_for_site(site_config, product, normalization_domain=domain)
    short = "POA" if str(site_config.get("site_slug")) == "porto_alegre" else display
    meta = PRODUCTS[product]
    name_suffix = ", MN regional" if domain == "regional" else ""
    short_labeled = f"{short}{name_suffix}"

    download: dict[str, Any] = {"cog_url": urls["cog"]}
    if urls.get("bairro_gpkg"):
        download["bairro_gpkg_url"] = urls["bairro_gpkg"]

    domain_note = (
        " Normalization domain: Minnesota state (regional dual product); "
        "scores are comparable across cities in MN."
        if domain == "regional"
        else " Normalization domain: city AOI (default screening product)."
    )

    if product == "risk":
        dq = {
            "temporal_coverage": (
                "Static composite from heat hazard ensemble + ACS block-group E/V rasterization"
            ),
            "accuracy": "R = (H × E × V)^(1/3) on cells where all three components are finite",
            "limitations": (
                "Screening-level composite; E/V constant per ACS block group; "
                "not IPCC full risk or loss modeling"
            ),
        }
        description = (
            f"OEF heat risk screening index (0–1) for {display}: geometric mean of hazard "
            "(OEF heat LST ensemble), exposure (ACS population density score), and vulnerability "
            "(ACS age/income/poverty composite). Computed by "
            "`transformation/heat_risk/compute_heat_risk.py`."
            f"{domain_note} "
            "Block-group vector (`bairro_gpkg_url`): zonal mean hazard, exposure, vulnerability, "
            "and risk per ACS block group."
        )
        source_url = "https://www.census.gov/programs-surveys/acs"
        crs = "EPSG:4326"
    elif product == "exposure":
        dq = {
            "temporal_coverage": "ACS 5-year estimates (block group)",
            "accuracy": (
                "Min–max normalized ACS population density burned to heat hazard grid"
            ),
            "limitations": (
                "Constant exposure within each block group; screening proxy, not asset inventory"
            ),
        }
        description = (
            f"ACS block-group exposure score (0–1) for {display} burned onto the heat hazard grid. "
            "Derived from ACS population density; E component of heat risk. "
            "Different raster grid than flood shared exposure. Computed via "
            "`transformation/acs_ev` + `transformation/heat_risk/compute_heat_risk.py`."
            f"{domain_note}"
        )
        source_url = "https://www.census.gov/programs-surveys/acs"
        crs = "EPSG:4326"
    else:
        dq = {
            "temporal_coverage": "ACS 5-year estimates (block group)",
            "accuracy": (
                "Composite ACS vulnerability (age / income / poverty where available) "
                "burned to heat hazard grid"
            ),
            "limitations": (
                "Constant vulnerability within each block group; some ACS indicators may be "
                "null for a site (e.g. poverty suppression)"
            ),
        }
        description = (
            f"ACS block-group vulnerability score (0–1) for {display} burned onto the heat "
            "hazard grid. V component of heat risk. Different raster grid than flood shared "
            "vulnerability. Computed via `transformation/acs_ev` + "
            "`transformation/heat_risk/compute_heat_risk.py`."
            f"{domain_note}"
        )
        source_url = "https://www.census.gov/programs-surveys/acs"
        crs = "EPSG:4326"

    return {
        "dataset_id": dataset_id,
        "dataset_name": str(meta["dataset_name_tpl"]).format(short=short_labeled),
        "normalization_domain": "minnesota" if domain == "regional" else "city",
        "comparability": "regional" if domain == "regional" else "city",
        "publisher": "Open Earth Foundation (derived processing)",
        "license": "CC BY 4.0",
        "resolution": "~250m",
        "crs": crs,
        "access_type": "internal_storage",
        "source_url": source_url,
        "dataset_type": meta["dataset_type"],
        "type": "numeric_raster",
        "data_quality": dq,
        "value_encoding": {
            "type": "rgb_24bit_scaled",
            "scale": VALUE_SCALE,
            "offset": 0.0,
            "unit": "score",
            "decode_formula": "value = (R + 256*G + 65536*B) / scale",
        },
        "assets": {
            "visual_tiles": {"url_template": urls["visual_tiles_template"]},
            "value_tiles": {"url_template": urls["value_tiles_template"]},
            "download": download,
            "metadata": {"url": []},
        },
        "description": description,
    }


def _format_catalog_block(entry: dict[str, Any]) -> str:
    dq = entry["data_quality"]
    ve = entry["value_encoding"]
    assets = entry["assets"]
    desc = str(entry["description"]).strip()
    desc_lines: list[str] = []
    line = ""
    for w in desc.split():
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

    limitations = str(dq["limitations"]).replace("\n", " ").strip()
    norm_fields = ""
    if entry.get("normalization_domain"):
        norm_fields = (
            f"    normalization_domain: {entry['normalization_domain']}\n"
            f"    comparability: {entry['comparability']}\n"
        )
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
        f"{norm_fields}"
        f"    data_quality:\n"
        f"      temporal_coverage: \"{dq['temporal_coverage']}\"\n"
        f"      accuracy: \"{dq['accuracy']}\"\n"
        f"      limitations: \"{limitations}\"\n"
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
    product: str,
    *,
    build: bool = True,
    upload: bool = False,
    write_catalog: bool = False,
    normalization_domain: str = "city",
) -> dict[str, str]:
    if product not in PRODUCTS:
        raise ValueError(f"Unknown product {product!r}; choose from {sorted(PRODUCTS)}")

    domain = _norm_domain(normalization_domain)
    site_config = load_site_config(site)
    publish_dir = publish_dir_for(site, product, normalization_domain=domain)
    tile_zoom = str(site_config.get("publish", {}).get("tile_zoom", "8-15"))
    gpkg = resolve_gpkg(site, product, normalization_domain=domain)

    if build:
        in_tif = resolve_score_tif(site, product, normalization_domain=domain)
        print(f"Building {product} publish artifacts from {in_tif} (domain={domain})")
        build_cog_and_tiles(
            in_tif=in_tif,
            publish_dir=publish_dir,
            product=product,
            tile_zoom=tile_zoom,
        )
    else:
        print(f"Skipping build; using existing artifacts in {publish_dir}")

    urls = upload_product_to_s3(
        site_config,
        publish_dir,
        product,
        upload=upload,
        gpkg_path=gpkg,
        normalization_domain=domain,
    )
    entry = build_catalog_entry(
        site_config, product, urls, normalization_domain=domain
    )
    catalog_path = find_catalog_path(HEAT_RISK_ROOT)
    upsert_datasets_yaml(entry, catalog_path, dry_run=not write_catalog)
    print(
        f"UPLOAD={upload} | WRITE_CATALOG={write_catalog} | product={product} | domain={domain}"
    )
    return urls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="plymouth")
    parser.add_argument(
        "--product",
        choices=sorted(PRODUCTS),
        default="risk",
        help="Which layer to publish (default: risk)",
    )
    parser.add_argument(
        "--normalization-domain",
        choices=["city", "regional"],
        default="city",
        help="city = AOI product (default); regional = Minnesota dual product",
    )
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
        help="Upload COG + tiles (+ GPKG for risk) to S3",
    )
    parser.add_argument(
        "--write-catalog",
        action="store_true",
        help="Write catalog/datasets.yaml (default: dry-run print)",
    )
    args = parser.parse_args(argv)
    try:
        run_publish(
            args.site,
            args.product,
            build=args.build,
            upload=args.upload,
            write_catalog=args.write_catalog,
            normalization_domain=args.normalization_domain,
        )
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
