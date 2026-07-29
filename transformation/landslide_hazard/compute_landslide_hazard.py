#!/usr/bin/env python3
"""Compute landslide hazard score from local input GeoTIFFs.

Reads slope / R90p / clay / NDVI / HAND / Dynamic World from
``sites/<city>/data/input/``, warps to ~90 m, computes gated weighted score,
writes GeoTIFF + SVG QA maps.

Example:
  python transformation/landslide_hazard/compute_landslide_hazard.py --site plymouth
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

LANDSLIDE_HAZARD_ROOT = Path(__file__).resolve().parent
if str(LANDSLIDE_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(LANDSLIDE_HAZARD_ROOT))

from site_config import load_site_config  # noqa: E402

REQUIRED_LAYER_KEYS = ["slope_deg", "r90p", "clay_pct", "ndvi_p10", "hand", "dw_mode"]
RESAMPLE: dict[str, Resampling] = {
    "slope_deg": Resampling.average,
    "r90p": Resampling.nearest,
    "clay_pct": Resampling.bilinear,
    "ndvi_p10": Resampling.bilinear,
    "hand": Resampling.bilinear,
    "dw_mode": Resampling.nearest,
}


def _color_ramp(t: float) -> str:
    t = max(0.0, min(1.0, float(t)))
    stops = [
        (0.0, (68, 1, 84)),
        (0.25, (49, 104, 142)),
        (0.5, (53, 183, 121)),
        (0.75, (110, 206, 88)),
        (1.0, (253, 231, 37)),
    ]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            rgb = tuple(int(c0[i] + u * (c1[i] - c0[i])) for i in range(3))
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    return "#fde725"


def write_raster_grid_svg(
    arr: np.ndarray,
    out_path: Path,
    *,
    title: str,
    subtitle: str = "",
    width: int = 900,
    height: int = 780,
    vmin: float | None = 0.0,
    vmax: float | None = 1.0,
    legend_label: str = "0–1",
) -> None:
    a = np.asarray(arr, dtype="float64")
    finite = a[np.isfinite(a)]
    if finite.size == 0:
        print(f"Skip map (no finite values): {out_path.name}")
        return
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
        f'<text x="20" y="32" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="18" font-weight="bold">{title}</text>',
    ]
    if subtitle:
        parts.append(
            f'<text x="20" y="52" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="12" fill="#444">{subtitle}</text>'
        )
    for i in range(nrows):
        for j in range(ncols):
            v = a[i, j]
            fill = "#9e9e9e" if not np.isfinite(v) else _color_ramp((float(v) - lo) / (hi - lo))
            x = margin_l + j * cell_w
            y = margin_t + i * cell_h
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w:.2f}" height="{cell_h:.2f}" '
                f'fill="{fill}" stroke="none"/>'
            )
    parts.append(
        f'<rect x="{margin_l}" y="{margin_t}" width="{map_w}" height="{map_h}" '
        f'fill="none" stroke="#666" stroke-width="1"/>'
    )
    lx = width - legend_w
    parts.append(
        f'<text x="{lx}" y="90" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="11">{legend_label}</text>'
    )
    for i in range(11):
        t = i / 10
        y = 100 + i * 22
        val = hi - t * (hi - lo)
        parts.append(
            f'<rect x="{lx}" y="{y}" width="18" height="18" '
            f'fill="{_color_ramp(1 - t)}" stroke="#666"/>'
        )
        parts.append(
            f'<text x="{lx + 26}" y="{y + 13}" font-family="Helvetica, Arial, sans-serif" '
            f'font-size="11">{val:.2f}</text>'
        )
    parts.append("</svg>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote map: {out_path}")


def clamp01(arr: np.ndarray) -> np.ndarray:
    return np.clip(arr, 0.0, 1.0)


def minmax_norm(arr: np.ndarray) -> np.ndarray:
    lo, hi = np.nanmin(arr), np.nanmax(arr)
    if not np.isfinite(lo) or not np.isfinite(hi) or hi == lo:
        return np.zeros_like(arr, dtype="float32")
    return ((arr - lo) / (hi - lo)).astype("float32")


def resolve_inputs(site_config: dict[str, Any]) -> dict[str, Path]:
    input_dir = Path(site_config["paths_abs"]["data_input"])
    layers_cfg = site_config.get("layers") or {}
    keys = list(site_config.get("required_inputs") or REQUIRED_LAYER_KEYS)
    missing: list[str] = []
    paths: dict[str, Path] = {}
    for key in keys:
        fname = layers_cfg.get(key)
        if not fname:
            missing.append(f"{key} (no layers.{key} in site config)")
            continue
        path = input_dir / str(fname)
        if not path.is_file():
            missing.append(f"{key} → {path}")
            continue
        paths[key] = path
    if missing:
        raise FileNotFoundError(
            "Missing required landslide hazard input GeoTIFF(s). "
            "Run upstream extract notebooks first.\n  - " + "\n  - ".join(missing)
        )
    return paths


def to_grid(
    src_path: Path,
    *,
    ref_height: int,
    ref_width: int,
    ref_transform,
    ref_crs,
    resampling: Resampling,
) -> np.ndarray:
    with rasterio.open(src_path) as src:
        out = np.full((ref_height, ref_width), np.nan, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=resampling,
        )
    return out


def run(
    site: str,
    *,
    write_qa: bool = True,
    root: Path | None = None,
) -> Path:
    root = Path(root or LANDSLIDE_HAZARD_ROOT).resolve()
    site_config = load_site_config(site, root)
    display = str(site_config.get("display_name") or site)
    hazard = site_config.get("hazard") or {}
    outputs = site_config["outputs"]
    output_dir = Path(site_config["paths_abs"]["data_output"])
    output_dir.mkdir(parents=True, exist_ok=True)

    input_paths = resolve_inputs(site_config)
    print(f"Landslide hazard site: {display} ({site})")
    print(f"Inputs ({len(input_paths)}):")
    for k, p in input_paths.items():
        print(f"  {k}: {p.name}")

    target_res_m = int(hazard.get("target_resolution_m", 90))
    deg_per_m = 1 / 111_320
    target_res_deg = target_res_m * deg_per_m
    lon_min, lat_min, lon_max, lat_max = site_config["bbox"]
    ref_crs = rasterio.CRS.from_epsg(4326)
    ref_width = math.ceil((lon_max - lon_min) / target_res_deg)
    ref_height = math.ceil((lat_max - lat_min) / target_res_deg)
    ref_transform = from_origin(lon_min, lat_max, target_res_deg, target_res_deg)
    print(f"Grid: {ref_height}×{ref_width} @ ~{target_res_m} m")

    arrays = {
        key: to_grid(
            path,
            ref_height=ref_height,
            ref_width=ref_width,
            ref_transform=ref_transform,
            ref_crs=ref_crs,
            resampling=RESAMPLE.get(key, Resampling.nearest),
        )
        for key, path in input_paths.items()
    }
    slope_arr = arrays["slope_deg"]
    r90p_arr = arrays["r90p"]
    clay_arr = arrays["clay_pct"]
    ndvi_arr = arrays["ndvi_p10"]
    hand_arr = arrays["hand"]
    dw_arr = arrays["dw_mode"]

    slope_gate = float(hazard.get("slope_gate_deg", 15))
    slope_sat = float(hazard.get("slope_sat_deg", 35))
    clay_sat = float(hazard.get("clay_sat_pct", 40))
    hand_sat = float(hazard.get("hand_sat_m", 50))
    ndvi_dense = float(hazard.get("ndvi_dense_threshold", 0.4))
    fill_cfg = hazard.get("fill") or {}

    hand_fill = np.where(
        np.isnan(hand_arr), float(fill_cfg.get("hand_m", 25.0)), hand_arr
    )
    clay_fill = np.where(
        np.isnan(clay_arr), float(fill_cfg.get("clay_pct", 35.0)), clay_arr
    )
    ndvi_fill = np.where(np.isnan(ndvi_arr), float(fill_cfg.get("ndvi", 0.3)), ndvi_arr)
    r90p_fill = np.where(np.isnan(r90p_arr), float(np.nanmedian(r90p_arr)), r90p_arr)

    slope_span = max(slope_sat - slope_gate, 1e-6)
    slope_risk = clamp01((slope_arr - slope_gate) / slope_span)
    precip_risk = minmax_norm(r90p_fill)
    soil_risk = clamp01(clay_fill / clay_sat)
    veg_protect = minmax_norm(ndvi_fill)
    hand_factor = clamp01(1.0 - (hand_fill / hand_sat))

    w = hazard.get("weights") or {}
    w_slope = float(w.get("slope_risk", 0.45))
    w_precip = float(w.get("precip_risk", 0.20))
    w_cohesion = float(w.get("low_cohesion", 0.15))
    w_veg = float(w.get("lack_of_veg", 0.10))
    w_hand = float(w.get("hand_factor", 0.10))

    H = (
        w_slope * slope_risk
        + w_precip * precip_risk * slope_risk
        + w_cohesion * (1 - soil_risk) * slope_risk
        + w_veg * (1 - veg_protect) * slope_risk
        + w_hand * hand_factor * slope_risk
    )

    mod = hazard.get("modifiers") or {}
    bare_built = set(int(x) for x in mod.get("bare_built_classes", [6, 7]))
    dense_veg_classes = set(int(x) for x in mod.get("dense_veg_classes", [1, 2, 3, 5]))
    boost = float(mod.get("bare_built_boost", 0.10))
    dampen = float(mod.get("dense_veg_factor", 0.85))

    bare_built_on_slope = np.isin(dw_arr.astype(int), list(bare_built)) & (
        slope_arr >= slope_gate
    )
    H = np.where(bare_built_on_slope, H + boost, H)
    dense_veg = np.isin(dw_arr.astype(int), list(dense_veg_classes)) & (
        ndvi_fill > ndvi_dense
    )
    H = np.where(dense_veg, H * dampen, H)

    hazard_score = clamp01(H)
    hazard_score = np.where(np.isfinite(slope_arr), hazard_score, np.nan).astype(
        "float32"
    )

    print(
        f"Hazard: min={float(np.nanmin(hazard_score)):.3f} "
        f"max={float(np.nanmax(hazard_score)):.3f} "
        f"%gt0={float(np.nanmean(hazard_score > 0) * 100):.1f}"
    )

    out_tif = output_dir / outputs["landslide_hazard_score"]
    write_meta = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": ref_width,
        "height": ref_height,
        "count": 1,
        "crs": ref_crs,
        "transform": ref_transform,
        "nodata": np.nan,
        "compress": "lzw",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    with rasterio.open(out_tif, "w", **write_meta) as dst:
        dst.write(hazard_score, 1)
        dst.set_band_description(1, "landslide_hazard_score_0_1")
    print(f"Wrote {out_tif}")

    components = {
        "slope_risk": slope_risk,
        "precip_risk": precip_risk,
        "soil_risk": soil_risk,
        "veg_protect": veg_protect,
        "hand_factor": hand_factor,
    }

    if write_qa:
        grid_sub = f"{display} · {ref_width}×{ref_height} · ~{target_res_m} m"
        write_raster_grid_svg(
            hazard_score,
            output_dir / "map_landslide_hazard_score.svg",
            title=f"Landslide hazard score — {display}",
            subtitle=grid_sub,
            vmin=0.0,
            vmax=1.0,
            legend_label="H 0–1",
        )
        write_raster_grid_svg(
            slope_arr,
            output_dir / "map_landslide_slope_deg.svg",
            title=f"Slope (deg) — {display}",
            subtitle=grid_sub,
            vmin=None,
            vmax=None,
            legend_label="degrees",
        )
        for name, arr in components.items():
            write_raster_grid_svg(
                np.where(np.isfinite(slope_arr), arr, np.nan),
                output_dir / f"map_landslide_{name}.svg",
                title=f"Landslide component {name} — {display}",
                subtitle=grid_sub,
                vmin=0.0,
                vmax=1.0,
                legend_label="0–1",
            )

    meta = {
        "site_slug": site,
        "display_name": display,
        "target_resolution_m": target_res_m,
        "slope_gate_deg": slope_gate,
        "weights": {
            "slope_risk": w_slope,
            "precip_risk": w_precip,
            "low_cohesion": w_cohesion,
            "lack_of_veg": w_veg,
            "hand_factor": w_hand,
        },
        "grid": {
            "height": ref_height,
            "width": ref_width,
            "crs": "EPSG:4326",
            "valid": int(np.isfinite(hazard_score).sum()),
            "gt0_pct": float(np.nanmean(hazard_score > 0) * 100)
            if np.isfinite(hazard_score).any()
            else None,
        },
        "inputs": {k: str(p) for k, p in input_paths.items()},
        "outputs": {"score": str(out_tif)},
        "qa_maps": sorted(str(p) for p in output_dir.glob("map_landslide_*.svg"))
        if write_qa
        else [],
    }
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")
    return output_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site",
        default=None,
        help="City slug (default: LANDSLIDES_SITE / porto_alegre)",
    )
    parser.add_argument("--no-qa", action="store_true", help="Skip SVG QA maps")
    args = parser.parse_args(argv)
    site = (
        args.site
        or os.environ.get("LANDSLIDES_SITE")
        or os.environ.get("FLOODS_SITE", "porto_alegre")
    )
    try:
        out = run(site, write_qa=not args.no_qa)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"\nDone. Outputs in: {out}")
    print(
        "Next: python transformation/landslide_hazard/landslide_hazard_publish.py "
        f"--site {site}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
