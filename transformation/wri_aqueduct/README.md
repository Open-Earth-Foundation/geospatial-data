# wri_aqueduct

WRI Aqueduct Flood Hazard Maps v2 — city-clipped river RP100 depth (and normalized companion) for the flood hazard ensemble.

**Catalog:** `wri_aqueduct_flood`  
**Score consumer:** `transformation/flood_hazard/` + `models/flood_hazard/`

## Layout

```text
wri_aqueduct/
├── README.md
└── release/v1/
    └── WRI_aqueduct.ipynb
```

## Site selection

City configs and runtime paths live under the score transformation (not here):

```bash
export FLOODS_SITE=porto_alegre
```

Notebooks resolve `transformation/flood_hazard/config/sites/{city_slug}.yaml` and write GeoTIFFs / tiles under:

`transformation/flood_hazard/sites/{city_slug}/data/` and `.../out/`.

## Usage

1. Ensure `transformation/flood_hazard/sites/{city}/boundary/site.geojson` exists.
2. From `release/v1/`, run `WRI_aqueduct.ipynb` (Earth Engine + GDAL).
3. Confirm outputs match filenames in the city site YAML (`layers.aqueduct_*`).
