"""Shared helpers for flood hazard input extract CLIs (GEE → sites/<city>/data/input/)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

FLOOD_HAZARD_ROOT = Path(__file__).resolve().parent


def ensure_flood_hazard_on_path() -> Path:
    root = FLOOD_HAZARD_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def load_flood_site(site: str | None = None) -> dict[str, Any]:
    """Load flood_hazard site config; site defaults to FLOODS_SITE / porto_alegre."""
    ensure_flood_hazard_on_path()
    from site_config import load_site_config

    slug = site or os.environ.get("FLOODS_SITE", "porto_alegre")
    return load_site_config(slug, FLOOD_HAZARD_ROOT)


def init_ee(*, project: str | None = None, authenticate: bool = False) -> Any:
    """Initialize Earth Engine. Project from EE_PROJECT or default OEF project."""
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
    """Site polygon when available; else bbox rectangle."""
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


def depth_to_impact_score(depth_img: Any, ee: Any, *, band_name: str = "hazard_score") -> Any:
    """Global impact-class normalization used by JRC and Aqueduct (0–1)."""
    score = depth_img.expression(
        "(d <= 0.15) ? 0"
        ": (d <= 0.5) ? 0.25"
        ": (d <= 1.0) ? 0.5"
        ": (d <= 2.0) ? 0.75"
        ": 1",
        {"d": depth_img},
    ).rename(band_name)
    return score.updateMask(depth_img.mask())


def export_paths_summary(site_config: dict[str, Any], keys: list[str]) -> None:
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers = site_config.get("layers") or {}
    print(f"Input dir: {input_dir}")
    for key in keys:
        name = layers.get(key)
        path = input_dir / str(name) if name else None
        status = "OK" if path and path.is_file() else "MISSING"
        print(f"  [{status}] {key}: {name}")
