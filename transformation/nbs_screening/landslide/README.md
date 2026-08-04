# Landslide NBS mechanism screening

Grid-cell dominant **landslide** mechanism type (90 m). Shared config and rules live in the parent `nbs_screening/` folder.

## Layout

```
landslide/sites/<city>/
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG (90 m)
└── out/            COG + tiles publish staging
```

Reference grid: OEF landslide hazard 90 m (`require_positive_hazard=True`).

## CLIs

| Script | Purpose |
|--------|---------|
| `extract_mechanism_inputs.py` | All landslide screening input layers (GEE extractors) |
| `compute_mechanism.py` | Grid screening + exports (L2) |
| `publish_mechanism.py` | COG/tiles + catalog (L3) |
| `batch_mechanism.py` | Multi-city inputs → compute → publish (L4) |
| `run_pipeline.py` | End-to-end landslide orchestrator (L4) |
| `run_mn_pipeline.py` | Minnesota cohort shortcut |

```bash
# 1. Extract catalog input layers
python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --site richfield

# 2. Compute mechanism grid
python transformation/nbs_screening/landslide/compute_mechanism.py --site richfield

# 3. Full pipeline (skip inputs when layers ready)
python transformation/nbs_screening/landslide/run_pipeline.py --site richfield --skip-inputs
python transformation/nbs_screening/landslide/run_mn_pipeline.py --skip-publish
```

Batch by country: `extract_mechanism_inputs.py --country "United States"`.
