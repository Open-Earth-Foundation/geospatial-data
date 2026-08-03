"""Shared helpers for Dynamic World site extract CLIs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

DYNAMIC_WORLD_ROOT = Path(__file__).resolve().parent
REPO_ROOT = DYNAMIC_WORLD_ROOT.parent.parent
LANDSLIDE_HAZARD_ROOT = DYNAMIC_WORLD_ROOT.parent / "landslide_hazard"
NBS_ROOT = DYNAMIC_WORLD_ROOT.parent / "nbs_screening"

DEFAULT_DW_YEAR = 2023
CRS = "EPSG:4326"
SCALE_10M = 10
SCALE_250M = 250
EE_COLLECTION = "GOOGLE/DYNAMICWORLD/V1"


def reexec_with_repo_venv_if_needed(*modules: str) -> None:
    """If required packages are missing, re-launch under ``geospatial-data/.venv``."""
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


def ensure_landslide_on_path() -> None:
    if str(LANDSLIDE_HAZARD_ROOT) not in sys.path:
        sys.path.insert(0, str(LANDSLIDE_HAZARD_ROOT))


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


def nbs_mode_10m_path(site: str, *, prefix: str, year: int) -> Path:
    return (
        DYNAMIC_WORLD_ROOT
        / "sites"
        / site
        / "data"
        / "output"
        / f"{prefix}_dynamicworld_{year}.tif"
    )


def nbs_mode_250m_path(site: str, *, prefix: str, year: int) -> Path:
    return (
        DYNAMIC_WORLD_ROOT
        / "sites"
        / site
        / "data"
        / "output"
        / f"{prefix}_dw_mode_250m_{year}.tif"
    )


def dw_qa_dir(site: str) -> Path:
    return DYNAMIC_WORLD_ROOT / "sites" / site / "data" / "intermediate" / "qa_inputs"


def landslide_dw_path(site_config: dict[str, Any]) -> Path:
    input_dir = Path(site_config["paths_abs"]["data_input"])
    filename = str((site_config.get("layers") or {})["dw_mode"])
    return input_dir / filename


def load_dw_site(site: str | None = None, *, dw_year: int | None = None) -> dict[str, Any]:
    """Landslide site config plus NBS catalog Dynamic World output paths."""
    ls_cfg = load_landslide_site(site)
    slug = str(ls_cfg.get("site_slug") or site or "porto_alegre")
    prefix = str(ls_cfg.get("output_prefix") or slug)
    year = int(dw_year if dw_year is not None else ls_cfg.get("dw_year", DEFAULT_DW_YEAR))
    mode_10m = nbs_mode_10m_path(slug, prefix=prefix, year=year)
    mode_250m = nbs_mode_250m_path(slug, prefix=prefix, year=year)
    ls_dw = landslide_dw_path(ls_cfg)
    qa_dir = dw_qa_dir(slug)
    return {
        **ls_cfg,
        "dw_year": year,
        "dw_mode_10m_path": mode_10m,
        "dw_mode_10m_path_abs": str(mode_10m.resolve()),
        "dw_mode_250m_path": mode_250m,
        "dw_mode_250m_path_abs": str(mode_250m.resolve()),
        "dw_landslide_path": ls_dw,
        "dw_landslide_path_abs": str(ls_dw.resolve()),
        "dw_qa_dir_abs": str(qa_dir.resolve()),
    }


def resolve_site_slugs(
    *,
    site: str | None = None,
    sites_csv: str | None = None,
    all_configured: bool = False,
    country: str | None = None,
    exclude: tuple[str, ...] = (),
) -> list[str]:
    """Resolve site list from NBS registry (``config/sites/{slug}.yaml``)."""
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
