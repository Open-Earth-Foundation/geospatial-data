# Heat NBS mechanism screening

Grid-cell dominant **heat** mechanism type (250 m). Shared config and rules live in the parent `nbs_screening/` folder.

## Layout

```
heat/sites/<city>/
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG (250 m)
└── out/            COG + tiles publish staging
```

Reference grid: OEF heat hazard 250 m. Seasonal LST inputs are configured per city in `config/sites/*.yaml`.

## CLIs

| Script | Purpose |
|--------|---------|
| `extract_mechanism_inputs.py` | All heat screening input layers (GEE extractors) |
| `compute_mechanism.py` | Grid screening + exports (H2) |
| `publish_mechanism.py` | COG/tiles + catalog (H3) |

```bash
# 1. Extract catalog input layers
python transformation/nbs_screening/heat/extract_mechanism_inputs.py --site richfield

# 2. Compute mechanism grid
python transformation/nbs_screening/heat/compute_mechanism.py --site richfield

# 3. Publish (optional)
python transformation/nbs_screening/heat/publish_mechanism.py --site richfield --build
python transformation/nbs_screening/check_nbs_layers.py --site richfield --hazard heat
```

Batch by country: `extract_mechanism_inputs.py --country "United States"`.
