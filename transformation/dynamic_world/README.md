# Dynamic World

Site-scoped export of Dynamic World annual mode land-cover for NBS mechanism screening.

## Source

**Dataset:** Google Dynamic World V1  
**GEE:** `GOOGLE/DYNAMICWORLD/V1` · band `label` (0–8 land-cover classes)  
**Composite:** per-pixel mode over calendar year

## CLI (D3)

Export to paths referenced in `nbs_screening/config/sites/{city}.yaml`:

```bash
# Single MN city (10 m + 250 m + landslide input sync)
python transformation/dynamic_world/extract_dw_mode.py --site richfield

# All Minnesota cities
python transformation/dynamic_world/extract_dw_mode.py --country "United States"

# NBS rasters only (skip landslide input copy)
python transformation/dynamic_world/extract_dw_mode.py --site richfield --only mode_10m,mode_250m

# Dry-run
python transformation/dynamic_world/extract_dw_mode.py --site richfield --dry-run
```

**Outputs**

| Product | Path |
|---------|------|
| `dynamic_world` (10 m) | `sites/{site}/data/output/{prefix}_dynamicworld_{year}.tif` |
| `dynamic_world_mode_250m` | `sites/{site}/data/output/{prefix}_dw_mode_250m_{year}.tif` |
| landslide input | `landslide_hazard/sites/{site}/data/input/{prefix}_dw_mode_{year}.tif` |

**QA SVGs:** `sites/{site}/data/intermediate/qa_inputs/`

Requires `earthengine-api` and `geemap` for local export (default), or set `GEE_EXPORT_MODE=drive`.

## NBS usage

Grid screening uses `dynamic_world_mode_250m` for `dw_built_pct_mean` (flood pluvial + landslide mechanisms).

## Notebooks

Legacy workflows: `dynamic_world_10m_v1.ipynb`, `release/v1/dynamic_world_landslide.ipynb`
