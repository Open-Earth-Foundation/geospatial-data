#!/usr/bin/env python3
"""Compute regional (state-boundary) normalization stats for CCRA dual-product.

Supports heat Landsat/MODIS P90 min–max and flood GFD robust P95+log1p constants
over the Minnesota state polygon (GEE ``TIGER/2018/States``, STATEFP=27).
Writes / merges versioned JSON under ``cache/regions/{region}/normalization/{stats_version}/``.

City AOI product is unchanged. This only fills constants for the regional product.

Examples:
  python transformation/_shared/regions/compute_regional_norm_stats.py \\
    --region minnesota --layers landsat_p90,modis_day_p90,modis_night_p90

  python transformation/_shared/regions/compute_regional_norm_stats.py \\
    --region minnesota --layers gfd_event_count

  python transformation/_shared/regions/compute_regional_norm_stats.py \\
    --region minnesota --layers r90p,ndvi_p10

  # Refresh local state.geojson from GEE (simplified)
  python transformation/_shared/regions/compute_regional_norm_stats.py \\
    --region minnesota --layers landsat_p90 --refresh-boundary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHARED_REGIONS = Path(__file__).resolve().parent
TRANSFORM = SHARED_REGIONS.parent.parent  # transformation/
REPO = TRANSFORM.parent  # geospatial-data/
HEAT_HAZARD = TRANSFORM / "heat_hazard"
LANDSAT = TRANSFORM / "landsat_lst"
MODIS = TRANSFORM / "modis_lst"

if str(HEAT_HAZARD) not in sys.path:
    sys.path.insert(0, str(HEAT_HAZARD))
if str(LANDSAT) not in sys.path:
    sys.path.insert(0, str(LANDSAT))
if str(MODIS) not in sys.path:
    sys.path.insert(0, str(MODIS))
if str(SHARED_REGIONS) not in sys.path:
    sys.path.insert(0, str(SHARED_REGIONS))

from input_common import init_ee, season_months  # noqa: E402
from norm_stats import default_stats_path  # noqa: E402

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc


# Defaults aligned with city heat extracts (MN sites use JJA 2015–2024).
DEFAULT_SEASON = "jja"
DEFAULT_START_YEAR = 2015
DEFAULT_END_YEAR = 2024
LANDSAT_NORM_SCALE_M = 300
LANDSAT_MAX_CLOUD_LAND = 30
MODIS_SCALE_M = 1000
GFD_BAND = "flood_event_count_no_perm_water"

HEAT_LAYER_KEYS = ("landsat_p90", "modis_day_p90", "modis_night_p90")
FLOOD_LAYER_KEYS = ("gfd_event_count",)
LANDSLIDE_LAYER_KEYS = ("r90p", "ndvi_p10")
SUPPORTED_LAYER_KEYS = HEAT_LAYER_KEYS + FLOOD_LAYER_KEYS + LANDSLIDE_LAYER_KEYS


def load_region_yaml(region_id: str) -> dict[str, Any]:
    path = SHARED_REGIONS / f"{region_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Region config not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_example_stats(region_id: str) -> dict[str, Any]:
    example = REPO / "docs" / "examples" / f"ccra_normalization_stats_{region_id}.example.json"
    if example.is_file():
        return json.loads(example.read_text(encoding="utf-8"))
    return {
        "schema_version": "1",
        "region_id": region_id,
        "stats_version": "v1",
        "layers": {},
    }


def load_or_init_stats(region_id: str, stats_version: str) -> dict[str, Any]:
    """Prefer existing cache so incremental layer runs do not wipe prior fill."""
    existing = default_stats_path(region_id, stats_version)
    if existing.is_file():
        payload = json.loads(existing.read_text(encoding="utf-8"))
        print(f"Merging into existing stats: {existing}")
        return payload
    return load_example_stats(region_id)


def stats_out_path(region: dict[str, Any], stats_version: str) -> Path:
    return default_stats_path(str(region["region_id"]), stats_version)


def load_state_roi(ee: Any, region: dict[str, Any]) -> Any:
    roi_cfg = region.get("roi") or {}
    if roi_cfg.get("type") != "state_boundary":
        raise ValueError(f"Expected roi.type=state_boundary, got {roi_cfg.get('type')!r}")

    gee_asset = roi_cfg.get("gee_asset") or "TIGER/2018/States"
    state_fips = str(roi_cfg.get("state_fips") or "27")
    fc = ee.FeatureCollection(gee_asset).filter(ee.Filter.eq("STATEFP", state_fips))
    size = fc.size().getInfo()
    if size != 1:
        raise RuntimeError(f"Expected 1 state feature for FIPS {state_fips}, got {size}")
    print(f"ROI: {gee_asset} STATEFP={state_fips} ({roi_cfg.get('display_name')})")
    return fc.geometry()


def refresh_local_boundary(ee: Any, region: dict[str, Any], roi: Any, *, max_error_m: float = 200.0) -> Path:
    """Write a simplified state polygon for local tooling (stats still use full GEE ROI)."""
    roi_cfg = region.get("roi") or {}
    rel = roi_cfg.get("boundary_path")
    if not rel:
        raise ValueError("roi.boundary_path missing in region YAML")
    dest = REPO / str(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    simplified = ee.Geometry(roi).simplify(maxError=max_error_m)
    geom = simplified.getInfo()
    props = {
        "STATEFP": str(roi_cfg.get("state_fips") or "27"),
        "STUSPS": roi_cfg.get("state_abbr") or "MN",
        "NAME": roi_cfg.get("display_name") or region.get("display_name"),
        "source": f"{roi_cfg.get('gee_asset')} (simplified maxError={max_error_m}m via GEE)",
        "note": "Local convenience polygon; regional norm stats use full GEE state geometry.",
    }
    out = {
        "type": "FeatureCollection",
        "name": f"{region['region_id']}_state",
        "features": [{"type": "Feature", "properties": props, "geometry": geom}],
    }
    dest.write_text(json.dumps(out) + "\n", encoding="utf-8")
    print(f"Wrote simplified boundary → {dest} ({dest.stat().st_size} bytes)")
    return dest


def _site_like_config(season: str, start_year: int, end_year: int) -> dict[str, Any]:
    return {"season": season, "start_year": start_year, "end_year": end_year}


def build_landsat_p90(ee: Any, roi: Any, *, season: str, start_year: int, end_year: int) -> Any:
    from extract_landsat_lst import preprocess  # type: ignore

    months = season_months(_site_like_config(season, start_year, end_year))
    raw = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterDate(f"{start_year}-01-01", f"{end_year}-12-31")
        .filterBounds(roi)
        .map(lambda image: image.set("month", image.date().get("month")))
        .filter(ee.Filter.inList("month", months))
        .filter(ee.Filter.eq("PROCESSING_LEVEL", "L2SP"))
        .filter(ee.Filter.lte("CLOUD_COVER_LAND", LANDSAT_MAX_CLOUD_LAND))
    )
    collection = raw.map(lambda img: preprocess(img, ee))
    n = collection.size().getInfo()
    print(f"  Landsat scenes in filter: {n}")
    lst_band = collection.select("lst_celsius")
    return lst_band.reduce(ee.Reducer.percentile([90])).rename("lst_p90_celsius").clip(roi)


def build_modis_p90(
    ee: Any,
    roi: Any,
    *,
    band: str,
    out_name: str,
    season: str,
    start_year: int,
    end_year: int,
) -> Any:
    from extract_modis_lst import preprocess_modis  # type: ignore

    months = season_months(_site_like_config(season, start_year, end_year))
    raw = (
        ee.ImageCollection("MODIS/061/MOD11A2")
        .filterDate(f"{start_year}-01-01", f"{end_year}-12-31")
        .filterBounds(roi)
        .map(lambda image: image.set("month", image.date().get("month")))
        .filter(ee.Filter.inList("month", months))
        .select(["LST_Day_1km", "QC_Day", "LST_Night_1km", "QC_Night"])
    )
    collection = raw.map(lambda img: preprocess_modis(img, ee))
    n = collection.size().getInfo()
    print(f"  MODIS composites in filter ({band}): {n}")
    return (
        collection.select(band)
        .reduce(ee.Reducer.percentile([90]))
        .rename(out_name)
        .clip(roi)
    )


def reduce_minmax(
    image: Any,
    *,
    band_name: str,
    roi: Any,
    ee: Any,
    scale: int,
) -> dict[str, float]:
    stats = image.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=roi,
        scale=scale,
        maxPixels=1e10,
        bestEffort=True,
        tileScale=4,
    ).getInfo()
    vmin = stats.get(f"{band_name}_min")
    vmax = stats.get(f"{band_name}_max")
    if vmin is None or vmax is None:
        raise RuntimeError(f"reduceRegion returned nulls for {band_name}: {stats}")
    return {"vmin": float(vmin), "vmax": float(vmax)}


def compute_heat_layer(
    ee: Any,
    roi: Any,
    layer_key: str,
    layer_cfg: dict[str, Any],
    *,
    season: str,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    print(f"Computing {layer_key} over state ROI …")
    if layer_key == "landsat_p90":
        img = build_landsat_p90(ee, roi, season=season, start_year=start_year, end_year=end_year)
        band = "lst_p90_celsius"
        scale = int(layer_cfg.get("scale_m") or LANDSAT_NORM_SCALE_M)
        # Prefer norm scale used in city extract for comparable vmin/vmax semantics
        scale = LANDSAT_NORM_SCALE_M
    elif layer_key == "modis_day_p90":
        img = build_modis_p90(
            ee,
            roi,
            band="lst_day_celsius",
            out_name="lst_day_p90",
            season=season,
            start_year=start_year,
            end_year=end_year,
        )
        band = "lst_day_p90"
        scale = int(layer_cfg.get("scale_m") or MODIS_SCALE_M)
    elif layer_key == "modis_night_p90":
        img = build_modis_p90(
            ee,
            roi,
            band="lst_night_celsius",
            out_name="lst_night_p90",
            season=season,
            start_year=start_year,
            end_year=end_year,
        )
        band = "lst_night_p90"
        scale = int(layer_cfg.get("scale_m") or MODIS_SCALE_M)
    else:
        raise ValueError(f"Unsupported heat layer for this spike: {layer_key}")

    mm = reduce_minmax(img, band_name=band, roi=roi, ee=ee, scale=scale)
    print(f"  {layer_key}: vmin={mm['vmin']:.4f} vmax={mm['vmax']:.4f} (scale={scale}m)")
    return {
        "method": "minmax",
        "unit": layer_cfg.get("unit") or "celsius",
        "vmin": mm["vmin"],
        "vmax": mm["vmax"],
        "scale_m": scale,
        "season": season,
        "period": f"{start_year}-{end_year}",
        "n_samples": None,
        "notes": "Computed over full state boundary (GEE TIGER), not batch union_bbox.",
    }


def build_gfd_count(ee: Any, roi: Any) -> Any:
    gfd = ee.ImageCollection("GLOBAL_FLOOD_DB/MODIS_EVENTS/V1")
    flood_only = gfd.map(
        lambda img: img.select("flooded")
        .updateMask(img.select("jrc_perm_water").neq(1))
        .rename("flooded_no_perm_water")
        .copyProperties(img, img.propertyNames())
    )
    return flood_only.sum().rename(GFD_BAND).clip(roi)


def compute_gfd_layer(ee: Any, roi: Any, layer_cfg: dict[str, Any]) -> dict[str, Any]:
    """State-domain robust P95 + log1p min–max constants (same algebra as extract_gfd)."""
    scale = int(layer_cfg.get("scale_m") or 250)
    print(f"Computing gfd_event_count over state ROI (scale={scale}m) …")
    count = build_gfd_count(ee, roi)
    pos_mask = count.gt(0)
    count_pos = count.updateMask(pos_mask)
    p95 = ee.Number(
        count_pos.reduceRegion(
            reducer=ee.Reducer.percentile([95]),
            geometry=roi,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
            tileScale=4,
        ).get(GFD_BAND)
    )
    p95_safe = ee.Number(ee.Algorithms.If(p95, ee.Algorithms.If(p95.gt(0), p95, 1), 1))
    count_cap = count_pos.min(p95_safe)
    count_log = count_cap.add(1).log()
    mm = count_log.reduceRegion(
        reducer=ee.Reducer.minMax(),
        geometry=roi,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
        tileScale=4,
    )
    p95_val = float(p95_safe.getInfo())
    mm_info = mm.getInfo()
    vmin = mm_info.get(f"{GFD_BAND}_min")
    vmax = mm_info.get(f"{GFD_BAND}_max")
    if vmin is None or vmax is None:
        raise RuntimeError(f"GFD log min/max nulls: p95={p95_val} mm={mm_info}")
    print(
        f"  gfd_event_count: p95={p95_val:.4f} "
        f"log_vmin={float(vmin):.6f} log_vmax={float(vmax):.6f}"
    )
    return {
        "method": "robust_p95_log1p_minmax",
        "unit": layer_cfg.get("unit") or "count",
        "p95": p95_val,
        "vmin": float(vmin),
        "vmax": float(vmax),
        "scale_m": scale,
        "n_samples": None,
        "notes": (
            "Zeros stay 0; positives: cap at regional P95, log1p, min–max over state. "
            "Matches extract_gfd.gfd_robust_normalize algebra."
        ),
    }



def compute_landslide_layer(
    ee: Any,
    roi: Any,
    layer_key: str,
    layer_cfg: dict[str, Any],
    *,
    season: str,
    start_year: int,
    end_year: int,
) -> dict[str, Any]:
    """State-domain min–max for CHIRPS R90p or MODIS NDVI P10."""
    months = season_months(_site_like_config(season, start_year, end_year))
    print(f"Computing {layer_key} over state ROI …")
    if layer_key == "r90p":
        scale = int(layer_cfg.get("scale_m") or 5000)
        raw = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterBounds(roi)
            .filterDate(f"{start_year}-01-01", f"{end_year}-12-31")
            .map(lambda image: image.set("month", image.date().get("month")))
            .filter(ee.Filter.inList("month", months))
        )
        n = raw.size().getInfo()
        print(f"  CHIRPS days in filter: {n}")
        img = (
            raw.reduce(ee.Reducer.percentile([90]))
            .rename("r90p")
            .clip(roi)
        )
        band = "r90p"
        unit = layer_cfg.get("unit") or "mm_day"
    elif layer_key == "ndvi_p10":
        scale = int(layer_cfg.get("scale_m") or 250)
        raw = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .select("NDVI")
            .filterBounds(roi)
            .filterDate(f"{start_year}-01-01", f"{end_year}-12-31")
            .map(lambda image: image.set("month", image.date().get("month")))
            .filter(ee.Filter.inList("month", months))
            .map(lambda img: img.multiply(0.0001).copyProperties(img, img.propertyNames()))
        )
        n = raw.size().getInfo()
        print(f"  MODIS NDVI images in filter: {n}")
        img = (
            raw.reduce(ee.Reducer.percentile([10]))
            .rename("ndvi_p10")
            .clip(roi)
        )
        band = "ndvi_p10"
        unit = layer_cfg.get("unit") or "ndvi"
    else:
        raise ValueError(f"Unsupported landslide layer: {layer_key}")

    mm = reduce_minmax(img, band_name=band, roi=roi, ee=ee, scale=scale)
    print(f"  {layer_key}: vmin={mm['vmin']:.6f} vmax={mm['vmax']:.6f} (scale={scale}m)")
    return {
        "method": "minmax",
        "unit": unit,
        "vmin": mm["vmin"],
        "vmax": mm["vmax"],
        "scale_m": scale,
        "season": season,
        "period": f"{start_year}-{end_year}",
        "n_samples": None,
        "notes": "Computed over full state boundary (GEE TIGER), not batch union_bbox.",
    }


def merge_status(layers: dict[str, Any]) -> str:
    filled = 0
    total = 0
    for _k, v in layers.items():
        if not isinstance(v, dict):
            continue
        total += 1
        method = v.get("method")
        if method == "minmax" and v.get("vmin") is not None and v.get("vmax") is not None:
            filled += 1
        elif method == "robust_p95_log1p_minmax" and v.get("p95") is not None:
            filled += 1
    if filled == 0:
        return "pending"
    if filled < total:
        return "partial"
    return "ready"


def run(
    *,
    region_id: str,
    layer_keys: list[str],
    stats_version: str,
    season: str,
    start_year: int,
    end_year: int,
    refresh_boundary: bool,
    authenticate: bool,
) -> Path:
    region = load_region_yaml(region_id)
    region_layers = region.get("layers") or {}
    for key in layer_keys:
        if key not in region_layers:
            raise KeyError(f"{key} not listed in {region_id}.yaml layers")
        if key not in SUPPORTED_LAYER_KEYS:
            raise ValueError(
                f"Unsupported layer {key!r}. Supported: {SUPPORTED_LAYER_KEYS}."
            )

    ee = init_ee(authenticate=authenticate)
    roi = load_state_roi(ee, region)
    if refresh_boundary:
        refresh_local_boundary(ee, region, roi)

    payload = load_or_init_stats(region_id, stats_version)
    payload["schema_version"] = "1"
    payload["region_id"] = region_id
    payload["stats_version"] = stats_version
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["source_run"] = {
        "tool": "compute_regional_norm_stats.py",
        "ee_project": os.environ.get("EE_PROJECT", "eecc-maureen"),
        "git_sha": os.environ.get("GIT_SHA"),
        "notes": (
            f"Layers: {', '.join(layer_keys)} over state boundary; "
            f"season={season} {start_year}-{end_year}."
        ),
    }
    roi_cfg = region.get("roi") or {}
    payload["roi"] = {
        "type": "state_boundary",
        "id": roi_cfg.get("id") or f"us-state-fips-{roi_cfg.get('state_fips')}",
        "display_name": roi_cfg.get("display_name"),
        "boundary_path": roi_cfg.get("boundary_path"),
        "gee_asset": roi_cfg.get("gee_asset"),
        "bbox": roi_cfg.get("bbox"),
    }

    layers_out = dict(payload.get("layers") or {})
    for key in layer_keys:
        if key in HEAT_LAYER_KEYS:
            layers_out[key] = compute_heat_layer(
                ee,
                roi,
                key,
                region_layers[key],
                season=season,
                start_year=start_year,
                end_year=end_year,
            )
        elif key in FLOOD_LAYER_KEYS:
            layers_out[key] = compute_gfd_layer(ee, roi, region_layers[key])
        elif key in LANDSLIDE_LAYER_KEYS:
            layers_out[key] = compute_landslide_layer(
                ee,
                roi,
                key,
                region_layers[key],
                season=season,
                start_year=start_year,
                end_year=end_year,
            )
        else:
            raise ValueError(f"Unhandled layer {key!r}")
    payload["layers"] = layers_out
    payload["status"] = merge_status(layers_out)

    out_path = stats_out_path(region, stats_version)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path} (status={payload['status']})")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="minnesota")
    parser.add_argument(
        "--layers",
        default="landsat_p90",
        help="Comma-separated layer keys (heat and/or gfd_event_count)",
    )
    parser.add_argument("--stats-version", default="v1")
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    parser.add_argument(
        "--refresh-boundary",
        action="store_true",
        help="Overwrite local state.geojson with simplified GEE state polygon",
    )
    parser.add_argument("--authenticate", action="store_true")
    args = parser.parse_args(argv)
    keys = [k.strip() for k in str(args.layers).split(",") if k.strip()]
    try:
        run(
            region_id=args.region,
            layer_keys=keys,
            stats_version=args.stats_version,
            season=args.season,
            start_year=args.start_year,
            end_year=args.end_year,
            refresh_boundary=args.refresh_boundary,
            authenticate=args.authenticate,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
