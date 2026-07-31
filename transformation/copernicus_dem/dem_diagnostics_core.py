"""Relative elevation and depression diagnostics from Copernicus DEM (30 m).

Logic ported from ``release/v1/relative_elevation_depression_from_dem.ipynb``.
Screening-only — not engineering-grade hydrology.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

D8_DR = np.array([-1, -1, 0, 1, 1, 1, 0, -1], dtype=np.int32)
D8_DC = np.array([0, 1, 1, 1, 0, -1, -1, -1], dtype=np.int32)
SQ2 = np.sqrt(2.0)
D8_DIST = np.array([1, SQ2, 1, SQ2, 1, SQ2, 1, SQ2], dtype=np.float64)


@dataclass
class DemDiagnosticsOutputs:
    relative_elevation: Path
    depression_mask: Path
    depression_depth: Path
    valid_cells: int
    sink_cells: int


def valid_dem_mask(dem: np.ndarray, nodata: float | int | None) -> np.ndarray:
    mask = np.isfinite(dem)
    if nodata is not None and not (isinstance(nodata, float) and np.isnan(nodata)):
        mask &= dem != nodata
    mask &= dem > -500
    return mask


def relative_elevation_index(dem: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """0–1 index: 1 = lowest elevation among valid cells."""
    out = np.full(dem.shape, np.nan, dtype=np.float32)
    vals = dem[valid].astype(np.float64)
    if vals.size == 0:
        return out
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(vals.size, dtype=np.float64)
    ranks[order] = np.arange(vals.size)
    denom = max(vals.size - 1, 1)
    out[valid] = (1.0 - ranks / denom).astype(np.float32)
    return out


def d8_flow_direction(dem: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Return int8 array: 0–7 = D8 direction, -1 = flat/pit/no outlet."""
    h, w = dem.shape
    flow = np.full((h, w), -1, dtype=np.int8)
    for r in range(h):
        for c in range(w):
            if not valid[r, c]:
                continue
            z = dem[r, c]
            best_drop = 0.0
            best_dir = -1
            for d in range(8):
                nr, nc = r + D8_DR[d], c + D8_DC[d]
                if nr < 0 or nr >= h or nc < 0 or nc >= w or not valid[nr, nc]:
                    continue
                drop = (z - dem[nr, nc]) / D8_DIST[d]
                if drop > best_drop:
                    best_drop = drop
                    best_dir = d
            flow[r, c] = best_dir
    return flow


def depression_sink_mask(dem: np.ndarray, valid: np.ndarray, flow: np.ndarray) -> np.ndarray:
    """Binary mask: D8 pit with no lower neighbour."""
    h, w = dem.shape
    sinks = np.zeros((h, w), dtype=np.uint8)
    for r in range(h):
        for c in range(w):
            if not valid[r, c] or flow[r, c] != -1:
                continue
            z = dem[r, c]
            is_lowest = True
            for d in range(8):
                nr, nc = r + D8_DR[d], c + D8_DC[d]
                if nr < 0 or nr >= h or nc < 0 or nc >= w or not valid[nr, nc]:
                    continue
                if dem[nr, nc] < z:
                    is_lowest = False
                    break
            if is_lowest:
                sinks[r, c] = 1
    return sinks


def priority_flood_fill(dem: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Priority-flood depression fill; invalid cells treated as barriers."""
    h, w = dem.shape
    filled = np.where(valid, dem.astype(np.float64), np.inf)
    visited = np.zeros((h, w), dtype=bool)
    heap: list[tuple[float, int, int]] = []

    for r in range(h):
        for c in range(w):
            if not valid[r, c]:
                continue
            on_edge = r == 0 or c == 0 or r == h - 1 or c == w - 1
            if on_edge:
                heapq.heappush(heap, (filled[r, c], r, c))
                visited[r, c] = True

    while heap:
        z, r, c = heapq.heappop(heap)
        if z > filled[r, c]:
            filled[r, c] = z
        for d in range(8):
            nr, nc = r + D8_DR[d], c + D8_DC[d]
            if nr < 0 or nr >= h or nc < 0 or nc >= w or not valid[nr, nc]:
                continue
            if visited[nr, nc]:
                continue
            visited[nr, nc] = True
            elev = max(filled[nr, nc], z)
            filled[nr, nc] = elev
            heapq.heappush(heap, (elev, nr, nc))

    return filled


def write_geotiff(path: Path, arr: np.ndarray, profile: dict[str, Any], *, nodata: Any = None) -> Path:
    out = profile.copy()
    dtype = rasterio.float32 if arr.dtype != np.uint8 else rasterio.uint8
    out.update(dtype=dtype, count=1, nodata=nodata, compress="deflate")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **out) as dst:
        dst.write(arr.astype(out["dtype"]), 1)
    return path


def compute_dem_diagnostics_from_path(
    dem_path: Path,
    *,
    out_relative_elevation: Path,
    out_depression_mask: Path,
    out_depression_depth: Path,
) -> DemDiagnosticsOutputs:
    """Compute relative elevation + depression layers from a local DEM GeoTIFF."""
    dem_path = Path(dem_path)
    if not dem_path.is_file():
        raise FileNotFoundError(f"Missing DEM: {dem_path}")

    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(np.float32)
        profile = src.profile
        nodata = src.nodata

    valid = valid_dem_mask(dem, nodata)
    valid_n = int(valid.sum())
    if valid_n == 0:
        raise ValueError(f"No valid DEM cells in {dem_path}")

    rel_elev = relative_elevation_index(dem, valid)
    flow = d8_flow_direction(dem, valid)
    dep_mask = depression_sink_mask(dem, valid, flow)
    filled = priority_flood_fill(dem, valid)
    dep_depth = np.where(
        valid,
        np.maximum(filled - dem.astype(np.float64), 0.0),
        np.nan,
    ).astype(np.float32)

    write_geotiff(out_relative_elevation, rel_elev, profile, nodata=np.nan)
    write_geotiff(out_depression_mask, dep_mask, profile, nodata=255)
    write_geotiff(out_depression_depth, dep_depth, profile, nodata=np.nan)

    return DemDiagnosticsOutputs(
        relative_elevation=out_relative_elevation,
        depression_mask=out_depression_mask,
        depression_depth=out_depression_depth,
        valid_cells=valid_n,
        sink_cells=int(dep_mask.sum()),
    )
