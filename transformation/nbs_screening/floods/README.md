# Flood NBS mechanism screening

Grid-cell dominant **flood** mechanism type (250 m). Shared config and rules live in the parent `nbs_screening/` folder.

## Layout

```
sites/<city>/floods/
├── data/input/     OSM waterways (extract_osm_rivers.py)
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG
└── out/            COG + tiles publish staging
```

Pre-N9 flat paths (`sites/<city>/data/…`) still resolve when the hazard-scoped folder is absent.

## CLIs

| Script | Purpose |
|--------|---------|
| `compute_mechanism.py` | Grid screening + exports (N2) |
| `publish_mechanism.py` | COG/tiles + catalog (N3) |
| `extract_osm_rivers.py` | OSM waterways for riverine proxy (N4) |
| `batch_mechanism.py` | Multi-city rivers → compute → publish (N5) |
| `run_pipeline.py` | End-to-end DEM + rivers + mechanism (N7) |

```bash
python transformation/nbs_screening/floods/compute_mechanism.py --site richfield
python transformation/nbs_screening/floods/run_pipeline.py --site richfield --publish-dem
python transformation/nbs_screening/floods/batch_mechanism.py --country "United States"
```

Minnesota cohort: `floods/batch_mn_mechanism.py` · full pipeline: `floods/run_mn_pipeline.py`.
