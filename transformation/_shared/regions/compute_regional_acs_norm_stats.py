#!/usr/bin/env python3
"""Compute Minnesota statewide ACS E/V normalization constants (state boundary).

Fetches ACS 5-year block-group tables for every county in the state, joins TIGER
ALAND, builds the same intermediate metrics as ``acs_ev/extract_acs_ev.py``, and
writes vmin/vmax into the regional dual-product stats JSON.

Requires network. ``CENSUS_API_KEY`` recommended (optional but rate-limited without).

Example:
  export CENSUS_API_KEY=...
  python transformation/_shared/regions/compute_regional_acs_norm_stats.py \\
    --region minnesota --acs-year 2023
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

REGIONS = Path(__file__).resolve().parent
TRANSFORM = REGIONS.parent.parent
ACS_EV = TRANSFORM / "acs_ev"
REPO = TRANSFORM.parent

if str(ACS_EV) not in sys.path:
    sys.path.insert(0, str(ACS_EV))
if str(REGIONS) not in sys.path:
    sys.path.insert(0, str(REGIONS))

from extract_acs_ev import (  # noqa: E402
    compute_scores,
    fetch_acs_block_groups,
    fetch_tiger_block_groups,
)
from norm_stats import (  # noqa: E402
    default_stats_path,
    load_norm_stats,
    save_norm_stats,
    update_layer_stats,
)

ACS_METRIC_KEYS = [
    ("population_density", "people_per_km2"),
    ("age_sensitive_share", "share"),
    ("poverty_rate", "share"),
    ("median_household_income", "usd"),
    ("incomplete_plumbing_share", "share"),
]


def _find_tiger_zip(state_fips: str, tiger_year: int) -> Path | None:
    name = f"tl_{tiger_year}_{state_fips}_bg.zip"
    for path in (ACS_EV / "sites").glob(f"*/cache/{name}"):
        if path.is_file():
            return path
    shared = REGIONS / "minnesota" / "cache" / name
    return shared if shared.is_file() else None


def load_state_block_groups(state_fips: str, tiger_year: int, cache_dir: Path) -> gpd.GeoDataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    existing = _find_tiger_zip(state_fips, tiger_year)
    dest = cache_dir / f"tl_{tiger_year}_{state_fips}_bg.zip"
    if existing and not dest.is_file():
        # reuse city cache copy
        dest.write_bytes(existing.read_bytes())
        print(f"Reused TIGER zip from {existing}")
    bg = fetch_tiger_block_groups(state_fips, tiger_year, cache_dir)
    return bg.to_crs(4326)


def fetch_all_counties_acs(
    *,
    year: int,
    state_fips: str,
    county_fips_list: list[str],
    api_key: str,
    sleep_s: float = 0.15,
    cache_parquet: Path | None = None,
) -> pd.DataFrame:
    if cache_parquet is not None and cache_parquet.is_file():
        print(f"Loading cached ACS table: {cache_parquet}")
        if cache_parquet.suffix == ".parquet":
            return pd.read_parquet(cache_parquet)
        return pd.read_pickle(cache_parquet)

    frames: list[pd.DataFrame] = []
    for i, county in enumerate(county_fips_list, start=1):
        print(f"[{i}/{len(county_fips_list)}] ACS county {county}")
        try:
            frames.append(
                fetch_acs_block_groups(
                    year=year,
                    state_fips=state_fips,
                    county_fips=county,
                    api_key=api_key,
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  WARN county {county}: {exc}")
        if sleep_s > 0:
            time.sleep(sleep_s)
    if not frames:
        raise RuntimeError("No ACS county tables downloaded")
    out = pd.concat(frames, ignore_index=True)
    if cache_parquet is not None:
        cache_parquet.parent.mkdir(parents=True, exist_ok=True)
        try:
            out.to_parquet(cache_parquet, index=False)
        except Exception:
            alt = cache_parquet.with_suffix(".pkl")
            out.to_pickle(alt)
            cache_parquet = alt
        print(f"Cached ACS → {cache_parquet}")
    return out


def run_from_city_gpkgs(
    *,
    region_id: str = "minnesota",
    stats_version: str = "v1",
) -> Path:
    """Provisional stats from existing city ACS GPKGs (needs CENSUS_API_KEY for full state)."""
    paths = sorted((ACS_EV / "sites").glob("*/data/output/acs_ev_block_groups.gpkg"))
    if not paths:
        raise FileNotFoundError("No city acs_ev_block_groups.gpkg found under acs_ev/sites/")
    frames = []
    for path in paths:
        gdf = gpd.read_file(path)
        gdf["source_gpkg"] = str(path)
        frames.append(gdf)
        print(f"  + {path.parent.parent.parent.name}: {len(gdf)} BGs")
    pooled = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry")
    if "GEOID" in pooled.columns:
        before = len(pooled)
        pooled = pooled.drop_duplicates(subset=["GEOID"], keep="first")
        print(f"Pooled {before} → {len(pooled)} unique GEOIDs")

    stats_path = default_stats_path(region_id, stats_version)
    payload = (
        load_norm_stats(region_id, stats_version=stats_version)
        if stats_path.is_file()
        else {
            "schema_version": "1",
            "region_id": region_id,
            "stats_version": stats_version,
            "layers": {},
        }
    )
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["source_run"] = {
        "tool": "compute_regional_acs_norm_stats.py --from-city-gpkgs",
        "ee_project": None,
        "git_sha": os.environ.get("GIT_SHA"),
        "notes": (
            "PROVISIONAL: vmin/vmax from pooled city ACS GPKGs (not full state). "
            "Re-run without --from-city-gpkgs once CENSUS_API_KEY is available."
        ),
    }

    for key, unit in ACS_METRIC_KEYS:
        if key not in pooled.columns:
            print(f"WARN: missing column {key} in pooled GPKGs — skip")
            continue
        s = pd.to_numeric(pooled[key], errors="coerce")
        valid = s.dropna()
        if valid.empty:
            print(f"WARN: {key} has no finite values in city GPKGs — skip (often poverty not exported)")
            # Drop stale NaN bounds from a prior run
            layers = dict(payload.get("layers") or {})
            if key in layers:
                layers.pop(key, None)
                payload["layers"] = layers
            continue
        vmin, vmax = float(valid.min()), float(valid.max())
        update_layer_stats(
            payload,
            key,
            vmin=vmin,
            vmax=vmax,
            unit=unit,
            n_samples=int(valid.size),
            notes="Provisional multi-city pool (not full MN state boundary).",
        )
        print(f"  {key}: vmin={vmin:.6g} vmax={vmax:.6g} n={valid.size:,}")

    out = save_norm_stats(payload, stats_path)
    print(f"\nWrote {out} (status={payload.get('status')})")
    return out


def run(
    *,
    region_id: str = "minnesota",
    state_fips: str = "27",
    acs_year: int = 2023,
    tiger_year: int = 2023,
    stats_version: str = "v1",
    api_key: str | None = None,
    from_city_gpkgs: bool = False,
) -> Path:
    if from_city_gpkgs:
        return run_from_city_gpkgs(region_id=region_id, stats_version=stats_version)

    api_key = api_key if api_key is not None else os.environ.get("CENSUS_API_KEY", "")
    if not api_key:
        raise SystemExit(
            "CENSUS_API_KEY is required for statewide ACS stats "
            "(Census API returns missing_key). "
            "Export CENSUS_API_KEY=... or pass --from-city-gpkgs for a provisional pool."
        )
    cache_dir = REGIONS / region_id / "cache" / "acs"
    bg = load_state_block_groups(state_fips, tiger_year, cache_dir)
    counties = sorted({str(c).zfill(3) for c in bg["COUNTYFP"].astype(str)})
    print(f"State {state_fips}: {len(bg):,} block groups · {len(counties)} counties")

    acs_cache = cache_dir / f"acs{acs_year}_bg_state{state_fips}.parquet"
    acs = fetch_all_counties_acs(
        year=acs_year,
        state_fips=state_fips,
        county_fips_list=counties,
        api_key=api_key,
        cache_parquet=acs_cache,
    )
    merged = bg.merge(acs, on="GEOID", how="left", suffixes=("", "_acs"))
    scored = compute_scores(merged)

    # Quick diagnostics for empty vulnerability components
    for col in ("poverty_universe", "poverty_count", "poverty_rate"):
        if col in scored.columns:
            n = int(pd.to_numeric(scored[col], errors="coerce").notna().sum())
            print(f"diag {col}: non-null={n:,} / {len(scored):,}")

    stats_path = default_stats_path(region_id, stats_version)
    if stats_path.is_file():
        payload = load_norm_stats(region_id, stats_version=stats_version)
    else:
        payload = {
            "schema_version": "1",
            "region_id": region_id,
            "stats_version": stats_version,
            "layers": {},
            "roi": {
                "type": "state_boundary",
                "id": f"us-state-fips-{state_fips}",
                "display_name": "State of Minnesota",
                "gee_asset": "TIGER/2018/States",
            },
        }

    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    payload["source_run"] = {
        "tool": "compute_regional_acs_norm_stats.py",
        "ee_project": None,
        "git_sha": os.environ.get("GIT_SHA"),
        "notes": f"ACS {acs_year} 5-year block groups over all MN counties; TIGER {tiger_year}.",
    }

    for key, unit in ACS_METRIC_KEYS:
        if key not in scored.columns:
            print(f"WARN: missing {key} after scoring — skip")
            continue
        s = pd.to_numeric(scored[key], errors="coerce")
        valid = s.dropna()
        if valid.empty:
            print(f"WARN: {key} has no finite values statewide — skip")
            layers = dict(payload.get("layers") or {})
            layers.pop(key, None)
            payload["layers"] = layers
            continue
        vmin, vmax = float(valid.min()), float(valid.max())
        update_layer_stats(
            payload,
            key,
            vmin=vmin,
            vmax=vmax,
            unit=unit,
            n_samples=int(valid.size),
            period=str(acs_year),
            notes="Statewide ACS block groups (state boundary), not city AOI.",
        )
        print(f"  {key}: vmin={vmin:.6g} vmax={vmax:.6g} n={valid.size:,}")

    out = save_norm_stats(payload, stats_path)
    print(f"\nWrote {out} (status={payload.get('status')})")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="minnesota")
    parser.add_argument("--state-fips", default="27")
    parser.add_argument("--acs-year", type=int, default=2023)
    parser.add_argument("--tiger-year", type=int, default=2023)
    parser.add_argument("--stats-version", default="v1")
    parser.add_argument(
        "--from-city-gpkgs",
        action="store_true",
        help="Provisional: pool existing city ACS GPKGs instead of statewide Census API",
    )
    args = parser.parse_args(argv)
    try:
        run(
            region_id=args.region,
            state_fips=args.state_fips,
            acs_year=args.acs_year,
            tiger_year=args.tiger_year,
            stats_version=args.stats_version,
            from_city_gpkgs=args.from_city_gpkgs,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
