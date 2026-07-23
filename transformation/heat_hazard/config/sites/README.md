# heat_hazard site configs

One YAML file per **city** (`{city_slug}.yaml`).

## Conventions

- `site_slug` must match the filename stem and `sites/{city_slug}/`
- Prefer municipality / metro city polygons — not statewide AOIs
- Include season (`djf` / `jja`), year range, and layer filenames
- Default scoring parameters come from `models/heat_hazard/config.yaml`
- Minnesota cities use **JJA** (northern summer); Porto Alegre uses **DJF**

## Cities currently configured

| site_slug | display_name | season | country |
|-----------|--------------|--------|---------|
| porto_alegre | Porto Alegre | DJF | Brazil |
| plymouth | Plymouth | JJA | United States (Minnesota) |
| edina | Edina | JJA | United States (Minnesota) |
| richfield | Richfield | JJA | United States (Minnesota) |
| rochester | Rochester | JJA | United States (Minnesota) |
| apple_valley | Apple Valley | JJA | United States (Minnesota) |

## Usage

```bash
export HEAT_SITE=edina
```
