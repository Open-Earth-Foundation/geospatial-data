# heat_hazard

Applies `models/heat_hazard` to produce the Level 2 heat hazard score per city.

## Status

- PR-A: scaffold (configs, layout)
- PR-D: `site_config.py`, input styles, Porto Alegre boundary; sibling input notebooks
- **PR-E:** score notebook + model card/config wiring
- **CLI:** `compute_heat_hazard.py` (score + SVG QA from local TIFs)

## Layout

```text
heat_hazard/
├── README.md
├── site_config.py
├── gee_local_export.py
├── input_common.py
├── extract_heat_inputs.py    # orchestrates MODIS + Landsat extracts
├── compute_heat_hazard.py    # preferred score entrypoint
├── heat_hazard_publish.py
├── heat_hazard_score.ipynb   # optional QA / legacy
├── config/sites/{city_slug}.yaml
├── sites/{city_slug}/
│   ├── boundary/site.geojson
│   ├── data/                 # gitignored
│   ├── cache/                # gitignored
│   └── out/                  # gitignored
└── styles/
```

## Upstream input notebooks

| Dataset | Notebook | CLI (preferred) |
|---------|----------|-----------------|
| Landsat 8 LST | `../landsat_lst/release/v1/lst_landsat8.ipynb` | `../landsat_lst/extract_landsat_lst.py` |
| MODIS MOD11A2 LST | `../modis_lst/release/v1/MOD11A2.ipynb` | `../modis_lst/extract_modis_lst.py` |
| ERA5-Land HW frequency (optional) | `../era_land/release/v1/era5_land.ipynb` | (notebook only for now) |

## Usage

```bash
export HEAT_SITE=plymouth
# optional: export EE_PROJECT=eecc-maureen
# optional: export GEE_EXPORT_MODE=drive

# 1) Extract MODIS + Landsat → sites/<city>/data/input/
#    (+ SVG QA under sites/<city>/data/intermediate/qa_inputs/)
python transformation/heat_hazard/extract_heat_inputs.py --site plymouth
# or one:          ... --only modis
# rebuild QA only: ... --qa-only
# skip QA:         ... --no-qa

# 2) Score + SVG QA
python transformation/heat_hazard/compute_heat_hazard.py --site plymouth

# 3) COG + tiles (+ optional S3 + catalog)
python transformation/heat_hazard/heat_hazard_publish.py --site plymouth
# upload + write catalog:
#   ... --upload --write-catalog
```

Requires Earth Engine auth. Helpers: `gee_local_export.py`, `input_common.py`.
If Drive export shards Landsat tiles, merge with:
`python transformation/landsat_lst/extract_landsat_lst.py --site plymouth --merge-shards`

### Score outputs (`sites/<city>/data/output/`)

| File | Content |
|------|---------|
| `heat_hazard_score_*.tif` | Ensemble 0–1 |
| `heat_hazard_n_layers_*.tif` | Valid layer count |
| `map_heat_hazard_score.svg` | QA grid map |
| `map_heat_hazard_n_layers.svg` | Coverage QA |
| `map_heat_input_*.svg` | Per-layer QA |
| `metadata.json` | Provenance |

Defaults: `models/heat_hazard/config.yaml`  
City overrides: `config/sites/{city}.yaml` (`hazard`, `publish`, optional `bairro`)

### Publish to S3 + catalog

```bash
python transformation/heat_hazard/heat_hazard_publish.py --site plymouth
python transformation/heat_hazard/heat_hazard_publish.py --site plymouth --upload --write-catalog
```

Builds COG + tiles under `sites/<city>/out/heat_hazard_score/`, optionally uploads to
`s3://geo-test-api/{s3_prefix}/hazard/` (bairro GPKG too if enabled), and upserts
`poa_heat_hazard` / `{city}_heat_hazard` in `catalog/datasets.yaml`.

| Flag | Default | Effect |
|------|---------|--------|
| `--build` | on | Build COG + tiles from score |
| `--no-build` | | Skip build; use existing `out/` |
| `--upload` | off | Upload to S3 |
| `--write-catalog` | off | Write catalog (default: dry-run print) |

Requires GDAL CLI for `--build`; AWS CLI + write access to `geo-test-api` when uploading.

## Model

- `models/heat_hazard/model_card.md`
- `models/heat_hazard/config.yaml`

## GEE export

Input notebooks write GeoTIFFs to `sites/<city>/data/input/` by default (gitignored).
Optional: `export GEE_EXPORT_MODE=drive`. Shared helper: `gee_local_export.py` (via `HEAT_SITE` site package path).

