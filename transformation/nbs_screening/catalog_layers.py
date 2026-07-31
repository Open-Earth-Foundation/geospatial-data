"""Catalog layer query helpers for NBS site screening.

Reads diagnostic COGs from the geospatial-data catalog (S3).
COG URLs are aligned with `geospatial-data/catalog/datasets.yaml`.

Step 0 bairro polygons load from catalog vector exports on S3 (gpkg).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import Resampling, reproject, transform as warp_transform, transform_bounds, transform_geom
from shapely.geometry import mapping, shape

HazardKind = Literal["flood", "heat", "landslide"]

# geospatial-data/transformation/nbs_screening/catalog_layers.py
NBS_SCREENING_ROOT = Path(__file__).resolve().parent
GEOSPATIAL_DATA_ROOT = NBS_SCREENING_ROOT.parent.parent
OUTPUT_DIR = NBS_SCREENING_ROOT / "output"
# Optional local OSM rivers sample for riverine distance (POA). Override with NBS_RIVERS_GEOJSON.
SAMPLE_DATA = Path(
    __import__("os").environ.get(
        "NBS_SAMPLE_DATA",
        str(GEOSPATIAL_DATA_ROOT.parent / "NBS-Project-Preparation" / "client" / "public" / "sample-data"),
    )
)
NBS_E2E_ROOT = NBS_SCREENING_ROOT  # backward-compatible alias
REPO_ROOT = GEOSPATIAL_DATA_ROOT  # backward-compatible alias

S3 = "https://geo-test-api.s3.us-east-1.amazonaws.com"

BARIO_VECTOR_URLS: dict[str, str] = {
    "flood": (
        f"{S3}/oef_calculation/release/v1/porto_alegre/climate_hazards/floods/vector/"
        "flood_risk_score_poa.gpkg"
    ),
    "heat": (
        f"{S3}/oef_calculation/release/v1/porto_alegre/climate_hazards/heat/vector/"
        "heat_risk_score_poa.gpkg"
    ),
    "landslide": (
        f"{S3}/oef_calculation/release/v1/porto_alegre/climate_hazards/landslides/vector/"
        "landslide_risk_score_poa.gpkg"
    ),
}

_GDF_CACHE: dict[str, gpd.GeoDataFrame] = {}
_RIVERS_FEATURE_CACHE: list[tuple[Any, dict]] | None = None
_RIVERS_RTREE_CACHE: Any | None = None


def _river_features() -> list[tuple[Any, dict]]:
    """Load OSM river geometries once (grid screening calls this per cell)."""
    global _RIVERS_FEATURE_CACHE
    if _RIVERS_FEATURE_CACHE is None:
        rivers_path = Path(__import__("os").environ["NBS_RIVERS_GEOJSON"]).expanduser() if __import__("os").environ.get("NBS_RIVERS_GEOJSON") else (SAMPLE_DATA / "porto-alegre-rivers.json")
        rivers = json.loads(rivers_path.read_text())
        _RIVERS_FEATURE_CACHE = [
            (shape(feat["geometry"]), feat.get("properties") or {})
            for feat in rivers["geoJson"]["features"]
        ]
    return _RIVERS_FEATURE_CACHE


def _bounds_for_crs(
    bounds: tuple[float, float, float, float],
    crs: Any,
) -> tuple[float, float, float, float]:
    """Reproject WGS84 AOI bounds to a layer CRS when needed."""
    if crs is None or crs.to_epsg() == 4326:
        return bounds
    return transform_bounds("EPSG:4326", crs, *bounds)


def _rowcol_for_lonlat(
    lon: float,
    lat: float,
    raster_transform: Any,
    crs: Any,
) -> tuple[int, int]:
    """Map WGS84 lon/lat to raster row/col, reprojecting when the layer is not EPSG:4326."""
    x, y = lon, lat
    if crs is not None and crs.to_epsg() != 4326:
        x, y = warp_transform("EPSG:4326", crs, [lon], [lat])
        x, y = float(x[0]), float(y[0])
    row, col = rasterio.transform.rowcol(raster_transform, x, y)
    return int(row), int(col)


def _river_strtree() -> Any:
    """Spatial index over OSM waterways (nearest-feature lookup per grid cell)."""
    global _RIVERS_RTREE_CACHE
    if _RIVERS_RTREE_CACHE is None:
        from shapely import STRtree

        _RIVERS_RTREE_CACHE = STRtree([line for line, _ in _river_features()])
    return _RIVERS_RTREE_CACHE


class RasterPointSampler:
    """Keep COG datasets open while sampling many lon/lat points (grid screening)."""

    def __init__(self, layers: dict[str, str | Path]):
        self.layers = layers
        self._src: dict[str, Any] = {}

    def __enter__(self) -> RasterPointSampler:
        for key, path in self.layers.items():
            try:
                self._src[key] = rasterio.open(str(path))
            except Exception:  # noqa: BLE001
                continue
        return self

    def __exit__(self, *_args: Any) -> None:
        for src in self._src.values():
            try:
                src.close()
            except Exception:  # noqa: BLE001
                pass
        self._src.clear()

    def read(self, key: str, lon: float, lat: float) -> float | None:
        src = self._src.get(key)
        if src is None:
            return None
        try:
            ys, xs = _rowcol_for_lonlat(lon, lat, src.transform, src.crs)
            if not (0 <= ys < src.height and 0 <= xs < src.width):
                return None
            val = float(src.read(1, window=((ys, ys + 1), (xs, xs + 1)))[0, 0])
            if src.nodata is not None and np.isfinite(src.nodata) and val == src.nodata:
                return None
            if val <= -9999 or not np.isfinite(val):
                return None
            return val
        except Exception:  # noqa: BLE001
            return None


class RasterLayerCache:
    """Preload COG windows into memory for bulk grid screening (avoids per-cell S3 reads)."""

    def __init__(
        self,
        layers: dict[str, str | Path],
        *,
        bounds: tuple[float, float, float, float] | None = None,
    ):
        self.layers = layers
        self.bounds = bounds
        self._data: dict[str, dict[str, Any]] = {}

    def __enter__(self) -> RasterLayerCache:
        from rasterio.windows import from_bounds

        for key, path in self.layers.items():
            try:
                with rasterio.open(str(path)) as src:
                    if self.bounds is not None:
                        layer_bounds = _bounds_for_crs(self.bounds, src.crs)
                        window = from_bounds(*layer_bounds, transform=src.transform)
                        window = window.intersection(
                            rasterio.windows.Window(0, 0, src.width, src.height)
                        )
                        band = src.read(1, window=window, masked=True)
                        transform = src.window_transform(window)
                    else:
                        band = src.read(1, masked=True)
                        transform = src.transform
                    self._data[key] = {
                        "array": band,
                        "transform": transform,
                        "nodata": src.nodata,
                        "crs": src.crs,
                    }
            except Exception:  # noqa: BLE001
                continue
        return self

    def __exit__(self, *_args: Any) -> None:
        self._data.clear()

    def read(self, key: str, lon: float, lat: float) -> float | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        try:
            ys, xs = _rowcol_for_lonlat(
                lon, lat, entry["transform"], entry.get("crs")
            )
            arr = entry["array"]
            if not (0 <= ys < arr.shape[0] and 0 <= xs < arr.shape[1]):
                return None
            if np.ma.is_masked(arr):
                if arr.mask[ys, xs]:
                    return None
                val = float(arr.data[ys, xs])
            else:
                val = float(arr[ys, xs])
            return _finite_raster_value(val, entry["nodata"])
        except Exception:  # noqa: BLE001
            return None


def sample_raster_zonal_mean_cached(cache: RasterLayerCache, key: str, geom) -> float | None:
    """Zonal mean from a preloaded layer (local array; no extra COG open per cell)."""
    from rasterio.features import geometry_mask

    entry = cache._data.get(key)
    if entry is None:
        return None
    try:
        g = mapping(geom)
        if entry["crs"] and entry["crs"].to_epsg() != 4326:
            g = transform_geom("EPSG:4326", entry["crs"], g)
        arr = entry["array"]
        inside = geometry_mask(
            [g], out_shape=arr.shape, transform=entry["transform"], invert=True
        )
        if np.ma.isMaskedArray(arr):
            valid = arr.data[inside & ~arr.mask]
        else:
            valid = arr[inside]
        valid = valid[np.isfinite(valid)]
        if entry["nodata"] is not None:
            valid = valid[valid != float(entry["nodata"])]
        valid = valid[valid > -9999]
        if valid.size == 0:
            return None
        return float(np.mean(valid))
    except Exception:  # noqa: BLE001
        return None


def dw_mode_fractions_cached(cache: RasterLayerCache, key: str, geom) -> dict[str, float]:
    """Dynamic World class fractions from a preloaded mode COG (no per-cell S3 open)."""
    from rasterio.features import geometry_mask

    entry = cache._data.get(key)
    if entry is None:
        return {}
    try:
        g = mapping(geom)
        if entry["crs"] and entry["crs"].to_epsg() != 4326:
            g = transform_geom("EPSG:4326", entry["crs"], g)
        arr = entry["array"]
        inside = geometry_mask(
            [g], out_shape=arr.shape, transform=entry["transform"], invert=True
        )
        if np.ma.isMaskedArray(arr):
            valid = arr.data[inside & ~arr.mask]
        else:
            valid = arr[inside]
        valid = valid[np.isfinite(valid)]
        if entry["nodata"] is not None:
            valid = valid[valid != float(entry["nodata"])]
        if valid.size == 0:
            return {}
        fractions = {
            f"dw_{label}_pct": _class_fraction(valid, class_id)
            for label, class_id in DYNAMIC_WORLD_CLASSES.items()
        }
        tree = float(fractions.get("dw_trees_pct") or 0.0)
        grass = float(fractions.get("dw_grass_pct") or 0.0)
        shrub = float(fractions.get("dw_shrub_pct") or 0.0)
        return {
            "dw_built_pct_mean": float(fractions.get("dw_built_pct") or 0.0),
            "dw_bare_pct_mean": float(fractions.get("dw_bare_pct") or 0.0),
            "green_pct_mean": tree + grass + shrub,
            "tree_pct_mean": tree,
        }
    except Exception:  # noqa: BLE001
        return {}


from site_config import (  # noqa: E402 — after path constants
    DEFAULT_SITE,
    get_catalog_urls,
    get_layer_sources as _resolve_layer_sources,
    get_local_layers,
    reference_hazard_layer,
)

# Porto Alegre defaults (from config/sites/porto_alegre.yaml) — backward-compatible aliases.
FLOOD_CATALOG_COGS: dict[str, str] = get_catalog_urls("flood", DEFAULT_SITE)
HEAT_CATALOG_COGS: dict[str, str] = get_catalog_urls("heat", DEFAULT_SITE)
LANDSLIDE_CATALOG_COGS: dict[str, str] = get_catalog_urls("landslide", DEFAULT_SITE)

# Backward-compatible alias for flood E2E notebook / run_e2e.py
CATALOG_COGS = FLOOD_CATALOG_COGS

# Raster screening uses catalog COGs only. Empty dict kept for API compatibility.
FLOOD_LOCAL_RASTERS: dict[str, Path] = {}
HEAT_LOCAL_RASTERS: dict[str, Path] = {}
LANDSLIDE_LOCAL_RASTERS: dict[str, Path] = {}

LOCAL_SCREENING_RASTERS = FLOOD_LOCAL_RASTERS

FLOOD_GRID_KEYS: dict[str, str] = {
    "flood_hazard": "flood_score_mean",
    "exposure": "exposure_score_mean",
    "vulnerability": "vulnerability_score_mean",
    "flood_risk": "risk_score_mean",
    "gfplain250m": "floodplain_adj_pct_mean",
    "poa_depression_mask": "depression_pct_mean",
    "poa_relative_elevation": "relative_elevation_mean",
    "poa_depression_depth": "depression_depth_mean",
    "poa_slope": "slope_mean",
    "soilgrids_clay": "clay_pct_mean",
}

HEAT_GRID_KEYS: dict[str, str] = {
    "heat_hazard": "heat_score_mean",
    "exposure": "exposure_score_mean",
    "vulnerability": "vulnerability_score_mean",
    "heat_risk": "heat_risk_score_mean",
    "landsat8_lst_djf": "landsat_lst_norm_mean",
    "modis_lst_day_p90": "modis_lst_day_norm_mean",
    "modis_lst_night_p90": "modis_lst_night_norm_mean",
    "poa_slope": "slope_mean",
    "soilgrids_clay": "clay_pct_mean",
    "hansen_treecover2000": "treecover2000_mean",
}

LANDSLIDE_GRID_KEYS: dict[str, str] = {
    "landslide_hazard": "landslide_score_mean",
    "exposure": "exposure_score_mean",
    "vulnerability": "vulnerability_score_mean",
    "landslide_risk": "landslide_risk_score_mean",
    "poa_slope": "slope_mean",
    "soilgrids_clay": "clay_pct_mean",
    "merit_hand": "merit_hand_mean",
    "merit_upa": "upstream_area_km2_mean",
    "chirps_r90p_climatology": "r90p_climatology_mean",
    "hansen_treecover2000": "treecover2000_mean",
    "ndvi_p10_djf": "ndvi_p10_mean",
}

HEV_GRID_KEYS = FLOOD_GRID_KEYS

DYNAMIC_WORLD_CLASSES = {
    "water": 0,
    "trees": 1,
    "grass": 2,
    "flooded_vegetation": 3,
    "crops": 4,
    "shrub": 5,
    "built": 6,
    "bare": 7,
}

JRC_WATER_TRANSITION_WET_CLASSES = {1, 2, 4, 5, 7, 8, 9, 10}
# JRC GSW transition class 1 = permanent water (1984–2021).
JRC_PERMANENT_WATER_TRANSITION_CLASS = 1
# Occurrence % threshold used in WRI Aqueduct POA workflows for Lago Guaíba.
JRC_PERMANENT_WATER_OCCURRENCE_MIN = 90

# Layers coarser than typical bairro polygons need all_touched masking so
# intersecting cells count even when no pixel center falls inside the polygon.
COARSE_MASK_LAYER_PREFIXES = ("chirps_", "modis_lst_", "modis_ndvi", "ndvi_p10")

HAZARD_CATALOG: dict[HazardKind, dict[str, str]] = {
    "flood": FLOOD_CATALOG_COGS,
    "heat": HEAT_CATALOG_COGS,
    "landslide": LANDSLIDE_CATALOG_COGS,
}

HAZARD_LOCAL_RASTERS: dict[HazardKind, dict[str, Path]] = {
    "flood": FLOOD_LOCAL_RASTERS,
    "heat": HEAT_LOCAL_RASTERS,
    "landslide": LANDSLIDE_LOCAL_RASTERS,
}

HAZARD_GRID_KEYS: dict[HazardKind, dict[str, str]] = {
    "flood": FLOOD_GRID_KEYS,
    "heat": HEAT_GRID_KEYS,
    "landslide": LANDSLIDE_GRID_KEYS,
}

# Hard requirements for mechanism screening. Risk/E/V stay optional until shared
# multi-city E/V migration; mechanism proxies still run when those are nodata.
HAZARD_REQUIRED_LAYERS: dict[HazardKind, tuple[str, ...]] = {
    "flood": ("flood_hazard",),
    "heat": ("heat_hazard",),
    "landslide": ("landslide_hazard",),
}

HAZARD_OPTIONAL_LAYERS: dict[HazardKind, tuple[str, ...]] = {
    "flood": ("flood_risk", "exposure", "vulnerability"),
    "heat": ("heat_risk", "exposure", "vulnerability"),
    "landslide": ("landslide_risk", "exposure", "vulnerability"),
}

# Remaining local-only assets (not raster COGs in catalog):
#   - lst_lc08_norm / mod11a2_lst_*_norm  (min–max normalized LST; catalog has P90 composites)
# Step 0 bairro vectors: catalog S3 gpkgs for POA; override locally for other cities.


def get_catalog_cogs(hazard: HazardKind = "flood", site: str | None = None) -> dict[str, str]:
    """Catalog layer URLs (or local path strings when a local file exists)."""
    if site is None:
        return HAZARD_CATALOG[hazard]
    return get_catalog_urls(hazard, site)


def get_local_rasters(hazard: HazardKind = "flood", site: str | None = None) -> dict[str, Path]:
    if site is None:
        return HAZARD_LOCAL_RASTERS[hazard]
    return get_local_layers(hazard, site)


def get_layer_sources(hazard: HazardKind = "flood", site: str | None = None) -> dict[str, str | Path]:
    """Resolved raster paths for grid screening (local preferred over URL)."""
    return _resolve_layer_sources(hazard, site or DEFAULT_SITE)


def get_reference_hazard_raster(hazard: HazardKind = "flood", site: str | None = None) -> str | Path:
    sources = get_layer_sources(hazard, site)
    layer_id = reference_hazard_layer(hazard)
    if layer_id not in sources:
        raise KeyError(f"Reference hazard layer {layer_id!r} missing for site={site or DEFAULT_SITE}")
    return sources[layer_id]


GRID_VALUE_LAYER_KEYS: dict[HazardKind, dict[str, str]] = {
    "flood": {
        "flood_score_mean": "flood_hazard",
        "exposure_score_mean": "exposure",
        "vulnerability_score_mean": "vulnerability",
        "risk_score_mean": "flood_risk",
        "floodplain_adj_pct_mean": "gfplain250m",
        "depression_pct_mean": "poa_depression_mask",
    },
    "heat": {
        "heat_score_mean": "heat_hazard",
        "exposure_score_mean": "exposure",
        "vulnerability_score_mean": "vulnerability",
        "heat_risk_score_mean": "heat_risk",
    },
    "landslide": {
        "landslide_score_mean": "landslide_hazard",
        "exposure_score_mean": "exposure",
        "vulnerability_score_mean": "vulnerability",
        "landslide_risk_score_mean": "landslide_risk",
        "slope_mean": "poa_slope",
        "clay_pct_mean": "soilgrids_clay",
        "merit_hand_mean": "merit_hand",
    },
}

GRID_OPTIONAL_LAYER_KEYS: dict[HazardKind, dict[str, str]] = {
    "flood": {
        "merit_hand_mean": "merit_hand",
        "imperv_pct_mean": "ghsl_built_up",
        "dw_built_pct_mean": "dynamic_world_mode_250m",
        "surface_water_occurrence_mean": "jrc_surface_water_occurrence",
        "surface_water_seasonality_mean": "jrc_surface_water_seasonality",
    },
    "heat": {
        "imperv_pct_mean": "ghsl_built_up",
        "treecover2000_mean": "hansen_treecover2000",
        "ndvi_mean": "modis_ndvi",
        "landsat_lst_norm_mean": "landsat8_lst_djf",
        "modis_lst_day_norm_mean": "modis_lst_day_p90",
        "modis_lst_night_norm_mean": "modis_lst_night_p90",
    },
    "landslide": {
        "upstream_area_km2_mean": "merit_upa",
        "r90p_climatology_mean": "chirps_r90p_climatology",
        "ndvi_p10_mean": "ndvi_p10_djf",
        "treecover2000_mean": "hansen_treecover2000",
        "dw_built_pct_mean": "dynamic_world_mode_250m",
    },
}


def build_grid_layer_urls(
    hazard: HazardKind,
    *,
    site: str | None = None,
    sample_catalog: bool = True,
) -> dict[str, str | Path]:
    """Stat-key → raster path map used by grid_screening sampling."""
    sources = get_layer_sources(hazard, site)
    urls: dict[str, str | Path] = {}
    for stat_key, layer_id in GRID_VALUE_LAYER_KEYS[hazard].items():
        if layer_id in sources:
            urls[stat_key] = sources[layer_id]
    if sample_catalog:
        for stat_key, layer_id in GRID_OPTIONAL_LAYER_KEYS.get(hazard, {}).items():
            if stat_key not in urls and layer_id in sources:
                urls[stat_key] = sources[layer_id]
    return urls


def poa_permanent_open_water_mask(ref_path: str | Path, site: str | None = None) -> np.ndarray:
    """Boolean mask (True = permanent open water) aligned to a POA 250 m reference grid.

    Combines JRC GSW transition class 1 (permanent water) with occurrence >= 90%,
    matching the WRI Aqueduct convention for masking Lago Guaíba.
    """
    ref_path = Path(str(ref_path))
    with rasterio.open(ref_path) as ref:
        shape = (ref.height, ref.width)
        dst_transform = ref.transform
        dst_crs = ref.crs
        water = np.zeros(shape, dtype=bool)

        for layer_key, predicate in (
            (
                "jrc_surface_water_transition",
                lambda band: band == JRC_PERMANENT_WATER_TRANSITION_CLASS,
            ),
            (
                "jrc_surface_water_occurrence",
                lambda band: band >= JRC_PERMANENT_WATER_OCCURRENCE_MIN,
            ),
        ):
            flood_sources = get_layer_sources("flood", site)
            cog_path = flood_sources[layer_key]
            with rasterio.open(cog_path) as src:
                aligned = np.zeros(shape, dtype=src.dtypes[0])
                reproject(
                    source=rasterio.band(src, 1),
                    destination=aligned,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest,
                )
                water |= predicate(aligned)

        return water


def _mask_all_touched(layer_id: str) -> bool:
    return layer_id.startswith(COARSE_MASK_LAYER_PREFIXES)


def _valid_band(data, nodata: float | int | None) -> np.ndarray:
    band = data[0].astype("float64").filled(np.nan)
    if nodata is not None and np.isfinite(nodata):
        band[band == nodata] = np.nan
    band[band <= -9999] = np.nan
    return band


def _class_fraction(valid: np.ndarray, class_id: int) -> float:
    if valid.size == 0:
        return 0.0
    return float(np.mean(valid.astype(int) == class_id))


def dw_built_pct_from_class_value(class_val: float) -> float:
    """Point or zonal class ID → built fraction (Dynamic World mode band)."""
    return 1.0 if int(class_val) == DYNAMIC_WORLD_CLASSES["built"] else 0.0


def _slope_stats_degrees(band: np.ndarray, xres: float, yres: float) -> dict[str, float | int | None]:
    if band.shape[0] < 2 or band.shape[1] < 2:
        return {}
    gy, gx = np.gradient(band, abs(yres), abs(xres))
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    valid = slope[np.isfinite(slope) & np.isfinite(band)]
    if valid.size == 0:
        return {}
    return {
        "slope_mean": float(np.mean(valid)),
        "slope_median": float(np.median(valid)),
        "slope_p90": float(np.percentile(valid, 90)),
        "slope_n_pixels": int(valid.size),
    }


def _apply_shared_layer_stats(layer_id: str, sample: LayerSample, stats: dict[str, Any]) -> None:
    if layer_id == "ghsl_built_up" and sample.stats.get("mean") is not None:
        stats["imperv_pct_mean"] = min(1.0, max(0.0, float(sample.stats["mean"]) / 10_000))
    elif layer_id == "merit_hand":
        stats["merit_hand_mean"] = sample.stats.get("mean")
    elif layer_id == "merit_upa":
        stats["upstream_area_km2_mean"] = sample.stats.get("mean")
    elif layer_id == "merit_elv":
        stats["merit_elv_mean"] = sample.stats.get("mean")
    elif layer_id == "dynamic_world":
        tree = float(sample.stats.get("dw_trees_pct") or 0.0)
        grass = float(sample.stats.get("dw_grass_pct") or 0.0)
        flooded_vegetation = float(sample.stats.get("dw_flooded_vegetation_pct") or 0.0)
        shrub = float(sample.stats.get("dw_shrub_pct") or 0.0)
        bare = float(sample.stats.get("dw_bare_pct") or 0.0)
        stats["dw_built_pct_mean"] = sample.stats.get("dw_built_pct")
        stats["dw_water_pct_mean"] = sample.stats.get("dw_water_pct")
        stats["dw_flooded_vegetation_pct_mean"] = sample.stats.get("dw_flooded_vegetation_pct")
        stats["green_pct_mean"] = tree + grass + flooded_vegetation + shrub
        stats["open_land_pct_mean"] = grass + shrub + bare
        stats["tree_pct_mean"] = tree
    elif layer_id == "modis_ndvi":
        stats["ndvi_mean"] = sample.stats.get("mean")
    elif layer_id == "hansen_treecover2000":
        stats["treecover2000_mean"] = sample.stats.get("mean")
    elif layer_id == "copernicus_dem":
        stats["elevation_mean"] = sample.stats.get("mean")
        if sample.stats.get("slope_mean") is not None:
            stats["slope_mean"] = sample.stats.get("slope_mean")
            stats["slope_p90"] = sample.stats.get("slope_p90")
    elif layer_id == "poa_slope":
        if sample.stats.get("slope_mean") is not None:
            stats["slope_mean"] = sample.stats.get("slope_mean")
            stats["slope_p90"] = sample.stats.get("slope_p90")
        elif sample.stats.get("mean") is not None:
            stats["slope_mean"] = sample.stats.get("mean")
    elif layer_id == "soilgrids_clay":
        stats["clay_pct_mean"] = sample.stats.get("mean")
    elif layer_id == "landsat8_lst_djf":
        stats["landsat_lst_norm_mean"] = sample.stats.get("mean")
    elif layer_id == "modis_lst_day_p90":
        stats["modis_lst_day_norm_mean"] = sample.stats.get("mean")
    elif layer_id == "modis_lst_night_p90":
        stats["modis_lst_night_norm_mean"] = sample.stats.get("mean")


def _apply_flood_layer_stats(layer_id: str, sample: LayerSample, stats: dict[str, Any]) -> None:
    if layer_id == "jrc_surface_water_transition":
        stats["surface_water_transition_wet_pct_mean"] = sample.stats.get(
            "surface_water_transition_wet_pct"
        )
    elif layer_id == "jrc_surface_water_occurrence":
        stats["surface_water_occurrence_mean"] = sample.stats.get("mean")
    elif layer_id == "jrc_surface_water_seasonality":
        stats["surface_water_seasonality_mean"] = sample.stats.get("mean")
    elif layer_id == "copernicus_emsn194":
        stats["observed_flood_depth_mean"] = sample.stats.get("mean")
        stats["observed_flood_depth_p90"] = sample.stats.get("p90")
    elif layer_id == "chirps_rx1day_2024":
        stats["rx1day_2024_mean"] = sample.stats.get("mean")
    elif layer_id == "chirps_rx5day_2024":
        stats["rx5day_2024_mean"] = sample.stats.get("mean")
    elif layer_id == "chirps_r90p_2024":
        stats["r90p_2024_mean"] = sample.stats.get("mean")
    elif layer_id == "gfplain250m":
        stats["floodplain_adj_pct_mean"] = sample.stats.get("mean")
    elif layer_id == "poa_depression_mask":
        stats["depression_pct_mean"] = sample.stats.get("mean")
    elif layer_id == "poa_relative_elevation":
        stats["relative_elevation_mean"] = sample.stats.get("mean")
    elif layer_id == "poa_depression_depth":
        stats["depression_depth_mean"] = sample.stats.get("mean")


def _apply_heat_layer_stats(layer_id: str, sample: LayerSample, stats: dict[str, Any]) -> None:
    if layer_id == "heat_hazard" and "n_cells" not in stats:
        stats["n_cells"] = sample.stats.get("n_pixels")


def _apply_landslide_layer_stats(layer_id: str, sample: LayerSample, stats: dict[str, Any]) -> None:
    if layer_id == "landslide_hazard" and "n_cells" not in stats:
        stats["n_cells"] = sample.stats.get("n_pixels")
    elif layer_id == "chirps_r90p_climatology":
        stats["r90p_climatology_mean"] = sample.stats.get("mean")
    elif layer_id == "ndvi_p10_djf":
        stats["ndvi_p10_mean"] = sample.stats.get("mean")
    elif layer_id == "dynamic_world_mode_250m":
        stats["dw_built_pct_mean"] = sample.stats.get("dw_built_pct")
        stats["dw_bare_pct_mean"] = sample.stats.get("dw_bare_pct")
        tree = float(sample.stats.get("dw_trees_pct") or 0.0)
        grass = float(sample.stats.get("dw_grass_pct") or 0.0)
        shrub = float(sample.stats.get("dw_shrub_pct") or 0.0)
        stats["green_pct_mean"] = tree + grass + shrub
        stats["tree_pct_mean"] = tree


@dataclass
class LayerSample:
    layer_id: str
    source: str
    status: str  # ok | error | fallback
    stats: dict[str, float | int | None] = field(default_factory=dict)
    note: str = ""


def zonal_stats_cog(layer_id: str, url: str, site_geom) -> LayerSample:
    """Mask a catalog COG to site geometry; return mean/median/p90."""
    try:
        with rasterio.open(url) as src:
            geom = mapping(site_geom)
            if src.crs and src.crs.to_epsg() != 4326:
                geom = transform_geom("EPSG:4326", src.crs, geom)
            geojson = [geom]
            all_touched = _mask_all_touched(layer_id)
            data, _ = mask(src, geojson, crop=True, filled=False, all_touched=all_touched)
            band = _valid_band(data, src.nodata)
            valid = band[np.isfinite(band)]
            if valid.size == 0:
                hint = (
                    " Coarse grid — try all_touched=True."
                    if not all_touched and _mask_all_touched(layer_id)
                    else ""
                )
                return LayerSample(
                    layer_id,
                    url,
                    "error",
                    note=f"No valid pixels in site mask.{hint}",
                )
            stats: dict[str, float | int | None] = {
                "mean": float(np.mean(valid)),
                "median": float(np.median(valid)),
                "p90": float(np.percentile(valid, 90)),
                "n_pixels": int(valid.size),
            }
            if layer_id == "dynamic_world":
                stats.update(
                    {
                        f"dw_{label}_pct": _class_fraction(valid, class_id)
                        for label, class_id in DYNAMIC_WORLD_CLASSES.items()
                    }
                )
            elif layer_id == "jrc_surface_water_transition":
                stats["surface_water_transition_wet_pct"] = float(
                    np.mean(np.isin(valid.astype(int), list(JRC_WATER_TRANSITION_WET_CLASSES)))
                )
            elif layer_id == "copernicus_dem":
                stats.update(_slope_stats_degrees(band, src.res[0], src.res[1]))
            elif layer_id == "poa_slope":
                stats.update(_slope_stats_degrees(band, src.res[0], src.res[1]))
                if stats.get("slope_mean") is None and valid.size:
                    stats["slope_mean"] = stats.get("mean")
            elif layer_id == "dynamic_world_mode_250m":
                stats.update(
                    {
                        f"dw_{label}_pct": _class_fraction(valid, class_id)
                        for label, class_id in DYNAMIC_WORLD_CLASSES.items()
                    }
                )
            return LayerSample(
                layer_id,
                url,
                "ok",
                stats=stats,
                note=(
                    f"Catalog COG; CRS {src.crs}; resolution {abs(src.res[0]):.4g} map units."
                    + (" all_touched mask for coarse grid." if all_touched else "")
                ),
            )
    except Exception as exc:  # noqa: BLE001 — surface catalog access failures to caller
        return LayerSample(layer_id, url, "error", note=str(exc))


def flood_grid_shared_context(site_geom, site: str | None = None) -> dict[str, float]:
    """Lightweight AOI context for grid screening (CHIRPS only — not full catalog)."""
    catalog = get_catalog_cogs("flood", site)
    shared: dict[str, float] = {}
    for layer_id, stat_key in (
        ("chirps_rx1day_2024", "rx1day_2024_mean"),
        ("chirps_rx5day_2024", "rx5day_2024_mean"),
    ):
        if layer_id not in catalog:
            continue
        sample = zonal_stats_cog(layer_id, catalog[layer_id], site_geom)
        if sample.status == "ok" and sample.stats.get("mean") is not None:
            shared[stat_key] = float(sample.stats["mean"])
    return shared


def zonal_stats_raster(layer_id: str, path: Path, site_geom) -> LayerSample:
    """Mask a local raster to site geometry; return mean/median/p90."""
    if not path.exists():
        return LayerSample(layer_id, str(path), "error", note="Local raster not found")
    try:
        with rasterio.open(path) as src:
            geom = mapping(site_geom)
            if src.crs and src.crs.to_epsg() != 4326:
                geom = transform_geom("EPSG:4326", src.crs, geom)
            geojson = [geom]
            all_touched = _mask_all_touched(layer_id)
            data, _ = mask(src, geojson, crop=True, filled=False, all_touched=all_touched)
            band = _valid_band(data, src.nodata)
            valid = band[np.isfinite(band)]
            if valid.size == 0:
                return LayerSample(
                    layer_id,
                    str(path),
                    "error",
                    note=(
                        "No valid pixels in site mask."
                        + (" Coarse grid — try all_touched=True." if not all_touched else "")
                    ),
                )
            stats: dict[str, float | int | None] = {
                "mean": float(np.mean(valid)),
                "median": float(np.median(valid)),
                "p90": float(np.percentile(valid, 90)),
                "n_pixels": int(valid.size),
            }
            if layer_id == "poa_slope":
                stats.update(_slope_stats_degrees(band, src.res[0], src.res[1]))
            elif layer_id == "dynamic_world_mode_250m":
                stats.update(
                    {
                        f"dw_{label}_pct": _class_fraction(valid, class_id)
                        for label, class_id in DYNAMIC_WORLD_CLASSES.items()
                    }
                )
            return LayerSample(
                layer_id,
                str(path),
                "ok",
                stats=stats,
                note=(
                    f"Local raster; resolution {abs(src.res[0]) * 111_000:.0f} m approx."
                    + (" all_touched mask for coarse grid." if all_touched else "")
                ),
            )
    except Exception as exc:  # noqa: BLE001 — keep notebook diagnostics readable
        return LayerSample(layer_id, str(path), "error", note=str(exc))


def load_site_geojson(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def _read_vector(url: str) -> gpd.GeoDataFrame:
    if url not in _GDF_CACHE:
        gdf = gpd.read_file(url)
        if gdf.crs is None:
            gdf = gdf.set_crs(4326)
        _GDF_CACHE[url] = gdf.to_crs(4326)
    return _GDF_CACHE[url]


def _barrio_row(gdf: gpd.GeoDataFrame, bairro_name: str) -> gpd.GeoSeries:
    row = gdf[gdf["NM_BAIRRO"] == bairro_name]
    if row.empty:
        raise ValueError(f"Bairro not found: {bairro_name}")
    return row.iloc[0]


def _barrio_risk_context(bairro_name: str, hazard: HazardKind) -> dict[str, Any]:
    r = _barrio_row(_read_vector(BARIO_VECTOR_URLS[hazard]), bairro_name)
    return {
        "bairro": bairro_name,
        "hazard_mean": float(r[f"{hazard}_hazard_mean"]),
        "risk_mean": float(r[f"{hazard}_risk_score"]),
        "exposure_score": float(r[f"{hazard}_exposure_score"]),
        "vulnerability_score": float(r[f"{hazard}_vulnerability_score"]),
        "geometry": r.geometry,
    }


def barrio_flood_context(bairro_name: str) -> dict[str, Any]:
    """Step 0 — flood risk attributes for a bairro polygon (catalog vector)."""
    return _barrio_risk_context(bairro_name, "flood")


def barrio_heat_context(bairro_name: str) -> dict[str, Any]:
    """Step 0 — heat risk attributes for a bairro polygon (catalog vector)."""
    return _barrio_risk_context(bairro_name, "heat")


def barrio_landslide_context(bairro_name: str) -> dict[str, Any]:
    """Step 0 — landslide risk attributes for a bairro polygon (catalog vector)."""
    return _barrio_risk_context(bairro_name, "landslide")


def barrio_context(bairro_name: str, hazard: HazardKind = "flood") -> dict[str, Any]:
    if hazard == "heat":
        return barrio_heat_context(bairro_name)
    if hazard == "landslide":
        return barrio_landslide_context(bairro_name)
    return barrio_flood_context(bairro_name)


def sample_grid_metrics(site_geom) -> LayerSample:
    """Fallback diagnostic proxies from POC 1 km sample grid (not catalog)."""
    grid_path = SAMPLE_DATA / "porto-alegre-grid.json"
    grid = json.loads(grid_path.read_text())
    feats = grid["geoJson"]["features"]
    inside = [f for f in feats if shape(f["geometry"]).intersects(site_geom)]
    if not inside:
        return LayerSample("sample_grid_1km", str(grid_path), "error", note="No grid cells intersect site")

    numeric_keys = [
        "imperv_pct",
        "building_density",
        "dist_river_m",
        "dist_water_m",
        "floodplain_adj_pct",
        "depression_pct",
        "flow_accum_pct",
        "flood_score",
        "green_pct",
        "canopy_pct",
        "slope_mean",
    ]
    stats: dict[str, float | None] = {"n_cells": len(inside)}
    for key in numeric_keys:
        vals = [
            f["properties"]["metrics"].get(key)
            for f in inside
            if f["properties"]["metrics"].get(key) is not None
        ]
        if vals:
            stats[f"{key}_mean"] = float(np.mean(vals))

    return LayerSample(
        "sample_grid_1km",
        str(grid_path),
        "fallback",
        stats=stats,
        note="POC 1 km grid — use catalog COGs in production",
    )


def grid_metrics(site_geom, hazard: HazardKind = "flood", site: str | None = None) -> LayerSample:
    """Diagnostic proxies aggregated from catalog COGs for the hazard profile."""
    catalog = get_catalog_cogs(hazard, site)
    grid_keys = HAZARD_GRID_KEYS[hazard]

    stats: dict[str, float | int | None] = {}
    notes: list[str] = []
    status = "ok"

    for layer_id, url in catalog.items():
        sample = zonal_stats_cog(layer_id, url, site_geom)
        if sample.status != "ok":
            notes.append(f"{layer_id}: {sample.note}")
            continue

        if layer_id in grid_keys:
            stats[grid_keys[layer_id]] = sample.stats.get("mean")
        _apply_shared_layer_stats(layer_id, sample, stats)
        if hazard == "flood":
            _apply_flood_layer_stats(layer_id, sample, stats)
        elif hazard == "heat":
            _apply_heat_layer_stats(layer_id, sample, stats)
        else:
            _apply_landslide_layer_stats(layer_id, sample, stats)

        if hazard == "flood" and layer_id == "flood_hazard":
            stats["n_cells"] = sample.stats.get("n_pixels")
        if hazard == "landslide" and layer_id == "landslide_hazard":
            stats["n_cells"] = sample.stats.get("n_pixels")

    if hazard == "flood":
        missing_main = {
            "flood_score_mean",
            "exposure_score_mean",
            "vulnerability_score_mean",
            "risk_score_mean",
        } - stats.keys()
    elif hazard == "heat":
        missing_main = {
            "heat_score_mean",
            "exposure_score_mean",
            "vulnerability_score_mean",
            "heat_risk_score_mean",
        } - stats.keys()
    else:
        missing_main = {
            "landslide_score_mean",
            "exposure_score_mean",
            "vulnerability_score_mean",
            "landslide_risk_score_mean",
        } - stats.keys()

    if missing_main:
        status = "partial"
        notes.append(
            f"Catalog incomplete for {hazard}; missing screening metrics: {sorted(missing_main)}."
        )

    if not stats:
        return sample_grid_metrics(site_geom)

    app_layer_id = {
        "flood": "app_hev_250m",
        "heat": "app_heat_250m",
        "landslide": "app_landslide_90m",
    }[hazard]
    notes.append(f"Screening metrics sampled from catalog COGs ({hazard}).")
    return LayerSample(
        app_layer_id,
        f"catalog COGs ({hazard})",
        status,
        stats=stats,
        note=" ".join(notes),
    )


def hev_grid_metrics(site_geom, hazard: HazardKind = "flood") -> LayerSample:
    """Backward-compatible alias for flood; accepts hazard='heat' for heat screening."""
    return grid_metrics(site_geom, hazard=hazard)


def nearest_waterway(site_geom) -> LayerSample:
    """Distance to nearest OSM waterway (sample GeoJSON)."""
    from shapely.geometry import Point

    if isinstance(site_geom, Point):
        pt = site_geom
    else:
        pt = site_geom.centroid
    return _water_stats_at_lonlat(pt.x, pt.y)


def water_stats_at_point(lon: float, lat: float) -> dict[str, float | int | str]:
    """Per-point water proximity (for grid-cell screening)."""
    sample = _water_stats_at_lonlat(lon, lat)
    return {**sample.stats, "_note": sample.note}


def _water_stats_at_lonlat(lon: float, lat: float) -> LayerSample:
    rivers_path = Path(__import__("os").environ["NBS_RIVERS_GEOJSON"]).expanduser() if __import__("os").environ.get("NBS_RIVERS_GEOJSON") else (SAMPLE_DATA / "porto-alegre-rivers.json")
    features = _river_features()
    pt = shape({"type": "Point", "coordinates": [lon, lat]})
    idx = int(_river_strtree().nearest(pt))
    line, props = features[idx]
    min_dist_deg = pt.distance(line)
    nearest = props.get("name") or props.get("waterway")
    dist_m = min_dist_deg * 111_000
    return LayerSample(
        "osm_waterways",
        str(rivers_path),
        "fallback",
        stats={"dist_nearest_m": float(dist_m), "intersects_waterway": int(dist_m < 1)},
        note=f"Nearest named feature (sample): {nearest}",
    )


def _finite_raster_value(val: float, nodata: float | int | None) -> float | None:
    if nodata is not None and np.isfinite(nodata) and val == nodata:
        return None
    if val <= -9999:
        return None
    if not np.isfinite(val):
        return None
    return val


def sample_raster_at_point(path_or_url: str | Path, lon: float, lat: float) -> float | None:
    """Read one raster value at a lon/lat point (local path or COG URL)."""
    try:
        with rasterio.open(str(path_or_url)) as src:
            xs, ys = rasterio.transform.rowcol(src.transform, lon, lat)
            if not (0 <= ys < src.height and 0 <= xs < src.width):
                return None
            val = float(src.read(1, window=((ys, ys + 1), (xs, xs + 1)))[0, 0])
            return _finite_raster_value(val, src.nodata)
    except Exception:  # noqa: BLE001
        return None


def sample_raster_zonal_mean(path_or_url: str | Path, geom) -> float | None:
    """Mean raster value over a geometry (cell polygon fallback when centroid is nodata)."""
    from rasterio.mask import mask

    try:
        with rasterio.open(str(path_or_url)) as src:
            g = mapping(geom)
            if src.crs and src.crs.to_epsg() != 4326:
                g = transform_geom("EPSG:4326", src.crs, g)
            data, _ = mask(src, [g], crop=True, filled=False)
            band = _valid_band(data, src.nodata)
            valid = band[np.isfinite(band)]
            if valid.size == 0:
                return None
            return float(np.mean(valid))
    except Exception:  # noqa: BLE001
        return None


def query_layers(site_geom, hazard: HazardKind = "flood", site: str | None = None) -> list[LayerSample]:
    """Query catalog COGs, aggregated grid metrics, and waterways."""
    results: list[LayerSample] = []
    for layer_id, url in get_catalog_cogs(hazard, site).items():
        results.append(zonal_stats_cog(layer_id, url, site_geom))
    results.append(grid_metrics(site_geom, hazard=hazard, site=site))
    # Riparian buffer (flood) and riparian cooling corridor (heat) need water proximity.
    results.append(nearest_waterway(site_geom))
    return results


def query_all_layers(site_geom) -> list[LayerSample]:
    """Flood screening (backward compatible with original E2E)."""
    return query_layers(site_geom, hazard="flood")
