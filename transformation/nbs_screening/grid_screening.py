"""Grid-cell NBS screening — mechanism flags and NBS scores per 250 m cell.

The grid cell is the primary unit. Bairro (or any AOI) is only a spatial filter.
Optional summaries roll up cell counts to % by mechanism for reporting.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.transform import xy
from rasterio.windows import from_bounds
from rasterio.warp import transform_geom
from shapely.geometry import box, mapping, shape

from catalog_layers import (
    DYNAMIC_WORLD_CLASSES,
    FLOOD_CATALOG_COGS,
    HEAT_CATALOG_COGS,
    LANDSLIDE_CATALOG_COGS,
    HazardKind,
    RasterLayerCache,
    RasterPointSampler,
    barrio_context,
    build_grid_layer_urls,
    dw_built_pct_from_class_value,
    dw_mode_fractions_cached,
    flood_grid_shared_context,
    get_reference_hazard_raster,
    grid_metrics,
    poa_permanent_open_water_mask,
    sample_raster_at_point,
    sample_raster_zonal_mean,
    sample_raster_zonal_mean_cached,
    water_stats_at_point,
    zonal_stats_cog,
)
from site_config import DEFAULT_SITE

RasterRef = Union[str, Path]

REF_RASTER: dict[HazardKind, RasterRef] = {
    "flood": FLOOD_CATALOG_COGS["flood_hazard"],
    "heat": HEAT_CATALOG_COGS["heat_hazard"],
    "landslide": LANDSLIDE_CATALOG_COGS["landslide_hazard"],
}

# GeoTIFF nodata for mechanism exports. Code 0 = without_clear_dominant must remain valid.
MECHANISM_RASTER_NODATA = 255

FLOOD_STRENGTH_KEYS = ("riverine", "pluvial", "low_lying", "drainage_constrained")
HEAT_STRENGTH_KEYS = (
    "uhi_built_up",
    "shade_deficit",
    "high_daytime_lst",
    "limited_nocturnal_cooling",
    "high_social_exposure",
)
LANDSLIDE_STRENGTH_KEYS = (
    "steep_activatable_slope",
    "rainfall_trigger",
    "low_cohesion_wet",
    "vegetation_deficit",
    "drainage_saturation",
    "disturbed_bare_slope",
    "upslope_convergence",
    "high_social_exposure",
)
MECHANISM_IDW_MAX_DIST_M = 750.0
MECHANISM_IDW_MIN_NEIGHBORS = 3
MECHANISM_IDW_POWER = 2.0
MECHANISM_IDW_K_NEIGHBORS = 32

from nbs_rules import (
    FloodMechanismClassification,
    HeatMechanismAssessment,
    HeatMechanismClassification,
    LandslideMechanismAssessment,
    LandslideMechanismClassification,
    MechanismAssessment,
    NbsRecommendation,
    classify_dominant_flood_mechanism,
    classify_dominant_heat_mechanism,
    classify_dominant_landslide_mechanism,
    classify_from_heat_strengths,
    classify_from_landslide_strengths,
    classify_from_strengths,
    infer_flood_mechanism,
    infer_heat_mechanism,
    infer_landslide_mechanism,
    recommend_flood_all,
    recommend_heat_all,
    recommend_landslide_all,
    LANDSLIDE_MIN_STRENGTH,
)

VALUE_RASTERS: dict[HazardKind, dict[str, RasterRef]] = {
    "flood": {
        "flood_score_mean": FLOOD_CATALOG_COGS["flood_hazard"],
        "exposure_score_mean": FLOOD_CATALOG_COGS["exposure"],
        "vulnerability_score_mean": FLOOD_CATALOG_COGS["vulnerability"],
        "risk_score_mean": FLOOD_CATALOG_COGS["flood_risk"],
        "floodplain_adj_pct_mean": FLOOD_CATALOG_COGS["gfplain250m"],
        "depression_pct_mean": FLOOD_CATALOG_COGS["poa_depression_mask"],
    },
    "heat": {
        "heat_score_mean": HEAT_CATALOG_COGS["heat_hazard"],
        "exposure_score_mean": HEAT_CATALOG_COGS["exposure"],
        "vulnerability_score_mean": HEAT_CATALOG_COGS["vulnerability"],
        "heat_risk_score_mean": HEAT_CATALOG_COGS["heat_risk"],
    },
    "landslide": {
        "landslide_score_mean": LANDSLIDE_CATALOG_COGS["landslide_hazard"],
        "exposure_score_mean": LANDSLIDE_CATALOG_COGS["exposure"],
        "vulnerability_score_mean": LANDSLIDE_CATALOG_COGS["vulnerability"],
        "landslide_risk_score_mean": LANDSLIDE_CATALOG_COGS["landslide_risk"],
        "slope_mean": LANDSLIDE_CATALOG_COGS["poa_slope"],
        "clay_pct_mean": LANDSLIDE_CATALOG_COGS["soilgrids_clay"],
        "merit_hand_mean": LANDSLIDE_CATALOG_COGS["merit_hand"],
    },
}

OPTIONAL_COG_SAMPLES: dict[HazardKind, dict[str, str]] = {
    "flood": {
        "merit_hand_mean": FLOOD_CATALOG_COGS["merit_hand"],
        "imperv_pct_mean": FLOOD_CATALOG_COGS["ghsl_built_up"],
        "dw_built_pct_mean": FLOOD_CATALOG_COGS["dynamic_world_mode_250m"],
        "surface_water_occurrence_mean": FLOOD_CATALOG_COGS["jrc_surface_water_occurrence"],
        "surface_water_seasonality_mean": FLOOD_CATALOG_COGS["jrc_surface_water_seasonality"],
    },
    "heat": {
        "imperv_pct_mean": HEAT_CATALOG_COGS["ghsl_built_up"],
        "treecover2000_mean": HEAT_CATALOG_COGS["hansen_treecover2000"],
        "ndvi_mean": HEAT_CATALOG_COGS["modis_ndvi"],
        "landsat_lst_norm_mean": HEAT_CATALOG_COGS["landsat8_lst_djf"],
        "modis_lst_day_norm_mean": HEAT_CATALOG_COGS["modis_lst_day_p90"],
        "modis_lst_night_norm_mean": HEAT_CATALOG_COGS["modis_lst_night_p90"],
    },
    "landslide": {
        "upstream_area_km2_mean": LANDSLIDE_CATALOG_COGS["merit_upa"],
        "r90p_climatology_mean": LANDSLIDE_CATALOG_COGS["chirps_r90p_climatology"],
        "ndvi_p10_mean": LANDSLIDE_CATALOG_COGS["ndvi_p10_djf"],
        "treecover2000_mean": LANDSLIDE_CATALOG_COGS["hansen_treecover2000"],
        "dw_built_pct_mean": LANDSLIDE_CATALOG_COGS["dynamic_world_mode_250m"],
    },
}


@dataclass
class GridCellScreening:
    cell_id: str
    row: int
    col: int
    centroid_lon: float
    centroid_lat: float
    geometry: Any
    ctx: dict[str, Any]
    grid_stats: dict[str, Any]
    water_stats: dict[str, Any]
    mechanism: MechanismAssessment | HeatMechanismAssessment | LandslideMechanismAssessment
    flood_mechanism: FloodMechanismClassification | None = None
    heat_mechanism: HeatMechanismClassification | None = None
    landslide_mechanism: LandslideMechanismClassification | None = None
    top_nbs: list[NbsRecommendation] = field(default_factory=list)
    dominant_nbs: str | None = None
    dominant_nbs_score: float | None = None
    hazard_valid: bool = True
    is_interpolated: bool = False


@dataclass
class GridScreeningResult:
    hazard: HazardKind
    aoi_label: str
    cell_size_m: float
    n_cells: int
    cells: list[GridCellScreening]
    mechanism_summary: dict[str, Any]
    aoi_context: dict[str, Any] = field(default_factory=dict)


def enumerate_raster_cells(
    aoi_geom,
    ref_path: RasterRef,
    *,
    require_hazard_valid: bool = True,
    require_positive_hazard: bool = False,
) -> list[dict[str, Any]]:
    """Return one reference-grid pixel polygon per 250 m cell inside the AOI."""
    cells: list[dict[str, Any]] = []
    geom = mapping(aoi_geom)
    aoi_shape = shape(geom)
    with rasterio.open(ref_path) as src:
        if src.crs and src.crs.to_epsg() != 4326:
            geom = transform_geom("EPSG:4326", src.crs, geom)
            aoi_shape = shape(geom)
        minx, miny, maxx, maxy = aoi_shape.bounds
        window = from_bounds(minx, miny, maxx, maxy, src.transform).round_offsets().round_lengths()
        band = src.read(1, window=window, masked=True)
        sub_transform = rasterio.windows.transform(window, src.transform)
        inside = geometry_mask(
            [mapping(aoi_shape)],
            out_shape=band.shape,
            transform=sub_transform,
            invert=True,
        )
        hazard_valid_mask = (~band.mask) & inside
        if require_positive_hazard:
            hazard_valid_mask = hazard_valid_mask & (band > 0)
        combined = hazard_valid_mask if require_hazard_valid else inside
        nodata = src.nodata
        row_offs, col_offs = np.where(combined)
        for row_off, col_off in zip(row_offs, col_offs):
            hazard_valid = bool(hazard_valid_mask[row_off, col_off])
            if hazard_valid:
                val = float(band[row_off, col_off])
                if nodata is not None and val == float(nodata):
                    continue
                if not np.isfinite(val):
                    continue
                if require_positive_hazard and val <= 0:
                    continue
            else:
                val = None

            global_row = int(window.row_off + row_off)
            global_col = int(window.col_off + col_off)
            x_min, y_max = xy(sub_transform, row_off, col_off, offset="ul")
            x_max, y_min = xy(sub_transform, row_off, col_off, offset="lr")
            cx, cy = xy(sub_transform, row_off, col_off, offset="center")
            cells.append(
                {
                    "cell_id": f"r{global_row}_c{global_col}",
                    "row": global_row,
                    "col": global_col,
                    "centroid_lon": float(cx),
                    "centroid_lat": float(cy),
                    "geometry": box(x_min, y_min, x_max, y_max),
                    "ref_value": val if hazard_valid else None,
                    "hazard_valid": hazard_valid,
                }
            )
    return cells


def _aoi_shared_grid_context(aoi_geom, hazard: HazardKind, site: str | None = None) -> dict[str, Any]:
    """AOI-level diagnostics shared across cells (e.g. CHIRPS heavy-rain proxy)."""
    if hazard == "flood":
        return flood_grid_shared_context(aoi_geom, site=site)
    if hazard == "heat":
        return {}
    if hazard == "landslide":
        return {}
    sample = grid_metrics(aoi_geom, hazard=hazard, site=site)
    if sample.status == "error" and not sample.stats:
        return {}
    return dict(sample.stats)


def _grid_layer_urls(
    hazard: HazardKind,
    *,
    sample_catalog: bool,
    site: str | None = None,
) -> dict[str, RasterRef]:
    return build_grid_layer_urls(hazard, site=site, sample_catalog=sample_catalog)


def _landslide_dw_fractions_from_class_value(class_val: float) -> dict[str, float]:
    """Fast Dynamic World cover proxy from mode class at pixel center."""
    cid = int(round(class_val))
    tree = 1.0 if cid == DYNAMIC_WORLD_CLASSES["trees"] else 0.0
    grass = 1.0 if cid == DYNAMIC_WORLD_CLASSES["grass"] else 0.0
    shrub = 1.0 if cid == DYNAMIC_WORLD_CLASSES["shrub"] else 0.0
    built = 1.0 if cid == DYNAMIC_WORLD_CLASSES["built"] else 0.0
    bare = 1.0 if cid == DYNAMIC_WORLD_CLASSES["bare"] else 0.0
    return {
        "dw_built_pct_mean": built,
        "dw_bare_pct_mean": bare,
        "green_pct_mean": tree + grass + shrub,
        "tree_pct_mean": tree,
    }


def _enrich_landslide_dw_fractions(
    stats: dict[str, Any],
    geometry: Any,
    sampler: RasterPointSampler | RasterLayerCache | None = None,
    *,
    lon: float | None = None,
    lat: float | None = None,
) -> None:
    """Add Dynamic World cover fractions for landslide disturbed/vegetation rules."""
    if sampler is not None and lon is not None and lat is not None:
        raw = sampler.read("dw_built_pct_mean", lon, lat)
        if raw is not None:
            stats.update(_landslide_dw_fractions_from_class_value(raw))
            return

    if geometry is None or not isinstance(sampler, RasterLayerCache):
        return

    fractions = dw_mode_fractions_cached(sampler, "dw_built_pct_mean", geometry)
    if fractions:
        stats.update({k: v for k, v in fractions.items() if v is not None})


def _sample_cell_layers(
    lon: float,
    lat: float,
    hazard: HazardKind,
    shared: dict[str, Any],
    *,
    geometry: Any = None,
    sample_catalog: bool = True,
    sampler: RasterPointSampler | RasterLayerCache | None = None,
    zonal_fallback: bool = True,
) -> dict[str, Any]:
    stats: dict[str, Any] = dict(shared)
    layer_urls = _grid_layer_urls(hazard, sample_catalog=sample_catalog)
    zonal_fallback_keys = set(VALUE_RASTERS[hazard].keys())
    for key, path in layer_urls.items():
        if sampler is not None:
            val = sampler.read(key, lon, lat)
        else:
            val = sample_raster_at_point(path, lon, lat)
        if (
            val is None
            and zonal_fallback
            and geometry is not None
            and key in zonal_fallback_keys
        ):
            if isinstance(sampler, RasterLayerCache):
                val = sample_raster_zonal_mean_cached(sampler, key, geometry)
            else:
                val = sample_raster_zonal_mean(path, geometry)
        if val is not None:
            if key == "imperv_pct_mean" and val > 1:
                stats[key] = min(1.0, max(0.0, val / 10_000))
            elif key == "dw_built_pct_mean":
                stats[key] = dw_built_pct_from_class_value(val)
            else:
                stats[key] = val
    if hazard == "landslide" and sample_catalog:
        _enrich_landslide_dw_fractions(stats, geometry, sampler, lon=lon, lat=lat)
    return stats


def _ctx_from_grid_stats(grid_stats: dict[str, Any], hazard: HazardKind) -> dict[str, Any]:
    if hazard == "flood":
        return {
            "risk_mean": grid_stats.get("risk_score_mean"),
            "exposure_score": grid_stats.get("exposure_score_mean"),
            "vulnerability_score": grid_stats.get("vulnerability_score_mean"),
        }
    if hazard == "landslide":
        return {
            "hazard_mean": grid_stats.get("landslide_score_mean"),
            "risk_mean": grid_stats.get("landslide_risk_score_mean"),
            "exposure_score": grid_stats.get("exposure_score_mean"),
            "vulnerability_score": grid_stats.get("vulnerability_score_mean"),
        }
    return {
        "hazard_mean": grid_stats.get("heat_score_mean"),
        "risk_mean": grid_stats.get("heat_risk_score_mean"),
        "exposure_score": grid_stats.get("exposure_score_mean"),
        "vulnerability_score": grid_stats.get("vulnerability_score_mean"),
    }


def summarize_flood_mechanisms(cells: list[GridCellScreening]) -> dict[str, Any]:
    n = len(cells)
    if n == 0:
        return {"n_cells": 0}

    riverine = sum(1 for c in cells if c.mechanism.riverine)
    pluvial = sum(1 for c in cells if c.mechanism.pluvial)
    low_lying = sum(1 for c in cells if c.mechanism.low_lying)
    multi = sum(
        1
        for c in cells
        if sum([c.mechanism.riverine, c.mechanism.pluvial, c.mechanism.low_lying]) >= 2
    )
    type_counts: dict[str, int] = {}
    for c in cells:
        if c.flood_mechanism is not None:
            type_counts[c.flood_mechanism.mechanism_type] = (
                type_counts.get(c.flood_mechanism.mechanism_type, 0) + 1
            )

    return {
        "n_cells": n,
        "pct_riverine": round(100 * riverine / n, 1),
        "pct_pluvial": round(100 * pluvial / n, 1),
        "pct_low_lying": round(100 * low_lying / n, 1),
        "pct_multi_mechanism": round(100 * multi / n, 1),
        "count_riverine": riverine,
        "count_pluvial": pluvial,
        "count_low_lying": low_lying,
        "dominant_mechanism_type_counts": type_counts,
        "pct_by_dominant_type": {
            k: round(100 * v / n, 1) for k, v in sorted(type_counts.items())
        },
    }


def summarize_heat_mechanisms(cells: list[GridCellScreening]) -> dict[str, Any]:
    n = len(cells)
    if n == 0:
        return {"n_cells": 0}

    flags = {
        "uhi_built_up": sum(1 for c in cells if c.mechanism.uhi_built_up),
        "shade_deficit": sum(1 for c in cells if c.mechanism.shade_deficit),
        "high_daytime_lst": sum(1 for c in cells if c.mechanism.high_daytime_lst),
        "limited_nocturnal_cooling": sum(1 for c in cells if c.mechanism.limited_nocturnal_cooling),
        "high_social_exposure": sum(1 for c in cells if c.mechanism.high_social_exposure),
    }
    type_counts: dict[str, int] = {}
    for c in cells:
        if c.heat_mechanism is not None:
            type_counts[c.heat_mechanism.mechanism_type] = (
                type_counts.get(c.heat_mechanism.mechanism_type, 0) + 1
            )
    multi = sum(
        1
        for c in cells
        if sum(
            [
                c.mechanism.uhi_built_up,
                c.mechanism.shade_deficit,
                c.mechanism.high_daytime_lst,
                c.mechanism.limited_nocturnal_cooling,
                c.mechanism.high_social_exposure,
            ]
        )
        >= 2
    )
    return {
        "n_cells": n,
        **{f"pct_{k}": round(100 * v / n, 1) for k, v in flags.items()},
        **{f"count_{k}": v for k, v in flags.items()},
        "pct_multi_mechanism": round(100 * multi / n, 1),
        "count_multi_mechanism": multi,
        "dominant_mechanism_type_counts": type_counts,
        "pct_by_dominant_type": {
            k: round(100 * v / n, 1) for k, v in sorted(type_counts.items())
        },
    }


def summarize_landslide_mechanisms(cells: list[GridCellScreening]) -> dict[str, Any]:
    n = len(cells)
    if n == 0:
        return {"n_cells": 0}

    flags = {
        "steep_activatable_slope": sum(1 for c in cells if c.mechanism.steep_activatable_slope),
        "rainfall_trigger": sum(1 for c in cells if c.mechanism.rainfall_trigger),
        "low_cohesion_wet": sum(1 for c in cells if c.mechanism.low_cohesion_wet),
        "vegetation_deficit": sum(1 for c in cells if c.mechanism.vegetation_deficit),
        "drainage_saturation": sum(1 for c in cells if c.mechanism.drainage_saturation),
        "disturbed_bare_slope": sum(1 for c in cells if c.mechanism.disturbed_bare_slope),
        "upslope_convergence": sum(1 for c in cells if c.mechanism.upslope_convergence),
        "high_social_exposure": sum(1 for c in cells if c.mechanism.high_social_exposure),
    }
    type_counts: dict[str, int] = {}
    for c in cells:
        if c.landslide_mechanism is not None:
            type_counts[c.landslide_mechanism.mechanism_type] = (
                type_counts.get(c.landslide_mechanism.mechanism_type, 0) + 1
            )
    multi = sum(
        1
        for c in cells
        if sum(
            [
                c.mechanism.steep_activatable_slope,
                c.mechanism.rainfall_trigger,
                c.mechanism.low_cohesion_wet,
                c.mechanism.vegetation_deficit,
                c.mechanism.drainage_saturation,
                c.mechanism.disturbed_bare_slope,
                c.mechanism.upslope_convergence,
                c.mechanism.high_social_exposure,
            ]
        )
        >= 2
    )
    return {
        "n_cells": n,
        **{f"pct_{k}": round(100 * v / n, 1) for k, v in flags.items()},
        **{f"count_{k}": v for k, v in flags.items()},
        "pct_multi_mechanism": round(100 * multi / n, 1),
        "count_multi_mechanism": multi,
        "dominant_mechanism_type_counts": type_counts,
        "pct_by_dominant_type": {
            k: round(100 * v / n, 1) for k, v in sorted(type_counts.items())
        },
    }


def screen_grid(
    aoi_geom,
    hazard: HazardKind = "flood",
    aoi_label: str = "aoi",
    *,
    site: str | None = None,
    sample_catalog: bool = True,
    include_nbs: bool = True,
    require_hazard_valid: bool = True,
    require_positive_hazard: bool = False,
    preload_layers: bool | None = None,
    zonal_fallback: bool = True,
) -> GridScreeningResult:
    """Screen each 250 m cell in the AOI; mechanism flags are per cell."""
    ref_path = get_reference_hazard_raster(hazard, site)
    with rasterio.open(ref_path) as src:
        cell_size_m = abs(src.res[0]) * 111_000

    shared = _aoi_shared_grid_context(aoi_geom, hazard, site=site)
    raw_cells = enumerate_raster_cells(
        aoi_geom,
        ref_path,
        require_hazard_valid=require_hazard_valid,
        require_positive_hazard=require_positive_hazard,
    )
    screened: list[GridCellScreening] = []
    n_raw = len(raw_cells)
    layer_urls = _grid_layer_urls(hazard, sample_catalog=sample_catalog, site=site)
    use_preload = preload_layers if preload_layers is not None else n_raw >= 500
    bounds = aoi_geom.bounds

    sampler_ctx: RasterLayerCache | RasterPointSampler
    if use_preload:
        sampler_ctx = RasterLayerCache(layer_urls, bounds=bounds)
        if n_raw >= 500:
            print(f"  preloading {len(layer_urls)} catalog layers for {n_raw} cells...", flush=True)
    else:
        sampler_ctx = RasterPointSampler(layer_urls)

    cell_geom = (lambda raw: raw["geometry"]) if zonal_fallback else (lambda _raw: None)

    with sampler_ctx as sampler:
        for i, raw in enumerate(raw_cells):
            lon, lat = raw["centroid_lon"], raw["centroid_lat"]
            grid_stats = _sample_cell_layers(
                lon,
                lat,
                hazard,
                shared,
                geometry=cell_geom(raw),
                sample_catalog=sample_catalog,
                sampler=sampler,
                zonal_fallback=zonal_fallback,
            )
            ctx = _ctx_from_grid_stats(grid_stats, hazard)
            water = water_stats_at_point(lon, lat, site=site)

            if hazard == "flood":
                mechanism = infer_flood_mechanism(ctx, grid_stats, water)
                flood_mech = classify_dominant_flood_mechanism(ctx, grid_stats, water)
                heat_mech = None
                landslide_mech = None
                top_nbs: list[NbsRecommendation] = []
                if include_nbs:
                    _, top_nbs = recommend_flood_all(ctx, grid_stats, water)
            elif hazard == "heat":
                mechanism = infer_heat_mechanism(ctx, grid_stats, water)
                flood_mech = None
                heat_mech = classify_dominant_heat_mechanism(ctx, grid_stats, water)
                landslide_mech = None
                top_nbs = []
                if include_nbs:
                    _, top_nbs = recommend_heat_all(ctx, grid_stats, water)
            else:
                mechanism = infer_landslide_mechanism(ctx, grid_stats, water)
                flood_mech = None
                heat_mech = None
                landslide_mech = classify_dominant_landslide_mechanism(ctx, grid_stats, water)
                top_nbs = []
                if include_nbs:
                    _, top_nbs = recommend_landslide_all(ctx, grid_stats, water)

            dominant = top_nbs[0] if top_nbs else None
            screened.append(
                GridCellScreening(
                    cell_id=raw["cell_id"],
                    row=raw["row"],
                    col=raw["col"],
                    centroid_lon=lon,
                    centroid_lat=lat,
                    geometry=raw["geometry"],
                    ctx=ctx,
                    grid_stats=grid_stats,
                    water_stats=water,
                    mechanism=mechanism,
                    flood_mechanism=flood_mech,
                    heat_mechanism=heat_mech,
                    landslide_mechanism=landslide_mech,
                    top_nbs=top_nbs,
                    dominant_nbs=dominant.nbs_type if dominant else None,
                    dominant_nbs_score=dominant.score if dominant else None,
                    hazard_valid=bool(raw.get("hazard_valid", True)),
                )
            )
            if n_raw > 20 and (i + 1) % max(1, n_raw // 10) == 0:
                print(f"  screened {i + 1}/{n_raw} cells...", flush=True)

    summary = (
        summarize_flood_mechanisms(screened)
        if hazard == "flood"
        else summarize_heat_mechanisms(screened)
        if hazard == "heat"
        else summarize_landslide_mechanisms(screened)
    )
    return GridScreeningResult(
        hazard=hazard,
        aoi_label=aoi_label,
        cell_size_m=cell_size_m,
        n_cells=len(screened),
        cells=screened,
        mechanism_summary=summary,
        aoi_context=shared,
    )


def screen_bairro_grid(
    bairro_name: str,
    hazard: HazardKind = "flood",
    **kwargs: Any,
) -> GridScreeningResult:
    """Convenience: use a bairro polygon only to filter which cells to screen."""
    ctx = barrio_context(bairro_name, hazard=hazard)
    geom = ctx.pop("geometry")
    result = screen_grid(geom, hazard=hazard, aoi_label=bairro_name, **kwargs)
    result.aoi_context = {**ctx, **result.aoi_context}
    return result


def _landslide_tied_mechanisms(
    mech: LandslideMechanismClassification | None,
    *,
    mixed_band: float = 0.15,
) -> str | None:
    """Comma-separated mechanism keys tied within mixed_band of the top strength."""
    if mech is None or mech.mechanism_type != "mixed":
        return None
    ranked = sorted(mech.strengths.items(), key=lambda kv: kv[1], reverse=True)
    top_val = ranked[0][1]
    tied = [
        name
        for name, val in mech.strengths.items()
        if val >= top_val - mixed_band and val >= LANDSLIDE_MIN_STRENGTH
    ]
    return ", ".join(tied) if tied else None


def cells_to_geodataframe(result: GridScreeningResult) -> gpd.GeoDataFrame:
    rows: list[dict[str, Any]] = []
    for cell in result.cells:
        mech = cell.mechanism
        row: dict[str, Any] = {
            "cell_id": cell.cell_id,
            "row": cell.row,
            "col": cell.col,
            "geometry": cell.geometry,
            "dominant_nbs": cell.dominant_nbs,
            "dominant_nbs_score": cell.dominant_nbs_score,
        }
        if isinstance(mech, MechanismAssessment):
            row.update(
                {
                    "riverine": mech.riverine,
                    "pluvial": mech.pluvial,
                    "low_lying": mech.low_lying,
                    "flood_mechanism_type": (
                        cell.flood_mechanism.mechanism_type if cell.flood_mechanism else None
                    ),
                    "flood_mechanism_code": (
                        cell.flood_mechanism.mechanism_code if cell.flood_mechanism else None
                    ),
                    "flood_score": cell.grid_stats.get("flood_score_mean"),
                    "risk_score": cell.grid_stats.get("risk_score_mean"),
                    "dist_river_m": cell.water_stats.get("dist_nearest_m"),
                    "hazard_valid": cell.hazard_valid,
                    "is_interpolated": cell.is_interpolated,
                }
            )
        elif isinstance(mech, HeatMechanismAssessment):
            row.update(
                {
                    "uhi_built_up": mech.uhi_built_up,
                    "shade_deficit": mech.shade_deficit,
                    "high_daytime_lst": mech.high_daytime_lst,
                    "limited_nocturnal_cooling": mech.limited_nocturnal_cooling,
                    "high_social_exposure": mech.high_social_exposure,
                    "heat_mechanism_type": (
                        cell.heat_mechanism.mechanism_type if cell.heat_mechanism else None
                    ),
                    "heat_mechanism_code": (
                        cell.heat_mechanism.mechanism_code if cell.heat_mechanism else None
                    ),
                    "heat_score": cell.grid_stats.get("heat_score_mean"),
                    "heat_risk_score": cell.grid_stats.get("heat_risk_score_mean"),
                    "hazard_valid": cell.hazard_valid,
                    "is_interpolated": cell.is_interpolated,
                }
            )
        else:
            row.update(
                {
                    "steep_activatable_slope": mech.steep_activatable_slope,
                    "rainfall_trigger": mech.rainfall_trigger,
                    "low_cohesion_wet": mech.low_cohesion_wet,
                    "vegetation_deficit": mech.vegetation_deficit,
                    "drainage_saturation": mech.drainage_saturation,
                    "disturbed_bare_slope": mech.disturbed_bare_slope,
                    "upslope_convergence": mech.upslope_convergence,
                    "high_social_exposure": mech.high_social_exposure,
                    "landslide_mechanism_type": (
                        cell.landslide_mechanism.mechanism_type
                        if cell.landslide_mechanism
                        else None
                    ),
                    "landslide_mechanism_code": (
                        cell.landslide_mechanism.mechanism_code
                        if cell.landslide_mechanism
                        else None
                    ),
                    "landslide_mechanism_strengths": (
                        cell.landslide_mechanism.strengths if cell.landslide_mechanism else None
                    ),
                    "mixed_tied_mechanisms": _landslide_tied_mechanisms(cell.landslide_mechanism),
                    "landslide_score": cell.grid_stats.get("landslide_score_mean"),
                    "landslide_risk_score": cell.grid_stats.get("landslide_risk_score_mean"),
                    "slope_deg": cell.grid_stats.get("slope_mean"),
                    "dist_river_m": cell.water_stats.get("dist_nearest_m"),
                    "hazard_valid": cell.hazard_valid,
                    "is_interpolated": cell.is_interpolated,
                }
            )
        rows.append(row)
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def result_to_geojson(result: GridScreeningResult) -> dict[str, Any]:
    gdf = cells_to_geodataframe(result)
    return {
        "type": "FeatureCollection",
        "properties": {
            "hazard": result.hazard,
            "aoi_label": result.aoi_label,
            "cell_size_m": result.cell_size_m,
            "mechanism_summary": result.mechanism_summary,
        },
        "features": json.loads(gdf.to_json())["features"],
    }


def result_to_report_dict(result: GridScreeningResult) -> dict[str, Any]:
    return {
        "exercise": "nbs_grid_screening",
        "hazard": result.hazard,
        "aoi_label": result.aoi_label,
        "cell_size_m": result.cell_size_m,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mechanism_summary": result.mechanism_summary,
        "aoi_context": result.aoi_context,
        "cells": [
            {
                "cell_id": c.cell_id,
                "centroid": [c.centroid_lon, c.centroid_lat],
                "ctx": c.ctx,
                "mechanism": asdict(c.mechanism),
                "flood_mechanism_type": (
                    c.flood_mechanism.mechanism_type if c.flood_mechanism else None
                ),
                "flood_mechanism_code": (
                    c.flood_mechanism.mechanism_code if c.flood_mechanism else None
                ),
                "flood_mechanism_strengths": (
                    c.flood_mechanism.strengths if c.flood_mechanism else None
                ),
                "heat_mechanism_type": (
                    c.heat_mechanism.mechanism_type if c.heat_mechanism else None
                ),
                "heat_mechanism_code": (
                    c.heat_mechanism.mechanism_code if c.heat_mechanism else None
                ),
                "heat_mechanism_strengths": (
                    c.heat_mechanism.strengths if c.heat_mechanism else None
                ),
                "dominant_nbs": c.dominant_nbs,
                "dominant_nbs_score": c.dominant_nbs_score,
                "dist_river_m": c.water_stats.get("dist_nearest_m"),
            }
            for c in result.cells
        ],
    }


def site_reference_bounds_geom(hazard: HazardKind, site: str | None = None):
    """Full extent of the hazard reference grid for *site*."""
    from shapely.geometry import box

    with rasterio.open(get_reference_hazard_raster(hazard, site)) as src:
        b = src.bounds
        return box(b.left, b.bottom, b.right, b.top)


def poa_flood_reference_bounds_geom():
    """Full POA extent of the 250 m flood hazard reference grid."""
    return site_reference_bounds_geom("flood", DEFAULT_SITE)


def screen_site_flood_mechanism_grid(
    site: str,
    aoi_geom=None,
    **kwargs: Any,
) -> GridScreeningResult:
    """Screen hazard-valid 250 m cells for *site*; default AOI is city boundary."""
    if aoi_geom is None:
        from site_config import site_boundary_path

        boundary_path = site_boundary_path(site)
        if not boundary_path.is_file():
            raise FileNotFoundError(f"Missing city boundary: {boundary_path}")
        gdf = gpd.read_file(boundary_path)
        if gdf.crs is None:
            gdf = gdf.set_crs(4326)
        aoi_geom = gdf.to_crs(4326).union_all()

    return screen_grid(
        aoi_geom,
        hazard="flood",
        site=site,
        aoi_label=site,
        require_hazard_valid=kwargs.pop("require_hazard_valid", True),
        preload_layers=kwargs.pop("preload_layers", True),
        zonal_fallback=kwargs.pop("zonal_fallback", False),
        **kwargs,
    )


def screen_poa_flood_mechanism_grid(**kwargs: Any) -> GridScreeningResult:
    """Screen hazard-valid 250 m cells on the POA flood grid; export IDW-fills gaps."""
    return screen_grid(
        poa_flood_reference_bounds_geom(),
        hazard="flood",
        aoi_label="porto_alegre",
        require_hazard_valid=kwargs.pop("require_hazard_valid", True),
        preload_layers=kwargs.pop("preload_layers", True),
        zonal_fallback=kwargs.pop("zonal_fallback", False),
        **kwargs,
    )


def poa_heat_reference_bounds_geom():
    """Full POA extent of the 250 m heat hazard reference grid."""
    return site_reference_bounds_geom("heat", DEFAULT_SITE)


def screen_poa_heat_mechanism_grid(**kwargs: Any) -> GridScreeningResult:
    """Screen hazard-valid 250 m cells on the POA heat grid; export IDW-fills gaps."""
    return screen_grid(
        poa_heat_reference_bounds_geom(),
        hazard="heat",
        aoi_label="porto_alegre",
        require_hazard_valid=kwargs.pop("require_hazard_valid", True),
        preload_layers=kwargs.pop("preload_layers", True),
        zonal_fallback=kwargs.pop("zonal_fallback", False),
        **kwargs,
    )


def _write_uint8_geotiff(
    out_arr: np.ndarray,
    out_path: Path,
    *,
    ref_path: RasterRef,
) -> Path:
    with rasterio.open(ref_path) as src:
        profile = src.profile.copy()
        profile.update(
            dtype="uint8",
            count=1,
            nodata=MECHANISM_RASTER_NODATA,
            compress="deflate",
        )
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(out_arr, 1)
    return out_path


def _mask_open_water_pixels(
    observed_grid: np.ndarray,
    filled_grid: np.ndarray,
    is_interp_grid: np.ndarray,
    water_mask: np.ndarray,
) -> int:
    """Set permanent open-water pixels (e.g. Lago Guaíba) to nodata on mechanism grids."""
    n = int(water_mask.sum())
    observed_grid[water_mask] = MECHANISM_RASTER_NODATA
    filled_grid[water_mask] = MECHANISM_RASTER_NODATA
    is_interp_grid[water_mask] = 0
    return n


def _exclude_open_water_from_observed(
    observed_grid: np.ndarray,
    strength_grids: dict[str, np.ndarray],
    water_mask: np.ndarray,
    strength_keys: tuple[str, ...],
) -> None:
    """Drop open-water pixels before IDW so they are neither sources nor fill targets."""
    observed_grid[water_mask] = MECHANISM_RASTER_NODATA
    for key in strength_keys:
        strength_grids[key][water_mask] = np.nan


def _flood_mechanism_grids_from_result(
    result: GridScreeningResult,
    ref_path: RasterRef,
    *,
    observed_only: bool,
) -> tuple[np.ndarray, dict[str, np.ndarray], Any]:
    """Build code + strength grids from screened cells (direct row/col indexing)."""
    if result.hazard != "flood":
        raise ValueError("_flood_mechanism_grids_from_result requires hazard='flood'")

    with rasterio.open(ref_path) as src:
        code_grid = np.full((src.height, src.width), MECHANISM_RASTER_NODATA, dtype=np.uint8)
        strength_grids = {
            key: np.full((src.height, src.width), np.nan, dtype=np.float32)
            for key in FLOOD_STRENGTH_KEYS
        }
        for cell in result.cells:
            if observed_only and not cell.hazard_valid:
                continue
            if cell.flood_mechanism is None:
                continue
            if not (0 <= cell.row < src.height and 0 <= cell.col < src.width):
                continue
            code_grid[cell.row, cell.col] = int(cell.flood_mechanism.mechanism_code)
            for key in FLOOD_STRENGTH_KEYS:
                strength_grids[key][cell.row, cell.col] = float(
                    cell.flood_mechanism.strengths[key]
                )
        return code_grid, strength_grids, src.transform


def _idw_fill_flood_mechanism_grid(
    code_grid: np.ndarray,
    strength_grids: dict[str, np.ndarray],
    transform: Any,
    *,
    max_dist_m: float = MECHANISM_IDW_MAX_DIST_M,
    min_neighbors: int = MECHANISM_IDW_MIN_NEIGHBORS,
    idw_power: float = MECHANISM_IDW_POWER,
    k_neighbors: int = MECHANISM_IDW_K_NEIGHBORS,
) -> tuple[np.ndarray, np.ndarray, dict[tuple[int, int], FloodMechanismClassification]]:
    """Gap-fill mechanism codes by IDW-interpolating observed strength grids."""
    from scipy.spatial import cKDTree

    filled = code_grid.copy()
    is_interp = np.zeros(code_grid.shape, dtype=np.uint8)
    filled_mechs: dict[tuple[int, int], FloodMechanismClassification] = {}

    observed = code_grid != MECHANISM_RASTER_NODATA
    gap = ~observed
    if not gap.any() or not observed.any():
        return filled, is_interp, filled_mechs

    height, width = code_grid.shape
    rows, cols = np.indices((height, width))
    xs, ys = xy(transform, rows.ravel(), cols.ravel(), offset="center")
    xs = np.asarray(xs, dtype=np.float64)
    ys = np.asarray(ys, dtype=np.float64)
    lat0 = float(np.nanmean(ys))
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(lat0))
    coords_m = np.column_stack([xs * m_per_deg_lon, ys * m_per_deg_lat])

    obs_flat_idx = np.flatnonzero(observed.ravel())
    gap_flat_idx = np.flatnonzero(gap.ravel())
    obs_coords = coords_m[obs_flat_idx]
    tree = cKDTree(obs_coords)
    k_query = min(k_neighbors, len(obs_flat_idx))
    gap_coords = coords_m[gap_flat_idx]

    dists, nn_idx = tree.query(gap_coords, k=k_query, workers=-1)
    if k_query == 1:
        dists = dists[:, None]
        nn_idx = nn_idx[:, None]

    valid_nn = (dists > 1e-6) & (dists <= max_dist_m)
    n_valid = valid_nn.sum(axis=1)
    ok = n_valid >= min_neighbors
    if not ok.any():
        return filled, is_interp, filled_mechs

    interp_by_key: dict[str, np.ndarray] = {}
    for key in FLOOD_STRENGTH_KEYS:
        obs_vals = strength_grids[key].ravel()[obs_flat_idx].astype(np.float64)
        vals_nn = obs_vals[nn_idx]
        with np.errstate(divide="ignore", invalid="ignore"):
            w = np.where(valid_nn, 1.0 / (dists**idw_power), 0.0)
        w_sum = w.sum(axis=1)
        interp_by_key[key] = np.where(w_sum > 0, (w * vals_nn).sum(axis=1) / w_sum, np.nan)

    for i, gi in enumerate(gap_flat_idx):
        if not ok[i]:
            continue
        strengths = {
            key: round(float(interp_by_key[key][i]), 3) for key in FLOOD_STRENGTH_KEYS
        }
        if not all(np.isfinite(v) for v in strengths.values()):
            continue
        mech = classify_from_strengths(
            strengths,
            rationale_prefix=["IDW gap-fill from observed neighbor strengths."],
        )
        row, col = np.unravel_index(gi, (height, width))
        filled[row, col] = mech.mechanism_code
        is_interp[row, col] = 1
        filled_mechs[(int(row), int(col))] = mech

    return filled, is_interp, filled_mechs


def _apply_filled_classifications_to_cells(
    result: GridScreeningResult,
    filled_mechs: dict[tuple[int, int], FloodMechanismClassification],
) -> None:
    for cell in result.cells:
        mech = filled_mechs.get((cell.row, cell.col))
        if mech is None:
            continue
        cell.flood_mechanism = mech
        cell.is_interpolated = True


def flood_mechanism_layer_stem(site: str) -> str:
    """Raster basename stem for flood mechanism exports (POA keeps legacy ``poa`` slug)."""
    slug = "poa" if site == DEFAULT_SITE else site
    return f"flood_mechanism_type_{slug}_250m"


def export_flood_mechanism_geotiff(
    result: GridScreeningResult,
    out_path: Path,
    *,
    ref_path: RasterRef | None = None,
    site: str | None = None,
    observed_only: bool = False,
) -> Path:
    """Rasterize dominant flood mechanism codes onto the 250 m reference grid."""
    if result.hazard != "flood":
        raise ValueError("export_flood_mechanism_geotiff requires hazard='flood'")

    ref_path = ref_path or get_reference_hazard_raster("flood", site)
    code_grid, _, _ = _flood_mechanism_grids_from_result(
        result, ref_path, observed_only=observed_only
    )
    return _write_uint8_geotiff(code_grid, out_path, ref_path=ref_path)


def export_flood_mechanism_layers(
    result: GridScreeningResult,
    out_dir: Path,
    *,
    site: str,
    ref_path: RasterRef | None = None,
    apply_open_water_mask: bool | None = None,
) -> dict[str, Path]:
    """Export observed, IDW-filled, and interpolation-mask rasters for flood mechanism."""
    if result.hazard != "flood":
        raise ValueError("export_flood_mechanism_layers requires hazard='flood'")

    from site_config import load_site_config, open_water_enabled

    ref_path = ref_path or get_reference_hazard_raster("flood", site)
    out_dir = Path(out_dir)
    stem = flood_mechanism_layer_stem(site)
    observed_path = out_dir / f"{stem}_observed.tif"
    filled_path = out_dir / f"{stem}.tif"
    if site == DEFAULT_SITE:
        interp_path = out_dir / "flood_mechanism_is_interpolated_poa_250m.tif"
    else:
        interp_path = out_dir / f"flood_mechanism_is_interpolated_{site}_250m.tif"

    observed_grid, strength_grids, transform = _flood_mechanism_grids_from_result(
        result, ref_path, observed_only=True
    )
    mask_water = (
        apply_open_water_mask
        if apply_open_water_mask is not None
        else open_water_enabled(load_site_config(site))
    )
    water_px = 0
    if mask_water:
        water_mask = poa_permanent_open_water_mask(ref_path, site=site)
        _exclude_open_water_from_observed(
            observed_grid, strength_grids, water_mask, FLOOD_STRENGTH_KEYS
        )
    else:
        water_mask = np.zeros(observed_grid.shape, dtype=bool)

    filled_grid, is_interp_grid, filled_mechs = _idw_fill_flood_mechanism_grid(
        observed_grid, strength_grids, transform
    )
    _apply_filled_classifications_to_cells(result, filled_mechs)

    if mask_water:
        water_px = _mask_open_water_pixels(
            observed_grid,
            filled_grid,
            is_interp_grid,
            water_mask,
        )

    paths = {
        "observed": _write_uint8_geotiff(observed_grid, observed_path, ref_path=ref_path),
        "filled": _write_uint8_geotiff(filled_grid, filled_path, ref_path=ref_path),
        "is_interpolated": _write_uint8_geotiff(is_interp_grid, interp_path, ref_path=ref_path),
    }

    observed_n = int((observed_grid != MECHANISM_RASTER_NODATA).sum())
    filled_n = int((filled_grid != MECHANISM_RASTER_NODATA).sum())
    interp_n = int(is_interp_grid.sum())
    print(
        f"{site} flood mechanism rasters: observed={observed_n} px, "
        f"filled={filled_n} px (+{filled_n - observed_n} IDW), interpolated={interp_n} px, "
        f"open_water_masked={water_px} px"
    )
    return paths


def export_poa_flood_mechanism_layers(
    result: GridScreeningResult,
    out_dir: Path,
    *,
    ref_path: RasterRef | None = None,
) -> dict[str, Path]:
    """Export observed, IDW-filled, and interpolation-mask rasters for POA flood mechanism."""
    return export_flood_mechanism_layers(
        result,
        out_dir,
        site=DEFAULT_SITE,
        ref_path=ref_path,
        apply_open_water_mask=True,
    )


def _heat_mechanism_grids_from_result(
    result: GridScreeningResult,
    ref_path: RasterRef,
    *,
    observed_only: bool,
) -> tuple[np.ndarray, dict[str, np.ndarray], Any]:
    """Build code + strength grids from screened heat cells (direct row/col indexing)."""
    if result.hazard != "heat":
        raise ValueError("_heat_mechanism_grids_from_result requires hazard='heat'")

    with rasterio.open(ref_path) as src:
        code_grid = np.full((src.height, src.width), MECHANISM_RASTER_NODATA, dtype=np.uint8)
        strength_grids = {
            key: np.full((src.height, src.width), np.nan, dtype=np.float32)
            for key in HEAT_STRENGTH_KEYS
        }
        for cell in result.cells:
            if observed_only and not cell.hazard_valid:
                continue
            if cell.heat_mechanism is None:
                continue
            if not (0 <= cell.row < src.height and 0 <= cell.col < src.width):
                continue
            code_grid[cell.row, cell.col] = int(cell.heat_mechanism.mechanism_code)
            for key in HEAT_STRENGTH_KEYS:
                strength_grids[key][cell.row, cell.col] = float(
                    cell.heat_mechanism.strengths[key]
                )
        return code_grid, strength_grids, src.transform


def _idw_fill_heat_mechanism_grid(
    code_grid: np.ndarray,
    strength_grids: dict[str, np.ndarray],
    transform: Any,
    *,
    max_dist_m: float = MECHANISM_IDW_MAX_DIST_M,
    min_neighbors: int = MECHANISM_IDW_MIN_NEIGHBORS,
    idw_power: float = MECHANISM_IDW_POWER,
    k_neighbors: int = MECHANISM_IDW_K_NEIGHBORS,
) -> tuple[np.ndarray, np.ndarray, dict[tuple[int, int], HeatMechanismClassification]]:
    """Gap-fill heat mechanism codes by IDW-interpolating observed strength grids."""
    from scipy.spatial import cKDTree

    filled = code_grid.copy()
    is_interp = np.zeros(code_grid.shape, dtype=np.uint8)
    filled_mechs: dict[tuple[int, int], HeatMechanismClassification] = {}

    observed = code_grid != MECHANISM_RASTER_NODATA
    gap = ~observed
    if not gap.any() or not observed.any():
        return filled, is_interp, filled_mechs

    height, width = code_grid.shape
    rows, cols = np.indices((height, width))
    xs, ys = xy(transform, rows.ravel(), cols.ravel(), offset="center")
    xs = np.asarray(xs, dtype=np.float64)
    ys = np.asarray(ys, dtype=np.float64)
    lat0 = float(np.nanmean(ys))
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(lat0))
    coords_m = np.column_stack([xs * m_per_deg_lon, ys * m_per_deg_lat])

    obs_flat_idx = np.flatnonzero(observed.ravel())
    gap_flat_idx = np.flatnonzero(gap.ravel())
    obs_coords = coords_m[obs_flat_idx]
    tree = cKDTree(obs_coords)
    k_query = min(k_neighbors, len(obs_flat_idx))
    gap_coords = coords_m[gap_flat_idx]

    dists, nn_idx = tree.query(gap_coords, k=k_query, workers=-1)
    if k_query == 1:
        dists = dists[:, None]
        nn_idx = nn_idx[:, None]

    valid_nn = (dists > 1e-6) & (dists <= max_dist_m)
    n_valid = valid_nn.sum(axis=1)
    ok = n_valid >= min_neighbors
    if not ok.any():
        return filled, is_interp, filled_mechs

    interp_by_key: dict[str, np.ndarray] = {}
    for key in HEAT_STRENGTH_KEYS:
        obs_vals = strength_grids[key].ravel()[obs_flat_idx].astype(np.float64)
        vals_nn = obs_vals[nn_idx]
        with np.errstate(divide="ignore", invalid="ignore"):
            w = np.where(valid_nn, 1.0 / (dists**idw_power), 0.0)
        w_sum = w.sum(axis=1)
        interp_by_key[key] = np.where(w_sum > 0, (w * vals_nn).sum(axis=1) / w_sum, np.nan)

    for i, gi in enumerate(gap_flat_idx):
        if not ok[i]:
            continue
        strengths = {
            key: round(float(interp_by_key[key][i]), 3) for key in HEAT_STRENGTH_KEYS
        }
        if not all(np.isfinite(v) for v in strengths.values()):
            continue
        mech = classify_from_heat_strengths(
            strengths,
            rationale_prefix=["IDW gap-fill from observed neighbor strengths."],
        )
        row, col = np.unravel_index(gi, (height, width))
        filled[row, col] = mech.mechanism_code
        is_interp[row, col] = 1
        filled_mechs[(int(row), int(col))] = mech

    return filled, is_interp, filled_mechs


def _apply_filled_heat_classifications_to_cells(
    result: GridScreeningResult,
    filled_mechs: dict[tuple[int, int], HeatMechanismClassification],
) -> None:
    for cell in result.cells:
        mech = filled_mechs.get((cell.row, cell.col))
        if mech is None:
            continue
        cell.heat_mechanism = mech
        cell.is_interpolated = True


def export_poa_heat_mechanism_layers(
    result: GridScreeningResult,
    out_dir: Path,
    *,
    ref_path: RasterRef | None = None,
) -> dict[str, Path]:
    """Export observed, IDW-filled, and interpolation-mask rasters for POA heat mechanism."""
    if result.hazard != "heat":
        raise ValueError("export_poa_heat_mechanism_layers requires hazard='heat'")

    ref_path = ref_path or REF_RASTER["heat"]
    out_dir = Path(out_dir)
    observed_path = out_dir / "heat_mechanism_type_poa_250m_observed.tif"
    filled_path = out_dir / "heat_mechanism_type_poa_250m.tif"
    interp_path = out_dir / "heat_mechanism_is_interpolated_poa_250m.tif"

    observed_grid, strength_grids, transform = _heat_mechanism_grids_from_result(
        result, ref_path, observed_only=True
    )
    water_mask = poa_permanent_open_water_mask(ref_path)
    _exclude_open_water_from_observed(
        observed_grid, strength_grids, water_mask, HEAT_STRENGTH_KEYS
    )
    filled_grid, is_interp_grid, filled_mechs = _idw_fill_heat_mechanism_grid(
        observed_grid, strength_grids, transform
    )
    _apply_filled_heat_classifications_to_cells(result, filled_mechs)

    water_px = _mask_open_water_pixels(
        observed_grid,
        filled_grid,
        is_interp_grid,
        water_mask,
    )

    paths = {
        "observed": _write_uint8_geotiff(observed_grid, observed_path, ref_path=ref_path),
        "filled": _write_uint8_geotiff(filled_grid, filled_path, ref_path=ref_path),
        "is_interpolated": _write_uint8_geotiff(is_interp_grid, interp_path, ref_path=ref_path),
    }

    observed_n = int((observed_grid != MECHANISM_RASTER_NODATA).sum())
    filled_n = int((filled_grid != MECHANISM_RASTER_NODATA).sum())
    interp_n = int(is_interp_grid.sum())
    print(
        f"POA heat mechanism rasters: observed={observed_n} px, "
        f"filled={filled_n} px (+{filled_n - observed_n} IDW), interpolated={interp_n} px, "
        f"open_water_masked={water_px} px"
    )
    return paths


def export_heat_mechanism_geotiff(
    result: GridScreeningResult,
    out_path: Path,
    *,
    ref_path: RasterRef | None = None,
    observed_only: bool = False,
) -> Path:
    """Rasterize dominant heat mechanism codes onto the 250 m reference grid."""
    if result.hazard != "heat":
        raise ValueError("export_heat_mechanism_geotiff requires hazard='heat'")

    ref_path = ref_path or REF_RASTER["heat"]
    code_grid, _, _ = _heat_mechanism_grids_from_result(
        result, ref_path, observed_only=observed_only
    )
    return _write_uint8_geotiff(code_grid, out_path, ref_path=ref_path)


def poa_landslide_reference_bounds_geom():
    """Full POA extent of the 90 m landslide hazard reference grid."""
    return site_reference_bounds_geom("landslide", DEFAULT_SITE)


def screen_poa_landslide_mechanism_grid(**kwargs: Any) -> GridScreeningResult:
    """Screen hazard-valid 90 m cells on the POA landslide grid; export IDW-fills gaps."""
    return screen_grid(
        poa_landslide_reference_bounds_geom(),
        hazard="landslide",
        aoi_label="porto_alegre",
        require_hazard_valid=kwargs.pop("require_hazard_valid", True),
        require_positive_hazard=kwargs.pop("require_positive_hazard", True),
        preload_layers=kwargs.pop("preload_layers", True),
        zonal_fallback=kwargs.pop("zonal_fallback", False),
        **kwargs,
    )


def _landslide_mechanism_grids_from_result(
    result: GridScreeningResult,
    ref_path: RasterRef,
    *,
    observed_only: bool,
) -> tuple[np.ndarray, dict[str, np.ndarray], Any]:
    if result.hazard != "landslide":
        raise ValueError("_landslide_mechanism_grids_from_result requires hazard='landslide'")

    with rasterio.open(ref_path) as src:
        code_grid = np.full((src.height, src.width), MECHANISM_RASTER_NODATA, dtype=np.uint8)
        strength_grids = {
            key: np.full((src.height, src.width), np.nan, dtype=np.float32)
            for key in LANDSLIDE_STRENGTH_KEYS
        }
        for cell in result.cells:
            if observed_only and not cell.hazard_valid:
                continue
            if cell.landslide_mechanism is None:
                continue
            if not (0 <= cell.row < src.height and 0 <= cell.col < src.width):
                continue
            code_grid[cell.row, cell.col] = int(cell.landslide_mechanism.mechanism_code)
            for key in LANDSLIDE_STRENGTH_KEYS:
                strength_grids[key][cell.row, cell.col] = float(
                    cell.landslide_mechanism.strengths[key]
                )
        return code_grid, strength_grids, src.transform


def _idw_fill_landslide_mechanism_grid(
    code_grid: np.ndarray,
    strength_grids: dict[str, np.ndarray],
    transform: Any,
    *,
    max_dist_m: float = MECHANISM_IDW_MAX_DIST_M,
    min_neighbors: int = MECHANISM_IDW_MIN_NEIGHBORS,
    idw_power: float = MECHANISM_IDW_POWER,
    k_neighbors: int = MECHANISM_IDW_K_NEIGHBORS,
) -> tuple[np.ndarray, np.ndarray, dict[tuple[int, int], LandslideMechanismClassification]]:
    from scipy.spatial import cKDTree

    filled = code_grid.copy()
    is_interp = np.zeros(code_grid.shape, dtype=np.uint8)
    filled_mechs: dict[tuple[int, int], LandslideMechanismClassification] = {}

    observed = code_grid != MECHANISM_RASTER_NODATA
    gap = ~observed
    if not gap.any() or not observed.any():
        return filled, is_interp, filled_mechs

    height, width = code_grid.shape
    rows, cols = np.indices((height, width))
    xs, ys = xy(transform, rows.ravel(), cols.ravel(), offset="center")
    xs = np.asarray(xs, dtype=np.float64)
    ys = np.asarray(ys, dtype=np.float64)
    lat0 = float(np.nanmean(ys))
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(lat0))
    coords_m = np.column_stack([xs * m_per_deg_lon, ys * m_per_deg_lat])

    obs_flat_idx = np.flatnonzero(observed.ravel())
    gap_flat_idx = np.flatnonzero(gap.ravel())
    obs_coords = coords_m[obs_flat_idx]
    tree = cKDTree(obs_coords)
    k_query = min(k_neighbors, len(obs_flat_idx))
    gap_coords = coords_m[gap_flat_idx]

    dists, nn_idx = tree.query(gap_coords, k=k_query, workers=-1)
    if k_query == 1:
        dists = dists[:, None]
        nn_idx = nn_idx[:, None]

    valid_nn = (dists > 1e-6) & (dists <= max_dist_m)
    n_valid = valid_nn.sum(axis=1)
    ok = n_valid >= min_neighbors
    if not ok.any():
        return filled, is_interp, filled_mechs

    interp_by_key: dict[str, np.ndarray] = {}
    for key in LANDSLIDE_STRENGTH_KEYS:
        obs_vals = strength_grids[key].ravel()[obs_flat_idx].astype(np.float64)
        vals_nn = obs_vals[nn_idx]
        with np.errstate(divide="ignore", invalid="ignore"):
            w = np.where(valid_nn, 1.0 / (dists**idw_power), 0.0)
        w_sum = w.sum(axis=1)
        interp_by_key[key] = np.where(w_sum > 0, (w * vals_nn).sum(axis=1) / w_sum, np.nan)

    for i, gi in enumerate(gap_flat_idx):
        if not ok[i]:
            continue
        strengths = {
            key: round(float(interp_by_key[key][i]), 3) for key in LANDSLIDE_STRENGTH_KEYS
        }
        if not all(np.isfinite(v) for v in strengths.values()):
            continue
        mech = classify_from_landslide_strengths(
            strengths,
            rationale_prefix=["IDW gap-fill from observed neighbor strengths."],
        )
        row, col = np.unravel_index(gi, (height, width))
        filled[row, col] = mech.mechanism_code
        is_interp[row, col] = 1
        filled_mechs[(int(row), int(col))] = mech

    return filled, is_interp, filled_mechs


def _apply_filled_landslide_classifications_to_cells(
    result: GridScreeningResult,
    filled_mechs: dict[tuple[int, int], LandslideMechanismClassification],
) -> None:
    for cell in result.cells:
        mech = filled_mechs.get((cell.row, cell.col))
        if mech is None:
            continue
        cell.landslide_mechanism = mech
        cell.is_interpolated = True


def export_poa_landslide_mechanism_layers(
    result: GridScreeningResult,
    out_dir: Path,
    *,
    ref_path: RasterRef | None = None,
) -> dict[str, Path]:
    """Export observed, IDW-filled, and interpolation-mask rasters for POA landslide mechanism."""
    if result.hazard != "landslide":
        raise ValueError("export_poa_landslide_mechanism_layers requires hazard='landslide'")

    ref_path = ref_path or REF_RASTER["landslide"]
    out_dir = Path(out_dir)
    observed_path = out_dir / "landslide_mechanism_type_poa_90m_observed.tif"
    filled_path = out_dir / "landslide_mechanism_type_poa_90m.tif"
    interp_path = out_dir / "landslide_mechanism_is_interpolated_poa_90m.tif"

    observed_grid, strength_grids, transform = _landslide_mechanism_grids_from_result(
        result, ref_path, observed_only=True
    )
    water_mask = poa_permanent_open_water_mask(ref_path)
    _exclude_open_water_from_observed(
        observed_grid, strength_grids, water_mask, LANDSLIDE_STRENGTH_KEYS
    )
    filled_grid, is_interp_grid, filled_mechs = _idw_fill_landslide_mechanism_grid(
        observed_grid, strength_grids, transform
    )
    _apply_filled_landslide_classifications_to_cells(result, filled_mechs)

    water_px = _mask_open_water_pixels(
        observed_grid,
        filled_grid,
        is_interp_grid,
        water_mask,
    )

    paths = {
        "observed": _write_uint8_geotiff(observed_grid, observed_path, ref_path=ref_path),
        "filled": _write_uint8_geotiff(filled_grid, filled_path, ref_path=ref_path),
        "is_interpolated": _write_uint8_geotiff(is_interp_grid, interp_path, ref_path=ref_path),
    }

    observed_n = int((observed_grid != MECHANISM_RASTER_NODATA).sum())
    filled_n = int((filled_grid != MECHANISM_RASTER_NODATA).sum())
    interp_n = int(is_interp_grid.sum())
    print(
        f"POA landslide mechanism rasters: observed={observed_n} px, "
        f"filled={filled_n} px (+{filled_n - observed_n} IDW), interpolated={interp_n} px, "
        f"open_water_masked={water_px} px"
    )
    return paths


def export_landslide_mechanism_geotiff(
    result: GridScreeningResult,
    out_path: Path,
    *,
    ref_path: RasterRef | None = None,
    observed_only: bool = False,
) -> Path:
    """Rasterize dominant landslide mechanism codes onto the 90 m reference grid."""
    if result.hazard != "landslide":
        raise ValueError("export_landslide_mechanism_geotiff requires hazard='landslide'")

    ref_path = ref_path or REF_RASTER["landslide"]
    code_grid, _, _ = _landslide_mechanism_grids_from_result(
        result, ref_path, observed_only=observed_only
    )
    return _write_uint8_geotiff(code_grid, out_path, ref_path=ref_path)
