# flood_hazard site configs

One YAML file per **city** (`{city_slug}.yaml`).

## Conventions

- `site_slug` must match the filename stem and `sites/{city_slug}/`
- Prefer municipality / metro city polygons — not statewide AOIs
- Default scoring parameters come from `models/flood_hazard/config.yaml`; site files hold paths, filenames, bbox, S3 prefix, and optional overrides

## Cities currently configured

| site_slug | display_name | country |
|-----------|--------------|---------|
| porto_alegre | Porto Alegre | Brazil |
| plymouth | Plymouth | United States (Minnesota) |
| edina | Edina | United States (Minnesota) |
| richfield | Richfield | United States (Minnesota) |
| rochester | Rochester | United States (Minnesota) |
| apple_valley | Apple Valley | United States (Minnesota) |

## Usage

```bash
export FLOODS_SITE=plymouth
```
