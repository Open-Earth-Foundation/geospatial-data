# jrc_global_river_flood_hazard_maps

JRC/CEMS GLOFAS Flood Hazard v2.1 — city-clipped RP100 depth (and impact-class normalized companion) for the flood hazard ensemble.

**Catalog:** `jrc_gloflor_v2`  
**Score consumer:** `transformation/flood_hazard/` + `models/flood_hazard/`

## Layout

```text
jrc_global_river_flood_hazard_maps/
├── README.md
└── release/v1/
    ├── jrc_global_river_flood.ipynb   # multi-city GEE + publish workflow
    └── data/                          # optional legacy POA depth GeoTIFFs
```

## Site selection

```bash
export FLOODS_SITE=porto_alegre
```

Runtime paths come from `transformation/flood_hazard/config/sites/{city_slug}.yaml`. Outputs are written under `transformation/flood_hazard/sites/{city}/`.

## Usage

1. Ensure city boundary GeoJSON exists under `transformation/flood_hazard/sites/{city}/boundary/`.
2. Run `release/v1/jrc_global_river_flood.ipynb` (Earth Engine + GDAL).
3. Confirm `layers.jrc_*` filenames in the site YAML.
