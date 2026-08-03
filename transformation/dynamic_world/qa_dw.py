"""Local QA for Dynamic World mode exports (10 m and 250 m)."""

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
qa_dw_mode = _landslide_qa.qa_dw_mode


def _qa_cfg(site_config: dict[str, Any]) -> dict[str, Any]:
    qa_dir = Path(site_config["dw_qa_dir_abs"])
    qa_dir.mkdir(parents=True, exist_ok=True)
    return {
        **site_config,
        "paths_abs": {
            **(site_config.get("paths_abs") or {}),
            "data_intermediate": str(qa_dir.parent),
        },
    }


def qa_dw_mode_10m(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    return qa_dw_mode(tif, _qa_cfg(site_config), display=display)


def qa_dw_mode_250m(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    """Reuse class-bar QA; outputs prefixed via landslide helper filenames."""
    outs = qa_dw_mode(tif, _qa_cfg(site_config), display=f"{display} (250 m)")
    renamed: list[Path] = []
    for path in outs:
        if path.name == "bars_dw_mode_classes.svg":
            target = path.parent / "bars_dw_mode_250m_classes.svg"
        elif path.name == "map_dw_mode.svg":
            target = path.parent / "map_dw_mode_250m.svg"
        else:
            target = path
        if target != path:
            path.replace(target)
        renamed.append(target)
    return renamed
