#!/usr/bin/env python3
"""Export MODIS MOD11A2 day/night P90 + norms into heat_hazard data/input/.

Example:
  python transformation/modis_lst/extract_modis_lst.py --site plymouth
  python transformation/modis_lst/extract_modis_lst.py --site plymouth --qa-only
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

TRANSFORMATION = Path(__file__).resolve().parents[1]
HEAT_HAZARD = TRANSFORMATION / "heat_hazard"
if str(HEAT_HAZARD) not in sys.path:
    sys.path.insert(0, str(HEAT_HAZARD))

from gee_local_export import export_image_to_input  # noqa: E402
from input_common import (  # noqa: E402
    export_paths_summary,
    init_ee,
    load_heat_site,
    load_site_roi,
    minmax_norm_roi,
    season_months,
)
from qa_local import qa_modis  # noqa: E402

SCALE_M = 1000
CRS = "EPSG:4326"
EXPORT_KEYS = ["modis_day_p90", "modis_night_p90", "modis_day_norm", "modis_night_norm"]


def preprocess_modis(image, ee):
    lst_day = (
        image.select("LST_Day_1km")
        .multiply(0.02)
        .subtract(273.15)
        .rename("lst_day_celsius")
    )
    good_day = image.select("QC_Day").bitwiseAnd(0b11).lt(2)
    lst_day = lst_day.updateMask(good_day)

    lst_night = (
        image.select("LST_Night_1km")
        .multiply(0.02)
        .subtract(273.15)
        .rename("lst_night_celsius")
    )
    good_night = image.select("QC_Night").bitwiseAnd(0b11).lt(2)
    lst_night = lst_night.updateMask(good_night)
    return image.addBands(lst_day).addBands(lst_night)


def run(
    site: str,
    *,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
) -> list[Path]:
    site_config = load_heat_site(site)
    display = site_config.get("display_name") or site
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers = site_config["layers"]
    paths = {key: input_dir / layers[key] for key in EXPORT_KEYS}

    if not qa_only:
        ee = init_ee(authenticate=authenticate)
        season = str(site_config.get("season") or "djf")
        season_label = str(site_config.get("season_label") or season.upper())
        start_year = int(site_config["start_year"])
        end_year = int(site_config["end_year"])
        months = season_months(site_config)
        roi = load_site_roi(site_config, ee)

        print(f"MODIS MOD11A2 → {display} ({site}) · {season_label} {start_year}–{end_year}")
        raw = (
            ee.ImageCollection("MODIS/061/MOD11A2")
            .filterDate(f"{start_year}-01-01", f"{end_year}-12-31")
            .filterBounds(roi)
            .map(lambda image: image.set("month", image.date().get("month")))
            .filter(ee.Filter.inList("month", months))
            .select(["LST_Day_1km", "QC_Day", "LST_Night_1km", "QC_Night"])
        )
        collection = raw.map(lambda img: preprocess_modis(img, ee))
        print(f"Composites in season filter: {collection.size().getInfo()}")

        day_col = collection.select("lst_day_celsius")
        night_col = collection.select("lst_night_celsius")
        lst_day_p90 = day_col.reduce(ee.Reducer.percentile([90])).rename("lst_day_p90").clip(roi)
        lst_night_p90 = (
            night_col.reduce(ee.Reducer.percentile([90])).rename("lst_night_p90").clip(roi)
        )
        lst_day_norm = minmax_norm_roi(
            lst_day_p90,
            band_name="lst_day_p90",
            roi=roi,
            ee=ee,
            scale=SCALE_M,
            out_name="lst_day_p90_norm",
        )
        lst_night_norm = minmax_norm_roi(
            lst_night_p90,
            band_name="lst_night_p90",
            roi=roi,
            ee=ee,
            scale=SCALE_M,
            out_name="lst_night_p90_norm",
        )

        period = f"{season_label} {start_year}-{end_year}"
        export_cfg = [
            (lst_day_p90, "modis_day_p90", f"modis_day_p90_{period}_{display}"),
            (lst_night_p90, "modis_night_p90", f"modis_night_p90_{period}_{display}"),
            (lst_day_norm, "modis_day_norm", f"modis_day_norm_{period}_{display}"),
            (lst_night_norm, "modis_night_norm", f"modis_night_norm_{period}_{display}"),
        ]
        for image, key, desc in export_cfg:
            export_image_to_input(
                image,
                filename=layers[key],
                region=roi,
                scale=SCALE_M,
                input_dir=input_dir,
                crs=CRS,
                description=Path(layers[key]).stem,
                drive_folder="EE_exports/heat",
            )
    else:
        missing = [str(p) for p in paths.values() if not p.is_file()]
        if missing:
            raise FileNotFoundError("Missing GeoTIFF(s) for --qa-only:\n  " + "\n  ".join(missing))

    export_paths_summary(site_config, EXPORT_KEYS)
    if write_qa:
        qa_modis(
            paths["modis_day_p90"],
            paths["modis_night_p90"],
            paths["modis_day_norm"],
            paths["modis_night_norm"],
            site_config,
            display=str(display),
        )
    return [paths[k] for k in EXPORT_KEYS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: HEAT_SITE)")
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true", help="Skip SVG QA maps/hists")
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Skip GEE export; rebuild QA from existing GeoTIFFs",
    )
    args = parser.parse_args(argv)
    site = args.site or os.environ.get("HEAT_SITE") or os.environ.get("FLOODS_SITE", "porto_alegre")
    try:
        paths = run(
            site,
            authenticate=args.authenticate,
            write_qa=not args.no_qa,
            qa_only=args.qa_only,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("\nDone:")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
