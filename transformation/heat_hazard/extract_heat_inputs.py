#!/usr/bin/env python3
"""Run heat hazard input extractors for one city (GEE → data/input/).

Order: MODIS (coarse, fast) → Landsat (30 m).
Each extractor also writes local QA SVGs under ``data/intermediate/qa_inputs/``.

Example:
  python transformation/heat_hazard/extract_heat_inputs.py --site plymouth
  python transformation/heat_hazard/extract_heat_inputs.py --site plymouth --only modis
  python transformation/heat_hazard/extract_heat_inputs.py --site plymouth --qa-only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

HEAT_HAZARD_ROOT = Path(__file__).resolve().parent
TRANSFORMATION = HEAT_HAZARD_ROOT.parent

EXTRACTORS: dict[str, Path] = {
    "modis": TRANSFORMATION / "modis_lst" / "extract_modis_lst.py",
    "landsat": TRANSFORMATION / "landsat_lst" / "extract_landsat_lst.py",
}
DEFAULT_ORDER = ["modis", "landsat"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: HEAT_SITE)")
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

    site = args.site or os.environ.get("HEAT_SITE") or os.environ.get("FLOODS_SITE", "porto_alegre")
    keys = DEFAULT_ORDER
    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        unknown = [k for k in keys if k not in EXTRACTORS]
        if unknown:
            print(f"ERROR: unknown extractors: {unknown}", file=sys.stderr)
            return 1

    print(f"Extracting heat inputs for site={site}: {keys}")
    for key in keys:
        script = EXTRACTORS[key]
        cmd = [sys.executable, str(script), "--site", site]
        if args.authenticate:
            cmd.append("--authenticate")
        if args.no_qa:
            cmd.append("--no-qa")
        if args.qa_only:
            cmd.append("--qa-only")
        print(f"\n=== {key}: {script.name} ===")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"ERROR: {key} failed with exit {result.returncode}", file=sys.stderr)
            return result.returncode

    print("\nAll heat input extracts finished.")
    print(f"QA SVGs (if enabled): heat_hazard/sites/{site}/data/intermediate/qa_inputs/")
    print(
        "Next: python transformation/heat_hazard/compute_heat_hazard.py "
        f"--site {site}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
