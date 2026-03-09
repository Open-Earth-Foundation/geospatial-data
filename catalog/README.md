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

## Access type values

- `gee`
- `manual_download`
- `public_api`
- `internal_storage`

Keep entries stable and append-only where possible to preserve reproducibility and provenance history.
