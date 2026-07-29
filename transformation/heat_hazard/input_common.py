"""Shared helpers for heat hazard input extract CLIs (GEE → sites/<city>/data/input/)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

HEAT_HAZARD_ROOT = Path(__file__).resolve().parent

SEASON_MONTHS: dict[str, list[int]] = {
    "djf": [12, 1, 2],
    "mam": [3, 4, 5],
    "jja": [6, 7, 8],
    "son": [9, 10, 11],
    "annual": list(range(1, 13)),
}


def ensure_heat_hazard_on_path() -> Path:
    root = HEAT_HAZARD_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def load_heat_site(site: str | None = None) -> dict[str, Any]:
    ensure_heat_hazard_on_path()
    from site_config import load_site_config

    slug = site or os.environ.get("HEAT_SITE") or os.environ.get("FLOODS_SITE", "porto_alegre")
    return load_site_config(slug, HEAT_HAZARD_ROOT)


def init_ee(*, project: str | None = None, authenticate: bool = False) -> Any:
    import ee

    proj = project or os.environ.get("EE_PROJECT", "eecc-maureen")
    if authenticate or os.environ.get("EE_AUTHENTICATE", "").strip() in {"1", "true", "yes"}:
        ee.Authenticate()
    ee.Initialize(
        project=proj,
        opt_url="https://earthengine-highvolume.googleapis.com",
    )
    print(f"Earth Engine initialized (project={proj})")
    return ee


def load_site_roi(site_config: dict[str, Any], ee: Any) -> Any:
    boundary_path = Path(site_config["boundary_path_abs"])
    if boundary_path.exists():
        data = json.loads(boundary_path.read_text(encoding="utf-8"))
        if data.get("type") == "FeatureCollection":
            features = [
                ee.Feature(ee.Geometry(feature["geometry"]), feature.get("properties", {}))
                for feature in data.get("features", [])
                if feature.get("geometry")
            ]
            if features:
                return ee.FeatureCollection(features).geometry()
        if data.get("type") == "Feature":
            return ee.Geometry(data["geometry"])
        if data.get("type") in {"Polygon", "MultiPolygon", "GeometryCollection"}:
            return ee.Geometry(data)
    return ee.Geometry.Rectangle(site_config["bbox"])


def season_months(site_config: dict[str, Any]) -> list[int]:
    season = str(site_config.get("season") or "djf").lower()
    months = SEASON_MONTHS.get(season)
    if months is None:
        raise ValueError(f"Unsupported season {season!r}. Expected one of {sorted(SEASON_MONTHS)}")
    return months


def minmax_norm_roi(
    image: Any,
    *,
    band_name: str,
    roi: Any,
    ee: Any,
    scale: int,
    out_name: str | None = None,
) -> Any:
    """Min-max normalize an image to [0,1] using ROI stats at the given scale."""
    roi_stats = image.reduceRegion(
        reducer=ee.Reducer.mean()
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.max(), sharedInputs=True),
        geometry=roi,
        scale=scale,
        maxPixels=1e8,
        bestEffort=True,
    )
    vmin = ee.Number(roi_stats.get(f"{band_name}_min"))
    vmax = ee.Number(roi_stats.get(f"{band_name}_max"))
    name = out_name or f"{band_name}_norm"
    return image.subtract(vmin).divide(vmax.subtract(vmin)).rename(name)


def export_paths_summary(site_config: dict[str, Any], keys: list[str]) -> None:
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers = site_config.get("layers") or {}
    print(f"Input dir: {input_dir}")
    for key in keys:
        name = layers.get(key)
        path = input_dir / str(name) if name else None
        status = "OK" if path and path.is_file() else "MISSING"
        print(f"  [{status}] {key}: {name}")
