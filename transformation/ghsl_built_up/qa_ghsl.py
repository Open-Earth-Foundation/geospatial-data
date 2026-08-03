"""Local QA maps/histograms for GHSL built-up GeoTIFFs."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

LS_QA = Path(__file__).resolve().parents[1] / "landslide_hazard" / "qa_local.py"
_spec = importlib.util.spec_from_file_location("_landslide_qa_local", LS_QA)
if _spec is None or _spec.loader is None:  # pragma: no cover
    raise ImportError(f"Could not load landslide QA helper at {LS_QA}")
_landslide_qa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_landslide_qa)
qa_continuous = _landslide_qa.qa_continuous

# GHSL built_surface is m² per 100 m cell (0–10 000). NBS impervious proxy = mean / 10 000.
BUILT_SURFACE_MAX_M2 = 10_000.0


def qa_ghsl_built_up(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    """Stats + hist + map for GHSL built-up surface export."""
    qa_dir = Path(site_config["ghsl_qa_dir_abs"])
    qa_dir.mkdir(parents=True, exist_ok=True)

    qa_cfg = {
        **site_config,
        "paths_abs": {
            **(site_config.get("paths_abs") or {}),
            "data_intermediate": str(qa_dir.parent),
        },
    }

    outs = qa_continuous(
        tif,
        qa_cfg,
        display=display,
        prefix="ghsl_built_up",
        title="GHSL built-up surface (100 m)",
        xlabel="Built surface (m² per 100 m cell)",
        legend_label="Built surface (m²)",
        vlines=[1000, 2500, 5000, 7500],
        note=(
            "NBS impervious proxy: mean / 10 000 (values 0–10 000 m² per cell). "
            "Used for pluvial runoff screening in flood/heat mechanisms."
        ),
    )

    with rasterio.open(tif) as src:
        arr = src.read(1).astype("float64")
    finite = arr[np.isfinite(arr)]
    if finite.size:
        imperv = min(1.0, max(0.0, float(np.mean(finite)) / BUILT_SURFACE_MAX_M2))
        print(f"  NBS imperv_pct_mean proxy: {imperv:.3f}")

    return outs
