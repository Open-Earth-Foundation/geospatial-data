# AI / MCP Guidance for Geospatial Data

This file helps AI assistants and MCP tools understand the geospatial-data repository. Read this first when answering questions about datasets, layers, or transformations.

## Purpose

The geospatial-data repository curates Level 0 source datasets and transformation pipelines that produce analytical outputs (COGs, tiles, GeoJSON) for city-scale mapping. AI assistants should use this guidance to answer questions about datasets, find transformation logic, and add new datasets following the established conventions.

## How to answer "What datasets do we have?"

Read `catalog/datasets.yaml`. It lists all Level 0 source datasets with `dataset_id`, `dataset_name`, `publisher`, `license`, `resolution`, `access_type`, `source_url`, `dataset_type`, `type`, `assets`, and `description`. Optional fields include `crs` for coordinate reference system.

## How to answer "What datasets are in category X?" or "What transport / land cover datasets exist?"

Read `collections/collections.yaml`. It groups datasets by category (e.g. `transport`, `land_cover`, `elevation`, `population`, `buildings`).

## How to answer "What analytical layers do we produce?" or "What does layer X depend on?"

Read `collections/layers.yaml`. It defines derived indicators (Level 1), composite layers (Level 2), and decision outputs (Level 3). Each layer has `source_datasets`, `dependencies`, `output_format`, and `description`.

## How to answer "Where is the transformation for dataset X?" or "How do we build layer Y?"

Look in `transformation/` — each subfolder (e.g. `poa_gtfs`, `land_cover`) contains scripts or notebooks that ingest source data and produce outputs. Check the folder's `README.md` for source, release layout, and usage.

## How to answer "What models do we use?" or "Where is the model for layer X?"

Read `models/README.md` and look in `models/` — each subfolder (e.g. `flood_hazard`, `composite_risk`) holds model configs, weights, and model cards for Level 2–3 layers. Models consume Level 1 indicators and produce composite analytical outputs.

## How to answer "What is the data quality of dataset X?" or "What are the limitations?"

Read `catalog/datasets.yaml` — datasets may have a `data_quality` block with `temporal_coverage`, `accuracy`, and `limitations`. If absent, no quality metadata is recorded.

## How to answer "How do I decode value tiles for dataset X?"

Read `catalog/datasets.yaml` — numeric rasters may have a `value_encoding` block with `type`, `scale`, `offset`, `unit`, and `decode_formula`. For Terrain RGB: `value = (R * 256² + G * 256 + B) * scale + offset`.

## How to answer "What CRS does dataset X use?" or "What coordinate system?"

Read `catalog/datasets.yaml` — datasets may have a `crs` field (e.g. `EPSG:4326`). If absent, GTFS and most web-served geodata default to WGS84 (EPSG:4326).

## How to answer "Where are the output files?" or "What does transformation X produce?"

Transformation outputs live under `transformation/{dataset_slug}/releases/{version}/output/`. Typical outputs: `*.geojson`, `*.tif` (COG), `*.pmtiles`, and `metadata.json`.

**Release vs time period:** The release folder (`releases/{version}/`) is the **dataset/transformation version** (e.g. `v1`, `v2`, `2024-10-01`), not the time period of the source data. The collection period (e.g. year 2024) belongs in a separate subdirectory, e.g. `releases/v1/2024/output/` for outputs built from 2024 source data.

## How to answer "How do I generate COGs and tiles?" or "How do I add a new dataset?"

Use the **add-geospatial-dataset** skill (`.cursor/skills/add-geospatial-dataset/`). It covers the full workflow: folder structure, GEE export, GDAL pipeline (COG + visual + value tiles), catalog and collection updates, and S3 upload.

## How to answer "How do I add a catalog entry?" or "Add dataset X to the catalog"

Use the **add-catalog-entry** skill (`.cursor/skills/add-catalog-entry/`). It adds an entry to `catalog/datasets.yaml` only — use when a transformation exists and you need to register it in the catalog.

## Dataset slug naming

Use **snake_case**. Prefer `{source}_{descriptor}` or `{source}_{product}`:

| Pattern | Examples |
|---------|----------|
| Publisher/source + descriptor | `ghsl_degree_urbanization`, `ghsl_built_up`, `ghsl_population`, `jrc_global_surface_water` |
| Publisher + product name | `copernicus_dem`, `hansen_forest_change`, `merit_hydro`, `noaa_viirs_nightlights` |
| Product name (well-known) | `dynamic_world`, `global_solar_atlas` |
| Geographic + product | `poa_gtfs`, `br_ibge` |

- **Source abbreviations:** `ghsl`, `jrc`, `noaa`, `copernicus`, `hansen`, `merit`
- **Avoid:** spaces, hyphens, camelCase; resolution in slug (e.g. prefer `copernicus_dem` not `dem_copernicus_30m`)

## Canonical paths

- **Catalog (all datasets):** `catalog/datasets.yaml`
- **Dataset categories:** `collections/collections.yaml`
- **Analytical layers:** `collections/layers.yaml`
- **Models (Level 2–3):** `models/{layer_id}/` — see `models/README.md`
- **Transformation scripts:** `transformation/{dataset_slug}/`
- **Transformation outputs:** `transformation/{dataset_slug}/releases/{version}/output/` or `transformation/{dataset_slug}/releases/{version}/{period}/output/` (period = data collection year/date)
- **Tile generation example:** `transformation/global_solar_atlas/v2/raster_transformation.ipynb`
- **Source data (per release):** `transformation/{dataset_slug}/releases/{version}/arquivo-gtfs/` (or similar)
