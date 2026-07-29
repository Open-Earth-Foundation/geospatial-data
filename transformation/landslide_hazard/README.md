# Landslide hazard transformation

Multi-city landslide susceptibility score (`H`) on a 90 m grid.

## Run

```bash
export LANDSLIDES_SITE=plymouth   # or porto_alegre, edina, richfield, rochester, apple_valley
# optional: export EE_PROJECT=eecc-maureen
# optional: export GEE_EXPORT_MODE=drive

# 1) Extract all input GeoTIFFs → sites/<city>/data/input/
#    (+ SVG QA under sites/<city>/data/intermediate/qa_inputs/)
python transformation/landslide_hazard/extract_landslide_inputs.py --site plymouth
# subset:          ... --only slope,hand,clay
# rebuild QA only: ... --qa-only
# skip QA:         ... --no-qa

# 2) Score + SVG QA
python transformation/landslide_hazard/compute_landslide_hazard.py --site plymouth
#   --no-qa to skip SVG maps

# 3) COG + tiles (+ optional S3 + catalog)
python transformation/landslide_hazard/landslide_hazard_publish.py --site plymouth
# upload + write catalog:
#   ... --upload --write-catalog
```

### Per-layer extract CLIs

| Layer key | CLI |
|-----------|-----|
| `slope_deg` | `../copernicus_dem/extract_slope.py` |
| `hand` | `../merit_hydro/extract_hand.py` |
| `clay_pct` | `../soilgrids/extract_clay.py` |
| `r90p` | `../chirps_r90p/extract_chirps_r90p.py` |
| `ndvi_p10` | `../modis_ndvi/extract_ndvi_p10.py` |
| `dw_mode` | `../dynamic_world/extract_dw_mode.py` |

Legacy notebooks remain under each dataset’s `release/v1/` for interactive QA.

### Score outputs (`sites/<city>/data/output/`)

| File | Content |
|------|---------|
| `landslide_hazard_score_*_90m.tif` | Gated weighted score 0–1 |
| `map_landslide_hazard_score.svg` | QA grid map |
| `map_landslide_slope_deg.svg` | Slope QA |
| `map_landslide_{slope_risk,precip_risk,...}.svg` | Component QA |
| `metadata.json` | Provenance |

### Publish outputs (`sites/<city>/out/landslide_hazard_score/`)

| File / dir | Content |
|------------|---------|
| `landslide_hazard_score_90m_cog.tif` | Cloud-optimized float score |
| `tiles_visual/` | Colorized XYZ PNG tiles |
| `tiles_values/` | RGB-encoded value XYZ tiles |
| `landslide_hazard_90m_colorized.tif` | Intermediate color-relief |
| `landslide_hazard_90m_value_encoded_rgb.tif` | Intermediate value RGB |

S3 layout: `s3://geo-test-api/{s3_prefix}/hazard/`. Catalog id: `{site}_landslide_hazard` (`poa_landslide_hazard` for Porto Alegre).

## Layout

| Path | Role |
|------|------|
| `extract_landslide_inputs.py` | Orchestrates input extracts |
| `compute_landslide_hazard.py` | Preferred score CLI |
| `landslide_hazard_publish.py` | COG + tiles + S3 + catalog |
| `input_common.py` | ROI / EE / season helpers |
| `config/sites/{city}.yaml` | City bbox, season, filenames |
| `sites/{city}/boundary/` | Tracked city polygon |
| `sites/{city}/data|cache|out/` | Runtime (gitignored) |
| `styles/` | Color tables for publish |
| `site_config.py` | Loads city YAML + merges `models/landslide_hazard/config.yaml` |

Defaults and methodology: `models/landslide_hazard/`.

**Out of scope here:** `landslide_risk` (needs shared E/V for Minnesota).

## GEE export

Input CLIs write GeoTIFFs to `sites/<city>/data/input/` by default (gitignored).
Optional: `export GEE_EXPORT_MODE=drive`. Shared helper: `gee_local_export.py`.
