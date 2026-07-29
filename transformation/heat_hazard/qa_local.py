"""Local QA maps/histograms for heat input GeoTIFFs (post-export checks)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import rasterio


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


def read_band(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float64")
        nodata = src.nodata
        if nodata is not None and np.isfinite(nodata):
            arr = np.where(arr == nodata, np.nan, arr)
        meta = {
            "crs": str(src.crs),
            "shape": arr.shape,
            "res": src.res,
            "nodata": nodata,
        }
    return arr, meta


def downsample_for_map(arr: np.ndarray, max_side: int = 200) -> np.ndarray:
    a = np.asarray(arr, dtype="float64")
    nrows, ncols = a.shape
    if max(nrows, ncols) <= max_side:
        return a
    factor = int(math.ceil(max(nrows, ncols) / max_side))
    new_r = nrows // factor
    new_c = ncols // factor
    if new_r < 1 or new_c < 1:
        return a
    trimmed = a[: new_r * factor, : new_c * factor]
    reshaped = trimmed.reshape(new_r, factor, new_c, factor)
    with np.errstate(all="ignore"):
        out = np.nanmean(reshaped, axis=(1, 3))
    return out


def print_raster_stats(arr: np.ndarray, *, label: str, percentiles: Sequence[float] | None = None) -> dict[str, float]:
    finite = arr[np.isfinite(arr)]
    stats: dict[str, float] = {"n_finite": float(finite.size), "n_total": float(arr.size)}
    if finite.size == 0:
        print(f"QA {label}: no finite pixels")
        return stats
    stats.update(
        {
            "min": float(np.min(finite)),
            "max": float(np.max(finite)),
            "mean": float(np.mean(finite)),
        }
    )
    pcts = list(percentiles or (10, 25, 50, 75, 90, 95, 99))
    for p in pcts:
        stats[f"p{int(p)}"] = float(np.percentile(finite, p))
    print(
        f"QA {label}: n={int(finite.size):,} / {arr.size:,} "
        f"min={stats['min']:.4g} mean={stats['mean']:.4g} max={stats['max']:.4g}"
    )
    print("  percentiles: " + ", ".join(f"p{int(p)}={stats[f'p{int(p)}']:.4g}" for p in pcts))
    return stats


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
    legend_label: str = "value",
    max_side: int = 200,
) -> None:
    a = downsample_for_map(arr, max_side=max_side)
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
            f'font-size="11">{val:.3g}</text>'
        )
    parts.append("</svg>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote map: {out_path}")


def write_histogram_svg(
    values: np.ndarray,
    out_path: Path,
    *,
    title: str,
    subtitle: str = "",
    xlabel: str = "value",
    bins: int = 40,
    width: int = 900,
    height: int = 420,
    vlines: Sequence[float] | None = None,
) -> None:
    vals = np.asarray(values, dtype="float64")
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        print(f"Skip hist (no values): {out_path.name}")
        return
    counts, edges = np.histogram(vals, bins=bins)
    max_c = int(counts.max()) if counts.size else 1
    margin_l, margin_r, margin_t, margin_b = 60, 30, 70, 50
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
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
    parts.append(
        f'<line x1="{margin_l}" y1="{margin_t}" x2="{margin_l}" y2="{margin_t + plot_h}" '
        f'stroke="#333" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{margin_l}" y1="{margin_t + plot_h}" x2="{margin_l + plot_w}" '
        f'y2="{margin_t + plot_h}" stroke="#333" stroke-width="1"/>'
    )
    n_bins = len(counts)
    bar_w = plot_w / max(n_bins, 1)
    for i, c in enumerate(counts):
        h = 0 if max_c == 0 else (c / max_c) * plot_h
        x = margin_l + i * bar_w
        y = margin_t + plot_h - h
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(bar_w - 1, 0.5):.2f}" height="{h:.2f}" '
            f'fill="#c45c26" stroke="none"/>'
        )
    if vlines:
        xmin, xmax = float(edges[0]), float(edges[-1])
        span = xmax - xmin if xmax > xmin else 1.0
        for xv in vlines:
            if xv < xmin or xv > xmax:
                continue
            px = margin_l + (xv - xmin) / span * plot_w
            parts.append(
                f'<line x1="{px:.2f}" y1="{margin_t}" x2="{px:.2f}" y2="{margin_t + plot_h}" '
                f'stroke="#dc143c" stroke-width="1.5" stroke-dasharray="4 3"/>'
            )
            parts.append(
                f'<text x="{px:.2f}" y="{margin_t - 4}" font-family="Helvetica, Arial, sans-serif" '
                f'font-size="10" fill="#dc143c" text-anchor="middle">{xv:g}</text>'
            )
    parts.append(
        f'<text x="{width / 2}" y="{height - 12}" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="12" text-anchor="middle">{xlabel}</text>'
    )
    parts.append(
        f'<text x="16" y="{margin_t + plot_h / 2}" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="12" transform="rotate(-90 16,{margin_t + plot_h / 2})">count</text>'
    )
    parts.append("</svg>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote hist: {out_path}")


def qa_dir_for_site(site_config: dict[str, Any]) -> Path:
    inter = Path(site_config["paths_abs"]["data_intermediate"])
    return inter / "qa_inputs"


def _qa_temp_and_norm(
    temp_tif: Path,
    norm_tif: Path,
    site_config: dict[str, Any],
    *,
    display: str,
    prefix: str,
    temp_title: str,
) -> list[Path]:
    out_dir = qa_dir_for_site(site_config)
    outs: list[Path] = []
    temp, tmeta = read_band(temp_tif)
    norm, nmeta = read_band(norm_tif)
    print_raster_stats(temp, label=f"{prefix}_p90")
    finite = temp[np.isfinite(temp)]
    hist = out_dir / f"hist_{prefix}_p90.svg"
    write_histogram_svg(
        finite,
        hist,
        title=f"{temp_title} — {display}",
        subtitle="P90 LST (°C)",
        xlabel="°C",
    )
    outs.append(hist)
    map_t = out_dir / f"map_{prefix}_p90.svg"
    write_raster_grid_svg(
        temp,
        map_t,
        title=f"{temp_title} — {display}",
        subtitle=f"{tmeta['shape'][1]}×{tmeta['shape'][0]} · °C",
        legend_label="°C",
    )
    outs.append(map_t)

    print_raster_stats(norm, label=f"{prefix}_norm")
    nfinite = norm[np.isfinite(norm)]
    if nfinite.size:
        in01 = float(((nfinite >= -1e-3) & (nfinite <= 1 + 1e-3)).mean())
        print(f"  norm in [0,1] ≈ {100 * in01:.1f}%  (min-max ROI check)")
    map_n = out_dir / f"map_{prefix}_norm.svg"
    write_raster_grid_svg(
        norm,
        map_n,
        title=f"{prefix.upper()} norm — {display}",
        subtitle=f"{nmeta['shape'][1]}×{nmeta['shape'][0]} · 0–1",
        vmin=0.0,
        vmax=1.0,
        legend_label="0–1",
    )
    outs.append(map_n)
    return outs


def qa_modis(
    day_p90: Path,
    night_p90: Path,
    day_norm: Path,
    night_norm: Path,
    site_config: dict[str, Any],
    *,
    display: str,
) -> list[Path]:
    outs: list[Path] = []
    outs.extend(
        _qa_temp_and_norm(
            day_p90,
            day_norm,
            site_config,
            display=display,
            prefix="modis_day",
            temp_title="MODIS day LST P90",
        )
    )
    outs.extend(
        _qa_temp_and_norm(
            night_p90,
            night_norm,
            site_config,
            display=display,
            prefix="modis_night",
            temp_title="MODIS night LST P90",
        )
    )
    return outs


def qa_landsat(
    p90_tif: Path,
    obs_tif: Path,
    norm_tif: Path,
    site_config: dict[str, Any],
    *,
    display: str,
) -> list[Path]:
    out_dir = qa_dir_for_site(site_config)
    outs = _qa_temp_and_norm(
        p90_tif,
        norm_tif,
        site_config,
        display=display,
        prefix="landsat",
        temp_title="Landsat 8 LST P90",
    )
    obs, ometa = read_band(obs_tif)
    print_raster_stats(obs, label="landsat_obs_count")
    ofinite = obs[np.isfinite(obs)]
    if ofinite.size:
        print(f"  obs=0 share ≈ {100 * (ofinite <= 0).mean():.1f}%")
    hist = out_dir / "hist_landsat_obs_count.svg"
    write_histogram_svg(
        ofinite,
        hist,
        title=f"Landsat obs count — {display}",
        xlabel="clear scenes",
    )
    outs.append(hist)
    map_o = out_dir / "map_landsat_obs_count.svg"
    write_raster_grid_svg(
        obs,
        map_o,
        title=f"Landsat obs count — {display}",
        subtitle=f"{ometa['shape'][1]}×{ometa['shape'][0]}",
        legend_label="count",
    )
    outs.append(map_o)
    return outs
