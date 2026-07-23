# NbS screening

Rule-based Nature-based Solutions site screening and dominant-mechanism layers
(flood / heat / landslide).

## Run

```bash
# From geospatial-data repo root (with deps: geopandas, rasterio, …)
python transformation/nbs_screening/run_e2e.py --hazard flood
python transformation/nbs_screening/run_e2e.py --hazard heat
python transformation/nbs_screening/run_e2e.py --hazard landslide

# Or open the site-query notebooks in transformation/nbs_screening/
```

Optional env:

| Variable | Purpose |
|----------|---------|
| `NBS_RIVERS_GEOJSON` | Local OSM rivers GeoJSON for riverine distance |
| `NBS_SAMPLE_DATA` | Directory containing `porto-alegre-rivers.json` |

## DEM diagnostics (flood low-lying)

```bash
export FLOODS_SITE=porto_alegre
# transformation/copernicus_dem/release/v1/relative_elevation_depression_from_dem.ipynb
```

Writes `relative_elevation` / `depression_mask` / `depression_depth` into
`transformation/flood_hazard/sites/<city>/data/output/`.

## Docs

See `docs/` in this folder and `models/nbs_*_mechanism_type/model_card.md`.

## Multi-city

Mechanism **rules** are city-agnostic. Catalog COG URLs in `catalog_layers.py` still
point at Porto Alegre S3 products. For new cities, generate local hazards + DEM
diagnostics first; wire city-specific catalog URLs in a follow-up.
