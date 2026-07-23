# flood_hazard

Level 2 flood hazard ensemble model.

## Status

Scaffold (PR-A). Model card and default weights land in a later PR when the score transformation moves into this repo.

## Planned contents

```text
flood_hazard/
├── README.md
├── model_card.md      # methodology (inputs, normalization, ensemble, IDW, limitations)
├── config.yaml        # default weights, min_layers, fluvial rules, IDW params
└── v1/                # optional versioned artifacts
```

## Runtime site overrides

Per-city paths and filenames live in:

`transformation/flood_hazard/config/sites/{city_slug}.yaml`

Default scoring parameters stay here in `config.yaml`; site YAML may override weights when needed.

## Related

- Layer registry: `collections/layers.yaml` → `layer_id: flood_hazard`
- Score pipeline: `transformation/flood_hazard/` (to be added)
- Upstream inputs: `jrc_gloflor_v2`, `global_flood_database`, `wri_aqueduct_flood`, `gfplain250m`
