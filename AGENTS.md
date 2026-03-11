# AI / MCP Guidance for Geospatial Data

This file helps AI assistants and MCP tools understand the geospatial-data repository. Read this first when answering questions about datasets, layers, or transformations.

## How to answer "What datasets do we have?"

Read `catalog/datasets.yaml`. It lists all Level 0 source datasets with `dataset_id`, `dataset_name`, `publisher`, `license`, `resolution`, `access_type`, `source_url`, `dataset_type`, `type`, `assets`, and `description`. Optional fields include `crs` for coordinate reference system.

## How to answer "What datasets are in category X?" or "What transport / land cover datasets exist?"

Read `collections/collections.yaml`. It groups datasets by category (e.g. `transport`, `land_cover`, `elevation`, `population`, `buildings`).

## How to answer "What analytical layers do we produce?" or "What does layer X depend on?"

Read `collections/layers.yaml`. It defines derived indicators (Level 1), composite layers (Level 2), and decision outputs (Level 3). Each layer has `source_datasets`, `dependencies`, `output_format`, and `description`.

## How to answer "Where is the transformation for dataset X?" or "How do we build layer Y?"

Look in `transformation/` — each subfolder (e.g. `poa_gtfs`, `land_cover`) contains scripts or notebooks that ingest source data and produce outputs. Check the folder's `README.md` for source, release layout, and usage.

## How to answer "What CRS does dataset X use?" or "What coordinate system?"

Read `catalog/datasets.yaml` — datasets may have a `crs` field (e.g. `EPSG:4326`). If absent, GTFS and most web-served geodata default to WGS84 (EPSG:4326).

## How to answer "Where are the output files?" or "What does transformation X produce?"

Transformation outputs live under `transformation/{theme}/release/{version}/output/`. Typical outputs: `*.geojson`, `*.tif` (COG), `*.pmtiles`, and `metadata.json`.

## Canonical paths

- **Catalog (all datasets):** `catalog/datasets.yaml`
- **Dataset categories:** `collections/collections.yaml`
- **Analytical layers:** `collections/layers.yaml`
- **Transformation scripts:** `transformation/{theme}/`
- **Transformation outputs:** `transformation/{theme}/release/{version}/output/`
- **Source data (per release):** `transformation/{theme}/release/{version}/arquivo-gtfs/` (or similar)
