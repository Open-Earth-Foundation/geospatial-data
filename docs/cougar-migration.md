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
| **B (current)** | Flood input transformations (`jrc_*`, `wri_aqueduct`, `global_flood_database`, `gfplain250m`) + shared `flood_hazard/site_config.py` | In progress |
| C | `flood_hazard` score notebooks + `models/flood_hazard/{model_card,config}` | Pending |
| D | Heat input transformations (`landsat_lst`, `modis_lst`, extend `era_land`) | Pending |
| E | `heat_hazard` score notebooks + `models/heat_hazard/{model_card,config}` | Pending |
| F | Minnesota **city** site YAMLs + boundaries | Pending |
| Later | Risk / E/V, landslides, NbS mechanism docs under `models/nbs_*` | Pending |

## Flood input wiring (PR-B)

Input notebooks resolve city config from `transformation/flood_hazard/` (not from each dataset folder):

```bash
export FLOODS_SITE=porto_alegre
# run notebooks under transformation/{dataset}/release/v1/
```

Outputs write to `transformation/flood_hazard/sites/{city}/data/` and `.../out/`.

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

Early multi-site experiments used a statewide `minnesota` slug. Going forward, add one config + boundary per city and publish under city-scoped S3 prefixes.
