# Cougar → geospatial-data migration

Plan and locked decisions for moving hazard/risk/NbS calculation work into this repository.

Local sandbox under `projects/cougar` may still exist on developer machines, but **new work and catalog references must not point at that folder**. Canonical code and docs live here.

## Locked decisions

1. **Site configs** live per score transformation: `transformation/{score}/config/sites/{city_slug}.yaml`
2. **City-level slugs only** (e.g. `porto_alegre`, `minneapolis`) — not statewide AOIs such as `minnesota`
3. **NbS methodology / matrices / rules docs** live under `models/nbs_*`
4. **Do not reference** the local `projects/cougar` path from this repo going forward
5. Migrate in small PRs; start with scaffold (PR-A)

## Target layout

```text
geospatial-data/
  models/
    flood_hazard/                 # model_card.md + config.yaml
    heat_hazard/
    nbs_opportunity_zones/
    nbs_flood_mechanism_type/
    nbs_heat_mechanism_type/
    nbs_landslide_mechanism_type/
    # later: flood_risk, heat_risk, landslide_hazard, exposure_score, …
  transformation/
    flood_hazard/
      config/sites/{city_slug}.yaml
      sites/{city_slug}/          # runtime data (mostly gitignored)
    heat_hazard/
      config/sites/{city_slug}.yaml
      sites/{city_slug}/
    # later: input dataset folders (wri_aqueduct, landsat_lst, …) and other scores
  catalog/datasets.yaml           # published assets + provenance
  collections/layers.yaml         # analytical layer graph
```

### Separation of concerns

| Concern | Location |
|---------|----------|
| Methodology, default weights, thresholds | `models/{layer_id}/` |
| Executable notebooks / scripts | `transformation/` |
| Per-city paths, bbox, season, filenames | `transformation/{score}/config/sites/` |
| Published COGs / tiles | S3 + `catalog/datasets.yaml` |

## PR sequence

| PR | Scope | Status |
|----|--------|--------|
| A | Scaffold `models/*`, `transformation/{flood,heat}_hazard/config/sites/`, fix `layers.yaml` deps, this doc | Merged |
| B | Flood input transformations (`jrc_*`, `wri_aqueduct`, `global_flood_database`, `gfplain250m`) + shared `flood_hazard/site_config.py` | Merged |
| C | `flood_hazard` score notebook + `models/flood_hazard/{model_card,config}` | Merged |
| D | Heat input transformations (`landsat_lst`, `modis_lst`, extend `era_land`) + shared `heat_hazard/site_config.py` | Merged |
| E | `heat_hazard` score notebook + `models/heat_hazard/{model_card,config}` | Merged |
| **F (current)** | Minnesota **city** site YAMLs + boundaries | In progress |
| Later | Risk / E/V, landslides, NbS mechanism docs under `models/nbs_*` | Pending |

## Flood input wiring (PR-B)

Input notebooks resolve city config from `transformation/flood_hazard/` (not from each dataset folder):

```bash
export FLOODS_SITE=porto_alegre
# run notebooks under transformation/{dataset}/release/v1/
```

Outputs write to `transformation/flood_hazard/sites/{city}/data/` and `.../out/`.

## Flood score wiring (PR-C)

```bash
export FLOODS_SITE=porto_alegre
# run transformation/flood_hazard/flood_hazard_score_v2.ipynb
```

- Defaults: `models/flood_hazard/config.yaml`
- Methodology: `models/flood_hazard/model_card.md`
- `site_config.load_site_config` merges model defaults with city `hazard` / `idw` overrides

## Heat input wiring (PR-D)

```bash
export HEAT_SITE=porto_alegre
# run notebooks under transformation/{landsat_lst,modis_lst,era_land}/release/v1/
```

Outputs write to `transformation/heat_hazard/sites/{city}/data/` and `.../out/`. Season and year range come from the city YAML.

## Heat score wiring (PR-E)

```bash
export HEAT_SITE=porto_alegre
# optional: export HEAT_BAIRRO_GPKG=/path/to/bairro.gpkg
# run transformation/heat_hazard/heat_hazard_score.ipynb
```

- Defaults: `models/heat_hazard/config.yaml`
- Methodology: `models/heat_hazard/model_card.md`
- `site_config.load_site_config` merges model defaults with city `hazard` / `publish` overrides
- Bairro aggregation is optional and skipped when the neighbourhood GeoPackage is unavailable

## Layer registry alignment (PR-A)

`collections/layers.yaml` now reflects the real flood/heat ensembles:

- **flood_hazard** inputs: `jrc_gloflor_v2`, `global_flood_database`, `wri_aqueduct_flood`, `gfplain250m`
- **heat_hazard** inputs: `landsat8_lst_djf`, `modis_mod11a2_lst_djf` (ERA5 optional at site level)

Season-specific catalog IDs (e.g. JJA for northern cities) can be added when those products are registered.

## What not to commit

- `transformation/*/sites/*/cache/`
- `transformation/*/sites/*/data/`
- `transformation/*/sites/*/out/`
- GeoTIFF / tile outputs (see root `.gitignore`)
- Virtualenvs

Small city boundary GeoJSON files under `sites/{city_slug}/boundary/` may be versioned when ready.

## Minnesota note

Early multi-site experiments used a statewide `minnesota` slug. That approach is superseded by city-level configs below.

## Minnesota cities (PR-F)

Configured city-level sites (not statewide):

| site_slug | City |
|-----------|------|
| plymouth | Plymouth |
| edina | Edina |
| richfield | Richfield |
| rochester | Rochester |
| apple_valley | Apple Valley |

Boundaries: OSM administrative polygons via Nominatim, stored under
`transformation/{flood,heat}_hazard/sites/{city}/boundary/site.geojson`.

Heat season for these cities: **JJA** (2015–2024).

```bash
export FLOODS_SITE=plymouth
export HEAT_SITE=apple_valley
```
