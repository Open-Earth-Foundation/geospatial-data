# geospatial-data

Repository for offline geospatial preprocessing used by the Nature-Based Solutions (NbS) prototype platform.

The platform does **not** run heavy geospatial analysis at request time. Instead, this repository computes analytical artifacts offline, stores them in S3, and exposes them through an API for fast map rendering and decision support.

## What this repository does

This repository has three core responsibilities:

1. Document upstream datasets used in the system.
2. Define analytical layers consumed by the platform.
3. Implement transformation pipelines that generate those layers.

## Repository structure

```text
geospatial-data/
  catalog/
    datasets.yaml
  collections/
    layers.yaml
  transformation/
    ... scripts grouped by theme ...
```

- `catalog/`: Level 0 raw source datasets and provenance metadata.
- `collections/`: analytical layer definitions and dependency graph (Levels 1-3).
- `transformation/`: scripts that ingest, transform, and publish layer outputs.

## Analytical pipeline model

The NbS workflow follows four levels:

- **Level 0 - Raw Source Data**: external inputs (DEM, rainfall, population, land cover, etc.).
- **Level 1 - Derived Indicators**: indicators computed from Level 0 (slope, canopy cover, impervious proxy, etc.).
- **Level 2 - Composite Analytical Layers**: thematic composites (hazards, exposure, ecosystem functions).
- **Level 3 - Decision Outputs**: final decision layers (risk, priority zones, opportunity zones).

Pipeline principle:

```text
Raw Data
  -> Offline Transformations
  -> Analytical Layers
  -> Stored in S3
  -> Served via API
  -> Displayed in Platform
```

## Folder details

### `catalog/`

Contains the dataset catalog (`catalog/datasets.yaml`) for all upstream sources used by transformations.

Each dataset entry should include:

- `dataset_id`
- `dataset_name`
- `publisher`
- `license`
- `resolution`
- `access_type` (`gee`, `manual_download`, `public_api`, `internal_storage`)
- `source_url`
- `dataset_type`
- `type` (`categorical_raster`, `numeric_raster`, `vector`)
- `assets`
  - `visual_tiles.url_template`
  - `value_tiles.url_template` (optional)
  - `download.cog_url`
  - `metadata.url`
- `description`

Why it exists:

- track provenance
- preserve reproducibility
- document upstream dependencies
- define API-ready asset locations for fast client integration

### `collections/`

Contains layer definitions (`collections/layers.yaml`) for all analytical outputs used by the platform.

Each layer entry should include:

- `layer_id`
- `layer_name`
- `layer_type`
- `analytical_level` (`1`, `2`, `3`)
- `category`
- `source_datasets` (for Level 1)
- `dependencies` (for Level 2/3)
- `transformation_script`
- `output_format` (`cog`, `geojson`, `pmtiles`, or mixed outputs)
- `s3_path`
- `description`

### `transformation/`

Contains executable scripts to build analytical products. Typical responsibilities:

- source ingestion
- reprojection and harmonization
- clipping to city boundaries
- raster/vector calculations
- indicator and composite index generation
- export and publication to S3

## Output products

Transformation pipelines should publish precomputed artifacts in S3:

- **Raster**: Cloud Optimized GeoTIFF (`.tif`), visual tiles (`.png`), optional value tiles
- **Vector**: GeoJSON, PMTiles
- **Metadata**: `metadata.json` with provenance, processing version, and schema notes

## Development conventions

- Keep `catalog/datasets.yaml` up to date before building new layers.
- Register new analytical outputs in `collections/layers.yaml`.
- Prefer deterministic, idempotent transformation scripts.
- Include metadata generation in every pipeline.
- Use stable, machine-friendly IDs (`snake_case`) for datasets and layers.