"""Resolve batch city entries to configured site slugs."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import CitySpec

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def flood_sites_dir() -> Path:
    return repo_root() / "transformation" / "flood_hazard" / "config" / "sites"


def list_configured_slugs() -> list[str]:
    root = flood_sites_dir()
    if not root.is_dir():
        return []
    return sorted(p.stem for p in root.glob("*.yaml") if p.stem != "README")


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is required to resolve site configs")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML object: {path}")
    return data


def _slugify_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r",?\s*(mn|minnesota|usa|united states)\s*$", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


@dataclass(frozen=True)
class SiteMeta:
    slug: str
    display_name: str
    bbox: tuple[float, float, float, float] | None  # west, south, east, north
    centroid: tuple[float, float] | None  # lon, lat


def _bbox_from_cfg(cfg: dict[str, Any]) -> tuple[float, float, float, float] | None:
    bbox = cfg.get("bbox")
    if isinstance(bbox, dict):
        try:
            return (
                float(bbox["west"]),
                float(bbox["south"]),
                float(bbox["east"]),
                float(bbox["north"]),
            )
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        w, s, e, n = (float(x) for x in bbox)
        return w, s, e, n
    return None


def load_site_meta(slug: str) -> SiteMeta:
    path = flood_sites_dir() / f"{slug}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"No flood_hazard site config for slug={slug!r} ({path})")
    cfg = _load_yaml(path)
    bbox = _bbox_from_cfg(cfg)
    centroid = None
    if bbox:
        w, s, e, n = bbox
        centroid = ((w + e) / 2.0, (s + n) / 2.0)
    display = str(cfg.get("display_name") or cfg.get("site_name") or slug)
    return SiteMeta(slug=slug, display_name=display, bbox=bbox, centroid=centroid)


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass(frozen=True)
class ResolvedCity:
    slug: str
    request_label: str
    resolution: str  # slug | id | name | coordinates
    display_name: str
    stages: tuple[str, ...]
    hazards: tuple[str, ...]
    lat: float | None = None
    lon: float | None = None
    distance_km: float | None = None


def resolve_city(
    city: CitySpec,
    *,
    default_stages: tuple[str, ...],
    default_hazards: tuple[str, ...],
    max_coord_distance_km: float = 75.0,
) -> ResolvedCity:
    """Map a JSON city entry onto an onboarded site slug."""
    configured = set(list_configured_slugs())
    stages = city.stages or default_stages
    hazards = city.hazards or default_hazards

    candidates: list[tuple[str, str, float | None]] = []
    # (slug, resolution, distance_km)

    if city.slug:
        slug = city.slug.strip()
        if slug not in configured:
            raise ValueError(
                f"Unknown slug {slug!r} for {city.label()}. Configured: {sorted(configured)}"
            )
        candidates.append((slug, "slug", None))
    elif city.id and city.id.strip() in configured:
        candidates.append((city.id.strip(), "id", None))
    elif city.name:
        exact = _slugify_name(city.name)
        if exact in configured:
            candidates.append((exact, "name", None))
        else:
            # fuzzy: slug contained in name slug or vice versa
            matches = [s for s in configured if exact in s or s in exact]
            if len(matches) == 1:
                candidates.append((matches[0], "name", None))
            elif len(matches) > 1:
                raise ValueError(
                    f"Ambiguous name {city.name!r} matched {matches}. Pass explicit slug."
                )

    if not candidates and city.lat is not None and city.lon is not None:
        best: tuple[str, float] | None = None
        for slug in configured:
            meta = load_site_meta(slug)
            if not meta.centroid:
                continue
            d = _haversine_km(city.lon, city.lat, meta.centroid[0], meta.centroid[1])
            if best is None or d < best[1]:
                best = (slug, d)
        if best is None:
            raise ValueError(f"No configured site has a bbox to match coordinates for {city.label()}")
        if best[1] > max_coord_distance_km:
            raise ValueError(
                f"Nearest configured site to ({city.lat}, {city.lon}) is "
                f"{best[0]} at {best[1]:.1f} km (> {max_coord_distance_km} km). "
                "Onboard a site YAML first or pass an explicit slug."
            )
        candidates.append((best[0], "coordinates", best[1]))

    if not candidates:
        raise ValueError(
            f"Could not resolve {city.label()} to a configured site. "
            f"Configured slugs: {sorted(configured)}"
        )

    slug, resolution, dist = candidates[0]
    meta = load_site_meta(slug)
    return ResolvedCity(
        slug=slug,
        request_label=city.label(),
        resolution=resolution,
        display_name=meta.display_name,
        stages=stages,
        hazards=hazards,
        lat=city.lat,
        lon=city.lon,
        distance_km=dist,
    )
