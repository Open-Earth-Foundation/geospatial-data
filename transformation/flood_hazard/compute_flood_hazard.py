#!/usr/bin/env python3
"""Compute flood hazard score from local input GeoTIFFs (no GEE / no notebooks).

Reads ensemble layers from ``sites/<city>/data/input/``, aligns to the reference
grid, computes partial + strict scores, optional IDW gap-fill, writes GeoTIFFs
and SVG QA maps under ``sites/<city>/data/output/``.

Example:
  python transformation/flood_hazard/compute_flood_hazard.py --site plymouth
  python transformation/flood_hazard/compute_flood_hazard.py --site plymouth --no-idw
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.transform import xy
from rasterio.warp import Resampling, reproject
from scipy.spatial import cKDTree

FLOOD_HAZARD_ROOT = Path(__file__).resolve().parent
if str(FLOOD_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(FLOOD_HAZARD_ROOT))

from site_config import load_site_config  # noqa: E402

# Score-layer keys (weights) → filename key under site config `layers:`
LAYER_FILE_KEYS: dict[str, str] = {
    "aqueduct_norm": "aqueduct_norm",
    "gfd_count_norm": "gfd_count_norm",
    "gfplain_250m": "gfplain",
    "jrc_norm": "jrc_norm",
}


def read_single_band_raster(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    """Read first band as float32, converting nodata to NaN."""
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        nodata = src.nodata
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)
        meta = {
            "path": str(path),
            "shape": arr.shape,
            "crs": src.crs,
            "transform": src.transform,
            "nodata": nodata,
            "dtype": str(src.dtypes[0]),
            "count": src.count,
        }
    return arr, meta


def reproject_to_reference(
    src_arr: np.ndarray,
    src_meta: dict[str, Any],
    ref_meta: dict[str, Any],
    ref_shape: tuple[int, int],
    resampling: Resampling,
) -> np.ndarray:
    dst = np.full(ref_shape, np.nan, dtype="float32")
    reproject(
        source=src_arr,
        destination=dst,
        src_transform=src_meta["transform"],
        src_crs=src_meta["crs"],
        dst_transform=ref_meta["transform"],
        dst_crs=ref_meta["crs"],
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=resampling,
    )
    return dst


def resolve_required_inputs(site_config: dict[str, Any]) -> dict[str, Path]:
    """Map weight keys → absolute input paths; raise if any are missing."""
    input_dir = site_config["paths_abs"]["data_input"]
    layers_cfg = site_config.get("layers") or {}
    hazard_cfg = site_config.get("hazard") or {}
    weight_keys = list((hazard_cfg.get("weights") or LAYER_FILE_KEYS).keys())

    # Allow explicit required_inputs override in city YAML
    required = site_config.get("required_inputs")
    if required:
        weight_keys = list(required)

    missing: list[str] = []
    paths: dict[str, Path] = {}
    for key in weight_keys:
        file_key = LAYER_FILE_KEYS.get(key, key)
        filename = layers_cfg.get(file_key)
        if not filename:
            missing.append(f"{key} (no layers.{file_key} in site config)")
            continue
        path = Path(input_dir) / str(filename)
        if not path.is_file():
            missing.append(f"{key} → {path}")
            continue
        paths[key] = path

    if missing:
        raise FileNotFoundError(
            "Missing required flood hazard input GeoTIFF(s). "
            "Run upstream extract notebooks/CLIs first.\n  - "
            + "\n  - ".join(missing)
        )
    return paths


def write_geotiff(
    path: Path,
    arr: np.ndarray,
    *,
    crs,
    transform,
    description: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": arr.shape[0],
        "width": arr.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": np.nan,
        "compress": "lzw",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(arr.astype("float32"), 1)
        dst.set_band_description(1, description)
    print(f"Wrote {path}")


def _color_ramp(t: float) -> str:
    """Viridis-like ramp matching flood_hazard_colors.txt."""
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
    """Choropleth-style SVG of a 2D float raster (one rect per cell) for QA."""
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


def compute_idw_gapfill(
    flood_score_base: np.ndarray,
    n_layers_used: np.ndarray,
    *,
    transform,
    idw_cfg: dict[str, Any],
    gfplain: np.ndarray | None = None,
    fluvial_present: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Distance-capped IDW fill. Returns (score_idw, is_interpolated, interp_distance_m)."""
    max_dist_m = float(idw_cfg.get("max_dist_m", 750.0))
    min_neighbors = int(idw_cfg.get("min_neighbors", 3))
    power = float(idw_cfg.get("power", 2.0))
    k_neighbors = int(idw_cfg.get("k_neighbors", 32))
    use_gfplain_mask = bool(idw_cfg.get("use_gfplain_mask", False))
    print(
        f"IDW params: max_dist_m={max_dist_m}, min_neighbors={min_neighbors}, "
        f"power={power}, k={k_neighbors}, gfplain_mask={use_gfplain_mask}"
    )

    observed = np.isfinite(flood_score_base)
    gap_mask = ~observed
    if use_gfplain_mask and gfplain is not None and fluvial_present is not None:
        gap_mask = gap_mask & ((gfplain == 1) | fluvial_present)

    height, width = flood_score_base.shape
    rows, cols = np.indices((height, width))
    xs, ys = xy(transform, rows.ravel(), cols.ravel(), offset="center")
    xs = np.asarray(xs, dtype="float64")
    ys = np.asarray(ys, dtype="float64")

    lat0 = float(np.nanmean(ys))
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(lat0))
    coords_m = np.column_stack([xs * m_per_deg_lon, ys * m_per_deg_lat])

    obs_flat_idx = np.flatnonzero(observed.ravel())
    gap_flat_idx = np.flatnonzero(gap_mask.ravel())
    if obs_flat_idx.size == 0 or gap_flat_idx.size == 0:
        return (
            flood_score_base.copy(),
            np.zeros_like(flood_score_base, dtype=bool),
            np.full_like(flood_score_base, np.nan, dtype="float32"),
        )

    obs_coords = coords_m[obs_flat_idx]
    obs_scores = flood_score_base.ravel()[obs_flat_idx].astype("float64")
    obs_nlayers = n_layers_used.ravel()[obs_flat_idx].astype("float64")
    obs_nlayers = np.where(obs_nlayers >= 3, obs_nlayers, 3.0)

    tree = cKDTree(obs_coords)
    k_query = min(k_neighbors, len(obs_flat_idx))
    gap_coords = coords_m[gap_flat_idx]

    dists, nn_idx = tree.query(gap_coords, k=k_query, workers=-1)
    if k_query == 1:
        dists = dists[:, None]
        nn_idx = nn_idx[:, None]

    scores_nn = obs_scores[nn_idx]
    nlayers_nn = obs_nlayers[nn_idx]
    valid_nn = (dists > 1e-6) & (dists <= max_dist_m)
    n_valid = valid_nn.sum(axis=1)

    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.where(valid_nn, nlayers_nn / (dists**power), 0.0)
    w_sum = w.sum(axis=1)
    filled = np.where(w_sum > 0, (w * scores_nn).sum(axis=1) / w_sum, np.nan)
    min_dist = np.where(valid_nn, dists, np.inf).min(axis=1)

    ok = (n_valid >= min_neighbors) & np.isfinite(filled)
    filled = np.clip(filled, 0.0, 1.0)

    flood_score_idw = flood_score_base.copy()
    is_interpolated = np.zeros_like(flood_score_base, dtype=bool)
    interp_distance_m = np.full_like(flood_score_base, np.nan, dtype="float32")

    fill_rows, fill_cols = np.unravel_index(gap_flat_idx[ok], (height, width))
    flood_score_idw[fill_rows, fill_cols] = filled[ok].astype("float32")
    is_interpolated[fill_rows, fill_cols] = True
    interp_distance_m[fill_rows, fill_cols] = min_dist[ok].astype("float32")

    print(
        f"IDW: observed={int(observed.sum())} gaps={int(gap_mask.sum())} "
        f"filled={int(is_interpolated.sum())} "
        f"finite_base={int(np.isfinite(flood_score_base).sum())} "
        f"finite_idw={int(np.isfinite(flood_score_idw).sum())}"
    )
    return flood_score_idw, is_interpolated, interp_distance_m


def run(
    site: str,
    *,
    do_idw: bool = True,
    write_qa: bool = True,
    root: Path | None = None,
) -> Path:
    root = Path(root or FLOOD_HAZARD_ROOT).resolve()
    site_config = load_site_config(site, root)
    display = str(site_config.get("display_name") or site)
    hazard_cfg = site_config["hazard"]
    idw_cfg = site_config["idw"]
    outputs = site_config["outputs"]
    output_dir = Path(site_config["paths_abs"]["data_output"])
    output_dir.mkdir(parents=True, exist_ok=True)

    input_paths = resolve_required_inputs(site_config)
    print(f"Flood hazard site: {display} ({site})")
    print(f"Inputs ({len(input_paths)}):")
    for k, p in input_paths.items():
        print(f"  {k}: {p.name}")

    layers: dict[str, np.ndarray] = {}
    layer_meta: dict[str, dict[str, Any]] = {}
    for name, path in input_paths.items():
        arr, meta = read_single_band_raster(path)
        layers[name] = arr
        layer_meta[name] = meta

    score_ref = str(hazard_cfg.get("reference_grid", "gfplain_250m"))
    if score_ref not in layers:
        raise KeyError(
            f"reference_grid={score_ref!r} not among loaded layers: {sorted(layers)}"
        )
    ref_meta = layer_meta[score_ref]
    ref_arr = layers[score_ref]

    aligned: dict[str, np.ndarray] = {score_ref: ref_arr.copy()}
    for name, arr in layers.items():
        if name == score_ref:
            continue
        is_binary = name in {"gfplain_250m", "gfd_observed_once"}
        rs = Resampling.nearest if is_binary else Resampling.bilinear
        aligned[name] = reproject_to_reference(
            arr, layer_meta[name], ref_meta, ref_arr.shape, rs
        )
    print(f"Aligned to reference grid: {score_ref} {ref_arr.shape}")

    weights = dict(hazard_cfg["weights"])
    layer_keys = list(weights.keys())
    for k in layer_keys:
        if k not in aligned:
            raise KeyError(f"Weight layer {k!r} missing after align")
    w = np.array([weights[k] for k in layer_keys], dtype="float32")[:, None, None]
    stack = np.stack([aligned[k] for k in layer_keys], axis=0)
    layer_valid = np.isfinite(stack)
    n_layers_used = layer_valid.sum(axis=0).astype("float32")

    fluvial_layers = hazard_cfg.get("fluvial_layers", ["jrc_norm", "aqueduct_norm"])
    fluvial_present = np.zeros(stack.shape[1:], dtype=bool)
    for name in fluvial_layers:
        if name in aligned:
            fluvial_present |= np.isfinite(aligned[name])
    if not hazard_cfg.get("require_fluvial_layer", True):
        fluvial_present = np.ones_like(fluvial_present, dtype=bool)
    min_layers = int(hazard_cfg.get("min_layers", 3))

    valid_mask_strict = layer_valid.all(axis=0)
    valid_mask_partial = (n_layers_used >= min_layers) & fluvial_present

    weighted_sum = np.sum(np.where(layer_valid, stack * w, 0.0), axis=0)
    weight_total = np.sum(np.where(layer_valid, w, 0.0), axis=0)
    weight_total = np.where(weight_total > 0, weight_total, np.nan)
    score_raw = weighted_sum / weight_total

    flood_score_strict = np.full_like(score_raw, np.nan, dtype="float32")
    flood_score_strict[valid_mask_strict] = score_raw[valid_mask_strict]
    flood_score_strict = np.clip(flood_score_strict, 0.0, 1.0)

    flood_score_base = np.full_like(score_raw, np.nan, dtype="float32")
    flood_score_base[valid_mask_partial] = score_raw[valid_mask_partial]
    flood_score_base = np.clip(flood_score_base, 0.0, 1.0)

    n_layers_used_out = np.full_like(n_layers_used, np.nan, dtype="float32")
    n_layers_used_out[valid_mask_partial] = n_layers_used[valid_mask_partial]

    print(
        f"Score base: valid={int(valid_mask_partial.sum())} "
        f"min/max={float(np.nanmin(flood_score_base)):.4f}/"
        f"{float(np.nanmax(flood_score_base)):.4f} "
        f"(strict={int(valid_mask_strict.sum())})"
    )

    paths = {
        "partial": output_dir / outputs["flood_hazard_score"],
        "strict": output_dir / outputs["flood_hazard_score_strict"],
        "n_layers": output_dir / outputs["flood_hazard_n_layers_used"],
    }
    for key, arr, desc in [
        ("partial", flood_score_base, "flood_score_partial_ge3of4_fluvial"),
        ("strict", flood_score_strict, "flood_score_strict_all4"),
        ("n_layers", n_layers_used_out, "n_layers_used_ge3of4_fluvial"),
    ]:
        write_geotiff(
            paths[key],
            arr,
            crs=ref_meta["crs"],
            transform=ref_meta["transform"],
            description=desc,
        )

    flood_score_idw = None
    is_interpolated = None
    interp_distance_m = None
    if do_idw:
        flood_score_idw, is_interpolated, interp_distance_m = compute_idw_gapfill(
            flood_score_base,
            n_layers_used,
            transform=ref_meta["transform"],
            idw_cfg=idw_cfg,
            gfplain=aligned.get("gfplain_250m"),
            fluvial_present=fluvial_present,
        )
        paths["idw"] = output_dir / outputs["flood_hazard_score_idw"]
        paths["is_interp"] = output_dir / outputs["flood_hazard_is_interpolated"]
        paths["interp_dist"] = output_dir / outputs["flood_hazard_interp_distance_m"]
        paths["interp_only"] = output_dir / outputs["flood_hazard_score_interpolated_only"]

        write_geotiff(
            paths["idw"],
            flood_score_idw,
            crs=ref_meta["crs"],
            transform=ref_meta["transform"],
            description="flood_score_idw_distance_capped",
        )
        write_geotiff(
            paths["is_interp"],
            is_interpolated.astype("float32"),
            crs=ref_meta["crs"],
            transform=ref_meta["transform"],
            description="is_interpolated_flag",
        )
        write_geotiff(
            paths["interp_dist"],
            interp_distance_m,
            crs=ref_meta["crs"],
            transform=ref_meta["transform"],
            description="interp_distance_m",
        )
        score_interp_only = np.where(is_interpolated, flood_score_idw, np.nan).astype(
            "float32"
        )
        write_geotiff(
            paths["interp_only"],
            score_interp_only,
            crs=ref_meta["crs"],
            transform=ref_meta["transform"],
            description="flood_score_interpolated_pixels_only",
        )

    if write_qa:
        grid_sub = f"{display} · {ref_arr.shape[1]}×{ref_arr.shape[0]} · {score_ref}"
        write_raster_grid_svg(
            flood_score_base,
            output_dir / "map_flood_hazard_score_base.svg",
            title=f"Flood hazard base (partial) — {display}",
            subtitle=grid_sub,
            vmin=0.0,
            vmax=1.0,
            legend_label="H 0–1",
        )
        write_raster_grid_svg(
            flood_score_strict,
            output_dir / "map_flood_hazard_score_strict.svg",
            title=f"Flood hazard strict (all layers) — {display}",
            subtitle=grid_sub,
            vmin=0.0,
            vmax=1.0,
            legend_label="H 0–1",
        )
        write_raster_grid_svg(
            n_layers_used_out,
            output_dir / "map_flood_hazard_n_layers.svg",
            title=f"Flood hazard n layers used — {display}",
            subtitle=grid_sub,
            vmin=0.0,
            vmax=float(len(layer_keys)),
            legend_label=f"0–{len(layer_keys)}",
        )
        if flood_score_idw is not None and is_interpolated is not None:
            write_raster_grid_svg(
                flood_score_idw,
                output_dir / "map_flood_hazard_score_idw.svg",
                title=f"Flood hazard IDW-filled — {display}",
                subtitle=grid_sub,
                vmin=0.0,
                vmax=1.0,
                legend_label="H 0–1",
            )
            write_raster_grid_svg(
                np.where(is_interpolated, flood_score_idw, np.nan),
                output_dir / "map_flood_hazard_interpolated_only.svg",
                title=f"Flood hazard interpolated cells only — {display}",
                subtitle=grid_sub,
                vmin=0.0,
                vmax=1.0,
                legend_label="H 0–1",
            )
            if interp_distance_m is not None and np.isfinite(interp_distance_m).any():
                write_raster_grid_svg(
                    interp_distance_m,
                    output_dir / "map_flood_hazard_interp_distance_m.svg",
                    title=f"IDW interp distance (m) — {display}",
                    subtitle=grid_sub,
                    vmin=None,
                    vmax=None,
                    legend_label="meters",
                )

    meta = {
        "site_slug": site,
        "display_name": display,
        "reference_grid": score_ref,
        "weights": weights,
        "min_layers": min_layers,
        "fluvial_layers": list(fluvial_layers),
        "idw": dict(idw_cfg) if do_idw else None,
        "grid": {
            "height": int(ref_arr.shape[0]),
            "width": int(ref_arr.shape[1]),
            "crs": str(ref_meta["crs"]),
            "valid_base": int(valid_mask_partial.sum()),
            "valid_strict": int(valid_mask_strict.sum()),
            "valid_idw": int(np.isfinite(flood_score_idw).sum())
            if flood_score_idw is not None
            else None,
            "interpolated": int(is_interpolated.sum())
            if is_interpolated is not None
            else None,
        },
        "inputs": {k: str(p) for k, p in input_paths.items()},
        "outputs": {k: str(p) for k, p in paths.items()},
        "qa_maps": sorted(str(p) for p in output_dir.glob("map_flood_hazard_*.svg"))
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
        help="City slug (default: FLOODS_SITE env or porto_alegre)",
    )
    parser.add_argument(
        "--no-idw",
        action="store_true",
        help="Skip IDW gap-fill (write base/strict/n_layers only)",
    )
    parser.add_argument(
        "--no-qa",
        action="store_true",
        help="Skip SVG QA maps",
    )
    args = parser.parse_args(argv)
    site = args.site or os.environ.get("FLOODS_SITE", "porto_alegre")
    try:
        out = run(site, do_idw=not args.no_idw, write_qa=not args.no_qa)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"\nDone. Outputs in: {out}")
    print(
        "Next: python transformation/flood_hazard/flood_hazard_publish.py "
        f"--site {site}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
