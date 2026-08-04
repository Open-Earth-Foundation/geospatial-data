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
# Legacy alias — prefer ``sites_for_country("United States")`` or ``list_configured_sites()``.
MN_SITES = ("apple_valley", "edina", "plymouth", "richfield", "rochester")


def list_configured_sites(nbs_root: Path | None = None) -> tuple[str, ...]:
    """All city slugs with ``config/sites/{slug}.yaml``."""
    root = Path(nbs_root or find_nbs_screening_root()).resolve()
    sites_dir = root / "config" / "sites"
    if not sites_dir.is_dir():
        return ()
    return tuple(sorted(p.stem for p in sites_dir.glob("*.yaml") if p.is_file()))


def sites_for_country(country: str, nbs_root: Path | None = None) -> tuple[str, ...]:
    """Configured sites whose YAML ``country`` field matches (case-insensitive)."""
    target = country.strip().lower()
    if not target:
        return ()
    out: list[str] = []
    for slug in list_configured_sites(nbs_root):
        cfg = load_site_config(slug, str(nbs_root) if nbs_root else None)
        if str(cfg.get("country", "")).strip().lower() == target:
            out.append(slug)
    return tuple(out)


def resolve_site_slugs(
    *,
    site: str | None = None,
    sites_csv: str | None = None,
    all_configured: bool = False,
    country: str | None = None,
    exclude: tuple[str, ...] = (),
    nbs_root: Path | None = None,
) -> list[str]:
    """Resolve a site list from CLI flags; validates against configured YAMLs."""
    if sites_csv:
        selected = [s.strip() for s in sites_csv.split(",") if s.strip()]
    elif site:
        selected = [site.strip()]
    elif country:
        selected = list(sites_for_country(country, nbs_root))
    elif all_configured:
        selected = list(list_configured_sites(nbs_root))
    else:
        selected = list(list_configured_sites(nbs_root))

    configured = set(list_configured_sites(nbs_root))
    unknown = [s for s in selected if s not in configured]
    if unknown:
        raise ValueError(
            f"Unknown site(s): {unknown}. "
            f"Configured: {', '.join(sorted(configured))}"
        )

    if exclude:
        skip = set(exclude)
        selected = [s for s in selected if s not in skip]
    return selected


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


def hazard_module_root(hazard: HazardKind, nbs_root: Path | None = None) -> Path:
    """N10 hazard CLI module root: ``nbs_screening/{hazard}/``."""
    root = Path(nbs_root or find_nbs_screening_root()).resolve()
    return root / hazard


def site_module_root(
    site: str,
    hazard: HazardKind = "flood",
    nbs_root: Path | None = None,
) -> Path:
    """N10 per-site runtime root: ``{hazard}/sites/{site}/`` (flat, like flood_hazard)."""
    return hazard_module_root(hazard, nbs_root) / "sites" / site


def _legacy_n9_flood_site_root(site: str, nbs_root: Path) -> Path:
    """N9 intermediate: ``sites/{site}/floods/`` (deprecated)."""
    return nbs_root / "sites" / site / "floods"


def _legacy_flood_output_dir(site: str, nbs_root: Path) -> Path:
    """Pre-N9 flat layout: ``sites/{site}/data/output`` (flood only)."""
    return nbs_root / "sites" / site / "data" / "output"


def _legacy_flood_publish_dir(site: str, nbs_root: Path, hazard: HazardKind) -> Path:
    return nbs_root / "sites" / site / "out" / f"{hazard}_mechanism_type"


def _legacy_flood_osm_path(site: str, nbs_root: Path) -> Path:
    return nbs_root / "sites" / site / "data" / "input" / f"osm_waterways_{site}.json"


def _legacy_n9_flood_osm_path(site: str, nbs_root: Path) -> Path:
    return _legacy_n9_flood_site_root(site, nbs_root) / "data" / "input" / f"osm_waterways_{site}.json"


def _first_existing_dir(*candidates: Path) -> Path:
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]


def site_output_dir(
    site: str,
    hazard: HazardKind = "flood",
    nbs_root: Path | None = None,
) -> Path:
    """N10 write path: ``{hazard}/sites/{site}/data/output``."""
    return site_module_root(site, hazard, nbs_root) / "data" / "output"


def resolve_site_output_dir(
    site: str,
    hazard: HazardKind = "flood",
    nbs_root: Path | None = None,
) -> Path:
    """Resolve existing mechanism outputs (N10 → N9 → legacy flat)."""
    root = Path(nbs_root or find_nbs_screening_root()).resolve()
    candidates = [site_output_dir(site, hazard, root)]
    if hazard == "flood":
        candidates.append(_legacy_n9_flood_site_root(site, root) / "data" / "output")
        candidates.append(_legacy_flood_output_dir(site, root))
    return _first_existing_dir(*candidates)


def site_publish_dir(site: str, hazard: HazardKind = "flood", nbs_root: Path | None = None) -> Path:
    """N10 publish staging: ``{hazard}/sites/{site}/out/{hazard}_mechanism_type``."""
    return site_module_root(site, hazard, nbs_root) / "out" / f"{hazard}_mechanism_type"


def resolve_site_publish_dir(
    site: str,
    hazard: HazardKind = "flood",
    nbs_root: Path | None = None,
) -> Path:
    """Resolve existing publish staging (N10 → legacy flat)."""
    root = Path(nbs_root or find_nbs_screening_root()).resolve()
    candidates = [site_publish_dir(site, hazard, root)]
    if hazard == "flood":
        candidates.append(_legacy_flood_publish_dir(site, root, hazard))
    return _first_existing_dir(*candidates)


def site_input_dir(
    site: str,
    hazard: HazardKind = "flood",
    nbs_root: Path | None = None,
) -> Path:
    """N10 input path: ``{hazard}/sites/{site}/data/input``."""
    return site_module_root(site, hazard, nbs_root) / "data" / "input"


def site_osm_rivers_path(site: str, nbs_root: Path | None = None) -> Path:
    """N10 default OSM extract target: ``flood/sites/{site}/data/input/osm_waterways_{site}.json``."""
    return site_input_dir(site, "flood", nbs_root) / f"osm_waterways_{site}.json"


def osm_rivers_write_path(site: str, nbs_root: Path | None = None) -> Path:
    """OSM extract write path: YAML ``osm_waterways.local`` when set, else N9 default."""
    cfg = load_site_config(site, str(nbs_root) if nbs_root else None)
    repo_root = Path(cfg["repo_root"])
    local_rel = (cfg.get("osm_waterways") or {}).get("local")
    if local_rel:
        path = Path(str(local_rel)).expanduser()
        if not path.is_absolute():
            path = repo_root / path
        return path
    return site_osm_rivers_path(str(cfg["site_slug"]), nbs_root)


def resolve_osm_rivers_path(site: str, nbs_root: Path | None = None) -> Path | None:
    """Resolved OSM waterways JSON for riverine distance (``None`` if not on disk)."""
    cfg = load_site_config(site, str(nbs_root) if nbs_root else None)
    repo_root = Path(cfg["repo_root"])
    osm_cfg = cfg.get("osm_waterways") or {}
    local_rel = osm_cfg.get("local")
    if local_rel:
        path = Path(str(local_rel)).expanduser()
        if not path.is_absolute():
            path = repo_root / path
        if path.is_file():
            return path.resolve()

    default = site_osm_rivers_path(str(cfg["site_slug"]), nbs_root)
    if default.is_file():
        return default.resolve()

    root = Path(nbs_root or find_nbs_screening_root()).resolve()
    slug = str(cfg["site_slug"])
    n9 = _legacy_n9_flood_osm_path(slug, root)
    if n9.is_file():
        return n9.resolve()
    legacy = _legacy_flood_osm_path(slug, root)
    if legacy.is_file():
        return legacy.resolve()
    return None


def site_boundary_path(site: str, repo_root: Path | None = None) -> Path:
    """City boundary GeoJSON shared with flood_hazard site layouts."""
    root = Path(repo_root or find_repo_root()).resolve()
    return root / "transformation" / "flood_hazard" / "sites" / site / "boundary" / "site.geojson"
