# Landslide hazard transformation

Multi-city landslide susceptibility score (`H`) on a 90 m grid.

## Run

```bash
export LANDSLIDES_SITE=porto_alegre   # or plymouth, edina, richfield, rochester, apple_valley
# optional (POA neighbourhoods):
# export LANDSLIDE_BAIRRO_GPKG=/path/to/brazil_neighbourhood_geometries.gpkg

# 1) Inputs (GEE exports → sites/<city>/data/input/)
# transformation/copernicus_dem/release/v1/slope_from_dem.ipynb
# transformation/chirps_r90p/release/v1/chirps_r90p_climatology.ipynb
# transformation/soilgrids/release/v1/clay_soilgrids.ipynb
# transformation/modis_ndvi/release/v1/ndvi_modis_landslide.ipynb
# transformation/merit_hydro/release/v1/hand_merit_landslide.ipynb
# transformation/dynamic_world/release/v1/dynamic_world_landslide.ipynb

# 2) Score
# transformation/landslide_hazard/landslide_hazard_score.ipynb
```

## Layout

| Path | Role |
|------|------|
| `config/sites/{city}.yaml` | City bbox, season, filenames |
| `sites/{city}/boundary/` | Tracked city polygon |
| `sites/{city}/data|cache|out/` | Runtime (gitignored) |
| `styles/` | Color tables for publish |
| `site_config.py` | Loads city YAML + merges `models/landslide_hazard/config.yaml` |

Defaults and methodology: `models/landslide_hazard/`.

**Out of scope here:** `landslide_risk` (needs shared E/V for Minnesota).
