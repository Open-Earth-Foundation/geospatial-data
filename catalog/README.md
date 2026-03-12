# catalog

`catalog/` contains the source dataset registry for Level 0 inputs.

## File

- `datasets.yaml`: canonical list of upstream datasets used by transformation scripts.

## Required fields per dataset

- `dataset_id`
- `dataset_name`
- `publisher`
- `license`
- `resolution`
- `access_type`
- `source_url`
- `dataset_type`
- `description`

## Optional: data_quality

Per-dataset quality metadata. Use when known:

- `temporal_coverage`: Time period of the data (e.g. "1999-2018 (LTAy)")
- `accuracy`: Typical uncertainty or error range (e.g. "±4% typical")
- `limitations`: Caveats for use (e.g. "Regional screening; site-specific validation recommended")

## Optional: value_encoding (numeric rasters)

For `type: numeric_raster` with value tiles. Tells frontends how to decode pixel RGB to real values:

- `type`: `terrain_rgb` (or `categorical` for class-based)
- `scale`: Multiplier (e.g. 0.001)
- `offset`: Additive offset (e.g. 0.0)
- `unit`: Display unit (e.g. "kWh/kWp/day")
- `decode_formula`: Human-readable formula for reference

## Access type values

- `gee`
- `manual_download`
- `public_api`
- `internal_storage`

Keep entries stable and append-only where possible to preserve reproducibility and provenance history.
