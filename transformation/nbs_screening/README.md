# NbS screening

Rule-based Nature-based Solutions **grid** screening and dominant-mechanism layers
(flood / heat / landslide). The primary unit is the **250 m cell**; bairro/AOI queries
are legacy and out of scope for the multi-city pipeline.

## Run (grid mechanism — N2)

```bash
# Flood mechanism type on city boundary (Minnesota pilot)
python transformation/nbs_screening/compute_nbs_mechanism.py --site richfield

# Full hazard grid extent (POA-style)
python transformation/nbs_screening/compute_nbs_mechanism.py --site porto_alegre --aoi full
```

Outputs: `transformation/nbs_screening/sites/<site>/data/output/`  
(`flood_mechanism_type_<site>_250m.tif`, observed + IDW mask, GeoJSON, `metadata.json`).

## Publish (N3 — flood mechanism COG + tiles)

```bash
# Build COG + XYZ tiles locally (Richfield pilot)
python transformation/nbs_screening/nbs_mechanism_publish.py --site richfield --build

# Upload to S3 and register in catalog/datasets.yaml
python transformation/nbs_screening/nbs_mechanism_publish.py \\
  --site richfield --build --upload --write-catalog
```

Publish staging: `transformation/nbs_screening/sites/<site>/out/flood_mechanism_type/`  
Catalog dataset id: `{site}_flood_mechanism_type` (POA keeps `poa_flood_mechanism_type`).

## OSM waterways (N4 — riverine distance)

Grid screening uses local OSM river/stream/canal linework for `dist_nearest_m` / riverine mechanism flags. Extract per city (Overpass API):

```bash
python transformation/nbs_screening/extract_osm_rivers.py --site richfield
python transformation/nbs_screening/extract_osm_rivers.py --all-configured
python transformation/nbs_screening/extract_osm_rivers.py --country "United States"
```

Output: `transformation/nbs_screening/sites/<site>/data/input/osm_waterways_<site>.json`  
(`geoJson` wrapper compatible with POA `porto-alegre-rivers.json`).

Override path: `NBS_RIVERS_GEOJSON` or `osm_waterways.local` in site YAML.

## Batch multi-city (N5)

End-to-end flood mechanism for any configured city (`config/sites/{slug}.yaml`):

```bash
# All configured sites (add a YAML to onboard a new city)
python transformation/nbs_screening/batch_flood_mechanism.py --all-configured

# Filter by country field in site YAML (current MN cohort)
python transformation/nbs_screening/batch_flood_mechanism.py --country "United States"

# Explicit list
python transformation/nbs_screening/batch_flood_mechanism.py --sites richfield,edina

# Exclude POA from a full run
python transformation/nbs_screening/batch_flood_mechanism.py --all-configured --exclude porto_alegre

# Upload + catalog
python transformation/nbs_screening/batch_flood_mechanism.py \\
  --country "United States" --upload --write-catalog --continue-on-error
```

Legacy alias: `batch_mn_flood_mechanism.py` → same as `--country "United States"`.

## Run (POA defaults / legacy)

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
python transformation/nbs_screening/check_nbs_layers.py --all-configured
python transformation/nbs_screening/check_nbs_layers.py --country "United States"
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
| **N1** | `site_config.py`, site YAMLs, `catalog_layers` refactor |
| **N2** | `compute_nbs_mechanism.py` flood grid CLI |
| **N3** | `nbs_mechanism_publish.py` flood COG/tiles + catalog |
| **N4** | `extract_osm_rivers.py` + site-aware waterways in screening |
| **N5** (this) | `batch_flood_mechanism.py` multi-city batch pipeline |
| N6+ | DEM diagnostics CLI |
