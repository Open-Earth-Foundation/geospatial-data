#!/usr/bin/env python3
"""Extract OSM waterways for NBS grid screening (riverine distance proxy).

Fetches river/stream/canal ways from the Overpass API inside the city boundary
(+ buffer) and writes POA-compatible JSON for ``catalog_layers.water_stats_at_point``.

Example:
  python transformation/nbs_screening/extract_osm_rivers.py --site richfield
  python transformation/nbs_screening/extract_osm_rivers.py --all-mn
  python transformation/nbs_screening/extract_osm_rivers.py --site edina --buffer-m 1500
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

NBS_ROOT = Path(__file__).resolve().parent
if str(NBS_ROOT) not in sys.path:
    sys.path.insert(0, str(NBS_ROOT))

from catalog_layers import clear_rivers_cache  # noqa: E402
from site_config import (  # noqa: E402
    find_repo_root,
    load_site_config,
    resolve_osm_rivers_path,
    site_boundary_path,
    site_osm_rivers_path,
)

MN_SITES = ("apple_valley", "edina", "plymouth", "richfield", "rochester")
DEFAULT_OVERPASS = "https://overpass-api.de/api/interpreter"
WATERWAY_REGEX = "river|stream|canal"
USER_AGENT = "OEF-NBS-Screening/1.0 (geospatial-data extract_osm_rivers.py)"


def _http_post(url: str, data: str, *, timeout: int = 180) -> dict[str, Any]:
    req = Request(
        url,
        data=data.encode("utf-8"),
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Overpass HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Overpass request failed: {exc}") from exc


def _load_boundary(site: str) -> Any:
    import geopandas as gpd

    path = site_boundary_path(site, find_repo_root(NBS_ROOT))
    if not path.is_file():
        raise FileNotFoundError(f"Missing city boundary: {path}")
    gdf = gpd.read_file(path)
    if gdf.empty:
        raise ValueError(f"Empty boundary GeoJSON: {path}")
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    else:
        gdf = gdf.to_crs(4326)
    return gdf.union_all()


def _buffered_bounds(site_geom: Any, buffer_m: float) -> tuple[float, float, float, float]:
    import geopandas as gpd

    gdf = gpd.GeoDataFrame(geometry=[site_geom], crs=4326)
    metric = gdf.to_crs(3857)
    buffered = metric.buffer(buffer_m)
    wgs = gpd.GeoDataFrame(geometry=buffered, crs=3857).to_crs(4326)
    minx, miny, maxx, maxy = wgs.total_bounds
    return float(minx), float(miny), float(maxx), float(maxy)


def build_overpass_query(bounds: tuple[float, float, float, float]) -> str:
    south, west, north, east = bounds[1], bounds[0], bounds[3], bounds[2]
    return f"""
[out:json][timeout:180];
(
  way["waterway"~"{WATERWAY_REGEX}"]({south},{west},{north},{east});
);
out geom;
""".strip()


def _line_length_km(coords: list[list[float]]) -> float:
    if len(coords) < 2:
        return 0.0
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(coords, coords[1:]):
        lat_mid = math.radians((lat1 + lat2) / 2.0)
        dx = math.radians(lon2 - lon1) * math.cos(lat_mid) * 6371.0
        dy = math.radians(lat2 - lat1) * 6371.0
        total += math.hypot(dx, dy)
    return total


def osm_elements_to_features(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    features: list[dict[str, Any]] = []
    for el in elements:
        if el.get("type") != "way":
            continue
        geom = el.get("geometry")
        if not geom or len(geom) < 2:
            continue
        coords = [[pt["lon"], pt["lat"]] for pt in geom]
        tags = el.get("tags") or {}
        waterway = tags.get("waterway")
        if not waterway:
            continue
        props = {
            "id": f"way/{el.get('id')}",
            "waterway": waterway,
        }
        if name := tags.get("name"):
            props["name"] = name
        for key in ("boat", "tunnel", "layer", "intermittent"):
            if key in tags:
                props[key] = tags[key]
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        )
    return features


def major_river_names(features: list[dict[str, Any]], *, top_n: int = 10) -> list[str]:
    names: list[str] = []
    for feat in features:
        props = feat.get("properties") or {}
        if props.get("waterway") != "river":
            continue
        name = props.get("name")
        if name:
            names.append(str(name))
    if not names:
        for feat in features:
            name = (feat.get("properties") or {}).get("name")
            if name:
                names.append(str(name))
    counts = Counter(names)
    return [name for name, _ in counts.most_common(top_n)]


def build_output_document(
    *,
    site: str,
    display_name: str,
    bounds: tuple[float, float, float, float],
    features: list[dict[str, Any]],
    overpass_url: str,
    buffer_m: float,
) -> dict[str, Any]:
    minx, miny, maxx, maxy = bounds
    total_km = sum(
        _line_length_km(feat["geometry"]["coordinates"]) for feat in features
    )
    type_counts = Counter((f.get("properties") or {}).get("waterway") for f in features)
    return {
        "site_slug": site,
        "display_name": display_name,
        "bounds": {
            "minLng": minx,
            "minLat": miny,
            "maxLng": maxx,
            "maxLat": maxy,
        },
        "totalLengthKm": round(total_km, 2),
        "majorRivers": major_river_names(features),
        "geoJson": {"type": "FeatureCollection", "features": features},
        "metadata": {
            "source": "OpenStreetMap",
            "overpassEndpoint": overpass_url,
            "site": site,
            "bufferM": buffer_m,
            "waterwayFilter": WATERWAY_REGEX,
            "featureCount": len(features),
            "waterwayTypeCounts": dict(type_counts),
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
        },
    }


def extract_osm_rivers(
    site: str,
    *,
    buffer_m: float = 3000.0,
    overpass_url: str = DEFAULT_OVERPASS,
    out_path: Path | None = None,
    dry_run: bool = False,
) -> Path:
    cfg = load_site_config(site)
    site_slug = str(cfg["site_slug"])
    display_name = str(cfg.get("display_name") or site_slug)
    out_path = Path(out_path or site_osm_rivers_path(site_slug))
    boundary = _load_boundary(site_slug)
    bounds = _buffered_bounds(boundary, buffer_m)
    query = build_overpass_query(bounds)

    if dry_run:
        print(f"Site: {site_slug}")
        print(f"Bounds (buffer={buffer_m} m): {bounds}")
        print(f"Overpass: {overpass_url}")
        print(query)
        return out_path

    print(f"Querying Overpass for {display_name} ({site_slug})…")
    payload = _http_post(overpass_url, urlencode({"data": query}))
    elements = payload.get("elements") or []
    features = osm_elements_to_features(elements)
    if not features:
        print(
            f"WARNING: no waterways returned for {site_slug} "
            f"(elements={len(elements)}). Writing empty FeatureCollection."
        )

    doc = build_output_document(
        site=site_slug,
        display_name=display_name,
        bounds=bounds,
        features=features,
        overpass_url=overpass_url,
        buffer_m=buffer_m,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    clear_rivers_cache()
    print(
        f"Wrote {len(features)} waterways ({doc['totalLengthKm']} km) → {out_path} "
        f"types={doc['metadata']['waterwayTypeCounts']}"
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="City slug (e.g. richfield)")
    parser.add_argument("--all-mn", action="store_true", help="Extract all Minnesota cities")
    parser.add_argument(
        "--buffer-m",
        type=float,
        default=3000.0,
        help="Buffer around city boundary for Overpass bbox (default: 3000 m)",
    )
    parser.add_argument(
        "--overpass-url",
        default=DEFAULT_OVERPASS,
        help=f"Overpass interpreter URL (default: {DEFAULT_OVERPASS})",
    )
    parser.add_argument("--out", type=Path, help="Override output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Print Overpass query only")
    args = parser.parse_args(argv)

    if args.all_mn:
        sites = list(MN_SITES)
    elif args.site:
        sites = [args.site]
    else:
        parser.error("Provide --site or --all-mn")

    try:
        for site in sites:
            path = extract_osm_rivers(
                site,
                buffer_m=args.buffer_m,
                overpass_url=args.overpass_url,
                out_path=args.out,
                dry_run=args.dry_run,
            )
            if not args.dry_run and resolve_osm_rivers_path(site) is None:
                print(f"NOTE: {site} waterways not resolved from config path yet.", file=sys.stderr)
            elif not args.dry_run:
                print(f"Resolved for screening: {resolve_osm_rivers_path(site)}")
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
