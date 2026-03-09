# collections

`collections/` defines analytical layers consumed by the NbS platform.

## File

- `layers.yaml`: registry of derived indicators, composite layers, and decision outputs.

## Analytical levels

- Level `1`: derived indicators
- Level `2`: composite analytical layers
- Level `3`: decision outputs

## Required fields per layer

- `layer_id`
- `layer_name`
- `layer_type`
- `analytical_level`
- `category`
- `source_datasets`
- `dependencies`
- `transformation_script`
- `output_format`
- `s3_path`
- `description`

Use `source_datasets` for direct Level 0 inputs and `dependencies` for upstream analytical layers.
