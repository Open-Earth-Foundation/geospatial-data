# NbS screening

Rule-based Nature-based Solutions **grid** screening and dominant-mechanism layers
(flood / heat / landslide). The primary unit is the **250 m cell**; bairro/AOI queries
are legacy and out of scope for the multi-city pipeline.

## Run (POA defaults)

```bash
# From geospatial-data repo root (with deps: geopandas, rasterio, pyyaml, …)
python transformation/nbs_screening/run_e2e.py --hazard flood   # bairro E2E (legacy)
```

Grid screening from Python:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("transformation/nbs_screening")))
from grid_screening import screen_grid, site_reference_bounds_geom

result = screen_grid(
    site_reference_bounds_geom("flood"),  # or a city boundary geometry
    hazard="flood",
    site="porto_alegre",                  # default when omitted
)
```

## Site configuration (PR N1)

Catalog layer URLs and local raster overrides live in:

`transformation/nbs_screening/config/sites/{city}.yaml`

- **Porto Alegre** — S3 COGs (published catalog products)
- **Minnesota cities** (`apple_valley`, `edina`, `plymouth`, `richfield`, `rochester`) — local hazard/risk paths (layers resolve when files exist on disk)

Helpers: `site_config.py`, `catalog_layers.get_layer_sources(hazard, site)`.

Set `NBS_SITE=porto_alegre` (default) or any configured city slug.

Check which layers exist on disk vs still pending extraction:

```bash
python transformation/nbs_screening/check_nbs_layers.py --site richfield
python transformation/nbs_screening/check_nbs_layers.py --all-mn
python transformation/nbs_screening/check_nbs_layers.py --site plymouth --hazard flood -v
```

Configured cities:

| Slug | Region | Layer source |
|------|--------|----------------|
| `porto_alegre` | Brazil | S3 catalog COGs |
| `apple_valley` | Minnesota | Local hazard/risk rasters |
| `edina` | Minnesota | Local hazard/risk rasters |
| `plymouth` | Minnesota | Local hazard/risk rasters |
| `richfield` | Minnesota | Local hazard/risk rasters |
| `rochester` | Minnesota | Local hazard/risk rasters |

Optional env:

| Variable | Purpose |
|----------|---------|
| `NBS_SITE` | Default city slug for layer resolution |
| `NBS_RIVERS_GEOJSON` | Local OSM rivers GeoJSON for riverine distance |
| `NBS_SAMPLE_DATA` | Directory containing `porto-alegre-rivers.json` |

## DEM diagnostics (flood low-lying)

```bash
export FLOODS_SITE=porto_alegre
# transformation/copernicus_dem/release/v1/relative_elevation_depression_from_dem.ipynb
```

## Docs

See `docs/` in this folder, `config/sites/README.md`, and
`models/nbs_*_mechanism_type/model_card.md`.

## Roadmap

| PR | Content |
|----|---------|
| **N1** (this) | `site_config.py`, site YAMLs, `catalog_layers` refactor |
| N2 | `compute_nbs_mechanism.py` (grid CLI, flood pilot) |
| N3 | Mechanism publish + catalog registration |
| N4+ | DEM diagnostics CLI, OSM rivers, MN cities batch |
