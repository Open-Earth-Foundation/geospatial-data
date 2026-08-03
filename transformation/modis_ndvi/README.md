# MODIS NDVI

Site-scoped export of MODIS NDVI composites for NBS mechanism screening and landslide inputs.

## Source

**Dataset:** MODIS/061/MOD13Q1  
**GEE band:** `NDVI` (scale 0.0001 → -1..1)  
**Resolution:** 250 m

## CLIs

### NDVI mean (D7) — NBS heat catalog path

```bash
python transformation/modis_ndvi/extract_ndvi_mean.py --site richfield
python transformation/modis_ndvi/extract_ndvi_mean.py --country "United States"
python transformation/modis_ndvi/extract_ndvi_mean.py --site richfield --year 2024
python transformation/modis_ndvi/extract_ndvi_mean.py --site richfield --dry-run
```

Default period: site `start_year`–`end_year` from landslide_hazard config (MN: 2015–2024).

**Output:** `sites/{site}/data/output/{prefix}_modis_ndvi_mean.tif`

### NDVI P10 — landslide hazard input

```bash
python transformation/modis_ndvi/extract_ndvi_p10.py --site richfield
```

## NBS usage

Heat grid screening uses `ndvi_mean` from the mean composite layer.

## Notebooks

Legacy Porto Alegre workflow: `release/v1/2024/transformation.ipynb`
