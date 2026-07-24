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
├── gee_local_export.py
├── heat_hazard_publish.py
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

### Publish to S3 + catalog

After the COG + Web Tiles cells, the notebook **Publish** cell uses
`heat_hazard_publish.py`:

| Flag | Default | Effect |
|------|---------|--------|
| `UPLOAD_TO_S3` | `False` | Upload COG + `tiles_visual` / `tiles_values` to `s3://geo-test-api/{s3_prefix}/hazard/` (bairro GPKG too if enabled) |
| `WRITE_CATALOG` | `False` | Upsert `catalog/datasets.yaml` (`poa_heat_hazard` or `{city}_heat_hazard`); dry-run prints YAML when False |

Requires AWS CLI + write access to `geo-test-api` when uploading.

## Model

- `models/heat_hazard/model_card.md`
- `models/heat_hazard/config.yaml`

## GEE export

Input notebooks write GeoTIFFs to `sites/<city>/data/input/` by default (gitignored).
Optional: `export GEE_EXPORT_MODE=drive`. Shared helper: `gee_local_export.py` (via `HEAT_SITE` site package path).

