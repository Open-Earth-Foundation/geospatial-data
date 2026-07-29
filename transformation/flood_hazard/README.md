# flood_hazard

Applies `models/flood_hazard` to produce the Level 2 flood hazard score per city.

## Status

- PR-A: scaffold (configs, layout)
- PR-B: `site_config.py`, input-layer styles, Porto Alegre boundary; sibling input notebooks
- **PR-C:** score notebook + model card/config wiring
- **CLI:** `compute_flood_hazard.py` (score + IDW + SVG QA from local TIFs)

## Layout

```text
flood_hazard/
├── README.md
├── site_config.py
├── gee_local_export.py
├── compute_flood_hazard.py   # preferred score entrypoint
├── flood_hazard_publish.py
├── flood_hazard_score_v2.ipynb  # optional QA / legacy; use CLI for batch
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
| JRC GLOFLO v2.1 | `../jrc_global_river_flood_hazard_maps/release/v1/jrc_global_river_flood.ipynb` | `../jrc_global_river_flood_hazard_maps/extract_jrc.py` |
| WRI Aqueduct | `../wri_aqueduct/release/v1/WRI_aqueduct.ipynb` | `../wri_aqueduct/extract_aqueduct.py` |
| Global Flood Database | `../global_flood_database/release/v1/global_flood_database.ipynb` | `../global_flood_database/extract_gfd.py` |
| GFPLAIN250m | `../gfplain250m/release/v1/GFPLAIN250m.ipynb` | `../gfplain250m/extract_gfplain.py` |

## Usage

```bash
export FLOODS_SITE=plymouth
# optional: export EE_PROJECT=eecc-maureen
# optional: export GEE_EXPORT_MODE=drive   # default is local download via geemap

# 1) Extract all flood input GeoTIFFs → sites/<city>/data/input/
#    (+ SVG QA under sites/<city>/data/intermediate/qa_inputs/)
python transformation/flood_hazard/extract_flood_inputs.py --site plymouth
# or one layer:  ... --only gfplain,jrc
# rebuild QA only: ... --qa-only
# skip QA:         ... --no-qa

# 2) Score + IDW + SVG QA maps
python transformation/flood_hazard/compute_flood_hazard.py --site plymouth

# 3) COG + tiles (+ optional S3 + catalog)
python transformation/flood_hazard/flood_hazard_publish.py --site plymouth
# upload + write catalog:
#   ... --upload --write-catalog

# Optional flags for score:
#   --no-idw   skip IDW gap-fill
#   --no-qa    skip SVG maps
```

Requires Earth Engine auth (`earthengine authenticate` or `--authenticate` once).
Local inputs/outputs under `sites/*/data/` and `sites/*/out/` are **gitignored**
(also `*.tif` globally). Helpers: `gee_local_export.py`, `input_common.py`.

### Score outputs (`sites/<city>/data/output/`)

| File | Content |
|------|---------|
| `flood_hazard_score_*.tif` | Base / partial score (≥3/4 + fluvial) |
| `flood_hazard_score_strict_*.tif` | All-layer intersection |
| `flood_hazard_n_layers_used_*.tif` | Coverage count |
| `flood_hazard_score_idw_*.tif` | Distance-capped IDW fill |
| `flood_hazard_is_interpolated_*.tif` | Interp flag |
| `flood_hazard_interp_distance_m_*.tif` | Distance to donors (m) |
| `flood_hazard_score_interpolated_only_*.tif` | Interp pixels only |
| `map_flood_hazard_*.svg` | Quick QA grid maps |
| `metadata.json` | Provenance |

### Publish to S3 + catalog

```bash
python transformation/flood_hazard/flood_hazard_publish.py --site plymouth
python transformation/flood_hazard/flood_hazard_publish.py --site plymouth --upload --write-catalog
```

Builds COG + `tiles_visual` / `tiles_values` under `sites/<city>/out/flood_hazard_score_idw/`,
optionally uploads to `s3://geo-test-api/{s3_prefix}/hazard/`, and upserts
`poa_flood_hazard` / `{city}_flood_hazard` in `catalog/datasets.yaml`.

| Flag | Default | Effect |
|------|---------|--------|
| `--build` | on | Build COG + tiles from IDW score |
| `--no-build` | | Skip build; use existing `out/` |
| `--upload` | off | Upload to S3 |
| `--write-catalog` | off | Write catalog (default: dry-run print) |

Requires GDAL CLI for `--build`; AWS CLI + write access to `geo-test-api` when uploading.

Defaults: `models/flood_hazard/config.yaml`  
City overrides: `config/sites/{city}.yaml` (`hazard`, `idw`, `s3_prefix`, `required_inputs`)

## Model

- `models/flood_hazard/model_card.md`
- `models/flood_hazard/config.yaml`
