#!/usr/bin/env python3
"""Apply regional (state) GFD robust norms to city flood event-count GeoTIFFs.

Does not re-run GEE. Reads existing raw ``gfd_count`` under the city input dir,
scales with ``p95`` / log ``vmin``/``vmax`` from regional stats, and writes a
``*_norm_*_regional.tif`` sibling for the dual-product regional flood score.

City ``*_norm_*.tif`` and fixed-threshold layers (JRC / Aqueduct / GFPLAIN) are
left untouched.

Example:
  python transformation/flood_hazard/apply_regional_flood_norms.py \\
    --site rochester --region minnesota
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

FLOOD_HAZARD_ROOT = Path(__file__).resolve().parent
TRANSFORM = FLOOD_HAZARD_ROOT.parent
REGIONS = TRANSFORM / "_shared" / "regions"
if str(FLOOD_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(FLOOD_HAZARD_ROOT))
if str(REGIONS) not in sys.path:
    sys.path.insert(0, str(REGIONS))

from norm_stats import layer_gfd_robust_params, load_norm_stats  # noqa: E402
from site_config import load_site_config  # noqa: E402


def regional_gfd_norm_filename(count_name: str) -> str:
    """Derive regional norm filename from raw GFD count GeoTIFF name."""
    stem = Path(count_name).stem
    # gfd_flood_event_count_no_perm_water_{site} → …_norm_{site}_regional
    if "_norm_" in stem:
        stem = f"{stem}_regional"
    elif stem.endswith("_norm"):
        stem = f"{stem}_regional"
    else:
        # insert _norm before trailing _{site} when possible
        parts = stem.rsplit("_", 1)
        if len(parts) == 2:
            stem = f"{parts[0]}_norm_{parts[1]}_regional"
        else:
            stem = f"{stem}_norm_regional"
    return f"{stem}.tif"


def apply_gfd_robust_tif(
    src_path: Path,
    dst_path: Path,
    *,
    p95: float,
    vmin: float,
    vmax: float,
) -> dict[str, Any]:
    """Zeros stay 0; positives: min(count,p95) → log1p → min–max to [0,1]."""
    with rasterio.open(src_path) as src:
        data = src.read(1).astype(np.float64)
        profile = src.profile.copy()
        nodata = src.nodata

    if nodata is not None:
        invalid = (data == nodata) | ~np.isfinite(data)
    else:
        invalid = ~np.isfinite(data)

    pos = (~invalid) & (data > 0)
    out = np.zeros(data.shape, dtype=np.float64)
    if pos.any():
        capped = np.minimum(data[pos], p95)
        logged = np.log1p(capped)
        den = vmax - vmin
        if den <= 1e-6:
            scaled = np.ones_like(logged)
        else:
            scaled = np.clip((logged - vmin) / den, 0.0, 1.0)
        out[pos] = scaled
    out = np.where(invalid, np.nan, out).astype(np.float32)

    profile.update(dtype="float32", count=1, nodata=np.nan, compress="lzw")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dst_path, "w", **profile) as dst:
        dst.write(out, 1)
        dst.set_band_description(1, "regional_gfd_robust_norm_0_1")
        dst.update_tags(
            normalization_domain="regional",
            p95=str(p95),
            vmin=str(vmin),
            vmax=str(vmax),
            source_count=str(src_path.name),
        )

    finite = out[np.isfinite(out)]
    return {
        "src": str(src_path),
        "dst": str(dst_path),
        "p95": p95,
        "vmin": vmin,
        "vmax": vmax,
        "n_valid": int(finite.size),
        "n_positive": int(pos.sum()),
        "out_min": float(finite.min()) if finite.size else None,
        "out_max": float(finite.max()) if finite.size else None,
    }


def run(
    site: str,
    *,
    region: str = "minnesota",
    stats_version: str = "v1",
    stats_path: Path | None = None,
) -> list[Path]:
    site_config = load_site_config(site, FLOOD_HAZARD_ROOT)
    layers = site_config.get("layers") or {}
    input_dir = Path(site_config["paths_abs"]["data_input"])
    stats = load_norm_stats(region, stats_version=stats_version, path=stats_path)
    params = layer_gfd_robust_params(stats, "gfd_event_count")
    print(
        f"Regional GFD norms ← {region} {stats.get('stats_version')} "
        f"(status={stats.get('status')}) · site={site}"
    )

    count_name = layers.get("gfd_count")
    if not count_name:
        raise KeyError(f"site layers.gfd_count missing in {site} config")
    src = input_dir / str(count_name)
    if not src.is_file():
        raise FileNotFoundError(f"Missing GFD count input: {src}")

    # Prefer sibling of city norm name if configured, else derive from count.
    city_norm = layers.get("gfd_count_norm")
    if city_norm:
        p = Path(str(city_norm))
        dst_name = f"{p.stem}_regional{p.suffix}"
    else:
        dst_name = regional_gfd_norm_filename(str(count_name))
    dst = input_dir / dst_name

    info = apply_gfd_robust_tif(
        src,
        dst,
        p95=params["p95"],
        vmin=params["vmin"],
        vmax=params["vmax"],
    )
    print(
        f"  gfd_count_norm_regional: {src.name} → {dst.name} "
        f"(p95={params['p95']:.4f}; log [{params['vmin']:.4f}, {params['vmax']:.4f}]; "
        f"out [{info['out_min']}, {info['out_max']}]; n_pos={info['n_positive']})"
    )

    meta = {
        "site_slug": site,
        "region_id": region,
        "stats_version": stats.get("stats_version"),
        "normalization_domain": region,
        "comparability": "regional",
        "layer": "gfd_event_count",
        "result": info,
    }
    meta_path = input_dir / f"regional_flood_norms_{region}.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {meta_path}")
    return [dst]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--region", default="minnesota")
    parser.add_argument("--stats-version", default="v1")
    parser.add_argument("--stats-path", default=None, help="Override stats JSON path")
    args = parser.parse_args(argv)
    try:
        paths = run(
            args.site,
            region=args.region,
            stats_version=args.stats_version,
            stats_path=Path(args.stats_path) if args.stats_path else None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("\nDone:")
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
