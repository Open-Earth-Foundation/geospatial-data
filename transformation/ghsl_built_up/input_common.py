"""Shared helpers for GHSL built-up site extract CLIs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

GHSL_BUILT_UP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = GHSL_BUILT_UP_ROOT.parent.parent
FLOOD_HAZARD_ROOT = GHSL_BUILT_UP_ROOT.parent / "flood_hazard"
NBS_ROOT = GHSL_BUILT_UP_ROOT.parent / "nbs_screening"

DEFAULT_GHSL_YEAR = 2025
SCALE_M = 100
CRS = "EPSG:4326"
EE_IMAGE = "JRC/GHSL/P2023A/GHS_BUILT_S"


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


def ensure_flood_hazard_on_path() -> None:
    if str(FLOOD_HAZARD_ROOT) not in sys.path:
        sys.path.insert(0, str(FLOOD_HAZARD_ROOT))


def load_flood_site(site: str | None = None) -> dict[str, Any]:
    import importlib.util

    path = FLOOD_HAZARD_ROOT / "site_config.py"
    spec = importlib.util.spec_from_file_location("_flood_site_config", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"Could not load flood site_config from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    slug = site or os.environ.get("FLOODS_SITE") or os.environ.get("NBS_SITE", "porto_alegre")
    return module.load_site_config(slug, FLOOD_HAZARD_ROOT)


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

    path = FLOOD_HAZARD_ROOT / "input_common.py"
    spec = importlib.util.spec_from_file_location("_flood_input_common", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"Could not load flood input_common from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_site_roi(site_config, ee)


def ghsl_output_path(site: str, *, prefix: str | None = None) -> Path:
    """NBS catalog target: ``sites/{site}/data/output/{prefix}_ghsl_built_up_100m.tif``."""
    stem = prefix or site
    return (
        GHSL_BUILT_UP_ROOT
        / "sites"
        / site
        / "data"
        / "output"
        / f"{stem}_ghsl_built_up_100m.tif"
    )


def ghsl_qa_dir(site: str) -> Path:
    return GHSL_BUILT_UP_ROOT / "sites" / site / "data" / "intermediate" / "qa_inputs"


def load_ghsl_site(site: str | None = None, *, ghsl_year: int = DEFAULT_GHSL_YEAR) -> dict[str, Any]:
    """Flood-hazard site config plus GHSL output paths (NBS catalog layout)."""
    flood_cfg = load_flood_site(site)
    slug = str(flood_cfg.get("site_slug") or site or "porto_alegre")
    prefix = str(flood_cfg.get("output_prefix") or slug)
    out_path = ghsl_output_path(slug, prefix=prefix)
    qa_dir = ghsl_qa_dir(slug)
    return {
        **flood_cfg,
        "ghsl_year": int(ghsl_year),
        "ghsl_output_path": out_path,
        "ghsl_output_path_abs": str(out_path.resolve()),
        "ghsl_qa_dir_abs": str(qa_dir.resolve()),
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
