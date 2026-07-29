#!/usr/bin/env python3
"""Compute landslide risk R = (H × E × V)^(1/3) for a city.

Rasterizes ACS block-group exposure/vulnerability onto the landslide hazard grid,
writes risk GeoTIFF + block-group zonal GeoPackage + SVG map.

Example:
  python transformation/landslide_risk/compute_landslide_risk.py --site plymouth
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio import features

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

LANDSLIDE_RISK_ROOT = Path(__file__).resolve().parent


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    out: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        key, val = line.split(":", 1)
        out[key.strip()] = val.strip().strip("'\"")
    return out


def _resolve(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _minmax_or_passthrough(arr: np.ndarray) -> np.ndarray:
    """Hazard may already be 0–1; keep values, only ensure float32."""
    return arr.astype("float32")


def rasterize_field(
    gdf: gpd.GeoDataFrame,
    field: str,
    *,
    out_shape: tuple[int, int],
    transform,
    nodata: float = np.nan,
) -> np.ndarray:
    gdf = gdf.copy()
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]
    gdf = gdf[np.isfinite(pd.to_numeric(gdf[field], errors="coerce"))]
    shapes = (
        (geom, float(val))
        for geom, val in zip(gdf.geometry, gdf[field], strict=False)
        if geom is not None
    )
    burned = features.rasterize(
        shapes=shapes,
        out_shape=out_shape,
        transform=transform,
        fill=nodata,
        dtype="float32",
        all_touched=False,
    )
    return burned


def zonal_means(
    gdf: gpd.GeoDataFrame,
    rasters: dict[str, np.ndarray],
    transform,
) -> gpd.GeoDataFrame:
    """Mean of each raster under each polygon (centroid sampling is too coarse;
    use mask per feature)."""
    out = gdf.copy()
    height, width = next(iter(rasters.values())).shape
    for name, arr in rasters.items():
        means = []
        for geom in out.geometry:
            if geom is None or geom.is_empty:
                means.append(np.nan)
                continue
            mask = features.geometry_mask(
                [geom],
                out_shape=(height, width),
                transform=transform,
                invert=True,
                all_touched=False,
            )
            vals = arr[mask]
            vals = vals[np.isfinite(vals)]
            means.append(float(np.mean(vals)) if vals.size else np.nan)
        out[name] = means
    return out


def _color_ramp(t: float) -> str:
    t = max(0.0, min(1.0, float(t)))
    stops = [
        (0.0, (255, 255, 204)),
        (0.35, (254, 217, 118)),
        (0.65, (253, 141, 60)),
        (1.0, (153, 0, 13)),
    ]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            rgb = tuple(int(c0[i] + u * (c1[i] - c0[i])) for i in range(3))
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    return "#99000d"


def write_choropleth_svg(
    gdf: gpd.GeoDataFrame,
    column: str,
    out_path: Path,
    *,
    title: str,
    subtitle: str = "",
    width: int = 900,
    height: int = 780,
) -> None:
    plot_gdf = gdf.to_crs(4326).copy()
    vals = pd.to_numeric(plot_gdf[column], errors="coerce")
    minx, miny, maxx, maxy = plot_gdf.total_bounds
    pad_x = (maxx - minx) * 0.05 or 0.01
    pad_y = (maxy - miny) * 0.05 or 0.01
    minx, maxx = minx - pad_x, maxx + pad_x
    miny, maxy = miny - pad_y, maxy + pad_y
    legend_w = 120
    map_w = width - legend_w - 40
    map_h = height - 90

    def project(x: float, y: float) -> tuple[float, float]:
        px = 20 + (x - minx) / (maxx - minx) * map_w
        py = 70 + (maxy - y) / (maxy - miny) * map_h
        return px, py

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#fafafa"/>',
        f'<text x="20" y="32" font-family="Helvetica, Arial, sans-serif" font-size="18" font-weight="bold">{title}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="20" y="52" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#444">{subtitle}</text>'
        )

    for idx, row in plot_gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        v = vals.loc[idx]
        fill = "#dddddd" if pd.isna(v) else _color_ramp(float(v))
        geoms = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for poly in geoms:
            if poly.geom_type != "Polygon":
                continue
            d_bits = []
            for ring in [poly.exterior, *poly.interiors]:
                coords = list(ring.coords)
                x0, y0 = project(coords[0][0], coords[0][1])
                d_bits.append(f"M{x0:.2f},{y0:.2f}")
                for x, y in coords[1:]:
                    px, py = project(x, y)
                    d_bits.append(f"L{px:.2f},{py:.2f}")
                d_bits.append("Z")
            parts.append(
                f'<path d="{" ".join(d_bits)}" fill="{fill}" stroke="#666" '
                f'stroke-width="0.4" fill-opacity="0.92"/>'
            )

    lx = width - legend_w
    parts.append(
        f'<text x="{lx}" y="90" font-family="Helvetica, Arial, sans-serif" font-size="11">Risk 0–1</text>'
    )
    for i in range(11):
        t = i / 10
        y = 100 + i * 22
        parts.append(
            f'<rect x="{lx}" y="{y}" width="18" height="18" fill="{_color_ramp(1 - t)}" stroke="#666"/>'
        )
        parts.append(
            f'<text x="{lx + 26}" y="{y + 13}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="11">{1 - t:.1f}</text>'
        )
    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote map: {out_path}")


def write_raster_grid_svg(
    arr: np.ndarray,
    out_path: Path,
    *,
    title: str,
    subtitle: str = "",
    width: int = 900,
    height: int = 780,
    vmin: float | None = None,
    vmax: float | None = None,
) -> None:
    """Choropleth-style SVG of a 2D float raster (one rect per cell) for QA."""
    a = np.asarray(arr, dtype="float64")
    finite = a[np.isfinite(a)]
    if finite.size == 0:
        raise ValueError(f"No finite values to plot for {out_path.name}")
    lo = float(np.nanmin(finite) if vmin is None else vmin)
    hi = float(np.nanmax(finite) if vmax is None else vmax)
    if hi <= lo:
        hi = lo + 1e-9

    nrows, ncols = a.shape
    legend_w = 120
    margin_l, margin_t, margin_b = 20, 70, 20
    map_w = width - legend_w - 40
    map_h = height - margin_t - margin_b
    cell_w = map_w / ncols
    cell_h = map_h / nrows

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#fafafa"/>',
        f'<text x="20" y="32" font-family="Helvetica, Arial, sans-serif" font-size="18" font-weight="bold">{title}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="20" y="52" font-family="Helvetica, Arial, sans-serif" font-size="12" fill="#444">{subtitle}</text>'
        )

    for i in range(nrows):
        for j in range(ncols):
            v = a[i, j]
            if not np.isfinite(v):
                fill = "#9e9e9e"
            else:
                t = (float(v) - lo) / (hi - lo)
                fill = _color_ramp(t)
            x = margin_l + j * cell_w
            y = margin_t + i * cell_h
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w:.2f}" height="{cell_h:.2f}" '
                f'fill="{fill}" stroke="none"/>'
            )

    # border
    parts.append(
        f'<rect x="{margin_l}" y="{margin_t}" width="{map_w}" height="{map_h}" '
        f'fill="none" stroke="#666" stroke-width="1"/>'
    )

    lx = width - legend_w
    parts.append(
        f'<text x="{lx}" y="90" font-family="Helvetica, Arial, sans-serif" font-size="11">'
        f"{lo:.2f}–{hi:.2f}</text>"
    )
    for i in range(11):
        t = i / 10
        y = 100 + i * 22
        val = hi - t * (hi - lo)
        parts.append(
            f'<rect x="{lx}" y="{y}" width="18" height="18" fill="{_color_ramp(1 - t)}" stroke="#666"/>'
        )
        parts.append(
            f'<text x="{lx + 26}" y="{y + 13}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="11">{val:.2f}</text>'
        )
    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote map: {out_path}")


def write_geotiff(path: Path, arr: np.ndarray, profile: dict[str, Any], description: str) -> None:
    prof = profile.copy()
    prof.update(dtype="float32", count=1, nodata=np.nan, compress="lzw")
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr.astype("float32"), 1)
        dst.set_band_description(1, description)
    print(f"Wrote {path}")


def run(site: str, root: Path | None = None) -> Path:
    root = root or LANDSLIDE_RISK_ROOT
    cfg_path = root / "config" / f"{site}.yaml"
    if not cfg_path.is_file():
        raise FileNotFoundError(cfg_path)
    cfg = _load_yaml(cfg_path)
    display = str(cfg.get("display_name", site))
    e_field = str(cfg.get("exposure_field", "exposure_score"))
    v_field = str(cfg.get("vulnerability_field", "vulnerability_score"))

    hazard_path = _resolve(root, str(cfg["hazard_tif"]))
    acs_path = _resolve(root, str(cfg["acs_ev_gpkg"]))

    out_dir = root / "sites" / site / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(hazard_path) as ds:
        h = _minmax_or_passthrough(ds.read(1))
        profile = ds.profile
        transform = ds.transform
        crs = ds.crs

    # Treat non-finite as nodata
    h = np.where(np.isfinite(h), h, np.nan).astype("float32")

    bg = gpd.read_file(acs_path)
    if bg.crs is None:
        bg = bg.set_crs(4326)
    bg = bg.to_crs(crs)

    e = rasterize_field(bg, e_field, out_shape=h.shape, transform=transform)
    v = rasterize_field(bg, v_field, out_shape=h.shape, transform=transform)

    valid = np.isfinite(h) & np.isfinite(e) & np.isfinite(v) & (h >= 0) & (e >= 0) & (v >= 0)
    risk = np.full(h.shape, np.nan, dtype="float32")
    # Geometric mean — same as poa_landslide_risk
    risk[valid] = np.power(h[valid] * e[valid] * v[valid], 1.0 / 3.0)

    print(
        f"Valid risk cells: {int(valid.sum())} / {h.size} | "
        f"R range: {np.nanmin(risk):.3f}–{np.nanmax(risk):.3f}"
    )

    prefix = site
    risk_tif = out_dir / f"landslide_risk_score_{prefix}.tif"
    e_tif = out_dir / f"landslide_exposure_score_{prefix}.tif"
    v_tif = out_dir / f"landslide_vulnerability_score_{prefix}.tif"
    write_geotiff(risk_tif, risk, profile, "landslide_risk_geometric_mean_HxExV")
    write_geotiff(e_tif, e, profile, "exposure_score_acs_block_group_burned")
    write_geotiff(v_tif, v, profile, "vulnerability_score_acs_block_group_burned")

    # Zonal means back to block groups (POA-style companion vector)
    zonal = zonal_means(
        bg,
        {
            "landslide_hazard_mean": h,
            "landslide_exposure_score": e,
            "landslide_vulnerability_score": v,
            "landslide_risk_score": risk,
        },
        transform,
    )
    # Keep useful ACS fields if present
    keep = [
        c
        for c in [
            "GEOID",
            "NAME",
            "total_population",
            "population_density",
            "exposure_score",
            "vulnerability_score",
            "landslide_hazard_mean",
            "landslide_exposure_score",
            "landslide_vulnerability_score",
            "landslide_risk_score",
            "geometry",
        ]
        if c in zonal.columns
    ]
    zonal_out = zonal[keep].copy()
    gpkg = out_dir / f"landslide_risk_score_{prefix}.gpkg"
    geojson = out_dir / f"landslide_risk_score_{prefix}.geojson"
    zonal_out.to_file(gpkg, driver="GPKG")
    zonal_out.to_file(geojson, driver="GeoJSON")
    print(f"Wrote {gpkg}")
    print(f"Wrote {geojson}")

    write_choropleth_svg(
        zonal_out,
        "landslide_risk_score",
        out_dir / "map_landslide_risk_score.svg",
        title=f"Landslide risk R=(H×E×V)^(1/3) — {display}",
        subtitle="Block-group mean · H=landslide hazard · E/V=ACS",
    )

    # Grid QA maps (direct from GeoTIFF arrays)
    grid_sub = f"{display} · hazard grid {h.shape[1]}×{h.shape[0]} cells"
    write_raster_grid_svg(
        risk,
        out_dir / "map_landslide_risk_score_grid.svg",
        title=f"Landslide risk grid R=(H×E×V)^(1/3) — {display}",
        subtitle=grid_sub,
        vmin=0.0,
        vmax=1.0,
    )
    write_raster_grid_svg(
        h,
        out_dir / "map_landslide_hazard_grid.svg",
        title=f"Landslide hazard H — {display}",
        subtitle=grid_sub,
        vmin=0.0,
        vmax=1.0,
    )
    write_raster_grid_svg(
        e,
        out_dir / "map_landslide_exposure_grid.svg",
        title=f"Exposure E (ACS burned) — {display}",
        subtitle=grid_sub,
        vmin=0.0,
        vmax=1.0,
    )
    write_raster_grid_svg(
        v,
        out_dir / "map_landslide_vulnerability_grid.svg",
        title=f"Vulnerability V (ACS burned) — {display}",
        subtitle=grid_sub,
        vmin=0.0,
        vmax=1.0,
    )

    meta = {
        "site_slug": site,
        "display_name": display,
        "formula": "R = (H * E * V) ** (1/3) where H, E, V finite",
        "hazard": {
            "path": str(hazard_path),
            "role": "H",
            "description": "Landslide hazard score (0–1)",
        },
        "exposure": {
            "path": str(acs_path),
            "field": e_field,
            "role": "E",
            "description": "ACS block-group exposure_score burned to hazard grid",
        },
        "vulnerability": {
            "path": str(acs_path),
            "field": v_field,
            "role": "V",
            "description": "ACS block-group vulnerability_score burned to hazard grid",
        },
        "grid": {
            "height": int(h.shape[0]),
            "width": int(h.shape[1]),
            "crs": str(crs),
            "valid_cells": int(valid.sum()),
        },
        "sector": {
            "sector": "Landslide",
            "risk": "Landslide",
            "note": "ACS E/V burned onto this hazard grid; grid may differ from flood/heat.",
        },
        "outputs": {
            "risk_tif": str(risk_tif),
            "exposure_tif": str(e_tif),
            "vulnerability_tif": str(v_tif),
            "gpkg": str(gpkg),
            "geojson": str(geojson),
        },
    }
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="plymouth")
    args = parser.parse_args(argv)
    try:
        out = run(args.site)
    except FileNotFoundError as exc:
        print(f"ERROR: missing input: {exc}", file=sys.stderr)
        return 1
    print(f"\nDone. Outputs in: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
