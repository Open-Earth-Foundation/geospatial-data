# landsat_lst

Landsat 8 Collection 2 Tier 1 land surface temperature (LST) — city-clipped seasonal P90 composites for the heat hazard ensemble.

**Catalog:** `landsat8_lst_djf` (DJF product; other seasons use city site config)  
**Score consumer:** `transformation/heat_hazard/` + `models/heat_hazard/`

## Layout

```text
landsat_lst/
├── README.md
└── release/v1/
    └── lst_landsat8.ipynb
```

## Site selection

```bash
export HEAT_SITE=porto_alegre
```

Runtime paths come from `transformation/heat_hazard/config/sites/{city_slug}.yaml`. Season (`djf` / `jja`) and year range are per city.

## Usage

1. Ensure `transformation/heat_hazard/sites/{city}/boundary/site.geojson` exists.
2. Run `release/v1/lst_landsat8.ipynb` (Earth Engine + GDAL).
3. Confirm `layers.landsat_*` filenames in the city site YAML.
