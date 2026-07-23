# modis_lst

MODIS Terra MOD11A2 daytime and nighttime LST — city-clipped seasonal P90 composites for the heat hazard ensemble.

**Catalog:** `modis_mod11a2_lst_djf`  
**Score consumer:** `transformation/heat_hazard/` + `models/heat_hazard/`

## Layout

```text
modis_lst/
├── README.md
└── release/v1/
    └── MOD11A2.ipynb
```

## Site selection

```bash
export HEAT_SITE=porto_alegre
```

Runtime paths come from `transformation/heat_hazard/config/sites/{city_slug}.yaml`.

## Usage

1. Ensure city boundary GeoJSON exists under `transformation/heat_hazard/sites/{city}/boundary/`.
2. Run `release/v1/MOD11A2.ipynb`.
3. Confirm `layers.modis_*` filenames in the site YAML.
