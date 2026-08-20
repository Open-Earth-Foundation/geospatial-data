#!/usr/bin/env python3
"""Compute heat hazard score from local normalized LST GeoTIFFs.

Reads Landsat / MODIS (optional ERA5) norms from ``sites/<city>/data/input/``,
resamples to a ~250 m grid, arithmetic-mean ensemble, writes GeoTIFFs + SVG QA.

Example:
  python transformation/heat_hazard/compute_heat_hazard.py --site plymouth
  python transformation/heat_hazard/compute_heat_hazard.py --site rochester --product regional
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

HEAT_HAZARD_ROOT = Path(__file__).resolve().parent
if str(HEAT_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(HEAT_HAZARD_ROOT))

from site_config import load_site_config  # noqa: E402

# layer_key → (default resampling, display label)
LAYER_SPEC: dict[str, tuple[Resampling, str]] = {
    "landsat_norm": (Resampling.bilinear, "Landsat LST"),
    "modis_day_norm": (Resampling.nearest, "MODIS LST Day"),
    "modis_night_norm": (Resampling.nearest, "MODIS LST Night"),
    "era5_hw_norm": (Resampling.nearest, "ERA5 HW Frequency"),
    "landsat_norm_regional": (Resampling.bilinear, "Landsat LST (regional)"),
    "modis_day_norm_regional": (Resampling.nearest, "MODIS LST Day (regional)"),
    "modis_night_norm_regional": (Resampling.nearest, "MODIS LST Night (regional)"),
}

CITY_NORM_KEYS = ["landsat_norm", "modis_day_norm", "modis_night_norm"]
REGIONAL_NORM_KEYS = [
    "landsat_norm_regional",
    "modis_day_norm_regional",
    "modis_night_norm_regional",
]


def regional_norm_filename(p90_name: str) -> str:
    stem = Path(p90_name).stem
    if "_p90_" in stem:
        stem = stem.replace("_p90_", "_norm_regional_", 1)
    elif stem.endswith("_p90"):
        stem = stem[: -len("_p90")] + "_norm_regional"
    else:
        stem = f"{stem}_norm_regional"
    return f"{stem}.tif"


def with_regional_suffix(filename: str) -> str:
    p = Path(filename)
    return f"{p.stem}_regional{p.suffix}"


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


def resolve_layers(
    site_config: dict[str, Any],
    *,
    product: str = "city",
) -> list[tuple[str, Path, float, Resampling]]:
    """Return [(key, path, weight, resampling), ...] for available configured layers."""
    hazard = site_config.get("hazard") or {}
    layers_cfg = dict(site_config.get("layers") or {})
    weights = dict(hazard.get("layer_weights") or {})
    input_dir = Path(site_config["paths_abs"]["data_input"])
    product = str(product or "city").lower()

    if product == "regional":
        keys = list(REGIONAL_NORM_KEYS)
        for p90_key, norm_key in (
            ("landsat_p90", "landsat_norm_regional"),
            ("modis_day_p90", "modis_day_norm_regional"),
            ("modis_night_p90", "modis_night_norm_regional"),
        ):
            if norm_key not in layers_cfg and layers_cfg.get(p90_key):
                layers_cfg[norm_key] = regional_norm_filename(str(layers_cfg[p90_key]))
        for city_key, reg_key in zip(CITY_NORM_KEYS, REGIONAL_NORM_KEYS):
            if reg_key not in weights and city_key in weights:
                weights[reg_key] = weights[city_key]
    else:
        keys = site_config.get("required_inputs")
        if not keys:
            keys = list(CITY_NORM_KEYS)
            if hazard.get("include_era5", False):
                keys = list(keys) + ["era5_hw_norm"]

    missing: list[str] = []
    resolved: list[tuple[str, Path, float, Resampling]] = []
    for key in keys:
        fname = layers_cfg.get(key)
        if not fname:
            missing.append(f"{key} (no layers.{key} in site config)")
            continue
        path = input_dir / str(fname)
        if not path.is_file():
            missing.append(f"{key} → {path}")
            continue
        rs, _label = LAYER_SPEC.get(key, (Resampling.nearest, key))
        w_key = key
        if key.endswith("_regional") and key not in weights:
            w_key = key.replace("_regional", "")
        w = float(weights.get(key, weights.get(w_key, 1.0)))
        resolved.append((key, path, w, rs))

    if missing:
        raise FileNotFoundError(
            "Missing required heat hazard input GeoTIFF(s). "
            "Run upstream LST extract / apply_regional_heat_norms.py first.\n  - "
            + "\n  - ".join(missing)
        )
    if not resolved:
        raise FileNotFoundError("No heat hazard input layers resolved.")
    return resolved


def resample_to_ref(
    src_path: Path,
    *,
    ref_height: int,
    ref_width: int,
    ref_transform,
    ref_crs,
    method: Resampling,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (data float32 clipped 0–1, invalid bool mask)."""
    dest_nodata = -9999.0
    with rasterio.open(src_path) as src:
        dest = np.empty((ref_height, ref_width), dtype=np.float64)
        reproject(
            source=rasterio.band(src, 1),
            destination=dest,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            dst_nodata=dest_nodata,
            resampling=method,
        )
    invalid = (dest == dest_nodata) | ~np.isfinite(dest)
    dest = np.clip(dest, 0.0, 1.0)
    return dest.astype(np.float32), invalid


def run(
    site: str,
    *,
    write_qa: bool = True,
    root: Path | None = None,
    product: str = "city",
) -> Path:
    root = Path(root or HEAT_HAZARD_ROOT).resolve()
    site_config = load_site_config(site, root)
    display = str(site_config.get("display_name") or site)
    hazard = site_config.get("hazard") or {}
    outputs = dict(site_config["outputs"])
    product = str(product or "city").lower()
    if product not in {"city", "regional"}:
        raise ValueError(f"product must be 'city' or 'regional', got {product!r}")
    if product == "regional":
        outputs["heat_hazard_score"] = with_regional_suffix(str(outputs["heat_hazard_score"]))
        outputs["heat_hazard_n_layers"] = with_regional_suffix(
            str(outputs["heat_hazard_n_layers"])
        )
    output_dir = Path(site_config["paths_abs"]["data_output"])
    output_dir.mkdir(parents=True, exist_ok=True)

    layer_specs = resolve_layers(site_config, product=product)
    min_layers = int(hazard.get("min_layers", 2))
    target_res_m = int(hazard.get("target_resolution_m", 250))
    deg_per_m = 1 / 111_320
    target_res_deg = target_res_m * deg_per_m
    lon_min, lat_min, lon_max, lat_max = site_config["bbox"]
    ref_crs = rasterio.CRS.from_epsg(4326)
    ref_width = math.ceil((lon_max - lon_min) / target_res_deg)
    ref_height = math.ceil((lat_max - lat_min) / target_res_deg)
    ref_transform = from_origin(lon_min, lat_max, target_res_deg, target_res_deg)

    print(f"Heat hazard site: {display} ({site}) · product={product}")
    print(f"Grid: {ref_height}×{ref_width} @ ~{target_res_m} m")
    print(f"Inputs ({len(layer_specs)}), min_layers={min_layers}:")

    arrays: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    for key, path, weight, method in layer_specs:
        data, invalid = resample_to_ref(
            path,
            ref_height=ref_height,
            ref_width=ref_width,
            ref_transform=ref_transform,
            ref_crs=ref_crs,
            method=method,
        )
        arrays.append(data)
        masks.append(invalid)
        valid_pct = (1.0 - invalid.mean()) * 100
        finite = data[~invalid]
        print(
            f"  {key:<28} w={weight:.2f} valid={valid_pct:.1f}% "
            f"min={finite.min():.3f} max={finite.max():.3f} ({path.name})"
        )

    stack = np.stack(arrays, axis=0)
    mask_stack = np.stack(masks, axis=0)
    valid_count = (~mask_stack).sum(axis=0).astype(np.float32)

    w_sum = np.zeros((ref_height, ref_width), dtype=np.float32)
    w_total = np.zeros((ref_height, ref_width), dtype=np.float32)
    for i, (_key, _path, w, _rs) in enumerate(layer_specs):
        valid = ~mask_stack[i]
        w_sum[valid] += stack[i][valid] * w
        w_total[valid] += w

    with np.errstate(invalid="ignore", divide="ignore"):
        ensemble = np.where(w_total > 0, w_sum / w_total, np.nan).astype(np.float32)
    insufficient = valid_count < min_layers
    ensemble = np.where(insufficient | ~np.isfinite(ensemble), np.nan, ensemble)

    print(
        f"Ensemble: valid={int(np.isfinite(ensemble).sum()):,} / {ensemble.size:,} "
        f"min={float(np.nanmin(ensemble)):.4f} max={float(np.nanmax(ensemble)):.4f}"
    )

    write_profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": ref_width,
        "height": ref_height,
        "count": 1,
        "crs": ref_crs,
        "transform": ref_transform,
        "nodata": np.nan,
        "compress": "lzw",
    }
    out_score = output_dir / outputs["heat_hazard_score"]
    with rasterio.open(out_score, "w", **write_profile) as dst:
        dst.write(ensemble.astype(np.float32), 1)
        dst.set_band_description(1, "heat_hazard_score_0_1")
        dst.update_tags(
            normalization_domain="city" if product == "city" else "regional",
            product=product,
            comparability="city" if product == "city" else "regional",
        )
    print(f"Wrote {out_score}")

    out_nlay = output_dir / outputs["heat_hazard_n_layers"]
    qa_profile = {**write_profile, "dtype": "uint8", "nodata": 255}
    with rasterio.open(out_nlay, "w", **qa_profile) as dst:
        dst.write(valid_count.astype(np.uint8), 1)
        dst.set_band_description(1, "n_valid_layers")
    print(f"Wrote {out_nlay}")

    qa_prefix = "map_heat_hazard" if product == "city" else "map_heat_hazard_regional"
    if write_qa:
        season = str(site_config.get("season_label") or site_config.get("season") or "")
        years = f"{site_config.get('start_year', '')}–{site_config.get('end_year', '')}"
        domain = "city AOI" if product == "city" else "regional (state) norms"
        grid_sub = (
            f"{display} · {domain} · {ref_width}×{ref_height} · "
            f"~{target_res_m} m · {season} {years}"
        ).strip()
        write_raster_grid_svg(
            ensemble,
            output_dir / f"{qa_prefix}_score.svg",
            title=f"Heat hazard score ({product}) — {display}",
            subtitle=grid_sub,
            vmin=0.0,
            vmax=1.0,
            legend_label="H 0–1",
        )
        write_raster_grid_svg(
            valid_count.astype("float64"),
            output_dir / f"{qa_prefix}_n_layers.svg",
            title=f"Heat hazard n layers ({product}) — {display}",
            subtitle=grid_sub,
            vmin=0.0,
            vmax=float(len(layer_specs)),
            legend_label=f"0–{len(layer_specs)}",
        )
        for i, (key, _path, _w, _rs) in enumerate(layer_specs):
            layer_arr = np.where(mask_stack[i], np.nan, stack[i])
            write_raster_grid_svg(
                layer_arr,
                output_dir / f"map_heat_input_{key}.svg",
                title=f"Heat input {key} — {display}",
                subtitle=grid_sub,
                vmin=0.0,
                vmax=1.0,
                legend_label="0–1",
            )

    meta = {
        "site_slug": site,
        "display_name": display,
        "product": product,
        "normalization_domain": "city" if product == "city" else "regional",
        "comparability": "city" if product == "city" else "regional",
        "min_layers": min_layers,
        "target_resolution_m": target_res_m,
        "include_era5": bool(hazard.get("include_era5", False)),
        "layers": [
            {"key": k, "path": str(p), "weight": w} for k, p, w, _ in layer_specs
        ],
        "grid": {
            "height": ref_height,
            "width": ref_width,
            "crs": "EPSG:4326",
            "valid": int(np.isfinite(ensemble).sum()),
        },
        "outputs": {
            "score": str(out_score),
            "n_layers": str(out_nlay),
        },
        "qa_maps": sorted(str(p) for p in output_dir.glob(f"{qa_prefix}*.svg"))
        if write_qa
        else [],
    }
    meta_name = "metadata.json" if product == "city" else "metadata_regional.json"
    meta_path = output_dir / meta_name
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")
    return output_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default=None, help="City slug (default: HEAT_SITE / porto_alegre)")
    parser.add_argument(
        "--product",
        choices=["city", "regional"],
        default="city",
        help="city = AOI min–max norms (default); regional = state-domain dual product",
    )
    parser.add_argument("--no-qa", action="store_true", help="Skip SVG QA maps")
    args = parser.parse_args(argv)
    site = args.site or os.environ.get("HEAT_SITE") or os.environ.get("FLOODS_SITE", "porto_alegre")
    try:
        out = run(site, write_qa=not args.no_qa, product=args.product)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"\nDone. Outputs in: {out}")
    print(
        "Next: python transformation/heat_hazard/heat_hazard_publish.py "
        f"--site {site}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
