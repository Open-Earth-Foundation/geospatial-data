"""Local QA for Hansen treecover2000 exports."""

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


def qa_hansen_treecover2000(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    qa_dir = Path(site_config["hansen_qa_dir_abs"])
    qa_dir.mkdir(parents=True, exist_ok=True)
    qa_cfg = {
        **site_config,
        "paths_abs": {
            **(site_config.get("paths_abs") or {}),
            "data_intermediate": str(qa_dir.parent),
        },
    }
    return qa_continuous(
        tif,
        qa_cfg,
        display=display,
        prefix="hansen_treecover2000",
        title="Hansen tree cover 2000 (30 m)",
        xlabel="Tree cover (%)",
        legend_label="Tree cover (%)",
        vlines=[10, 25, 50, 75],
        note="NBS heat/landslide grid uses treecover2000_mean from this layer (0–100%).",
    )
