# flood_hazard

Transformation that applies `models/flood_hazard` to produce the Level 2 flood hazard score per city.

Input-layer notebooks live in sibling dataset folders and share this folder’s city configs via `site_config.py`.

## Status

- **PR-A:** scaffold (configs, layout)
- **PR-B:** `site_config.py`, styles for input layers, Porto Alegre boundary; input notebooks in sibling folders
- **PR-C (next):** score notebook + `models/flood_hazard/{model_card,config}`

## Layout

```text
flood_hazard/
├── README.md
├── site_config.py              # shared by flood input + score notebooks
├── config/
│   └── sites/
│       ├── README.md
│       └── {city_slug}.yaml    # one file per city
├── sites/
│   └── {city_slug}/
│       ├── boundary/site.geojson
│       ├── data/               # gitignored
│       ├── cache/              # gitignored
│       └── out/                # gitignored
└── styles/                     # color tables / value-tile templates
```

## Upstream input notebooks (PR-B)

| Dataset | Notebook |
|---------|----------|
| JRC GLOFLO v2.1 | `../jrc_global_river_flood_hazard_maps/release/v1/jrc_global_river_flood.ipynb` |
| WRI Aqueduct | `../wri_aqueduct/release/v1/WRI_aqueduct.ipynb` |
| Global Flood Database | `../global_flood_database/release/v1/global_flood_database.ipynb` |
| GFPLAIN250m | `../gfplain250m/release/v1/GFPLAIN250m.ipynb` |

## Site selection

```bash
export FLOODS_SITE=porto_alegre
```

Use city-level slugs only. Runtime GeoTIFFs are written under `sites/{city_slug}/`.

## Model

Default weights and methodology: `models/flood_hazard/` (model card lands in PR-C).
