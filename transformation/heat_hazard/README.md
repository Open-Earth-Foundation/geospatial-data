# heat_hazard

Transformation that applies `models/heat_hazard` to produce the Level 2 heat hazard score per city.

Input-layer notebooks live in sibling dataset folders and share this folder’s city configs via `site_config.py`.

## Status

- PR-A: scaffold (configs, layout)
- **PR-D:** `site_config.py`, input styles, Porto Alegre boundary; sibling input notebooks
- PR-E (next): score notebook + `models/heat_hazard/{model_card,config}`

## Layout

```text
heat_hazard/
├── README.md
├── site_config.py
├── config/sites/{city_slug}.yaml
├── sites/{city_slug}/
│   ├── boundary/site.geojson
│   ├── data/                 # gitignored
│   ├── cache/                # gitignored
│   └── out/                  # gitignored
└── styles/
```

## Upstream input notebooks (PR-D)

| Dataset | Notebook |
|---------|----------|
| Landsat 8 LST | `../landsat_lst/release/v1/lst_landsat8.ipynb` |
| MODIS MOD11A2 LST | `../modis_lst/release/v1/MOD11A2.ipynb` |
| ERA5-Land HW frequency (optional) | `../era_land/release/v1/era5_land.ipynb` |

## Site selection

```bash
export HEAT_SITE=porto_alegre
```

Use city-level slugs only. Season (`djf` / `jja`) is configured per city YAML.

## Model

Default weights and methodology: `models/heat_hazard/` (model card lands in PR-E).
