# flood_hazard

Applies `models/flood_hazard` to produce the Level 2 flood hazard score per city.

## Status

- PR-A: scaffold (configs, layout)
- PR-B: `site_config.py`, input-layer styles, Porto Alegre boundary; sibling input notebooks
- **PR-C:** score notebook + model card/config wiring

## Layout

```text
flood_hazard/
├── README.md
├── site_config.py
├── flood_hazard_score_v2.ipynb
├── config/sites/{city_slug}.yaml
├── sites/{city_slug}/
│   ├── boundary/site.geojson
│   ├── data/                 # gitignored
│   ├── cache/                # gitignored
│   └── out/                  # gitignored
└── styles/
```

## Upstream input notebooks

| Dataset | Notebook |
|---------|----------|
| JRC GLOFLO v2.1 | `../jrc_global_river_flood_hazard_maps/release/v1/jrc_global_river_flood.ipynb` |
| WRI Aqueduct | `../wri_aqueduct/release/v1/WRI_aqueduct.ipynb` |
| Global Flood Database | `../global_flood_database/release/v1/global_flood_database.ipynb` |
| GFPLAIN250m | `../gfplain250m/release/v1/GFPLAIN250m.ipynb` |

## Usage

```bash
export FLOODS_SITE=plymouth
# Minnesota: plymouth | edina | richfield | rochester | apple_valley

# 1) Input notebooks (sibling folders) — default exports GeoTIFFs locally to
#    sites/<city>/data/input/ via geemap (no Google Drive).
#    Optional: export GEE_EXPORT_MODE=drive
# 2) flood_hazard_score_v2.ipynb from this directory
```

Local inputs/outputs under `sites/*/data/` and `sites/*/out/` are **gitignored**
(also `*.tif` globally). Helper: `gee_local_export.py`.

Defaults: `models/flood_hazard/config.yaml`  
City overrides: `config/sites/{city}.yaml` (`hazard`, `idw`)

## Model

- `models/flood_hazard/model_card.md`
- `models/flood_hazard/config.yaml`
