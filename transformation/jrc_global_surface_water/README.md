# JRC Global Surface Water

Site-scoped export of JRC GSW v1.4 layers for NBS flood mechanism screening.

## Source

**Dataset:** JRC Global Surface Water v1.4  
**GEE:** `JRC/GSW1_4/GlobalSurfaceWater`  
**Bands:** `occurrence` (%), `seasonality` (months 0–12), `transition` (class 0–10)

## CLI (D4)

Export to paths referenced in `nbs_screening/config/sites/{city}.yaml`:

```bash
# Single MN city (all three layers)
python transformation/jrc_global_surface_water/extract_gsw.py --site richfield

# All Minnesota cities
python transformation/jrc_global_surface_water/extract_gsw.py --country "United States"

# Occurrence + seasonality only (grid-critical for flood mechanism)
python transformation/jrc_global_surface_water/extract_gsw.py --site richfield --only occurrence,seasonality

# Dry-run
python transformation/jrc_global_surface_water/extract_gsw.py --site richfield --dry-run
```

**Outputs**

| Layer | NBS catalog key | Path |
|-------|-----------------|------|
| occurrence | `jrc_surface_water_occurrence` | `sites/{site}/data/output/{prefix}_gsw_occurrence_30m.tif` |
| seasonality | `jrc_surface_water_seasonality` | `.../{prefix}_gsw_seasonality_30m.tif` |
| transition | `jrc_surface_water_transition` | `.../{prefix}_gsw_transition_30m.tif` |

**QA SVGs:** `sites/{site}/data/intermediate/qa_inputs/`

## NBS usage

Flood low-lying mechanism uses `surface_water_occurrence_mean` (≥ 10%) and `surface_water_seasonality_mean` (≥ 1 month). Transition supports open-water masking when enabled.

## Notebooks

Legacy Porto Alegre workflows: `release/v1/GSW_*_30m_v1_4.ipynb`
