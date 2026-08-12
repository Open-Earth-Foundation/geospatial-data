"""Clip regional GeoTIFFs into per-city ``data/input/`` files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def _load_boundary_geom(boundary_path: Path) -> Any | None:
    try:
        from shapely.geometry import shape
    except ImportError:
        return None
    if not boundary_path.is_file():
        return None
    data = json.loads(boundary_path.read_text(encoding="utf-8"))
    if data.get("type") == "FeatureCollection":
        geoms = [shape(f["geometry"]) for f in data.get("features", []) if f.get("geometry")]
        if not geoms:
            return None
        from shapely.ops import unary_union

        return unary_union(geoms)
    if data.get("type") == "Feature":
        return shape(data["geometry"])
    if data.get("type") in {"Polygon", "MultiPolygon"}:
        return shape(data)
    return None


def clip_raster_to_site(
    regional_tif: Path,
    out_path: Path,
    *,
    bbox: list[float] | tuple[float, float, float, float],
    boundary_path: Path | None = None,
    all_touched: bool = True,
) -> Path:
    """Window-crop ``regional_tif`` to city bbox and optionally mask to boundary.

    ``bbox`` is ``[west, south, east, north]`` in the raster CRS (EPSG:4326 for CCRA extracts).
    """
    import rasterio
    from rasterio.mask import mask as rio_mask
    from rasterio.windows import from_bounds

    regional_tif = Path(regional_tif)
    out_path = Path(out_path)
    if not regional_tif.is_file():
        raise FileNotFoundError(regional_tif)

    west, south, east, north = (float(x) for x in bbox)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(regional_tif) as src:
        window = from_bounds(west, south, east, north, transform=src.transform)
        window = window.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
        if window.width <= 0 or window.height <= 0:
            raise ValueError(
                f"City bbox {[west, south, east, north]} does not intersect {regional_tif}"
            )

        geom = _load_boundary_geom(boundary_path) if boundary_path else None
        if geom is not None:
            # Mask on full regional grid then crop — preserves city polygon nodata.
            try:
                data, transform = rio_mask(
                    src,
                    [geom.__geo_interface__],
                    crop=True,
                    all_touched=all_touched,
                    filled=True,
                    nodata=src.nodata if src.nodata is not None else 0,
                )
            except ValueError:
                # Fallback to bbox window if polygon is outside (should be rare).
                data = src.read(window=window, boundless=False)
                transform = src.window_transform(window)
        else:
            data = src.read(window=window, boundless=False)
            transform = src.window_transform(window)

        profile = src.profile.copy()
        profile.update(
            {
                "height": data.shape[1],
                "width": data.shape[2],
                "transform": transform,
                "compress": "deflate",
            }
        )
        # Ensure finite arrays (some EE exports use NaN).
        if np.issubdtype(data.dtype, np.floating):
            data = np.where(np.isfinite(data), data, profile.get("nodata") or 0).astype(data.dtype)

    if out_path.exists():
        out_path.unlink()
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data)
    return out_path


def materialize_city_flood_inputs(
    regional_layers_dir: Path,
    site_config: dict[str, Any],
    *,
    layer_map: dict[str, str] | None = None,
) -> dict[str, Path]:
    """Clip available regional flood layers into the city's ``data/input`` filenames.

    ``layer_map`` maps regional stem → site ``layers`` key, e.g.
    ``{"gfplain_250m": "gfplain", "jrc_rp100_depth": "jrc_depth", ...}``.
    """
    default_map = {
        "gfplain_250m": "gfplain",
        "jrc_rp100_depth": "jrc_depth",
        "jrc_rp100_depth_norm": "jrc_norm",
        "aqueduct_depth_rp100": "aqueduct_depth",
        "aqueduct_depth_rp100_norm": "aqueduct_norm",
    }
    layer_map = layer_map or default_map
    layers = site_config.get("layers") or {}
    input_dir = Path(site_config["paths_abs"]["data_input"])
    bbox = site_config["bbox"]
    boundary = Path(site_config["boundary_path_abs"])
    written: dict[str, Path] = {}

    for regional_stem, layer_key in layer_map.items():
        src = regional_layers_dir / f"{regional_stem}.tif"
        if not src.is_file():
            continue
        filename = layers.get(layer_key)
        if not filename:
            continue
        out = input_dir / str(filename)
        clip_raster_to_site(src, out, bbox=bbox, boundary_path=boundary)
        written[layer_key] = out
        print(f"[regional-clip] {regional_stem}.tif → {out.name}")
    return written
