# GHSL Built-Up

Site-scoped export of GHSL built-up surface (100 m) for NBS mechanism screening.

**Release convention:** `release/{version}/` — see `transformation/README.md`.

## Source

**Dataset:** GHSL Built-Up Settlement Grid P2023A (`GHS_BUILT_S`)  
**Publisher:** JRC / GHSL  
**License:** CC BY 4.0  
**GEE:** `JRC/GHSL/P2023A/GHS_BUILT_S/{year}` · band `built_surface` (m² per 100 m cell)

## CLI (D2)

Export to paths referenced in `nbs_screening/config/sites/{city}.yaml`:

```bash
# Single MN city
python transformation/ghsl_built_up/extract_ghsl_built_up.py --site richfield

# All Minnesota cities (NBS registry)
python transformation/ghsl_built_up/extract_ghsl_built_up.py --country "United States"

# Dry-run (planned paths only)
python transformation/ghsl_built_up/extract_ghsl_built_up.py --site richfield --dry-run
```

**Output:** `sites/{site}/data/output/{prefix}_ghsl_built_up_100m.tif`  
**QA SVGs:** `sites/{site}/data/intermediate/qa_inputs/`

Requires `earthengine-api` and `geemap` for local export (default), or set `GEE_EXPORT_MODE=drive`.

## Notebook

Legacy Porto Alegre workflow (COG + tiles): `release/v1/GHSL_built_up_100m_P2023A.ipynb`

## NBS usage

Grid screening maps `imperv_pct_mean` = mean built_surface / 10 000 (flood pluvial + heat mechanisms).
