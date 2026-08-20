# CCRA regional normalization — runbook (heat)

**Status:** Heat hazard + heat risk dual product proven on **Rochester, MN** (city product unchanged).  
**Policy:** Option 1 — state-boundary constants; both products stay published.  
**Decision:** [ccra_normalization_decision.md](./ccra_normalization_decision.md) · Config: [`transformation/_shared/regions/`](../transformation/_shared/regions/)

---

## Dual products (do not replace city)

| Product | Domain | Outputs | Use |
|---------|--------|---------|-----|
| **City** (default) | Min–max inside city AOI | `{city}_heat_hazard`, `{city}_heat_risk`, … | Local hotspots / screening |
| **Regional** (opt-in) | Same `vmin`/`vmax` for Minnesota | `{city}_heat_*_regional` | Compare cities within MN |

Never mix city H with regional E/V (or vice versa) when computing risk.

---

## Prerequisites

From repo root `geospatial-data/`:

1. **City heat inputs already extracted** for the site (`*_p90_*.tif` under `transformation/heat_hazard/sites/{site}/data/input/`).
2. **GEE auth** (only when recomputing state heat stats).
3. **`CENSUS_API_KEY`** (preferred for statewide ACS stats).
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

# Optional: refresh local state.geojson from GEE
# python transformation/_shared/regions/compute_regional_norm_stats.py \
#   --region minnesota --layers landsat_p90 --refresh-boundary
```

### ACS E/V (statewide block groups)

```bash
export CENSUS_API_KEY=...   # required for full-state ACS

python transformation/_shared/regions/compute_regional_acs_norm_stats.py \
  --region minnesota
```

Provisional fallback (union of city GPKGs only — not preferred):

```bash
python transformation/_shared/regions/compute_regional_acs_norm_stats.py \
  --region minnesota --from-city-gpkgs
```

Bump `stats_version` / write `cache/.../vN/` when recomputing.

---

## Per city: Rochester example (end-to-end)

Replace `rochester` with any MN site that already has city heat inputs.

### 1. Apply regional norms to heat P90 (no GEE)

Leaves city `*_norm_*.tif` untouched; writes `*_norm_*_regional.tif`.

```bash
python transformation/heat_hazard/apply_regional_heat_norms.py \
  --site rochester --region minnesota
```

### 2. Score heat hazard — regional product

```bash
python transformation/heat_hazard/compute_heat_hazard.py \
  --site rochester --product regional
```

City product (unchanged workflow):

```bash
python transformation/heat_hazard/compute_heat_hazard.py --site rochester
# or explicitly: --product city
```

### 3. Apply regional ACS E/V to the city

```bash
python transformation/acs_ev/apply_regional_acs_ev.py \
  --site rochester --region minnesota
```

Writes `acs_ev_block_groups_regional.gpkg` (city GPKG unchanged).

### 4. Score heat risk — regional product

Uses regional H + regional ACS GPKG.

```bash
python transformation/heat_risk/compute_heat_risk.py \
  --site rochester --product regional
```

### 5. Publish COG + tiles + catalog (regional only)

Local build (no S3):

```bash
python transformation/heat_hazard/heat_hazard_publish.py \
  --site rochester --normalization-domain regional --build

python transformation/heat_risk/heat_risk_publish.py \
  --site rochester --product risk --normalization-domain regional --build

# Optional components:
python transformation/heat_risk/heat_risk_publish.py \
  --site rochester --product exposure --normalization-domain regional --build
python transformation/heat_risk/heat_risk_publish.py \
  --site rochester --product vulnerability --normalization-domain regional --build
```

Upload + write catalog:

```bash
python transformation/heat_hazard/heat_hazard_publish.py \
  --site rochester --normalization-domain regional --no-build --upload --write-catalog

python transformation/heat_risk/heat_risk_publish.py \
  --site rochester --product risk --normalization-domain regional --no-build --upload --write-catalog

python transformation/heat_risk/heat_risk_publish.py \
  --site rochester --product exposure --normalization-domain regional --no-build --upload --write-catalog

python transformation/heat_risk/heat_risk_publish.py \
  --site rochester --product vulnerability --normalization-domain regional --no-build --upload --write-catalog
```

City publish stays the previous commands (`--normalization-domain city` is the default).

---

## Naming & S3 layout

Under `oef_calculation/release/v1/{city}/climate_hazards/heat/`:

| Layer | `dataset_id` | S3 folder |
|-------|--------------|-----------|
| H city | `{city}_heat_hazard` | `hazard/` |
| H regional | `{city}_heat_hazard_regional` | `hazard_regional/` |
| R city | `{city}_heat_risk` | `risk/` |
| R regional | `{city}_heat_risk_regional` | `risk_regional/` |
| E / V regional | `{city}_heat_exposure_regional` / `_vulnerability_regional` | `exposure_regional/` / `vulnerability_regional/` |

Catalog fields on regional entries:

```yaml
normalization_domain: minnesota
comparability: regional
```

**Proven on S3 (Rochester):** `rochester_heat_hazard_regional`, `rochester_heat_risk_regional`, plus exposure/vulnerability regional.

Local publish dirs:

```text
transformation/heat_hazard/sites/{site}/out/heat_hazard_score_regional/
transformation/heat_risk/sites/{site}/out/heat_{risk,exposure,vulnerability}_score_regional/
```

---

## What this does *not* cover yet

- Flood regional product (mainly **GFD** domain-scaled; depth / GFPLAIN stay fixed-threshold)
- Landslide regional product (**r90p**, **ndvi_p10**)
- Rolling regional product to all MN cities (same commands; needs city inputs + publish)

See layer list in [`minnesota.yaml`](../transformation/_shared/regions/minnesota.yaml) and the new-hazard checklist: [ccra_new_hazard_normalization_checklist.md](./ccra_new_hazard_normalization_checklist.md).
