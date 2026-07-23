# gfplain250m

GFPLAIN250m geomorphic floodplain mask — city-clipped binary susceptibility layer for the flood hazard ensemble.

**Catalog:** `gfplain250m`  
**Score consumer:** `transformation/flood_hazard/` + `models/flood_hazard/`

## Layout

```text
gfplain250m/
├── README.md
└── release/v1/
    └── GFPLAIN250m.ipynb
```

## Site selection

```bash
export FLOODS_SITE=porto_alegre
```

Runtime paths come from `transformation/flood_hazard/config/sites/{city_slug}.yaml`.

## Usage

1. Ensure city boundary GeoJSON exists under `transformation/flood_hazard/sites/{city}/boundary/`.
2. Run `release/v1/GFPLAIN250m.ipynb`.
3. Confirm `layers.gfplain` filename in the site YAML.
