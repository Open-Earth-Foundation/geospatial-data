#!/usr/bin/env python3
"""Extract ACS block-group exposure & vulnerability for a Minnesota city.

Writes GeoPackage/GeoJSON, metadata (incl. sector tags), and SVG choropleth maps.

Example:
  export CENSUS_API_KEY=...
  python transformation/acs_ev/extract_acs_ev.py --site plymouth
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
import numpy as np
import pandas as pd

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ACS_ROOT = Path(__file__).resolve().parent

# ACS 5-year Detailed Tables used for E + V (block group).
ACS_VARS: dict[str, str] = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B17001_001E": "poverty_universe",
    "B17001_002E": "poverty_count",
    # Age: under 5
    "B01001_003E": "male_under_5",
    "B01001_027E": "female_under_5",
    # Age: 65+
    "B01001_020E": "male_65_66",
    "B01001_021E": "male_67_69",
    "B01001_022E": "male_70_74",
    "B01001_023E": "male_75_79",
    "B01001_024E": "male_80_84",
    "B01001_025E": "male_85_plus",
    "B01001_044E": "female_65_66",
    "B01001_045E": "female_67_69",
    "B01001_046E": "female_70_74",
    "B01001_047E": "female_75_79",
    "B01001_048E": "female_80_84",
    "B01001_049E": "female_85_plus",
    # Plumbing (sanitation / water proxy)
    "B25047_001E": "plumbing_universe",
    "B25047_003E": "lacking_complete_plumbing",
}

# Sector / risk applicability for scored fields (from climate_risk_indicators_by_sector.json).
SECTOR_APPLICABILITY: dict[str, list[dict[str, str]]] = {
    "exposure_score": [
        {"sector": "Hydrogeological Disasters", "risk": "Floods", "component": "Exposure", "indicator": "Population density"},
        {"sector": "Hydrogeological Disasters", "risk": "Landslides", "component": "Exposure", "indicator": "Population density"},
        {"sector": "Public Health", "risk": "Heatwaves", "component": "Exposure", "indicator": "Population density"},
        {"sector": "Energy Security", "risk": "Heatwaves", "component": "Exposure", "indicator": "Population density"},
        {"sector": "Food Security", "risk": "Floods", "component": "Exposure", "indicator": "Population density"},
        {"sector": "Water Resources", "risk": "Droughts", "component": "Exposure", "indicator": "Population density"},
    ],
    "vulnerability_score": [
        {"sector": "Hydrogeological Disasters", "risk": "Floods", "component": "Vulnerability", "indicator": "Income + Age Distribution"},
        {"sector": "Hydrogeological Disasters", "risk": "Landslides", "component": "Vulnerability", "indicator": "Income + Age Distribution"},
        {"sector": "Public Health", "risk": "Heatwaves", "component": "Vulnerability", "indicator": "Income + Age Distribution"},
        {"sector": "Energy Security", "risk": "Heatwaves", "component": "Vulnerability", "indicator": "Income (+ energy-poverty proxies later)"},
    ],
    "age_sensitive_share": [
        {"sector": "Hydrogeological Disasters", "risk": "Floods", "component": "Vulnerability", "indicator": "Age Distribution"},
        {"sector": "Hydrogeological Disasters", "risk": "Landslides", "component": "Vulnerability", "indicator": "Age Distribution"},
        {"sector": "Public Health", "risk": "Heatwaves", "component": "Vulnerability", "indicator": "Age Distribution"},
    ],
    "poverty_rate": [
        {"sector": "Hydrogeological Disasters", "risk": "Floods", "component": "Vulnerability", "indicator": "Income"},
        {"sector": "Hydrogeological Disasters", "risk": "Landslides", "component": "Vulnerability", "indicator": "Income"},
        {"sector": "Public Health", "risk": "Heatwaves", "component": "Vulnerability", "indicator": "Income"},
        {"sector": "Energy Security", "risk": "Heatwaves", "component": "Vulnerability", "indicator": "Income"},
    ],
    "income_vulnerability": [
        {"sector": "Hydrogeological Disasters", "risk": "Floods", "component": "Vulnerability", "indicator": "Income"},
        {"sector": "Hydrogeological Disasters", "risk": "Landslides", "component": "Vulnerability", "indicator": "Income"},
        {"sector": "Public Health", "risk": "Heatwaves", "component": "Vulnerability", "indicator": "Income"},
        {"sector": "Energy Security", "risk": "Heatwaves", "component": "Vulnerability", "indicator": "Income"},
    ],
    "incomplete_plumbing_share": [
        {"sector": "Water Resources", "risk": "Droughts", "component": "Vulnerability", "indicator": "Inadequate water access"},
        {"sector": "Public Health", "risk": "Diseases", "component": "Vulnerability", "indicator": "Inadequate Sanitation"},
    ],
}


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    # Minimal fallback for our small configs
    out: dict[str, Any] = {}
    current_list_key = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  - "):
            if current_list_key:
                out.setdefault(current_list_key, []).append(line[4:].strip().strip("'\""))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        if val == "":
            current_list_key = key
            out[key] = []
        else:
            if val.replace(".", "", 1).isdigit():
                out[key] = float(val) if "." in val else int(val)
            else:
                out[key] = val
    return out


def _http_get_json(url: str, timeout: int = 120) -> Any:
    req = Request(url, headers={"User-Agent": "oef-geospatial-data/acs_ev"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_download(url: str, dest: Path, timeout: int = 300) -> None:
    req = Request(url, headers={"User-Agent": "oef-geospatial-data/acs_ev"})
    with urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)


def resolve_boundary(cfg: dict[str, Any], acs_root: Path) -> Path:
    for rel in cfg.get("boundary_candidates", []):
        path = (acs_root / rel).resolve()
        if path.is_file():
            return path
    raise FileNotFoundError(
        "No city boundary found. Tried: "
        + ", ".join(str((acs_root / r).resolve()) for r in cfg.get("boundary_candidates", []))
    )


def fetch_tiger_block_groups(state_fips: str, tiger_year: int, cache_dir: Path) -> gpd.GeoDataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"tl_{tiger_year}_{state_fips}_bg.zip"
    zip_path = cache_dir / zip_name
    url = f"https://www2.census.gov/geo/tiger/TIGER{tiger_year}/BG/{zip_name}"
    if not zip_path.is_file():
        print(f"Downloading TIGER block groups: {url}")
        _http_download(url, zip_path)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        shp = next(Path(tmp).glob("*.shp"))
        gdf = gpd.read_file(shp)
    return gdf


def fetch_acs_block_groups(
    *,
    year: int,
    state_fips: str,
    county_fips: str,
    api_key: str,
) -> pd.DataFrame:
    var_list = ["NAME", *ACS_VARS.keys()]
    # Census API get= list; keep under URL limits
    params = {
        "get": ",".join(var_list),
        "for": "block group:*",
        "in": f"state:{state_fips} county:{county_fips}",
        "key": api_key,
    }
    url = f"https://api.census.gov/data/{year}/acs/acs5?{urlencode(params)}"
    print(f"Fetching ACS {year} 5-year block groups for {state_fips}-{county_fips}…")
    rows = _http_get_json(url)
    header, *body = rows
    df = pd.DataFrame(body, columns=header)
    df["GEOID"] = (
        df["state"].astype(str)
        + df["county"].astype(str)
        + df["tract"].astype(str)
        + df["block group"].astype(str)
    )
    rename = {code: name for code, name in ACS_VARS.items()}
    df = df.rename(columns=rename)
    for col in rename.values():
        df[col] = scrub_acs_value(df[col])
    return df


def minmax_01(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float)
    valid = s.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=s.index, dtype="float64")
    lo, hi = float(valid.min()), float(valid.max())
    if hi <= lo:
        out = pd.Series(np.nan, index=s.index, dtype="float64")
        out.loc[valid.index] = 0.5
        return out
    return (s - lo) / (hi - lo)


def scrub_acs_value(series: pd.Series) -> pd.Series:
    """Census ACS uses large negative sentinels (e.g. -666666666) for NA — keep as null."""
    s = pd.to_numeric(series, errors="coerce").astype(float)
    return s.mask(s < 0)


def compute_scores(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gdf.copy()
    # Land area from TIGER (m²); fall back to projected geometry area
    if "ALAND" in out.columns:
        area_m2 = pd.to_numeric(out["ALAND"], errors="coerce").astype(float)
    else:
        area_m2 = out.to_crs(3857).geometry.area

    # Scrub ACS sentinels on all numeric ACS fields present
    for col in [
        "total_population",
        "median_household_income",
        "poverty_universe",
        "poverty_count",
        "male_under_5",
        "female_under_5",
        "male_65_66",
        "male_67_69",
        "male_70_74",
        "male_75_79",
        "male_80_84",
        "male_85_plus",
        "female_65_66",
        "female_67_69",
        "female_70_74",
        "female_75_79",
        "female_80_84",
        "female_85_plus",
        "plumbing_universe",
        "lacking_complete_plumbing",
    ]:
        if col in out.columns:
            out[col] = scrub_acs_value(out[col])

    pop = out["total_population"]
    has_pop = pop.notna() & (pop > 0)

    out["area_km2"] = area_m2 / 1_000_000.0
    # No population → null density (not 0): avoids implying "no exposure"
    out["population_density"] = (pop / out["area_km2"].where(out["area_km2"] > 0)).where(has_pop)

    if all(
        c in out.columns
        for c in ("male_under_5", "female_under_5", "male_65_66", "female_65_66")
    ):
        under5 = out["male_under_5"].fillna(0) + out["female_under_5"].fillna(0)
        age65 = (
            out["male_65_66"].fillna(0)
            + out["male_67_69"].fillna(0)
            + out["male_70_74"].fillna(0)
            + out["male_75_79"].fillna(0)
            + out["male_80_84"].fillna(0)
            + out["male_85_plus"].fillna(0)
            + out["female_65_66"].fillna(0)
            + out["female_67_69"].fillna(0)
            + out["female_70_74"].fillna(0)
            + out["female_75_79"].fillna(0)
            + out["female_80_84"].fillna(0)
            + out["female_85_plus"].fillna(0)
        )
        out["age_sensitive_count"] = under5 + age65
        out["age_sensitive_share"] = (out["age_sensitive_count"] / pop.where(has_pop)).where(has_pop)
    elif "age_sensitive_share" in out.columns:
        out["age_sensitive_share"] = pd.to_numeric(out["age_sensitive_share"], errors="coerce").where(
            has_pop
        )
    else:
        out["age_sensitive_share"] = np.nan

    if "poverty_count" in out.columns and "poverty_universe" in out.columns:
        out["poverty_rate"] = (
            out["poverty_count"] / out["poverty_universe"].where(out["poverty_universe"] > 0)
        ).where(has_pop)
    elif "poverty_rate" in out.columns:
        out["poverty_rate"] = pd.to_numeric(out["poverty_rate"], errors="coerce").where(has_pop)
    else:
        out["poverty_rate"] = np.nan

    if "lacking_complete_plumbing" in out.columns and "plumbing_universe" in out.columns:
        out["incomplete_plumbing_share"] = (
            out["lacking_complete_plumbing"]
            / out["plumbing_universe"].where(out["plumbing_universe"] > 0)
        ).where(has_pop)
    elif "incomplete_plumbing_share" in out.columns:
        out["incomplete_plumbing_share"] = pd.to_numeric(
            out["incomplete_plumbing_share"], errors="coerce"
        ).where(has_pop)
    else:
        out["incomplete_plumbing_share"] = np.nan

    if "median_household_income" in out.columns:
        out["median_household_income"] = scrub_acs_value(out["median_household_income"]).where(
            has_pop
        )

    # Scores 0–1 within city (null stays null — never coerce missing → 0)
    out["exposure_score"] = minmax_01(out["population_density"])

    age_n = minmax_01(out["age_sensitive_share"])
    pov_n = minmax_01(out["poverty_rate"])
    # Low income → high vulnerability; missing income → null (not 1.0)
    inc_n = (1.0 - minmax_01(out["median_household_income"])).where(
        out["median_household_income"].notna()
    )
    plum_n = minmax_01(out["incomplete_plumbing_share"])
    out["income_vulnerability"] = inc_n

    v_stack = pd.concat([age_n, pov_n, inc_n, plum_n], axis=1)
    # mean of available components; if none → null (not 0)
    out["vulnerability_score"] = v_stack.mean(axis=1, skipna=True)
    out.loc[v_stack.notna().sum(axis=1) == 0, "vulnerability_score"] = np.nan
    out.loc[~has_pop, "vulnerability_score"] = np.nan
    out.loc[~has_pop, "exposure_score"] = np.nan

    out["age_sensitive_share_score"] = age_n
    out["poverty_rate_score"] = pov_n
    out["incomplete_plumbing_score"] = plum_n
    return out


def _color_ramp(t: float) -> str:
    """Yellow → orange → red for 0–1."""
    t = max(0.0, min(1.0, float(t)))
    # interpolate #f7fbff-ish low to #a50f15 high via #fdae61
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
    """SVG choropleth without matplotlib (geopandas + stdlib only)."""
    plot_gdf = gdf.to_crs(4326).copy()
    vals = pd.to_numeric(plot_gdf[column], errors="coerce")
    bounds = plot_gdf.total_bounds  # minx, miny, maxx, maxy
    minx, miny, maxx, maxy = bounds
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

    parts: list[str] = [
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
        fill = "#9e9e9e" if pd.isna(v) else _color_ramp(float(v))
        geoms = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for poly in geoms:
            if poly.geom_type != "Polygon":
                continue
            rings = [poly.exterior, *poly.interiors]
            d_bits = []
            for ring in rings:
                coords = list(ring.coords)
                if not coords:
                    continue
                x0, y0 = project(coords[0][0], coords[0][1])
                d_bits.append(f"M{x0:.2f},{y0:.2f}")
                for x, y in coords[1:]:
                    px, py = project(x, y)
                    d_bits.append(f"L{px:.2f},{py:.2f}")
                d_bits.append("Z")
            d = " ".join(d_bits)
            parts.append(
                f'<path d="{d}" fill="{fill}" stroke="#666" stroke-width="0.4" fill-opacity="0.92"/>'
            )

    # Legend
    lx = width - legend_w
    parts.append(
        f'<text x="{lx}" y="90" font-family="Helvetica, Arial, sans-serif" font-size="11">Score 0–1</text>'
    )
    for i in range(11):
        t = i / 10
        y = 100 + i * 22
        parts.append(
            f'<rect x="{lx}" y="{y}" width="18" height="18" fill="{_color_ramp(1 - t)}" stroke="#666"/>'
        )
        label = f"{1 - t:.1f}"
        parts.append(
            f'<text x="{lx + 26}" y="{y + 13}" font-family="Helvetica, Arial, sans-serif" font-size="11">{label}</text>'
        )
    # Explicit no-data swatch
    y_nd = 100 + 11 * 22 + 8
    parts.append(
        f'<rect x="{lx}" y="{y_nd}" width="18" height="18" fill="#9e9e9e" stroke="#666"/>'
    )
    parts.append(
        f'<text x="{lx + 26}" y="{y_nd + 13}" font-family="Helvetica, Arial, sans-serif" font-size="11">No data</text>'
    )

    parts.append("</svg>")
    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote map: {out_path}")


def build_sector_summary() -> dict[str, Any]:
    return {
        "note": (
            "Exposure and vulnerability scores are shared across hazards; "
            "apply the same rasters/vectors when computing flood, heat, and landslide risk."
        ),
        "fields": SECTOR_APPLICABILITY,
    }


def run(site: str, api_key: str, acs_root: Path | None = None) -> Path:
    acs_root = acs_root or ACS_ROOT
    cfg_path = acs_root / "config" / f"{site}.yaml"
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Missing site config: {cfg_path}")
    cfg = _load_yaml(cfg_path)

    state_fips = str(cfg["state_fips"]).zfill(2)
    county_fips = str(cfg["county_fips"]).zfill(3)
    acs_year = int(cfg.get("acs_year", 2023))
    tiger_year = int(cfg.get("tiger_year", 2023))
    min_overlap = float(cfg.get("min_overlap_frac", 0.05))
    display = str(cfg.get("display_name", site))

    boundary_path = resolve_boundary(cfg, acs_root)
    print(f"Boundary: {boundary_path}")
    city = gpd.read_file(boundary_path)
    if city.crs is None:
        city = city.set_crs(4326)
    city = city.to_crs(4326)

    cache_dir = acs_root / "sites" / site / "cache"
    out_dir = acs_root / "sites" / site / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    bg = fetch_tiger_block_groups(state_fips, tiger_year, cache_dir)
    bg = bg[bg["COUNTYFP"].astype(str).str.zfill(3) == county_fips].copy()
    bg = bg.to_crs(4326)

    # Keep block groups that meaningfully intersect the city
    # Overlap fractions in equal-area CRS (degree areas are misleading)
    city_ea = city.to_crs(5070)  # NAD83 / Conus Albers
    bg_ea = bg.to_crs(5070)
    if hasattr(city_ea, "union_all"):
        city_union = city_ea.union_all()
    else:
        city_union = city_ea.unary_union
    overlap = []
    for g in bg_ea.geometry:
        if g is None or g.is_empty or g.area <= 0:
            overlap.append(0.0)
        else:
            overlap.append(float(g.intersection(city_union).area / g.area))
    bg["overlap_frac"] = overlap
    bg = bg[bg["overlap_frac"] >= min_overlap].copy()
    print(f"Block groups intersecting {display}: {len(bg)}")

    acs = fetch_acs_block_groups(
        year=acs_year,
        state_fips=state_fips,
        county_fips=county_fips,
        api_key=api_key,
    )
    merged = bg.merge(acs, on="GEOID", how="left", suffixes=("", "_acs"))
    if "NAME" not in merged.columns or merged["NAME"].isna().all():
        if "NAMELSAD" in merged.columns:
            merged["NAME"] = merged["NAMELSAD"]
        elif "NAME_acs" in merged.columns:
            merged["NAME"] = merged["NAME_acs"]
    scored = compute_scores(merged)
    scored["site_slug"] = site
    scored["display_name"] = display

    # Persist
    gpkg = out_dir / "acs_ev_block_groups.gpkg"
    geojson = out_dir / "acs_ev_block_groups.geojson"
    keep_cols = [
        "GEOID",
        "NAME",
        "site_slug",
        "display_name",
        "overlap_frac",
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
    # NAME may be NAME from ACS
    if "NAME" not in scored.columns and "NAME_acs" in scored.columns:
        scored = scored.rename(columns={"NAME_acs": "NAME"})
    export = scored[[c for c in keep_cols if c in scored.columns]].copy()
    export.to_file(gpkg, driver="GPKG")
    export.to_file(geojson, driver="GeoJSON")
    print(f"Wrote {gpkg}")
    print(f"Wrote {geojson}")

    meta = {
        "site_slug": site,
        "display_name": display,
        "acs_year": acs_year,
        "acs_dataset": f"{acs_year}/acs/acs5",
        "tiger_year": tiger_year,
        "state_fips": state_fips,
        "county_fips": county_fips,
        "boundary": str(boundary_path),
        "n_block_groups": int(len(export)),
        "acs_variables": ACS_VARS,
        "score_definitions": {
            "exposure_score": "Min-max of population_density within the city (0=lowest density, 1=highest).",
            "vulnerability_score": (
                "Mean of within-city min-max: age_sensitive_share, poverty_rate, "
                "inverted median_household_income, incomplete_plumbing_share."
            ),
        },
        "sector_applicability": build_sector_summary(),
        "outputs": {
            "gpkg": str(gpkg),
            "geojson": str(geojson),
        },
    }
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {meta_path}")

    subtitle = f"{display}, MN · ACS {acs_year} 5-year · block group"
    write_choropleth_svg(
        export,
        "exposure_score",
        out_dir / "map_exposure_population_density.svg",
        title=f"Exposure — population density ({display})",
        subtitle=subtitle + " · sectors: flood, landslide, heat, drought, food",
    )
    write_choropleth_svg(
        export,
        "vulnerability_score",
        out_dir / "map_vulnerability_composite.svg",
        title=f"Vulnerability — composite ({display})",
        subtitle=subtitle + " · sectors: flood, landslide, heat, energy",
    )
    write_choropleth_svg(
        export,
        "age_sensitive_share_score",
        out_dir / "map_vulnerability_age.svg",
        title=f"Vulnerability — age-sensitive share ({display})",
        subtitle=subtitle + " · indicator: Age Distribution",
    )
    write_choropleth_svg(
        export,
        "poverty_rate_score",
        out_dir / "map_vulnerability_poverty.svg",
        title=f"Vulnerability — poverty rate ({display})",
        subtitle=subtitle + " · indicator: Income / poverty",
    )

    print("\nSector applicability (see metadata.json for full list):")
    for field, rows in SECTOR_APPLICABILITY.items():
        sectors = sorted({f"{r['sector']} / {r['risk']}" for r in rows})
        print(f"  {field}: {', '.join(sectors)}")

    return out_dir


def rescore_existing(site: str, acs_root: Path | None = None) -> Path:
    """Recompute scores/maps from an existing GeoPackage (no Census API call)."""
    acs_root = acs_root or ACS_ROOT
    cfg = _load_yaml(acs_root / "config" / f"{site}.yaml")
    display = str(cfg.get("display_name", site))
    out_dir = acs_root / "sites" / site / "data" / "output"
    gpkg = out_dir / "acs_ev_block_groups.gpkg"
    if not gpkg.is_file():
        raise FileNotFoundError(gpkg)

    gdf = gpd.read_file(gpkg)
    # Restore sentinel if it was already written as that number
    if "median_household_income" in gdf.columns:
        gdf["median_household_income"] = scrub_acs_value(gdf["median_household_income"])
    if "total_population" in gdf.columns:
        gdf["total_population"] = scrub_acs_value(gdf["total_population"])

    scored = compute_scores(gdf)
    scored["site_slug"] = site
    scored["display_name"] = display

    keep_cols = [
        "GEOID",
        "NAME",
        "site_slug",
        "display_name",
        "overlap_frac",
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
    export = scored[[c for c in keep_cols if c in scored.columns]].copy()
    export.to_file(gpkg, driver="GPKG")
    export.to_file(out_dir / "acs_ev_block_groups.geojson", driver="GeoJSON")
    print(f"Rescored and wrote {gpkg}")

    meta_path = out_dir / "metadata.json"
    meta = {}
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["null_policy"] = (
        "ACS sentinels (<0) and block groups with no population are null "
        "(not 0). Missing components do not imply low exposure/vulnerability."
    )
    meta["n_block_groups"] = int(len(export))
    meta["n_block_groups_with_population"] = int(
        (pd.to_numeric(export["total_population"], errors="coerce") > 0).sum()
    )
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    subtitle = f"{display}, MN · ACS rescored · null = no data"
    write_choropleth_svg(
        export,
        "exposure_score",
        out_dir / "map_exposure_population_density.svg",
        title=f"Exposure — population density ({display})",
        subtitle=subtitle + " · sectors: flood, landslide, heat, drought, food",
    )
    write_choropleth_svg(
        export,
        "vulnerability_score",
        out_dir / "map_vulnerability_composite.svg",
        title=f"Vulnerability — composite ({display})",
        subtitle=subtitle + " · sectors: flood, landslide, heat, energy",
    )
    write_choropleth_svg(
        export,
        "age_sensitive_share_score",
        out_dir / "map_vulnerability_age.svg",
        title=f"Vulnerability — age-sensitive share ({display})",
        subtitle=subtitle + " · indicator: Age Distribution",
    )
    write_choropleth_svg(
        export,
        "poverty_rate_score",
        out_dir / "map_vulnerability_poverty.svg",
        title=f"Vulnerability — poverty rate ({display})",
        subtitle=subtitle + " · indicator: Income / poverty",
    )
    write_choropleth_svg(
        export,
        "income_vulnerability",
        out_dir / "map_vulnerability_income.svg",
        title=f"Vulnerability — income (inverted) ({display})",
        subtitle=subtitle + " · indicator: Income",
    )
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="plymouth", help="Site slug (config/sites/{site}.yaml)")
    parser.add_argument(
        "--census-api-key",
        default=os.environ.get("CENSUS_API_KEY", ""),
        help="Census API key (or set CENSUS_API_KEY)",
    )
    parser.add_argument(
        "--rescore-existing",
        action="store_true",
        help="Recompute scores/maps from existing GeoPackage (no API key needed)",
    )
    args = parser.parse_args(argv)

    if args.rescore_existing:
        out = rescore_existing(args.site)
        print(f"\nDone (rescore). Outputs in: {out}")
        return 0

    if not args.census_api_key:
        print(
            "ERROR: Census API key required.\n"
            "  1) Sign up: https://api.census.gov/data/key_signup.html\n"
            "  2) export CENSUS_API_KEY=...\n"
            "  3) re-run this script\n"
            "Or: --rescore-existing to rebuild scores from the last GeoPackage.",
            file=sys.stderr,
        )
        return 2

    out = run(args.site, args.census_api_key)
    print(f"\nDone. Outputs in: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
