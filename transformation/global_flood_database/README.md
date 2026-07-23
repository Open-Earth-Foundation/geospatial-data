# global_flood_database

Global Flood Database v1 (MODIS events) — city-clipped observed flood event count (excluding permanent water) and observed-once mask for the flood hazard ensemble.

**Catalog:** `global_flood_database`  
**Score consumer:** `transformation/flood_hazard/` + `models/flood_hazard/`

## Layout

```text
global_flood_database/
├── README.md
└── release/v1/
    └── global_flood_database.ipynb
```

## Site selection

```bash
export FLOODS_SITE=porto_alegre
```

Runtime paths come from `transformation/flood_hazard/config/sites/{city_slug}.yaml`.

## Usage

1. Ensure city boundary GeoJSON exists under `transformation/flood_hazard/sites/{city}/boundary/`.
2. Run `release/v1/global_flood_database.ipynb`.
3. Confirm `layers.gfd_*` filenames in the site YAML.
