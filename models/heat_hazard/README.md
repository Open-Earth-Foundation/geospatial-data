# heat_hazard

Level 2 heat hazard ensemble model.

## Contents

```text
heat_hazard/
├── README.md
├── model_card.md      # methodology and limitations
├── config.yaml        # default min_layers, include_era5, weights, resolution
└── v1/                # optional versioned artifacts (unused for now)
```

## Runtime site overrides

Per-city paths, season, and filenames:

`transformation/heat_hazard/config/sites/{city_slug}.yaml`

`site_config.py` merges `config.yaml` defaults with city `hazard` / `publish` blocks (city wins).

## Pipeline

1. Build inputs (Landsat LST, MODIS LST, optional ERA5) via sibling `transformation/*` notebooks.
2. Run `transformation/heat_hazard/heat_hazard_score.ipynb` with `HEAT_SITE=<city>`.
3. Publish COG / tiles from the notebook; register assets in `catalog/datasets.yaml`.

## Related

- Layer registry: `collections/layers.yaml` → `layer_id: heat_hazard`
- Score notebook: `transformation/heat_hazard/heat_hazard_score.ipynb`
