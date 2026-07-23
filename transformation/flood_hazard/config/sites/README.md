# flood_hazard site configs

One YAML file per **city** (`{city_slug}.yaml`).

## Conventions

- `site_slug` must match the filename stem and `sites/{city_slug}/`
- Prefer municipality / metro city polygons — not statewide AOIs
- Minnesota work uses city slugs (e.g. `minneapolis`, `duluth`), not `minnesota`
- Default scoring parameters come from `models/flood_hazard/config.yaml`; site files hold paths, filenames, bbox, S3 prefix, and optional overrides

## Example

See `porto_alegre.yaml` for the city-level shape. Additional Minnesota city YAMLs will be added when city boundaries are ready.
