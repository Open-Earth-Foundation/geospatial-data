"""Shared helpers for MERIT Hydro site extract CLIs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Literal

MERIT_HYDRO_ROOT = Path(__file__).resolve().parent
REPO_ROOT = MERIT_HYDRO_ROOT.parent.parent
FLOOD_HAZARD_ROOT = MERIT_HYDRO_ROOT.parent / "flood_hazard"
NBS_ROOT = MERIT_HYDRO_ROOT.parent / "nbs_screening"

CRS = "EPSG:4326"
SCALE_M = 90
EE_IMAGE = "MERIT/Hydro/v1_0_1"

MeritLayer = Literal["upa", "elv"]
MERIT_LAYERS: tuple[MeritLayer, ...] = ("upa", "elv")
MERIT_BANDS: dict[MeritLayer, str] = {"upa": "upa", "elv": "elv"}


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


def merit_output_path(site: str, *, prefix: str, layer: MeritLayer) -> Path:
    suffix = {"upa": "merit_hydro_upa_90m", "elv": "merit_hydro_elv_90m"}[layer]
    return MERIT_HYDRO_ROOT / "sites" / site / "data" / "output" / f"{prefix}_{suffix}.tif"


def merit_qa_dir(site: str) -> Path:
    return MERIT_HYDRO_ROOT / "sites" / site / "data" / "intermediate" / "qa_inputs"


def load_merit_site(site: str | None = None) -> dict[str, Any]:
    flood_cfg = load_flood_site(site)
    slug = str(flood_cfg.get("site_slug") or site or "porto_alegre")
    prefix = str(flood_cfg.get("output_prefix") or slug)
    paths = {layer: merit_output_path(slug, prefix=prefix, layer=layer) for layer in MERIT_LAYERS}
    qa_dir = merit_qa_dir(slug)
    return {
        **flood_cfg,
        "merit_paths": paths,
        "merit_paths_abs": {k: str(v.resolve()) for k, v in paths.items()},
        "merit_qa_dir_abs": str(qa_dir.resolve()),
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
