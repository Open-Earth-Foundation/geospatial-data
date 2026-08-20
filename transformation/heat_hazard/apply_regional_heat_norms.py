#!/usr/bin/env python3
"""Apply regional (state) min–max constants to city heat P90 GeoTIFFs.

Does not re-run GEE. Reads existing ``*_p90_*.tif`` under the city input dir,
scales with constants from ``cache/regions/{region}/normalization/vN/``, and
writes ``*_norm_*_regional.tif`` siblings for the dual-product regional heat score.

City ``*_norm_*.tif`` files are left untouched.

Example:
  python transformation/heat_hazard/apply_regional_heat_norms.py \\
    --site rochester --region minnesota
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

HEAT_HAZARD_ROOT = Path(__file__).resolve().parent
TRANSFORM = HEAT_HAZARD_ROOT.parent
REGIONS = TRANSFORM / "_shared" / "regions"
if str(HEAT_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(HEAT_HAZARD_ROOT))
if str(REGIONS) not in sys.path:
    sys.path.insert(0, str(REGIONS))

from norm_stats import layer_minmax, load_norm_stats  # noqa: E402
from site_config import load_site_config  # noqa: E402

# (p90 layer key in site yaml, stats layer key, output norm layer key)
HEAT_REGIONAL_MAP: list[tuple[str, str, str]] = [
    ("landsat_p90", "landsat_p90", "landsat_norm_regional"),
    ("modis_day_p90", "modis_day_p90", "modis_day_norm_regional"),
    ("modis_night_p90", "modis_night_p90", "modis_night_norm_regional"),
]


def regional_norm_filename(p90_name: str) -> str:
    """Derive regional norm filename from a P90 GeoTIFF name."""
    stem = Path(p90_name).stem
    # lst_lc08_p90_jja_... → lst_lc08_norm_regional_jja_...
    if "_p90_" in stem:
        stem = stem.replace("_p90_", "_norm_regional_", 1)
    elif stem.endswith("_p90"):
        stem = stem[: -len("_p90")] + "_norm_regional"
    else:
        stem = f"{stem}_norm_regional"
    return f"{stem}.tif"


def apply_minmax_tif(
    src_path: Path,
    dst_path: Path,
    *,
    vmin: float,
    vmax: float,
) -> dict[str, Any]:
    with rasterio.open(src_path) as src:
        data = src.read(1).astype(np.float64)
        profile = src.profile.copy()
        nodata = src.nodata

    if nodata is not None:
        invalid = (data == nodata) | ~np.isfinite(data)
    else:
        invalid = ~np.isfinite(data)

    scaled = (data - vmin) / (vmax - vmin)
    scaled = np.clip(scaled, 0.0, 1.0)
    scaled = np.where(invalid, np.nan, scaled).astype(np.float32)

    profile.update(dtype="float32", count=1, nodata=np.nan, compress="lzw")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dst_path, "w", **profile) as dst:
        dst.write(scaled, 1)
        dst.set_band_description(1, "regional_minmax_0_1")
        dst.update_tags(
            normalization_domain="regional",
            vmin=str(vmin),
            vmax=str(vmax),
            source_p90=str(src_path.name),
        )

    finite = scaled[np.isfinite(scaled)]
    return {
        "src": str(src_path),
        "dst": str(dst_path),
        "vmin": vmin,
        "vmax": vmax,
        "n_valid": int(finite.size),
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
    site_config = load_site_config(site, HEAT_HAZARD_ROOT)
    layers = site_config.get("layers") or {}
    input_dir = Path(site_config["paths_abs"]["data_input"])
    stats = load_norm_stats(region, stats_version=stats_version, path=stats_path)
    print(
        f"Regional norms ← {region} {stats.get('stats_version')} "
        f"(status={stats.get('status')}) · site={site}"
    )

    written: list[Path] = []
    report: list[dict[str, Any]] = []
    for p90_key, stats_key, out_key in HEAT_REGIONAL_MAP:
        p90_name = layers.get(p90_key)
        if not p90_name:
            raise KeyError(f"site layers.{p90_key} missing in {site} config")
        src = input_dir / str(p90_name)
        if not src.is_file():
            raise FileNotFoundError(f"Missing P90 input: {src}")
        vmin, vmax = layer_minmax(stats, stats_key)
        dst_name = regional_norm_filename(str(p90_name))
        dst = input_dir / dst_name
        info = apply_minmax_tif(src, dst, vmin=vmin, vmax=vmax)
        info["layer_key"] = out_key
        info["stats_key"] = stats_key
        report.append(info)
        written.append(dst)
        print(
            f"  {out_key}: {src.name} → {dst.name} "
            f"(state vmin={vmin:.4f} vmax={vmax:.4f}; "
            f"out [{info['out_min']:.3f}, {info['out_max']:.3f}])"
        )

    meta = {
        "site_slug": site,
        "region_id": region,
        "stats_version": stats.get("stats_version"),
        "normalization_domain": region,
        "comparability": "regional",
        "layers": report,
    }
    meta_path = input_dir / f"regional_heat_norms_{region}.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {meta_path}")
    return written


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
