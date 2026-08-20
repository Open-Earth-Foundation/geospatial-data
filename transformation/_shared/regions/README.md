# CCRA regional normalization domains

Config for **dual-product** scoring: city AOI (**default, never replaced**) + optional regional (state) domain.

| File / path | Role |
|-------------|------|
| `{region_id}.yaml` | Region policy: ROI = state boundary, layer list, stats path, catalog suffix |
| `norm_stats.py` | Load / save / update versioned stats helpers |
| `compute_regional_norm_stats.py` | Heat / GFD / landslide vmin–vmax over state ROI (GEE) |
| `compute_regional_acs_norm_stats.py` | Statewide ACS min–max for E/V |
| `docs/examples/ccra_normalization_stats.schema.json` | JSON Schema for versioned stats |
| `cache/regions/{region}/normalization/vN/normalization_stats.json` | Computed constants (**gitignored**) |
| `{region}/boundary/state.geojson` | Local state polygon |

## Design locks (Minnesota)

1. **ROI** = full state boundary (FIPS 27), not batch `union_bbox`
2. **Two products** — city screening unchanged; regional is a second output
3. **Versioned stats** — `stats_version: v1` under `cache/.../v1/`

## How to run

**Operator runbook:** [docs/ccra_regional_normalization_runbook.md](../../../docs/ccra_regional_normalization_runbook.md)

Landslide (R90p + NDVI regional only):

```bash
python transformation/_shared/regions/compute_regional_norm_stats.py \
  --region minnesota --layers r90p,ndvi_p10
python transformation/landslide_hazard/apply_regional_landslide_norms.py \
  --site rochester --region minnesota
python transformation/landslide_hazard/compute_landslide_hazard.py \
  --site rochester --product regional
python transformation/landslide_hazard/landslide_hazard_publish.py \
  --site rochester --normalization-domain regional --upload --write-catalog
```

## Status

| Hazard | Regional dual product | Notes |
|--------|----------------------|--------|
| Heat H + R (+ E/V) | Done (Rochester on S3) | See runbook |
| Flood H | Done (Rochester on S3) | GFD regional only |
| Landslide H | Done (Rochester on S3) | r90p + ndvi_p10; slope/clay/HAND fixed |

See `docs/ccra_normalization_decision.md` (Option 1).
