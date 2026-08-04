# Flood NBS mechanism screening

Grid-cell dominant **flood** mechanism type (250 m). Shared config and rules live in the parent `nbs_screening/` folder.

## Layout

```
flood/sites/<city>/
├── data/input/     OSM waterways (extract_osm_rivers.py)
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG
└── out/            COG + tiles publish staging
```

Pre-N9 paths (`sites/<city>/data/…`, `sites/<city>/floods/…`) still resolve for reads when N10 data is absent.

## CLIs

| Script | Purpose |
|--------|---------|
| `compute_mechanism.py` | Grid screening + exports (N2) |
| `publish_mechanism.py` | COG/tiles + catalog (N3) |
| `extract_osm_rivers.py` | OSM waterways for riverine proxy (N4) |
| `batch_mechanism.py` | Multi-city rivers → compute → publish (N5) |
| `run_pipeline.py` | End-to-end DEM + rivers + mechanism (N7) |

```bash
python transformation/nbs_screening/flood/compute_mechanism.py --site richfield
python transformation/nbs_screening/flood/run_pipeline.py --site richfield --publish-dem
python transformation/nbs_screening/flood/batch_mechanism.py --country "United States"
```

Minnesota cohort: `flood/batch_mn_mechanism.py` · full pipeline: `flood/run_mn_pipeline.py`.

Deprecated shims: `floods/` re-execs matching `flood/` scripts (remove after one release).
