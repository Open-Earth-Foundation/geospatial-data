"""Shared helpers for MODIS NDVI site extract CLIs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

MODIS_NDVI_ROOT = Path(__file__).resolve().parent
REPO_ROOT = MODIS_NDVI_ROOT.parent.parent
LANDSLIDE_HAZARD_ROOT = MODIS_NDVI_ROOT.parent / "landslide_hazard"
NBS_ROOT = MODIS_NDVI_ROOT.parent / "nbs_screening"

CRS = "EPSG:4326"
SCALE_M = 250
EE_COLLECTION = "MODIS/061/MOD13Q1"
EE_BAND = "NDVI"
NDVI_SCALE = 0.0001


def reexec_with_repo_venv_if_needed(*modules: str) -> None:
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
        f"  Fix:  {sys.executable} -m pip install numpy rasterio earthengine-api geemap",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _load_landslide_site_config_module() -> Any:
    import importlib.util

    path = LANDSLIDE_HAZARD_ROOT / "site_config.py"
    spec = importlib.util.spec_from_file_location("_landslide_site_config", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"Could not load landslide site_config from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_landslide_site(site: str | None = None) -> dict[str, Any]:
    module = _load_landslide_site_config_module()
    slug = (
        site
        or os.environ.get("LANDSLIDES_SITE")
        or os.environ.get("FLOODS_SITE")
        or os.environ.get("NBS_SITE", "porto_alegre")
    )
    return module.load_site_config(slug, LANDSLIDE_HAZARD_ROOT)


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
    import importlib.util

    path = LANDSLIDE_HAZARD_ROOT / "input_common.py"
    spec = importlib.util.spec_from_file_location("_landslide_input_common", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"Could not load landslide input_common from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_site_roi(site_config, ee)


def ndvi_mean_output_path(site: str, *, prefix: str) -> Path:
    return (
        MODIS_NDVI_ROOT
        / "sites"
        / site
        / "data"
        / "output"
        / f"{prefix}_modis_ndvi_mean.tif"
    )


def ndvi_qa_dir(site: str) -> Path:
    return MODIS_NDVI_ROOT / "sites" / site / "data" / "intermediate" / "qa_inputs"


def load_ndvi_mean_site(site: str | None = None) -> dict[str, Any]:
    ls_cfg = load_landslide_site(site)
    slug = str(ls_cfg.get("site_slug") or site or "porto_alegre")
    prefix = str(ls_cfg.get("output_prefix") or slug)
    out_path = ndvi_mean_output_path(slug, prefix=prefix)
    qa_dir = ndvi_qa_dir(slug)
    return {
        **ls_cfg,
        "ndvi_output_path": out_path,
        "ndvi_output_path_abs": str(out_path.resolve()),
        "ndvi_qa_dir_abs": str(qa_dir.resolve()),
        "ndvi_start_year": int(ls_cfg.get("start_year", 2015)),
        "ndvi_end_year": int(ls_cfg.get("end_year", 2024)),
    }


def resolve_site_slugs(
    *,
    site: str | None = None,
    sites_csv: str | None = None,
    all_configured: bool = False,
    country: str | None = None,
    exclude: tuple[str, ...] = (),
) -> list[str]:
    if str(NBS_ROOT) not in sys.path:
        sys.path.insert(0, str(NBS_ROOT))
    from site_config import resolve_site_slugs as _resolve

    return _resolve(
        site=site,
        sites_csv=sites_csv,
        all_configured=all_configured,
        country=country,
        exclude=exclude,
    )
