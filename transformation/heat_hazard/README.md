# heat_hazard

Applies `models/heat_hazard` to produce the Level 2 heat hazard score per city.

## Status

- PR-A: scaffold (configs, layout)
- PR-D: `site_config.py`, input styles, Porto Alegre boundary; sibling input notebooks
- **PR-E:** score notebook + model card/config wiring

## Layout

```text
heat_hazard/
├── README.md
├── site_config.py
├── heat_hazard_score.ipynb
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
| Landsat 8 LST | `../landsat_lst/release/v1/lst_landsat8.ipynb` |
| MODIS MOD11A2 LST | `../modis_lst/release/v1/MOD11A2.ipynb` |
| ERA5-Land HW frequency (optional) | `../era_land/release/v1/era5_land.ipynb` |

## Usage

```bash
export HEAT_SITE=porto_alegre
# Minnesota (JJA): plymouth | edina | richfield | rochester | apple_valley
# optional POA bairro polygons:
# export HEAT_BAIRRO_GPKG=/path/to/brazil_neighbourhood_geometries.gpkg
# 1) run input notebooks (sibling folders)
# 2) run heat_hazard_score.ipynb from this directory
```

Defaults: `models/heat_hazard/config.yaml`  
City overrides: `config/sites/{city}.yaml` (`hazard`, `publish`, optional `bairro`)

## Model

- `models/heat_hazard/model_card.md`
- `models/heat_hazard/config.yaml`
