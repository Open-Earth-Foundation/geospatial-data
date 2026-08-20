# CCRA regional normalization — runbook (heat + flood + landslide)

**Status:** Dual product proven on **Rochester, MN** for **heat** (H + R), **flood hazard**, and **landslide hazard** (city product unchanged).  
**Policy:** Option 1 — state-boundary constants; both products stay published.  
**Decision:** [ccra_normalization_decision.md](./ccra_normalization_decision.md) · Config: [`transformation/_shared/regions/`](../transformation/_shared/regions/)

Use the repo `.venv` if present (`geospatial-data/.venv/bin/python`).

---

## Dual products (do not replace city)

| Product | Domain | Outputs | Use |
|---------|--------|---------|-----|
| **City** (default) | City AOI norms | `{city}_*_hazard`, `{city}_heat_risk`, … | Local hotspots / screening |
| **Regional** (opt-in) | Minnesota state constants | `{city}_*_regional` | Compare cities within MN |

**What is re-scaled regionally**

| Hazard | Regional layers | Unchanged (fixed / binary) |
|--------|-----------------|----------------------------|
| Heat | Landsat / MODIS LST (+ ACS for risk) | — |
| Flood | GFD event count | JRC, Aqueduct, GFPLAIN |
| Landslide | R90p, NDVI P10 | slope, clay, HAND, Dynamic World |

Never mix city H with regional E/V (or vice versa) when computing heat risk.

---

## Prerequisites

From repo root `geospatial-data/`:

1. City inputs already extracted for the site.
2. GEE auth when recomputing state stats.
3. `CENSUS_API_KEY` for statewide ACS (heat risk).
4. GDAL + AWS CLI for publish/upload.

```text
cache/regions/minnesota/normalization/v1/normalization_stats.json
```

(`cache/regions/` is gitignored.)

---

## One-time: Minnesota constants

```bash
# Heat LST
python transformation/_shared/regions/compute_regional_norm_stats.py \
  --region minnesota --layers landsat_p90,modis_day_p90,modis_night_p90

# Flood GFD
python transformation/_shared/regions/compute_regional_norm_stats.py \
  --region minnesota --layers gfd_event_count

# Landslide R90p + NDVI
python transformation/_shared/regions/compute_regional_norm_stats.py \
  --region minnesota --layers r90p,ndvi_p10

# ACS E/V (heat risk)
export CENSUS_API_KEY=...
python transformation/_shared/regions/compute_regional_acs_norm_stats.py --region minnesota
```

Incremental runs **merge** into the existing stats JSON.

---

## Per city: heat

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

## Per city: flood

```bash
python transformation/flood_hazard/apply_regional_flood_norms.py --site rochester --region minnesota
python transformation/flood_hazard/compute_flood_hazard.py --site rochester --product regional
python transformation/flood_hazard/flood_hazard_publish.py \
  --site rochester --normalization-domain regional --upload --write-catalog
```

---

## Per city: landslide

```bash
python transformation/landslide_hazard/apply_regional_landslide_norms.py \
  --site rochester --region minnesota
python transformation/landslide_hazard/compute_landslide_hazard.py \
  --site rochester --product regional
python transformation/landslide_hazard/landslide_hazard_publish.py \
  --site rochester --normalization-domain regional --upload --write-catalog
```

---

## Naming & S3 layout

| Hazard | Regional `dataset_id` | Regional S3 |
|--------|----------------------|-------------|
| Heat H | `{city}_heat_hazard_regional` | `…/heat/hazard_regional/` |
| Heat R | `{city}_heat_risk_regional` | `…/heat/risk_regional/` |
| Flood H | `{city}_flood_hazard_regional` | `…/floods/hazard_regional/` |
| Landslide H | `{city}_landslide_hazard_regional` | `…/landslides/hazard_regional/` |

Catalog: `normalization_domain: minnesota`, `comparability: regional`.

**Proven on S3 (Rochester):** heat, flood, and landslide `*_regional`.

---

## Not yet

- Flood / landslide risk (E/V) regional products
- Rollout to all MN cities

See [`minnesota.yaml`](../transformation/_shared/regions/minnesota.yaml) · [ccra_new_hazard_normalization_checklist.md](./ccra_new_hazard_normalization_checklist.md).
