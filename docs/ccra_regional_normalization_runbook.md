# CCRA regional normalization — runbook (heat + flood)

**Status:** Dual product proven on **Rochester, MN** for **heat** (H + R) and **flood hazard** (city product unchanged).  
**Policy:** Option 1 — state-boundary constants; both products stay published.  
**Decision:** [ccra_normalization_decision.md](./ccra_normalization_decision.md) · Config: [`transformation/_shared/regions/`](../transformation/_shared/regions/)

Use the repo `.venv` if present (`geospatial-data/.venv/bin/python`).

---

## Dual products (do not replace city)

| Product | Domain | Outputs | Use |
|---------|--------|---------|-----|
| **City** (default) | City AOI norms (GFD / LST / ACS) | `{city}_*_hazard`, `{city}_heat_risk`, … | Local hotspots / screening |
| **Regional** (opt-in) | Minnesota state constants | `{city}_*_regional` | Compare cities within MN |

**Flood note:** only **GFD** is re-scaled regionally. JRC / Aqueduct / GFPLAIN stay fixed-threshold on both products.

Never mix city H with regional E/V (or vice versa) when computing heat risk.

---

## Prerequisites

From repo root `geospatial-data/`:

1. **City inputs already extracted** for the site (heat P90s and/or flood ensemble layers under `sites/{site}/data/input/`).
2. **GEE auth** (only when recomputing state heat / GFD stats).
3. **`CENSUS_API_KEY`** (preferred for statewide ACS stats — heat risk).
4. Tools for publish: GDAL (`gdal_translate`, `gdaldem`, `gdal_calc.py`, `gdal2tiles.py`) and AWS CLI (upload).

Regional stats path (versioned):

```text
cache/regions/minnesota/normalization/v1/normalization_stats.json
```

(`cache/regions/` is gitignored — recompute or restore locally before apply.)

---

## One-time / rare: compute Minnesota constants

### Heat LST (GEE over state polygon)

```bash
python transformation/_shared/regions/compute_regional_norm_stats.py \
  --region minnesota \
  --layers landsat_p90,modis_day_p90,modis_night_p90
```

### Flood GFD (GEE over state polygon)

Merges into the same stats JSON (does not wipe heat layers):

```bash
python transformation/_shared/regions/compute_regional_norm_stats.py \
  --region minnesota \
  --layers gfd_event_count
```

Writes `layers.gfd_event_count.{p95,vmin,vmax}` (robust P95 + log1p min–max, scale ~250 m).

### ACS E/V (statewide block groups)

```bash
export CENSUS_API_KEY=...
python transformation/_shared/regions/compute_regional_acs_norm_stats.py \
  --region minnesota
```

Bump `stats_version` / write `cache/.../vN/` when recomputing.

---

## Per city: heat (Rochester)

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

---

## Per city: flood (Rochester)

Only GFD uses regional constants. City product remains default.

```bash
python transformation/flood_hazard/apply_regional_flood_norms.py \
  --site rochester --region minnesota
python transformation/flood_hazard/compute_flood_hazard.py \
  --site rochester --product regional
python transformation/flood_hazard/flood_hazard_publish.py \
  --site rochester --normalization-domain regional --upload --write-catalog
```

---

## Naming & S3 layout

| Hazard | City `dataset_id` | Regional `dataset_id` | Regional S3 |
|--------|-------------------|-----------------------|-------------|
| Heat H | `{city}_heat_hazard` | `{city}_heat_hazard_regional` | `…/heat/hazard_regional/` |
| Heat R | `{city}_heat_risk` | `{city}_heat_risk_regional` | `…/heat/risk_regional/` |
| Flood H | `{city}_flood_hazard` | `{city}_flood_hazard_regional` | `…/floods/hazard_regional/` |

Catalog fields: `normalization_domain: minnesota`, `comparability: regional`.

**Proven on S3 (Rochester):** heat `*_regional` + `rochester_flood_hazard_regional`.

---

## Not yet

- Landslide regional (**r90p**, **ndvi_p10**)
- Flood risk / E/V regional
- All MN cities rolled out

See [`minnesota.yaml`](../transformation/_shared/regions/minnesota.yaml) · [ccra_new_hazard_normalization_checklist.md](./ccra_new_hazard_normalization_checklist.md).
