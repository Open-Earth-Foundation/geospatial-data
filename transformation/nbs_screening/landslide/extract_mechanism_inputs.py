#!/usr/bin/env python3
"""Extract NBS landslide mechanism screening input layers for configured cities.

Examples:
  python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --site richfield
  python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --country "United States"
  python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --site plymouth --only landslide_inputs,merit_upa
  python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --site richfield --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

LANDSLIDE_ROOT = Path(__file__).resolve().parent
NBS_ROOT = LANDSLIDE_ROOT.parent
if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from extract_common import make_step, run_cli  # noqa: E402

STEPS = (
    make_step(
        "landslide_inputs",
        "landslide_hazard/extract_landslide_inputs.py",
        note="slope, HAND, clay, r90p clim, NDVI p10, DW",
    ),
    make_step(
        "merit_upa",
        "merit_hydro/extract_merit_hydro.py",
        "--only",
        "upa",
        note="upstream area (grid optional)",
    ),
    make_step("hansen", "hansen_forest_change/extract_treecover2000.py"),
)


def main(argv: list[str] | None = None) -> int:
    return run_cli("landslide", STEPS, argv=argv, doc=__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
