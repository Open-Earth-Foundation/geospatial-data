# ACS exposure & vulnerability (block group)

Extract US Census **ACS 5-year** indicators at **block group** for Minnesota cities,
clip to the city boundary, score exposure / vulnerability, and write choropleth maps.

Aligned with [`docs/mn_exposure_candidates_plymouth.md`](../../docs/mn_exposure_candidates_plymouth.md)
and [`docs/climate_risk_indicators_by_sector.json`](../../docs/climate_risk_indicators_by_sector.json).

## Setup

```bash
# Free key: https://api.census.gov/data/key_signup.html
export CENSUS_API_KEY=your_key_here

# Dependencies: geopandas, pandas, requests, matplotlib, pyyaml
python transformation/acs_ev/extract_acs_ev.py --site plymouth
```

## Outputs (gitignored under `sites/<city>/data/`)

| File | Content |
|------|---------|
| `acs_ev_block_groups.gpkg` | Block groups + raw ACS + scores |
| `acs_ev_block_groups.geojson` | Same as GeoJSON |
| `metadata.json` | Provenance, variable map, sector applicability |
| `map_exposure_population_density.svg` | Exposure choropleth (density → score) |
| `map_vulnerability_composite.svg` | Composite V choropleth |
| `map_vulnerability_age.svg` | Age-sensitive share |
| `map_vulnerability_poverty.svg` | Poverty rate |

## Scores

- **Exposure (`exposure_score`)**: min–max of population density within the city (0–1).
- **Vulnerability (`vulnerability_score`)**: mean of available within-city min–max components:
  age-sensitive share, poverty rate, inverted median income, incomplete plumbing share.

**Null policy:** ACS sentinels (`< 0`, e.g. `-666666666`) and block groups with **no population**
are **null** (not 0 and not 1). Maps show gray **No data**; risk cells without E or V stay nodata.

Sector → risk tags are recorded in `metadata.json` (shared E/V across flood / heat / landslide).

```bash
# Rebuild scores/maps from the last GeoPackage without calling the Census API:
python transformation/acs_ev/extract_acs_ev.py --site plymouth --rescore-existing
```
