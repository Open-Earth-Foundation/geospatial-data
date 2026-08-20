# Minnesota state boundary

**Source of truth for regional stats:** GEE `TIGER/2018/States` filtered to `STATEFP == "27"` (see `minnesota.yaml` → `roi`).

`state.geojson` is a **local convenience** polygon for desktop tooling. Prefer regenerating it from GEE (simplified) when running the spike:

```bash
python transformation/_shared/regions/compute_regional_norm_stats.py \
  --region minnesota --layers landsat_p90 --refresh-boundary
```

Do **not** use the CCRA batch `union_bbox` for scoring constants.

