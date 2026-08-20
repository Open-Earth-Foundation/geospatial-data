#!/usr/bin/env python3
"""Apply regional (state) min–max constants to city landslide R90p / NDVI GeoTIFFs.

Does not re-run GEE. Reads raw ``r90p`` / ``ndvi_p10`` under the city input dir,
scales with constants from regional stats, and writes ``*_norm_regional.tif``
siblings for inspection / dual-product QA.

City raw inputs and fixed layers (slope / clay / HAND / DW) are left untouched.
``compute_landslide_hazard.py --product regional`` applies the same constants at
score time (fill + min–max); these TIFs are optional diagnostics.

Example:
  python transformation/landslide_hazard/apply_regional_landslide_norms.py \\
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

LANDSLIDE_HAZARD_ROOT = Path(__file__).resolve().parent
TRANSFORM = LANDSLIDE_HAZARD_ROOT.parent
REGIONS = TRANSFORM / "_shared" / "regions"
if str(LANDSLIDE_HAZARD_ROOT) not in sys.path:
    sys.path.insert(0, str(LANDSLIDE_HAZARD_ROOT))
if str(REGIONS) not in sys.path:
    sys.path.insert(0, str(REGIONS))

from norm_stats import layer_minmax, load_norm_stats  # noqa: E402
from site_config import load_site_config  # noqa: E402

# (site layers key, stats layer key)
LANDSLIDE_REGIONAL_MAP: list[tuple[str, str]] = [
    ("r90p", "r90p"),
    ("ndvi_p10", "ndvi_p10"),
]


def regional_norm_filename(raw_name: str) -> str:
    stem = Path(raw_name).stem
    return f"{stem}_norm_regional.tif"


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
            source=str(src_path.name),
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
    site_config = load_site_config(site, LANDSLIDE_HAZARD_ROOT)
    layers = site_config.get("layers") or {}
    input_dir = Path(site_config["paths_abs"]["data_input"])
    stats = load_norm_stats(region, stats_version=stats_version, path=stats_path)
    print(
        f"Regional landslide norms ← {region} {stats.get('stats_version')} "
        f"(status={stats.get('status')}) · site={site}"
    )

    written: list[Path] = []
    report: list[dict[str, Any]] = []
    for layer_key, stats_key in LANDSLIDE_REGIONAL_MAP:
        raw_name = layers.get(layer_key)
        if not raw_name:
            raise KeyError(f"site layers.{layer_key} missing in {site} config")
        src = input_dir / str(raw_name)
        if not src.is_file():
            raise FileNotFoundError(f"Missing input: {src}")
        vmin, vmax = layer_minmax(stats, stats_key)
        dst = input_dir / regional_norm_filename(str(raw_name))
        info = apply_minmax_tif(src, dst, vmin=vmin, vmax=vmax)
        info["layer_key"] = layer_key
        info["stats_key"] = stats_key
        report.append(info)
        written.append(dst)
        print(
            f"  {layer_key}: {src.name} → {dst.name} "
            f"(state vmin={vmin:.4f} vmax={vmax:.4f}; "
            f"out [{info['out_min']}, {info['out_max']}])"
        )

    meta = {
        "site_slug": site,
        "region_id": region,
        "stats_version": stats.get("stats_version"),
        "normalization_domain": region,
        "comparability": "regional",
        "layers": report,
    }
    meta_path = input_dir / f"regional_landslide_norms_{region}.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {meta_path}")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--region", default="minnesota")
    parser.add_argument("--stats-version", default="v1")
    parser.add_argument("--stats-path", default=None)
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
