# era_land

ERA5-Land temperature-derived products.

This folder includes earlier extreme-temperature notebooks plus the multi-city heat-wave frequency workflow used as an optional heat hazard input.

**Catalog (heat-wave frequency):** `era5_land_heatwave_freq_djf`  
**Score consumer:** `transformation/heat_hazard/` (optional; `include_era5` in site config)

## Layout

```text
era_land/
├── README.md
├── extreme_temp_projections.ipynb   # legacy / related products
├── temp_extreme_final.ipynb
└── release/v1/
    └── era5_land.ipynb              # city heat-wave day frequency (multi-site)
```

## Site selection (heat-wave frequency notebook)

```bash
export HEAT_SITE=porto_alegre
```

Runtime paths come from `transformation/heat_hazard/config/sites/{city_slug}.yaml`.

## Usage

1. Ensure city boundary GeoJSON exists under `transformation/heat_hazard/sites/{city}/boundary/`.
2. Run `release/v1/era5_land.ipynb` when regional air-temperature frequency is needed.
3. Confirm `layers.era5_*` filenames in the site YAML.

Note: the operational heat hazard ensemble may exclude ERA5 at ~9 km (see site `hazard.include_era5`).
