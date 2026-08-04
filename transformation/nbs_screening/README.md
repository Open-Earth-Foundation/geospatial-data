# NbS screening

Rule-based Nature-based Solutions **grid** screening and dominant-mechanism layers
(flood / heat / landslide). The primary unit is the **250 m cell** (90 m for landslide);
bairro/AOI queries are legacy and out of scope for the multi-city pipeline.

## Layout (N10)

Each hazard module owns its runtime data (same flat `sites/{city}/` pattern as `flood_hazard`):

```
transformation/nbs_screening/
├── site_config.py, catalog_layers.py, grid_screening.py, nbs_rules.py  # shared
├── config/sites/{city}.yaml                                             # multi-hazard index
├── flood/          flood mechanism CLIs + sites/{city}/ (N2–N7, D10 inputs)
├── heat/           heat mechanism CLIs + sites/{city}/ (H2–H3, D10 inputs)
├── landslide/      landslide mechanism CLIs + sites/{city}/ (L2–L3, D10 inputs)
├── extract_common.py   shared input-orchestrator helpers
```

See `flood/README.md`, `heat/README.md`, `landslide/README.md`.

## Run (grid mechanism — N2, flood)

```bash
# Flood mechanism type on city boundary (Minnesota pilot)
python transformation/nbs_screening/flood/compute_mechanism.py --site richfield

# Full hazard grid extent (POA-style)
python transformation/nbs_screening/flood/compute_mechanism.py --site porto_alegre --aoi full
```

Outputs: `transformation/nbs_screening/flood/sites/<site>/data/output/`  
(`flood_mechanism_type_<site>_250m.tif`, observed + IDW mask, GeoJSON, QA SVG, `metadata.json`).

## Publish (N3 — flood mechanism COG + tiles)

```bash
# Build COG + XYZ tiles locally (Richfield pilot)
python transformation/nbs_screening/flood/publish_mechanism.py --site richfield --build

# Upload to S3 and register in catalog/datasets.yaml
python transformation/nbs_screening/flood/publish_mechanism.py \\
  --site richfield --build --upload --write-catalog
```

Publish staging: `transformation/nbs_screening/flood/sites/<site>/out/flood_mechanism_type/`  
Catalog dataset id: `{site}_flood_mechanism_type` (POA keeps `poa_flood_mechanism_type`).

## Run (grid mechanism — H2, heat)

```bash
python transformation/nbs_screening/heat/compute_mechanism.py --site richfield
python transformation/nbs_screening/heat/publish_mechanism.py --site richfield --build
```

Outputs: `transformation/nbs_screening/heat/sites/<site>/data/output/` (250 m grid).

## Run (grid mechanism — L2, landslide)

```bash
python transformation/nbs_screening/landslide/compute_mechanism.py --site richfield
python transformation/nbs_screening/landslide/publish_mechanism.py --site richfield --build
```

Outputs: `transformation/nbs_screening/landslide/sites/<site>/data/output/` (90 m grid).

## OSM waterways (N4 — riverine distance)

Grid screening uses local OSM river/stream/canal linework for `dist_nearest_m` / riverine mechanism flags. Extract per city (Overpass API):

```bash
python transformation/nbs_screening/flood/extract_osm_rivers.py --site richfield
python transformation/nbs_screening/flood/extract_osm_rivers.py --all-configured
python transformation/nbs_screening/flood/extract_osm_rivers.py --country "United States"
```

Output: `transformation/nbs_screening/flood/sites/<site>/data/input/osm_waterways_<site>.json`  
(`geoJson` wrapper compatible with POA `porto-alegre-rivers.json`).

Override path: `NBS_RIVERS_GEOJSON` or `osm_waterways.local` in site YAML.

## Batch multi-city (N5)

End-to-end flood mechanism for any configured city (`config/sites/{slug}.yaml`):

```bash
python transformation/nbs_screening/flood/batch_mechanism.py --all-configured
python transformation/nbs_screening/flood/batch_mechanism.py --country "United States"
python transformation/nbs_screening/flood/batch_mechanism.py --sites richfield,edina
python transformation/nbs_screening/flood/batch_mechanism.py --all-configured --exclude porto_alegre
python transformation/nbs_screening/flood/batch_mechanism.py \\
  --country "United States" --upload --write-catalog --continue-on-error
```

Minnesota cohort shortcut: `flood/batch_mn_mechanism.py` (defaults to `--country "United States"`).

## Full flood pipeline (N7)

```bash
python transformation/nbs_screening/flood/run_pipeline.py --site richfield
python transformation/nbs_screening/flood/run_pipeline.py \\
  --country "United States" --skip-dem
python transformation/nbs_screening/flood/run_pipeline.py \\
  --site richfield --publish-dem --upload --write-catalog
python transformation/nbs_screening/flood/run_pipeline.py \\
  --all-configured --upload --write-catalog --continue-on-error
```

Minnesota cohort shortcut: `flood/run_mn_pipeline.py` (defaults to `--country "United States"`).

## Mechanism input layers (D10 / N10b)

Extract catalog rasters used by grid screening (GEE + OSM + DEM diagnostics). Run **before** `run_pipeline` / `compute_mechanism` when layers are missing:

```bash
python transformation/nbs_screening/flood/extract_mechanism_inputs.py --site richfield
python transformation/nbs_screening/heat/extract_mechanism_inputs.py --country "United States"
python transformation/nbs_screening/landslide/extract_mechanism_inputs.py --site richfield
python transformation/nbs_screening/check_nbs_layers.py --site richfield --hazard flood
```

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

## DEM diagnostics (N6 — flood low-lying)

Relative elevation, depression mask, and depression depth from Copernicus DEM GLO-30 (30 m):

```bash
python transformation/copernicus_dem/compute_dem_diagnostics.py --site richfield
python transformation/copernicus_dem/compute_dem_diagnostics.py --country "United States"
python transformation/copernicus_dem/compute_dem_diagnostics.py --all-configured --continue-on-error
```

Optional GEE export when DEM is missing locally: `--export-dem` (see notebook
`transformation/copernicus_dem/release/v1/relative_elevation_depression_from_dem.ipynb`).

Outputs: `transformation/flood_hazard/sites/<site>/data/output/{prefix}_relative_elevation_30m.tif`
(and depression mask/depth). Wired in NBS site YAML as `poa_relative_elevation`, etc.

## Docs

See `docs/` in this folder, `config/sites/README.md`, and
`models/nbs_*_mechanism_type/model_card.md`.

## Roadmap

| PR | Content |
|----|---------|
| **N1** | `site_config.py`, site YAMLs, `catalog_layers` refactor |
| **N2** | `flood/compute_mechanism.py` flood grid CLI |
| **N3** | `flood/publish_mechanism.py` flood COG/tiles + catalog |
| **N4** | `flood/extract_osm_rivers.py` + site-aware waterways in screening |
| **N5** | `flood/batch_mechanism.py` multi-city batch pipeline |
| **N6** | `compute_dem_diagnostics.py` relative elevation + depression |
| **N7** | `flood/run_pipeline.py` end-to-end flood orchestrator |
| **N8** | `publish_dem_diagnostics.py` DEM COG/tiles + catalog |
| **N9** | Hazard-scoped layout (superseded by N10) |
| **N10** | Per-hazard module owns `sites/{city}/` (`flood/`, not root `sites/`) |
| **N10b** | Per-hazard `extract_mechanism_inputs.py` (replaces `inputs/`) |
| **N10c** | Drop legacy `sites/{city}/` read fallbacks in `site_config.py` |
| **N10d** | Document NBS layout in `transformation/README.md` |
| **N10e** | `heat/` + `landslide/` compute/publish CLIs (H2/L2, H3/L3) |
