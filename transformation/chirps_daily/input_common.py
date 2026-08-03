"""Shared helpers for CHIRPS daily extreme-index extract CLIs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Literal

CHIRPS_DAILY_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CHIRPS_DAILY_ROOT.parent.parent
FLOOD_HAZARD_ROOT = CHIRPS_DAILY_ROOT.parent / "flood_hazard"
NBS_ROOT = CHIRPS_DAILY_ROOT.parent / "nbs_screening"

CRS = "EPSG:4326"
SCALE_M = 5000
EE_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"
EE_BAND = "precipitation"
DEFAULT_YEAR = 2024

ChirpsLayer = Literal["rx1day", "rx5day", "r90p"]
CHIRPS_LAYERS: tuple[ChirpsLayer, ...] = ("rx1day", "rx5day", "r90p")


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


def chirps_output_path(site: str, *, prefix: str, layer: ChirpsLayer, year: int) -> Path:
    filename = f"{prefix}_{layer}_{year}.tif"
    return CHIRPS_DAILY_ROOT / "sites" / site / "data" / "output" / filename


def chirps_qa_dir(site: str) -> Path:
    return CHIRPS_DAILY_ROOT / "sites" / site / "data" / "intermediate" / "qa_inputs"


def load_chirps_site(site: str | None = None, *, year: int = DEFAULT_YEAR) -> dict[str, Any]:
    flood_cfg = load_flood_site(site)
    slug = str(flood_cfg.get("site_slug") or site or "porto_alegre")
    prefix = str(flood_cfg.get("output_prefix") or slug)
    paths = {
        layer: chirps_output_path(slug, prefix=prefix, layer=layer, year=year)
        for layer in CHIRPS_LAYERS
    }
    qa_dir = chirps_qa_dir(slug)
    return {
        **flood_cfg,
        "chirps_year": int(year),
        "chirps_paths": paths,
        "chirps_paths_abs": {k: str(v.resolve()) for k, v in paths.items()},
        "chirps_qa_dir_abs": str(qa_dir.resolve()),
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


def daily_collection(ee: Any, roi: Any, *, year: int) -> Any:
    return (
        ee.ImageCollection(EE_COLLECTION)
        .select(EE_BAND)
        .filterBounds(roi)
        .filterDate(f"{year}-01-01", f"{year + 1}-01-01")
    )


def compute_rx1day(chirps: Any, ee: Any) -> Any:
    return chirps.max().rename("rx1day")


def compute_r90p(chirps: Any, ee: Any) -> Any:
    return chirps.reduce(ee.Reducer.percentile([90])).rename("r90p")


def compute_rx5day(chirps: Any, ee: Any) -> Any:
    """Maximum 5-day rolling precipitation sum within the filtered daily collection."""
    size = chirps.size()
    listed = chirps.toList(size)

    def _sum_from(start_idx: Any) -> Any:
        start = ee.Number(start_idx)
        window = ee.List.sequence(0, 4).map(lambda offset: ee.Image(listed.get(start.add(offset))))
        return ee.ImageCollection.fromImages(window).sum()

    n_windows = size.subtract(4)
    rolling = ee.ImageCollection(ee.List.sequence(0, n_windows.subtract(1)).map(_sum_from))
    return rolling.max().rename("rx5day")


COMPUTE_FNS = {
    "rx1day": compute_rx1day,
    "rx5day": compute_rx5day,
    "r90p": compute_r90p,
}
