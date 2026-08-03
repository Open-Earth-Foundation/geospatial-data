"""Local QA for JRC Global Surface Water exports."""

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
write_class_bars_svg = _landslide_qa.write_class_bars_svg
write_raster_grid_svg = _landslide_qa.write_raster_grid_svg
read_band = _landslide_qa.read_band
print_raster_stats = _landslide_qa.print_raster_stats

TRANSITION_LABELS = {
    0: "no data",
    1: "permanent",
    2: "new permanent",
    3: "lost permanent",
    4: "seasonal permanent",
    5: "new seasonal",
    6: "lost seasonal",
    7: "seasonal to permanent",
    8: "permanent to seasonal",
    9: "ephemeral permanent",
    10: "ephemeral seasonal",
}


def _qa_cfg(site_config: dict[str, Any]) -> dict[str, Any]:
    qa_dir = Path(site_config["gsw_qa_dir_abs"])
    qa_dir.mkdir(parents=True, exist_ok=True)
    return {
        **site_config,
        "paths_abs": {
            **(site_config.get("paths_abs") or {}),
            "data_intermediate": str(qa_dir.parent),
        },
    }


def qa_gsw_occurrence(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    return qa_continuous(
        tif,
        _qa_cfg(site_config),
        display=display,
        prefix="gsw_occurrence",
        title="JRC GSW occurrence (30 m)",
        xlabel="Occurrence (%)",
        legend_label="Occurrence (%)",
        vlines=[10, 50, 90],
        note="NBS low-lying signal when mean ≥ 10%.",
    )


def qa_gsw_seasonality(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    return qa_continuous(
        tif,
        _qa_cfg(site_config),
        display=display,
        prefix="gsw_seasonality",
        title="JRC GSW seasonality (30 m)",
        xlabel="Months water present (0–12)",
        legend_label="Seasonality (months)",
        vlines=[1, 3, 6, 12],
        note="NBS low-lying signal when mean ≥ 1 month.",
    )


def qa_gsw_transition(tif: Path, site_config: dict[str, Any], *, display: str) -> list[Path]:
    qa_dir = Path(site_config["gsw_qa_dir_abs"])
    qa_dir.mkdir(parents=True, exist_ok=True)
    outs: list[Path] = []
    arr, meta = read_band(tif)
    print_raster_stats(arr, label="gsw_transition")
    finite = arr[np.isfinite(arr)]
    labels: list[str] = []
    counts: list[int] = []
    for code in range(11):
        labels.append(f"{code}:{TRANSITION_LABELS[code]}")
        counts.append(int(np.isclose(finite, code, atol=0.1).sum()) if finite.size else 0)
    bars = qa_dir / "bars_gsw_transition_classes.svg"
    write_class_bars_svg(
        labels,
        counts,
        bars,
        title=f"JRC GSW transition — {display}",
        subtitle="transition class counts (0–10)",
        colors=["#cccccc", "#253494", "#2c7fb8", "#41b6c4", "#7fcdbb", "#c7e9b4", "#edf8b1", "#fee090", "#fdae61", "#f46d43", "#d73027"],
    )
    outs.append(bars)
    map_path = qa_dir / "map_gsw_transition.svg"
    write_raster_grid_svg(
        arr,
        map_path,
        title=f"JRC GSW transition — {display}",
        subtitle=f"{meta['shape'][1]}×{meta['shape'][0]} · class 0–10",
        vmin=0.0,
        vmax=10.0,
        legend_label="class",
        max_side=250,
    )
    outs.append(map_path)
    return outs


QA_BY_LAYER = {
    "occurrence": qa_gsw_occurrence,
    "seasonality": qa_gsw_seasonality,
    "transition": qa_gsw_transition,
}
