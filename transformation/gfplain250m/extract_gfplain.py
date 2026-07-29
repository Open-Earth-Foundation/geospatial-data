#!/usr/bin/env python3
"""Export GFPLAIN250m floodplain mask into flood_hazard site data/input/.

Example:
  python transformation/gfplain250m/extract_gfplain.py --site plymouth
  python transformation/gfplain250m/extract_gfplain.py --site plymouth --qa-only
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
    export_paths_summary,
    init_ee,
    load_flood_site,
    load_site_roi,
)
from qa_local import qa_gfplain  # noqa: E402

SCALE_M = 250
CRS = "EPSG:4326"


def run(
    site: str,
    *,
    authenticate: bool = False,
    write_qa: bool = True,
    qa_only: bool = False,
) -> Path:
    site_config = load_flood_site(site)
    display = site_config.get("display_name") or site
    input_dir = Path(site_config["paths_abs"]["data_input"])
    prefix = site_config["output_prefix"]
    filename = site_config["layers"]["gfplain"]
    out_path = input_dir / filename

    if not qa_only:
        ee = init_ee(authenticate=authenticate)
        roi = load_site_roi(site_config, ee)
        print(f"GFPLAIN250m → {display} ({site})")
        gfplain = ee.Image("IAHS/GFPLAIN250/v0").clip(roi)
        gfplain_1 = ee.Image.constant(1).updateMask(gfplain.mask()).rename("gfplain_1")
        export_image_to_input(
            gfplain_1,
            filename=filename,
            region=roi,
            scale=SCALE_M,
            input_dir=input_dir,
            crs=CRS,
            description=f"gfplain_250m_{prefix}",
            drive_folder="OEF_GFPLAIN250",
        )
    elif not out_path.is_file():
        raise FileNotFoundError(f"Missing GeoTIFF for --qa-only: {out_path}")

    export_paths_summary(site_config, ["gfplain"])
    if write_qa:
        qa_gfplain(out_path, site_config, display=str(display))
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: FLOODS_SITE)")
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true", help="Skip SVG QA maps/hists")
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Skip GEE export; rebuild QA from existing GeoTIFF",
    )
    args = parser.parse_args(argv)
    site = args.site or os.environ.get("FLOODS_SITE", "porto_alegre")
    try:
        out = run(
            site,
            authenticate=args.authenticate,
            write_qa=not args.no_qa,
            qa_only=args.qa_only,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"\nDone: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
