#!/usr/bin/env python3
"""Extract NBS heat mechanism screening input layers for configured cities.

Examples:
  python transformation/nbs_screening/heat/extract_mechanism_inputs.py --site richfield
  python transformation/nbs_screening/heat/extract_mechanism_inputs.py --country "United States"
  python transformation/nbs_screening/heat/extract_mechanism_inputs.py --site richfield --only heat_inputs,ndvi_mean
  python transformation/nbs_screening/heat/extract_mechanism_inputs.py --site richfield --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

HEAT_ROOT = Path(__file__).resolve().parent
NBS_ROOT = HEAT_ROOT.parent
if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from extract_common import make_step, run_cli  # noqa: E402

STEPS = (
    make_step(
        "heat_inputs",
        "heat_hazard/extract_heat_inputs.py",
        note="MODIS + Landsat LST → heat_hazard/input",
    ),
    make_step("ghsl", "ghsl_built_up/extract_ghsl_built_up.py"),
    make_step("hansen", "hansen_forest_change/extract_treecover2000.py"),
    make_step("ndvi_mean", "modis_ndvi/extract_ndvi_mean.py"),
    make_step("slope", "copernicus_dem/extract_slope.py"),
    make_step("clay", "soilgrids/extract_clay.py"),
)


def main(argv: list[str] | None = None) -> int:
    return run_cli("heat", STEPS, argv=argv, doc=__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
