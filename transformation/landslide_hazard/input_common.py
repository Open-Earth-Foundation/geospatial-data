"""Shared helpers for landslide hazard input extract CLIs."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

LANDSLIDE_HAZARD_ROOT = Path(__file__).resolve().parent
REPO_ROOT = LANDSLIDE_HAZARD_ROOT.parent.parent  # geospatial-data/


def reexec_with_repo_venv_if_needed(*modules: str) -> None:
    """If required packages are missing, re-launch under ``geospatial-data/.venv``.

    Conda ``(base)`` + a shadow ``python`` on PATH often bypasses the project
    venv; child extractors then fail with ``ModuleNotFoundError``.
    """
    needed = modules or ("numpy", "rasterio")
    missing = []
    for name in needed:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if not missing:
        return

    venv_py = REPO_ROOT / ".venv" / "bin" / "python"
    current = Path(sys.executable).resolve()
    if venv_py.is_file() and current != venv_py.resolve():
        print(
            f"NOTE: {', '.join(missing)} missing in {sys.executable}; "
            f"re-launching with {venv_py}",
            flush=True,
        )
        os.execv(str(venv_py), [str(venv_py), *sys.argv])

    print(
        f"ERROR: missing {', '.join(missing)} in {sys.executable}\n"
        f"  Fix:  {sys.executable} -m pip install numpy rasterio earthengine-api geemap\n"
        f"  Or:   {venv_py} transformation/landslide_hazard/extract_landslide_inputs.py ...",
        file=sys.stderr,
    )
    raise SystemExit(1)


def ensure_landslide_on_path() -> Path:
    root = LANDSLIDE_HAZARD_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def load_landslide_site(site: str | None = None) -> dict[str, Any]:
    ensure_landslide_on_path()
    from site_config import load_site_config

    slug = (
        site
        or os.environ.get("LANDSLIDES_SITE")
        or os.environ.get("FLOODS_SITE", "porto_alegre")
    )
    return load_site_config(slug, LANDSLIDE_HAZARD_ROOT)


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


def season_month_filter(ee: Any, season: str) -> Any:
    """Match notebook calendarRange filters for DJF / JJA."""
    s = season.lower()
    if s == "djf":
        return ee.Filter.calendarRange(12, 2, "month")
    if s == "jja":
        return ee.Filter.calendarRange(6, 8, "month")
    raise ValueError(f"Unsupported season {season!r}; expected djf or jja")


def export_paths_summary(site_config: dict[str, Any], keys: list[str]) -> None:
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers = site_config.get("layers") or {}
    print(f"Input dir: {input_dir}")
    for key in keys:
        name = layers.get(key)
        path = input_dir / str(name) if name else None
        status = "OK" if path and path.is_file() else "MISSING"
        print(f"  [{status}] {key}: {name}")
