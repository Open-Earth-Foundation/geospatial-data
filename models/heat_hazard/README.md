# heat_hazard

Level 2 heat hazard ensemble model.

## Status

Scaffold (PR-A). Model card and default weights land in a later PR when the score transformation moves into this repo.

## Planned contents

```text
heat_hazard/
├── README.md
├── model_card.md      # methodology (LST ensemble, season, normalization, limitations)
├── config.yaml        # default min_layers, reference layer, ERA5 toggle
└── v1/                # optional versioned artifacts
```

## Runtime site overrides

Per-city paths, season, and filenames live in:

`transformation/heat_hazard/config/sites/{city_slug}.yaml`

Default scoring parameters stay here in `config.yaml`; site YAML may override season or `include_era5` when needed.

## Related

- Layer registry: `collections/layers.yaml` → `layer_id: heat_hazard`
- Score pipeline: `transformation/heat_hazard/` (to be added)
- Upstream inputs: `landsat8_lst_*`, `modis_mod11a2_lst_*`, optional `era5_land_heatwave_freq_*`
