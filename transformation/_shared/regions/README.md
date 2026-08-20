# CCRA regional normalization domains

Config for **dual-product** scoring: city AOI (**default, never replaced**) + optional regional (state) domain.

| File / path | Role |
|-------------|------|
| `{region_id}.yaml` | Region policy: ROI = state boundary, layer list, stats path, catalog suffix |
| `norm_stats.py` | Load / save / update versioned stats helpers |
| `compute_regional_norm_stats.py` | Heat (etc.) vmin/vmax over state ROI (GEE) |
| `compute_regional_acs_norm_stats.py` | Statewide ACS min–max for E/V |
| `docs/examples/ccra_normalization_stats.schema.json` | JSON Schema for versioned stats |
| `docs/examples/ccra_normalization_stats_{region}.example.json` | Example / placeholder stats |
| `cache/regions/{region}/normalization/vN/normalization_stats.json` | Computed constants (**gitignored**) |
| `{region}/boundary/state.geojson` | Local state polygon |

## Design locks (Minnesota)

1. **ROI** = full state boundary (FIPS 27), not batch `union_bbox`
2. **Two products** — city screening unchanged; regional is a second output
3. **Versioned stats** — `stats_version: v1` under `cache/.../v1/`

## How to run (heat)

**Operator runbook:** [docs/ccra_regional_normalization_runbook.md](../../../docs/ccra_regional_normalization_runbook.md)

Short path (after stats exist + city P90 inputs exist):

```bash
python transformation/heat_hazard/apply_regional_heat_norms.py --site rochester --region minnesota
python transformation/heat_hazard/compute_heat_hazard.py --site rochester --product regional
python transformation/acs_ev/apply_regional_acs_ev.py --site rochester --region minnesota
python transformation/heat_risk/compute_heat_risk.py --site rochester --product regional
python transformation/heat_hazard/heat_hazard_publish.py \
  --site rochester --normalization-domain regional --upload --write-catalog
python transformation/heat_risk/heat_risk_publish.py \
  --site rochester --product risk --normalization-domain regional --upload --write-catalog
```

## Status

| Hazard | Regional dual product | Notes |
|--------|----------------------|--------|
| Heat H + R (+ E/V) | Done (Rochester spike on S3) | See runbook |
| Flood | Not yet | Domain-scaled: GFD only |
| Landslide | Not yet | Domain-scaled: r90p, ndvi_p10 |

See `docs/ccra_normalization_decision.md` (Option 1).
