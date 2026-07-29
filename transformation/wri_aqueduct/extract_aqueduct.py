#!/usr/bin/env python3
"""Export WRI Aqueduct RP100 river depth + impact-class norm into flood_hazard data/input/.

Example:
  python transformation/wri_aqueduct/extract_aqueduct.py --site plymouth
  python transformation/wri_aqueduct/extract_aqueduct.py --site plymouth --qa-only
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

TRANSFORMATION = Path(__file__).resolve().parents[1]
FLOOD_HAZARD = TRANSFORMATION / "flood_hazard"
if str(FLOOD_HAZARD) not in sys.path:
    sys.path.insert(0, str(FLOOD_HAZARD))

from gee_local_export import export_image_to_input  # noqa: E402
from input_common import (  # noqa: E402
    depth_to_impact_score,
    export_paths_summary,
    init_ee,
    load_flood_site,
    load_site_roi,
)
from qa_local import qa_depth_and_norm  # noqa: E402

SCALE_M = 1000
CRS = "EPSG:4326"


def run(
    site: str,
    *,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
) -> list[Path]:
    site_config = load_flood_site(site)
    display = site_config.get("display_name") or site
    input_dir = Path(site_config["paths_abs"]["data_input"])
    prefix = site_config["output_prefix"]
    layers = site_config["layers"]
    depth_path = input_dir / layers["aqueduct_depth"]
    norm_path = input_dir / layers["aqueduct_norm"]

    if not qa_only:
        ee = init_ee(authenticate=authenticate)
        roi = load_site_roi(site_config, ee)
        print(f"WRI Aqueduct RP100 → {display} ({site})")
        dataset = ee.ImageCollection("WRI/Aqueduct_Flood_Hazard_Maps/V2")
        river_historical = (
            dataset.filter(ee.Filter.eq("floodtype", "inunriver"))
            .filter(ee.Filter.eq("returnperiod", 100))
            .filter(ee.Filter.eq("climatescenario", "historical"))
        )
        image = ee.Image(river_historical.first()).clip(roi)
        depth = image.select("inundation_depth")
        score = depth_to_impact_score(depth, ee, band_name="flood_hazard_score").clip(roi)
        for img, key, desc in [
            (depth, "aqueduct_depth", f"aqueduct_depth_rp100_{prefix}"),
            (score, "aqueduct_norm", f"aqueduct_depth_rp100_norm_{prefix}"),
        ]:
            export_image_to_input(
                img,
                filename=layers[key],
                region=roi,
                scale=SCALE_M,
                input_dir=input_dir,
                crs=CRS,
                description=desc,
                drive_folder="OEF_Aqueduct_Depth",
            )
    else:
        for p in (depth_path, norm_path):
            if not p.is_file():
                raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {p}")

    export_paths_summary(site_config, ["aqueduct_depth", "aqueduct_norm"])
    if write_qa:
        qa_depth_and_norm(
            depth_path,
            norm_path,
            site_config,
            display=str(display),
            prefix="aqueduct",
        )
    return [depth_path, norm_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: FLOODS_SITE)")
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true")
    parser.add_argument("--qa-only", action="store_true")
    args = parser.parse_args(argv)
    site = args.site or os.environ.get("FLOODS_SITE", "porto_alegre")
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
