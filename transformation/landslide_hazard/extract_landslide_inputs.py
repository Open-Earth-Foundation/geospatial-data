#!/usr/bin/env python3
"""Run all landslide hazard input extractors for one city (GEE → data/input/).

Order: slope → hand → clay → chirps → ndvi → dynamic_world
(Dynamic World last — finest resolution / slowest).
Each extractor also writes local QA SVGs under ``data/intermediate/qa_inputs/``.

Example:
  python transformation/landslide_hazard/extract_landslide_inputs.py --site plymouth
  python transformation/landslide_hazard/extract_landslide_inputs.py --site plymouth --only slope,hand
  python transformation/landslide_hazard/extract_landslide_inputs.py --site plymouth --qa-only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

LANDSLIDE_HAZARD_ROOT = Path(__file__).resolve().parent
TRANSFORMATION = LANDSLIDE_HAZARD_ROOT.parent

if str(LANDSLIDE_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(LANDSLIDE_HAZARD_ROOT))

from input_common import reexec_with_repo_venv_if_needed  # noqa: E402

reexec_with_repo_venv_if_needed("numpy", "rasterio")

EXTRACTORS: dict[str, Path] = {
    "slope": TRANSFORMATION / "copernicus_dem" / "extract_slope.py",
    "hand": TRANSFORMATION / "merit_hydro" / "extract_hand.py",
    "clay": TRANSFORMATION / "soilgrids" / "extract_clay.py",
    "chirps": TRANSFORMATION / "chirps_r90p" / "extract_chirps_r90p.py",
    "ndvi": TRANSFORMATION / "modis_ndvi" / "extract_ndvi_p10.py",
    "dw": TRANSFORMATION / "dynamic_world" / "extract_dw_mode.py",
}
DEFAULT_ORDER = ["slope", "hand", "clay", "chirps", "ndvi", "dw"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: LANDSLIDES_SITE)")
    parser.add_argument(
        "--only",
        default=None,
        help=f"Comma-separated subset of: {','.join(DEFAULT_ORDER)}",
    )
    parser.add_argument("--authenticate", action="store_true")
    parser.add_argument("--no-qa", action="store_true", help="Skip SVG QA on extractors")
    parser.add_argument(
        "--qa-only",
        action="store_true",
        help="Skip GEE export; rebuild QA from existing GeoTIFFs",
    )
    args = parser.parse_args(argv)

    site = (
        args.site
        or os.environ.get("LANDSLIDES_SITE")
        or os.environ.get("FLOODS_SITE", "porto_alegre")
    )
    keys = DEFAULT_ORDER
    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        unknown = [k for k in keys if k not in EXTRACTORS]
        if unknown:
            print(f"ERROR: unknown extractors: {unknown}", file=sys.stderr)
            return 1

    print(f"Using Python: {sys.executable}", flush=True)
    print(f"Extracting landslide inputs for site={site}: {keys}", flush=True)
    for key in keys:
        script = EXTRACTORS[key]
        cmd = [sys.executable, str(script), "--site", site]
        if args.authenticate:
            cmd.append("--authenticate")
        if args.no_qa:
            cmd.append("--no-qa")
        if args.qa_only:
            cmd.append("--qa-only")
        print(f"\n=== {key}: {script.name} ===", flush=True)
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"ERROR: {key} failed with exit {result.returncode}", file=sys.stderr)
            return result.returncode

    print("\nAll landslide input extracts finished.")
    print(f"QA SVGs (if enabled): landslide_hazard/sites/{site}/data/intermediate/qa_inputs/")
    print(
        "Next: python transformation/landslide_hazard/compute_landslide_hazard.py "
        f"--site {site}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
