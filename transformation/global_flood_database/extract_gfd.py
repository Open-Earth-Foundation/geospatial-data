#!/usr/bin/env python3
"""Export Global Flood Database layers into flood_hazard site data/input/.

Writes event count, robust-normalized count, and observed-once mask.

Example:
  python transformation/global_flood_database/extract_gfd.py --site plymouth
  python transformation/global_flood_database/extract_gfd.py --site plymouth --qa-only
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

TRANSFORMATION = Path(__file__).resolve().parents[1]
FLOOD_HAZARD = TRANSFORMATION / "flood_hazard"
if str(FLOOD_HAZARD) not in sys.path:
    sys.path.insert(0, str(FLOOD_HAZARD))

from gee_local_export import export_image_to_input  # noqa: E402
from input_common import (  # noqa: E402
    export_paths_summary,
    init_ee,
    load_flood_site,
    load_site_roi,
)
from qa_local import qa_gfd  # noqa: E402

SCALE_M = 30
CRS = "EPSG:4326"


def gfd_robust_normalize(count: Any, roi: Any, ee: Any) -> Any:
    """Keep zeros as 0; stretch positive counts to [0,1] via P95+log1p+minmax."""
    pos_mask = count.gt(0)
    count_pos = count.updateMask(pos_mask)
    p95 = ee.Number(
        count_pos.reduceRegion(
            reducer=ee.Reducer.percentile([95]),
            geometry=roi,
            scale=SCALE_M,
            maxPixels=1e10,
        ).get("flood_event_count_no_perm_water")
    )
    p95_safe = ee.Number(ee.Algorithms.If(p95, ee.Algorithms.If(p95.gt(0), p95, 1), 1))
    count_cap = count_pos.min(p95_safe)
    count_log = count_cap.add(1).log()
    mm = count_log.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=roi,
        scale=SCALE_M,
        maxPixels=1e10,
    )
    log_min = ee.Number(mm.get("flood_event_count_no_perm_water_min"))
    log_max = ee.Number(mm.get("flood_event_count_no_perm_water_max"))
    den = log_max.subtract(log_min)
    norm_pos = ee.Image(
        ee.Algorithms.If(
            den.lte(1e-6),
            ee.Image.constant(1).updateMask(pos_mask),
            count_log.subtract(log_min).divide(den).clamp(0, 1).updateMask(pos_mask),
        )
    )
    return norm_pos.unmask(0).rename("flood_event_count_norm_0_1")


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
    count_path = input_dir / layers["gfd_count"]
    norm_path = input_dir / layers["gfd_count_norm"]
    once_path = input_dir / layers["gfd_observed_once"]

    if not qa_only:
        ee = init_ee(authenticate=authenticate)
        roi = load_site_roi(site_config, ee)
        print(f"Global Flood Database → {display} ({site})")
        gfd = ee.ImageCollection("GLOBAL_FLOOD_DB/MODIS_EVENTS/V1")
        flood_only = gfd.map(
            lambda img: img.select("flooded")
            .updateMask(img.select("jrc_perm_water").neq(1))
            .rename("flooded_no_perm_water")
            .copyProperties(img, img.propertyNames())
        )
        count = flood_only.sum().rename("flood_event_count_no_perm_water")
        observed_once = count.gt(0).rename("flood_observed_once")
        count_norm = gfd_robust_normalize(count, roi, ee)
        for img, key, desc in [
            (count.toFloat().clip(roi), "gfd_count", f"gfd_flood_event_count_no_perm_water_{prefix}"),
            (count_norm.toFloat().clip(roi), "gfd_count_norm", f"gfd_flood_event_count_norm_{prefix}"),
            (observed_once.toFloat().clip(roi), "gfd_observed_once", f"gfd_flood_observed_once_{prefix}"),
        ]:
            export_image_to_input(
                img,
                filename=layers[key],
                region=roi,
                scale=SCALE_M,
                input_dir=input_dir,
                crs=CRS,
                description=desc,
                drive_folder="OEF_GlobalFloodDB",
            )
    else:
        for p in (count_path, norm_path, once_path):
            if not p.is_file():
                raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {p}")

    export_paths_summary(site_config, ["gfd_count", "gfd_count_norm", "gfd_observed_once"])
    if write_qa:
        qa_gfd(
            count_path,
            norm_path,
            once_path,
            site_config,
            display=str(display),
        )
    return [count_path, norm_path, once_path]


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
