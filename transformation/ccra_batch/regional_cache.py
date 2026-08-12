"""Regional cache helpers to avoid redundant multi-city prep work.

City-domain normalization remains the scoring contract (see
``docs/ccra_normalization_decision.md``). This module records the **union AOI**
and city manifest for a batch so:

1. Operators can see which cities share a region.
2. Future extractors can fetch once for the union bbox and clip per city.
3. ACS county FIPS can be deduplicated across cities in the same county.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .resolve import ResolvedCity, load_site_meta, repo_root


def regional_cache_dir(region: str, batch_id: str) -> Path:
    safe_region = "".join(c if c.isalnum() or c in "-_" else "_" for c in region)
    safe_batch = "".join(c if c.isalnum() or c in "-_" else "_" for c in batch_id)
    return repo_root() / "cache" / "regions" / safe_region / safe_batch


def _union_bbox(cities: list[ResolvedCity]) -> dict[str, float] | None:
    west = south = east = north = None
    for city in cities:
        meta = load_site_meta(city.slug)
        if not meta.bbox:
            continue
        w, s, e, n = meta.bbox
        west = w if west is None else min(west, w)
        south = s if south is None else min(south, s)
        east = e if east is None else max(east, e)
        north = n if north is None else max(north, n)
    if west is None:
        return None
    return {"west": west, "south": south, "east": east, "north": north}


def _acs_county_fips(slug: str) -> list[str]:
    path = repo_root() / "transformation" / "acs_ev" / "config" / f"{slug}.yaml"
    if not path.is_file():
        return []
    from .resolve import _load_yaml

    cfg = _load_yaml(path)
    # Common shapes: county_fips: "053" | counties: [...] | county_fips: ["053", ...]
    single = cfg.get("county_fips")
    if isinstance(single, (str, int)):
        return [str(single)]
    counties = cfg.get("counties") or single or []
    if isinstance(counties, dict):
        return sorted({str(v) for v in counties.values()})
    if isinstance(counties, list):
        out: list[str] = []
        for item in counties:
            if isinstance(item, dict):
                fips = item.get("fips") or item.get("county_fips")
                if fips:
                    out.append(str(fips))
            else:
                out.append(str(item))
        return sorted(set(out))
    return []


def prepare_regional_cache(
    *,
    region: str,
    batch_id: str,
    cities: list[ResolvedCity],
) -> Path:
    """Write union bbox + manifest. Returns the cache directory."""
    out_dir = regional_cache_dir(region, batch_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    city_rows: list[dict[str, Any]] = []
    fips_to_cities: dict[str, list[str]] = {}
    for city in cities:
        meta = load_site_meta(city.slug)
        fips_list = _acs_county_fips(city.slug)
        for fips in fips_list:
            fips_to_cities.setdefault(fips, []).append(city.slug)
        city_rows.append(
            {
                "slug": city.slug,
                "display_name": city.display_name,
                "request_label": city.request_label,
                "resolution": city.resolution,
                "bbox": (
                    {
                        "west": meta.bbox[0],
                        "south": meta.bbox[1],
                        "east": meta.bbox[2],
                        "north": meta.bbox[3],
                    }
                    if meta.bbox
                    else None
                ),
                "acs_county_fips": fips_list,
                "stages": list(city.stages),
                "hazards": list(city.hazards),
            }
        )

    shared_counties = {k: v for k, v in fips_to_cities.items() if len(v) > 1}
    payload = {
        "region": region,
        "batch_id": batch_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "n_cities": len(cities),
        "union_bbox": _union_bbox(cities),
        "shared_acs_counties": shared_counties,
        "efficiency_notes": [
            "City-domain normalization still applies per city AOI.",
            "union_bbox is the candidate region for a future single GEE extract + per-city clip.",
            "shared_acs_counties lists FIPS used by multiple cities — fetch once, reuse block groups.",
        ],
        "cities": city_rows,
    }
    (out_dir / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if payload["union_bbox"]:
        (out_dir / "union_bbox.json").write_text(
            json.dumps(payload["union_bbox"], indent=2) + "\n", encoding="utf-8"
        )
    return out_dir
