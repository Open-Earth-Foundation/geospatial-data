# flood_hazard

Level 2 flood hazard ensemble model.

## Contents

```text
flood_hazard/
├── README.md
├── model_card.md      # methodology, validation, limitations
├── config.yaml        # default weights, coverage rules, IDW params
└── v1/                # optional versioned artifacts (unused for now)
```

## Runtime site overrides

Per-city paths and filenames:

`transformation/flood_hazard/config/sites/{city_slug}.yaml`

`site_config.py` merges `config.yaml` defaults with city `hazard` / `idw` blocks (city wins).

## Pipeline

1. Build inputs (JRC, Aqueduct, GFD, GFPLAIN) via sibling `transformation/*` notebooks.
2. Run `transformation/flood_hazard/flood_hazard_score_v2.ipynb` with `FLOODS_SITE=<city>`.
3. Publish COG / tiles from the notebook; register assets in `catalog/datasets.yaml`.

## Related

- Layer registry: `collections/layers.yaml` → `layer_id: flood_hazard`
- Score notebook: `transformation/flood_hazard/flood_hazard_score_v2.ipynb`
