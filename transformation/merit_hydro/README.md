# MERIT Hydro

Site-scoped export of MERIT Hydro layers for NBS mechanism screening and landslide inputs.

## Source

**Dataset:** MERIT Hydro v1.0.1  
**GEE:** `MERIT/Hydro/v1_0_1`  
**Bands:** `upa` (km²), `elv` (m), `hnd` (HAND — via separate CLI)

## CLIs

### UPA + ELV (D5) — NBS catalog paths

```bash
python transformation/merit_hydro/extract_merit_hydro.py --site richfield
python transformation/merit_hydro/extract_merit_hydro.py --country "United States"
python transformation/merit_hydro/extract_merit_hydro.py --site richfield --only upa
python transformation/merit_hydro/extract_merit_hydro.py --site richfield --dry-run
```

| Layer | NBS key | Output |
|-------|---------|--------|
| upa | `merit_upa` | `sites/{site}/data/output/{prefix}_merit_hydro_upa_90m.tif` |
| elv | `merit_elv` | `sites/{site}/data/output/{prefix}_merit_hydro_elv_90m.tif` |

### HAND — landslide hazard input

```bash
python transformation/merit_hydro/extract_hand.py --site richfield
```

## NBS usage

Landslide grid screening uses `merit_upa` → `upstream_area_km2_mean`. Flood/landslide also use `merit_hand` from `extract_hand.py`.

## Notebooks

Legacy Porto Alegre workflows: `release/v1/MERIT_*_90m_v1_0_1.ipynb`
