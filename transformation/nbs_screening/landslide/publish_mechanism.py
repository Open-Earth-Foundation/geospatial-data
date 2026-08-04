#!/usr/bin/env python3
"""Build landslide mechanism COG + XYZ tiles, upload to S3, upsert catalog/datasets.yaml.

Example (Richfield, build only):
  python transformation/nbs_screening/landslide/publish_mechanism.py --site richfield --build

Example (upload + catalog):
  python transformation/nbs_screening/landslide/publish_mechanism.py \\
    --site richfield --build --upload --write-catalog
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

LANDSLIDE_ROOT = Path(__file__).resolve().parent
NBS_ROOT = LANDSLIDE_ROOT.parent
for _path in (LANDSLIDE_ROOT, NBS_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from grid_screening import landslide_mechanism_layer_stem  # noqa: E402
from nbs_rules import (  # noqa: E402
    LANDSLIDE_MECHANISM_COLORS,
    LANDSLIDE_MECHANISM_DISPLAY_LABELS,
    LANDSLIDE_MECHANISM_TYPE_CODES,
)
from grid_screening import MECHANISM_RASTER_NODATA  # noqa: E402
from publish_common import (  # noqa: E402
    DEFAULT_TILE_ZOOM,
    build_mechanism_cog_and_tiles,
    dataset_id_for_site,
    find_catalog_path,
    hazard_source_url,
    s3_prefix_for_site,
    upload_mechanism_to_s3,
    upsert_datasets_yaml,
    write_mechanism_colors,
)
from site_config import (  # noqa: E402
    DEFAULT_SITE,
    load_site_config,
    resolve_site_output_dir,
    site_publish_dir,
)

LANDSLIDE_MECHANISM_CLASS_NAMES: dict[int, str] = {
    code: LANDSLIDE_MECHANISM_DISPLAY_LABELS[mech_type]
    for mech_type, code in LANDSLIDE_MECHANISM_TYPE_CODES.items()
}
MAX_CODE = max(LANDSLIDE_MECHANISM_TYPE_CODES.values())


def write_landslide_mechanism_colors(colors_path: Path) -> None:
    write_mechanism_colors(
        colors_path,
        header_lines=[
            "# Dominant landslide mechanism type. GDAL color-relief for visual tiles.",
            f"# Raster nodata = {MECHANISM_RASTER_NODATA}; code 0 = without_clear_dominant",
        ],
        type_codes=LANDSLIDE_MECHANISM_TYPE_CODES,
        type_colors=LANDSLIDE_MECHANISM_COLORS,
    )


def resolve_input_tif(site: str) -> Path:
    stem = landslide_mechanism_layer_stem(site)
    path = resolve_site_output_dir(site, "landslide") / f"{stem}.tif"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing filled mechanism raster: {path}. "
            f"Run: python transformation/nbs_screening/landslide/compute_mechanism.py --site {site}"
        )
    return path


def resolve_geojson(site: str) -> Path:
    stem = landslide_mechanism_layer_stem(site)
    path = resolve_site_output_dir(site, "landslide") / f"{stem}.geojson"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing mechanism GeoJSON: {path}. "
            f"Run landslide/compute_mechanism.py --site {site} first."
        )
    return path


def build_catalog_entry(
    site_cfg: dict[str, Any],
    urls: dict[str, str],
    *,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    site_slug = str(site_cfg["site_slug"])
    display = str(site_cfg.get("display_name") or site_slug)
    short = "POA" if site_slug == DEFAULT_SITE else display
    dataset_id = dataset_id_for_site(site_slug, hazard="landslide")
    slug = landslide_mechanism_layer_stem(site_slug)
    hazard_id = (
        "poa_landslide_hazard" if site_slug == DEFAULT_SITE else f"{site_slug}_landslide_hazard"
    )

    classes: dict[int, dict[str, str]] = {}
    for mech_type, code in sorted(LANDSLIDE_MECHANISM_TYPE_CODES.items(), key=lambda kv: kv[1]):
        classes[code] = {
            "name": LANDSLIDE_MECHANISM_CLASS_NAMES[code],
            "color": LANDSLIDE_MECHANISM_COLORS[mech_type],
        }

    return {
        "dataset_id": dataset_id,
        "dataset_name": f"Landslide Mechanism Type ({short}, 90 m)",
        "publisher": "Open Earth Foundation (derived processing)",
        "license": "CC BY 4.0",
        "resolution": "~90m",
        "crs": "EPSG:3857",
        "access_type": "internal_storage",
        "source_url": hazard_source_url(
            site_slug,
            hazard_dataset_id=hazard_id,
            default_hazard_key="landslides/hazard/landslide_hazard_score_idw_cog.tif",
            catalog_path=catalog_path,
        ),
        "dataset_type": "landslide",
        "type": "categorical_raster",
        "data_quality": {
            "temporal_coverage": "Static screening layer from current catalog COGs and terrain inputs",
            "accuracy": (
                "Per-cell dominant mechanism from rule-based NBS screening "
                "(slope, rainfall, cohesion, vegetation, drainage, disturbance, upslope convergence)"
            ),
            "limitations": (
                "Screening-level classification only; not event-specific landslide runout or depth"
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
            f"OEF dominant landslide mechanism type per 90 m cell for {display}. Integer codes 0–9 "
            "for without_clear_dominant through mixed (see nbs_rules.py). Produced by "
            "`transformation/nbs_screening/landslide/compute_mechanism.py`. Methodology: "
            "`models/nbs_landslide_mechanism_type/`. Rasterized on the OEF landslide hazard 90 m grid."
        ),
        "_slug": slug,
    }


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
    slug = landslide_mechanism_layer_stem(site_slug)
    publish_dir = site_publish_dir(site_slug, "landslide")
    s3_prefix = s3_prefix_for_site(site_slug, hazard_subdir="landslides/landslide_mechanism")
    zoom = tile_zoom or DEFAULT_TILE_ZOOM

    if build:
        in_tif = resolve_input_tif(site_slug)
        print(f"Building landslide mechanism publish artifacts from {in_tif}")
        build_mechanism_cog_and_tiles(
            in_tif=in_tif,
            publish_dir=publish_dir,
            slug=slug,
            write_colors=write_landslide_mechanism_colors,
            max_code=MAX_CODE,
            decode_title=f"Landslide mechanism type value tiles ({slug})",
            decode_code_name="landslide_mechanism_code",
            type_codes=LANDSLIDE_MECHANISM_TYPE_CODES,
            tile_zoom=zoom,
        )
    else:
        print(f"Skipping build; using existing artifacts in {publish_dir}")

    urls = upload_mechanism_to_s3(
        site_slug,
        "landslide",
        slug=slug,
        s3_prefix=s3_prefix,
        geojson_path=resolve_geojson(site_slug),
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
    parser.add_argument("--build", action="store_true", default=True, help="Build COG + tiles")
    parser.add_argument("--no-build", action="store_false", dest="build", help="Skip COG/tiles build")
    parser.add_argument("--upload", action="store_true", help="Upload COG, tiles, and GeoJSON to S3")
    parser.add_argument("--write-catalog", action="store_true", help="Write catalog/datasets.yaml")
    parser.add_argument("--tile-zoom", default=DEFAULT_TILE_ZOOM, help="XYZ zoom range for gdal2tiles")
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
