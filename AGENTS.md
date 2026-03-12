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

## How to answer "What is the data quality of dataset X?" or "What are the limitations?"

Read `catalog/datasets.yaml` — datasets may have a `data_quality` block with `temporal_coverage`, `accuracy`, and `limitations`. If absent, no quality metadata is recorded.

## How to answer "How do I decode value tiles for dataset X?"

Read `catalog/datasets.yaml` — numeric rasters may have a `value_encoding` block with `type`, `scale`, `offset`, `unit`, and `decode_formula`. For Terrain RGB: `value = (R * 256² + G * 256 + B) * scale + offset`.

## How to answer "What CRS does dataset X use?" or "What coordinate system?"

Read `catalog/datasets.yaml` — datasets may have a `crs` field (e.g. `EPSG:4326`). If absent, GTFS and most web-served geodata default to WGS84 (EPSG:4326).

## How to answer "Where are the output files?" or "What does transformation X produce?"

Transformation outputs live under `transformation/{theme}/release/{version}/output/`. Typical outputs: `*.geojson`, `*.tif` (COG), `*.pmtiles`, and `metadata.json`.

## How to answer "How do I generate COGs and tiles from a raster?"

Generic pipeline for any GeoTIFF that needs web map tiles:

1. **Reproject to Web Mercator** (if not already EPSG:3857):
   ```bash
   gdalwarp -t_srs EPSG:3857 -r near input.tif input_3857.tif
   ```

2. **Convert to COG**:
   ```bash
   gdal_translate -of COG input_3857.tif output_cog.tif \
     -co COMPRESS=DEFLATE -co OVERVIEWS=AUTO \
     -co RESAMPLING=AVERAGE   # numeric data
     # -co RESAMPLING=NEAREST  # categorical data
   ```

3. **Colorize for visual tiles** (create a `value R G B` colors file):
   ```bash
   gdaldem color-relief output_cog.tif colors.txt colorized.tif
   ```

4. **Generate XYZ tiles**:
   ```bash
   gdal2tiles.py -r near -z 8-15 --xyz -w none colorized.tif output/tiles_visual/
   ```

5. **Value tiles** (for hover/click lookup):
   - **Categorical**: R=class_id, G=0, B=0. Create colors file mapping each class to its ID in R.
   - **Numeric (Terrain RGB)**: `encoded = round((value - offset) / scale)` → R,G,B. Create colors file mapping value ranges to encoded RGB. Add `value_encoding` (scale, offset, unit) to `catalog/datasets.yaml`.

**Tools:** `gdalwarp`, `gdal_translate`, `gdaldem color-relief`, `gdal2tiles.py`

**Example:** `transformation/global_solar_atlas/AGENTS.md` and `transformation/global_solar_atlas/v2/raster_transformation.ipynb` for PVOUT.

## Canonical paths

- **Catalog (all datasets):** `catalog/datasets.yaml`
- **Dataset categories:** `collections/collections.yaml`
- **Analytical layers:** `collections/layers.yaml`
- **Transformation scripts:** `transformation/{theme}/`
- **Transformation outputs:** `transformation/{theme}/release/{version}/output/` or `transformation/{theme}/v2/output/`
- **Tile generation example:** `transformation/global_solar_atlas/v2/raster_transformation.ipynb`
- **Source data (per release):** `transformation/{theme}/release/{version}/arquivo-gtfs/` (or similar)
