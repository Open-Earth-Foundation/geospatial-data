"""Load per-city NBS grid-screening layer configs.

Site YAMLs live under ``config/sites/{site_slug}.yaml``. Each catalog entry
may specify ``local`` (path relative to geospatial-data root or absolute) and/or
``url`` (S3/HTTP COG). Resolved layer paths prefer an existing local file over
``url``.

Set ``NBS_SITE`` (default ``porto_alegre``) to pick a city without passing
``--site`` on future CLIs.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

try:
    import yaml
except ImportError:  # pragma: no cover - notebooks may run without PyYAML
    yaml = None

HazardKind = Literal["flood", "heat", "landslide"]

DEFAULT_SITE = "porto_alegre"
SITE_ENV_VAR = "NBS_SITE"


def find_nbs_screening_root(start: Path | None = None) -> Path:
    """Resolve ``transformation/nbs_screening`` from *start* or this file."""
    here = Path(__file__).resolve().parent
    if start is None:
        return here
    path = Path(start).resolve()
    for candidate in (path, *path.parents):
        if (candidate / "transformation" / "nbs_screening" / "site_config.py").exists():
            return candidate / "transformation" / "nbs_screening"
        if candidate.name == "nbs_screening" and (candidate / "site_config.py").exists():
            return candidate
    return here


def find_repo_root(nbs_screening_root: Path | None = None) -> Path:
    root = Path(nbs_screening_root or find_nbs_screening_root()).resolve()
    return root.parent.parent


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        raise ImportError(
            "PyYAML is required to load NBS site configs. "
            "Install pyyaml or run from an environment that includes it."
        )
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def site_config_path(site_slug: str, nbs_root: Path | None = None) -> Path:
    root = Path(nbs_root or find_nbs_screening_root()).resolve()
    return root / "config" / "sites" / f"{site_slug}.yaml"


@lru_cache(maxsize=16)
def load_site_config(site_slug: str | None = None, nbs_root: str | None = None) -> dict[str, Any]:
    """Load a city site config with absolute path helpers."""
    root = Path(nbs_root) if nbs_root else find_nbs_screening_root()
    root = root.resolve()
    slug = site_slug or os.environ.get(SITE_ENV_VAR, DEFAULT_SITE)
    config_path = site_config_path(slug, root)
    if not config_path.exists():
        raise FileNotFoundError(f"Missing NBS screening site config: {config_path}")

    config = _load_yaml(config_path)
    repo_root = find_repo_root(root)
    config["site_slug"] = config.get("site_slug") or slug
    config["nbs_screening_root"] = root
    config["repo_root"] = repo_root
    config["config_path"] = config_path
    return config


def _layer_entry(entry: Any) -> dict[str, Any]:
    if entry is None:
        return {}
    if isinstance(entry, str):
        return {"url": entry}
    if isinstance(entry, dict):
        return dict(entry)
    raise TypeError(f"Invalid catalog layer entry: {entry!r}")


def resolve_layer_path(
    entry: Any,
    *,
    repo_root: Path,
) -> str | Path | None:
    """Return local path if configured and present, else ``url``."""
    spec = _layer_entry(entry)
    local = spec.get("local")
    if local:
        local_path = Path(str(local)).expanduser()
        if not local_path.is_absolute():
            local_path = repo_root / local_path
        if local_path.exists():
            return local_path.resolve()
    url = spec.get("url")
    if url:
        return str(url)
    return None


def merged_catalog_entries(config: dict[str, Any], hazard: HazardKind) -> dict[str, Any]:
    """Merge ``catalog.shared`` with ``catalog.{hazard}`` (hazard wins on key clash)."""
    catalog = config.get("catalog") or {}
    shared = catalog.get("shared") or {}
    hazard_layers = catalog.get(hazard) or {}
    merged: dict[str, Any] = {}
    for key, entry in shared.items():
        merged[key] = entry
    for key, entry in hazard_layers.items():
        merged[key] = entry
    return merged


def get_layer_sources(
    hazard: HazardKind = "flood",
    site: str | None = None,
    *,
    nbs_root: Path | None = None,
) -> dict[str, str | Path]:
    """Resolved raster paths for grid screening (local preferred over URL)."""
    config = load_site_config(site, str(nbs_root) if nbs_root else None)
    repo_root = Path(config["repo_root"])
    entries = merged_catalog_entries(config, hazard)
    sources: dict[str, str | Path] = {}
    for layer_id, entry in entries.items():
        resolved = resolve_layer_path(entry, repo_root=repo_root)
        if resolved is not None:
            sources[layer_id] = resolved
    return sources


def get_catalog_urls(
    hazard: HazardKind = "flood",
    site: str | None = None,
) -> dict[str, str]:
    """URL-only catalog view (backward compatible with pre-N1 notebooks)."""
    config = load_site_config(site)
    repo_root = Path(config["repo_root"])
    entries = merged_catalog_entries(config, hazard)
    urls: dict[str, str] = {}
    for layer_id, entry in entries.items():
        spec = _layer_entry(entry)
        local = spec.get("local")
        if local:
            local_path = Path(str(local)).expanduser()
            if not local_path.is_absolute():
                local_path = repo_root / local_path
            if local_path.exists():
                urls[layer_id] = str(local_path.resolve())
                continue
        url = spec.get("url")
        if url:
            urls[layer_id] = str(url)
    return urls


def get_local_layers(
    hazard: HazardKind = "flood",
    site: str | None = None,
) -> dict[str, Path]:
    """Layers that resolve to existing local files only."""
    config = load_site_config(site)
    repo_root = Path(config["repo_root"])
    entries = merged_catalog_entries(config, hazard)
    local: dict[str, Path] = {}
    for layer_id, entry in entries.items():
        spec = _layer_entry(entry)
        rel = spec.get("local")
        if not rel:
            continue
        path = Path(str(rel)).expanduser()
        if not path.is_absolute():
            path = repo_root / path
        if path.exists():
            local[layer_id] = path.resolve()
    return local


def reference_hazard_layer(hazard: HazardKind, config: dict[str, Any] | None = None) -> str:
    """Catalog layer id used as the 250 m reference grid for *hazard*."""
    cfg = config or load_site_config()
    refs = cfg.get("reference_hazard") or {}
    defaults = {
        "flood": "flood_hazard",
        "heat": "heat_hazard",
        "landslide": "landslide_hazard",
    }
    return str(refs.get(hazard) or defaults[hazard])


def open_water_enabled(config: dict[str, Any] | None = None, site: str | None = None) -> bool:
    """Whether permanent open-water masking runs on mechanism exports."""
    cfg = config or load_site_config(site)
    open_water = cfg.get("open_water") or {}
    return bool(open_water.get("enabled", False))


def site_output_dir(site: str, nbs_root: Path | None = None) -> Path:
    """Default grid mechanism outputs: ``sites/{site}/data/output``."""
    root = Path(nbs_root or find_nbs_screening_root()).resolve()
    return root / "sites" / site / "data" / "output"


def site_boundary_path(site: str, repo_root: Path | None = None) -> Path:
    """City boundary GeoJSON shared with flood_hazard site layouts."""
    root = Path(repo_root or find_repo_root()).resolve()
    return root / "transformation" / "flood_hazard" / "sites" / site / "boundary" / "site.geojson"
