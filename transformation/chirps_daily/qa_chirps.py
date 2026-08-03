"""Local QA for CHIRPS daily extreme-index exports."""

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
    qa_dir = Path(site_config["chirps_qa_dir_abs"])
    qa_dir.mkdir(parents=True, exist_ok=True)
    return {
        **site_config,
        "paths_abs": {
            **(site_config.get("paths_abs") or {}),
            "data_intermediate": str(qa_dir.parent),
        },
    }


def qa_chirps_rx1day(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    year = site_config.get("chirps_year", 2024)
    return qa_continuous(
        tif,
        _qa_cfg(site_config),
        display=display,
        prefix="chirps_rx1day",
        title=f"CHIRPS RX1day ({year})",
        xlabel="Max 1-day precipitation (mm)",
        legend_label="RX1day (mm)",
        vlines=[50, 100, 150],
        note="NBS pluvial signal when grid mean ≥ 50 mm (see nbs_rules).",
    )


def qa_chirps_rx5day(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    year = site_config.get("chirps_year", 2024)
    return qa_continuous(
        tif,
        _qa_cfg(site_config),
        display=display,
        prefix="chirps_rx5day",
        title=f"CHIRPS RX5day ({year})",
        xlabel="Max 5-day precipitation (mm)",
        legend_label="RX5day (mm)",
        vlines=[100, 150, 200],
        note="NBS pluvial signal when grid mean ≥ 100 mm (see nbs_rules).",
    )


def qa_chirps_r90p(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    year = site_config.get("chirps_year", 2024)
    return qa_continuous(
        tif,
        _qa_cfg(site_config),
        display=display,
        prefix="chirps_r90p",
        title=f"CHIRPS R90p ({year})",
        xlabel="90th percentile daily precipitation (mm)",
        legend_label="R90p (mm)",
        vlines=[10, 25, 50],
        note="Used as alternate r90p proxy in landslide mechanism screening.",
    )


QA_BY_LAYER = {
    "rx1day": qa_chirps_rx1day,
    "rx5day": qa_chirps_rx5day,
    "r90p": qa_chirps_r90p,
}
