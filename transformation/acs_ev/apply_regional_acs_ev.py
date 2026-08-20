#!/usr/bin/env python3
"""Apply regional (state) ACS min–max constants to a city E/V GeoPackage.

Reads ``acs_ev_block_groups.gpkg`` (raw metrics already present), rescales
exposure/vulnerability with statewide vmin/vmax from regional stats, and writes
``acs_ev_block_groups_regional.gpkg`` (+ GeoJSON + choropleth QA).

City GPKG is left untouched.

Example:
  python transformation/acs_ev/apply_regional_acs_ev.py --site rochester --region minnesota
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

ACS_ROOT = Path(__file__).resolve().parent
TRANSFORM = ACS_ROOT.parent
REGIONS = TRANSFORM / "_shared" / "regions"

if str(ACS_ROOT) not in sys.path:
    sys.path.insert(0, str(ACS_ROOT))
if str(REGIONS) not in sys.path:
    sys.path.insert(0, str(REGIONS))

from extract_acs_ev import compute_scores, write_choropleth_svg  # noqa: E402
from norm_stats import layer_minmax, load_norm_stats  # noqa: E402

RAW_KEYS = [
    "population_density",
    "age_sensitive_share",
    "poverty_rate",
    "median_household_income",
    "incomplete_plumbing_share",
]


def bounds_from_stats(stats: dict[str, Any]) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for key in RAW_KEYS:
        try:
            out[key] = layer_minmax(stats, key)
        except (ValueError, KeyError) as exc:
            print(f"WARN: skip regional bound for {key}: {exc}")
    if "population_density" not in out:
        raise ValueError("population_density regional bounds are required for exposure")
    return out


def run(
    site: str,
    *,
    region: str = "minnesota",
    stats_version: str = "v1",
    stats_path: Path | None = None,
) -> Path:
    out_dir = ACS_ROOT / "sites" / site / "data" / "output"
    src = out_dir / "acs_ev_block_groups.gpkg"
    if not src.is_file():
        raise FileNotFoundError(
            f"Missing {src}. Run extract_acs_ev.py --site {site} first."
        )

    stats = load_norm_stats(region, stats_version=stats_version, path=stats_path)
    bounds = bounds_from_stats(stats)

    gdf = gpd.read_file(src)
    missing = [k for k in RAW_KEYS if k not in gdf.columns]
    if missing:
        # Recompute intermediates from ACS columns if only scores were stored oddly
        raise KeyError(f"City GPKG missing raw metric columns: {missing}")

    # Re-run scoring with regional bounds (keeps raw metrics; replaces score columns)
    # compute_scores expects ACS count columns OR already-derived shares; city gpkg
    # already has derived shares — feed a frame that still has ALAND/pop if present.
    scored = compute_scores(gdf, norm_bounds=bounds)
    scored["normalization_domain"] = region
    scored["comparability"] = "regional"
    scored["site_slug"] = site

    keep = [
        c
        for c in [
            "GEOID",
            "NAME",
            "site_slug",
            "display_name",
            "overlap_frac",
            "normalization_domain",
            "comparability",
            "total_population",
            "area_km2",
            "population_density",
            "exposure_score",
            "age_sensitive_share",
            "poverty_rate",
            "median_household_income",
            "income_vulnerability",
            "incomplete_plumbing_share",
            "vulnerability_score",
            "age_sensitive_share_score",
            "poverty_rate_score",
            "incomplete_plumbing_score",
            "geometry",
        ]
        if c in scored.columns
    ]
    export = scored[keep].copy()
    gpkg = out_dir / "acs_ev_block_groups_regional.gpkg"
    geojson = out_dir / "acs_ev_block_groups_regional.geojson"
    export.to_file(gpkg, driver="GPKG")
    export.to_file(geojson, driver="GeoJSON")
    print(f"Wrote {gpkg} ({len(export)} features)")
    print(f"Wrote {geojson}")

    display = str(export["display_name"].iloc[0]) if "display_name" in export.columns else site
    write_choropleth_svg(
        export,
        "exposure_score",
        out_dir / "map_exposure_population_density_regional.svg",
        title=f"Exposure (regional norms) — {display}",
        subtitle=f"Min–max vs {region} state domain",
    )
    write_choropleth_svg(
        export,
        "vulnerability_score",
        out_dir / "map_vulnerability_composite_regional.svg",
        title=f"Vulnerability (regional norms) — {display}",
        subtitle=f"Min–max vs {region} state domain",
    )

    e = pd.to_numeric(export["exposure_score"], errors="coerce")
    v = pd.to_numeric(export["vulnerability_score"], errors="coerce")
    meta = {
        "site_slug": site,
        "region_id": region,
        "stats_version": stats.get("stats_version"),
        "normalization_domain": region,
        "comparability": "regional",
        "source_city_gpkg": str(src),
        "outputs": {"gpkg": str(gpkg), "geojson": str(geojson)},
        "score_ranges": {
            "exposure_score": {
                "min": float(e.min(skipna=True)),
                "max": float(e.max(skipna=True)),
                "mean": float(e.mean(skipna=True)),
            },
            "vulnerability_score": {
                "min": float(v.min(skipna=True)),
                "max": float(v.max(skipna=True)),
                "mean": float(v.mean(skipna=True)),
            },
        },
        "norm_bounds": {k: {"vmin": lo, "vmax": hi} for k, (lo, hi) in bounds.items()},
    }
    meta_path = out_dir / "metadata_regional.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {meta_path}")
    print(
        f"E range [{meta['score_ranges']['exposure_score']['min']:.3f}, "
        f"{meta['score_ranges']['exposure_score']['max']:.3f}] · "
        f"V range [{meta['score_ranges']['vulnerability_score']['min']:.3f}, "
        f"{meta['score_ranges']['vulnerability_score']['max']:.3f}]"
    )
    return gpkg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True)
    parser.add_argument("--region", default="minnesota")
    parser.add_argument("--stats-version", default="v1")
    parser.add_argument("--stats-path", default=None)
    args = parser.parse_args(argv)
    try:
        run(
            args.site,
            region=args.region,
            stats_version=args.stats_version,
            stats_path=Path(args.stats_path) if args.stats_path else None,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
