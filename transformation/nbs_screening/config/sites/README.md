# NBS grid screening — site configs

One YAML per city under `config/sites/{site_slug}.yaml`.

## Schema

```yaml
site_slug: porto_alegre
display_name: Porto Alegre

open_water:
  enabled: true              # flood mechanism export masks permanent water
  transition_layer: jrc_surface_water_transition
  occurrence_layer: jrc_surface_water_occurrence

# POA uses NBS_SAMPLE_DATA/porto-alegre-rivers.json when no local file is set.

reference_hazard:            # catalog layer id used as the 250 m reference grid
  flood: flood_hazard
  heat: heat_hazard
  landslide: landslide_hazard

catalog:
  shared:                    # merged into every hazard profile
    exposure:
      url: https://.../exposure_cog.tif
    ghsl_built_up:
      local: transformation/ghsl_built_up/sites/richfield/...   # preferred when file exists
      url: https://.../fallback_cog.tif
  flood: { ... hazard-specific layers ... }
  heat: { ... }
  landslide: { ... }
```

Each layer entry is either a URL string or a mapping with optional `local` and `url`.
`local` paths are relative to the **geospatial-data** repo root unless absolute.

Optional top-level **`osm_waterways`** (Minnesota cities):

```yaml
osm_waterways:
  local: transformation/nbs_screening/sites/richfield/data/input/osm_waterways_richfield.json
```

Generate with `python transformation/nbs_screening/extract_osm_rivers.py --site richfield`.
POA falls back to `NBS_SAMPLE_DATA/porto-alegre-rivers.json` when unset.

## Runtime

```python
from site_config import load_site_config, get_layer_sources

cfg = load_site_config("porto_alegre")
layers = get_layer_sources("flood", "porto_alegre")
```

Set `NBS_SITE=richfield` to pick a default city without passing `--site` on future CLIs.

## Configured sites

| Slug | Notes |
|------|--------|
| `porto_alegre` | Full S3 catalog (production POA) |
| `apple_valley` | MN — full POA-parity layer inventory (local paths) |
| `edina` | MN — full POA-parity layer inventory (local paths) |
| `plymouth` | MN — full POA-parity layer inventory (local paths) |
| `richfield` | MN — full POA-parity layer inventory (local paths) |
| `rochester` | MN — full POA-parity layer inventory (local paths) |

Minnesota YAMLs list **every layer key** present in `porto_alegre.yaml` (35 unique keys
across shared + flood + heat + landslide). Inline comments mark extraction status:

| Tag | Meaning |
|-----|---------|
| `[CCRA]` | Hazard/risk/DEM from CCRA compute pipeline |
| `[INPUT]` | Written by landslide/heat hazard input extractors |
| `[PUB]` | Exposure/vulnerability from `flood_risk_publish` |
| `[TODO]` | Not yet extracted for MN — path is the planned target |

At runtime, `get_layer_sources()` only returns layers whose local file exists (or URL
for POA). Missing `[TODO]` layers are skipped until extracts are run.

Audit readiness:

```bash
python transformation/nbs_screening/check_nbs_layers.py --site richfield
python transformation/nbs_screening/check_nbs_layers.py --all-mn --json
```
