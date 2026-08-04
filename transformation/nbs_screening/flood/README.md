# Flood NBS mechanism screening

Grid-cell dominant **flood** mechanism type (250 m). Shared config and rules live in the parent `nbs_screening/` folder.

## Layout

```
flood/sites/<city>/
├── data/input/     OSM waterways (extract_osm_rivers.py)
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG
└── out/            COG + tiles publish staging
```

## CLIs

| Script | Purpose |
|--------|---------|
| `extract_mechanism_inputs.py` | All flood screening input layers (GEE + OSM + DEM diagnostics) |
| `compute_mechanism.py` | Grid screening + exports (N2) |
| `publish_mechanism.py` | COG/tiles + catalog (N3) |
| `extract_osm_rivers.py` | OSM waterways only (N4) |
| `batch_mechanism.py` | Multi-city rivers → compute → publish (N5) |
| `run_pipeline.py` | DEM + rivers + mechanism (+ optional publish) (N7) |

```bash
# 1. Extract catalog input layers (before mechanism)
python transformation/nbs_screening/flood/extract_mechanism_inputs.py --site richfield

# 2. Compute + publish mechanism
python transformation/nbs_screening/flood/run_pipeline.py --site richfield
python transformation/nbs_screening/flood/compute_mechanism.py --site richfield
```

Minnesota cohort: `flood/batch_mn_mechanism.py` · full pipeline: `flood/run_mn_pipeline.py`.
