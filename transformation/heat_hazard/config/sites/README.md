# heat_hazard site configs

One YAML file per **city** (`{city_slug}.yaml`).

## Conventions

- `site_slug` must match the filename stem and `sites/{city_slug}/`
- Prefer municipality / metro city polygons — not statewide AOIs
- Minnesota work uses city slugs (e.g. `minneapolis`, `duluth`), not `minnesota`
- Include season (`djf` / `jja`), year range, and layer filenames
- Default scoring parameters come from `models/heat_hazard/config.yaml`

## Example

See `porto_alegre.yaml` for the city-level shape. Additional Minnesota city YAMLs will be added when city boundaries are ready.
