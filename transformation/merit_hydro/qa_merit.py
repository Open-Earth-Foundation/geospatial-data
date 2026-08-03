"""Local QA for MERIT Hydro UPA/ELV exports."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

LS_QA = Path(__file__).resolve().parents[1] / "landslide_hazard" / "qa_local.py"
_spec = importlib.util.spec_from_file_location("_landslide_qa_local", LS_QA)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError(f"Could not load landslide QA helper at {LS_QA}")
_landslide_qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_landslide_qa)
qa_continuous = _landslide_qa.qa_continuous


def _qa_cfg(site_config: dict[str, Any]) -> dict[str, Any]:
    qa_dir = Path(site_config["merit_qa_dir_abs"])
    qa_dir.mkdir(parents=True, exist_ok=True)
    return {
        **site_config,
        "paths_abs": {
            **(site_config.get("paths_abs") or {}),
            "data_intermediate": str(qa_dir.parent),
        },
    }


def qa_merit_upa(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    return qa_continuous(
        tif,
        _qa_cfg(site_config),
        display=display,
        prefix="merit_upa",
        title="MERIT Hydro upstream area (90 m)",
        xlabel="Upstream drainage area (km²)",
        legend_label="UPA (km²)",
        note="NBS landslide grid uses upstream_area_km2_mean from this layer.",
    )


def qa_merit_elv(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    return qa_continuous(
        tif,
        _qa_cfg(site_config),
        display=display,
        prefix="merit_elv",
        title="MERIT Hydro elevation (90 m)",
        xlabel="Elevation (m)",
        legend_label="Elevation (m)",
        note="Auxiliary MERIT Hydro elevation for NBS catalog completeness.",
    )


QA_BY_LAYER = {
    "upa": qa_merit_upa,
    "elv": qa_merit_elv,
}
