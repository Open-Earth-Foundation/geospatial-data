# Landslide NBS mechanism screening

Placeholder for hazard-specific CLIs (L1–L4). Shared screening logic already exists in `grid_screening.py` (POA exports); multi-city compute/publish/batch will land here.

## Planned layout

```
landslide/sites/<city>/
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG (90 m)
└── out/            COG + tiles publish staging
```

Reference grid: OEF landslide hazard 90 m (`require_positive_hazard=True`).

```bash
python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --site richfield
python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --country "United States"
```
