#!/usr/bin/env python3
"""Extract NBS flood mechanism screening input layers for configured cities.

Chains per-layer CLIs (D2–D8 + flood prep) in hazard-specific order. Does not
compute the mechanism grid — use ``run_pipeline.py`` or ``compute_mechanism.py``
after inputs are ready.

Examples:
  python transformation/nbs_screening/flood/extract_mechanism_inputs.py --site richfield
  python transformation/nbs_screening/flood/extract_mechanism_inputs.py --country "United States"
  python transformation/nbs_screening/flood/extract_mechanism_inputs.py --site richfield --only merit_hydro,gsw
  python transformation/nbs_screening/flood/extract_mechanism_inputs.py --site richfield --dry-run
"""

from __future__ import annotations

import sys
from pathlib import Path

FLOOD_ROOT = Path(__file__).resolve().parent
NBS_ROOT = FLOOD_ROOT.parent
if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from extract_common import make_step, run_cli  # noqa: E402

STEPS = (
    make_step("osm_rivers", "nbs_screening/flood/extract_osm_rivers.py", note="riverine distance"),
    make_step(
        "dem_diagnostics",
        "copernicus_dem/compute_dem_diagnostics.py",
        note="relative elevation + depression",
    ),
    make_step("merit_hydro", "merit_hydro/extract_merit_hydro.py", note="UPA + ELV"),
    make_step("gsw", "jrc_global_surface_water/extract_gsw.py", note="JRC surface water"),
    make_step("chirps_daily", "chirps_daily/extract_chirps_daily.py", note="RX1/RX5/R90p 2024"),
    make_step("ghsl", "ghsl_built_up/extract_ghsl_built_up.py", note="impervious proxy"),
    make_step("dynamic_world", "dynamic_world/extract_dw_mode.py", note="10 m + 250 m mode"),
    make_step("slope", "copernicus_dem/extract_slope.py", note="poa_slope"),
    make_step("clay", "soilgrids/extract_clay.py", note="soilgrids_clay"),
)


def main(argv: list[str] | None = None) -> int:
    return run_cli("flood", STEPS, argv=argv, doc=__doc__)


if __name__ == "__main__":
    raise SystemExit(main())
