# Heat NBS mechanism screening

Placeholder for hazard-specific CLIs (H1–H4). Shared screening logic already exists in `grid_screening.py` (POA exports); multi-city compute/publish/batch will land here.

## Planned layout

```
heat/sites/<city>/
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG (250 m)
└── out/            COG + tiles publish staging
```

Reference grid: OEF heat hazard 250 m. Seasonal LST inputs are configured per city in `config/sites/*.yaml`.
