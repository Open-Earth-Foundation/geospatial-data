# CCRA wildfire hazard — methodology and dataset exploration

**Status:** Exploration (recommendation for v1, not implemented)  
**Ticket:** [CC-648](https://linear.app/openearth/issue/CC-648/explore-methodology-and-datasets-for-2-additional-hazards-droughts-and)  
**Date:** 2026-08-25  
**Scope of this file:** wildfire only. Drought sibling: [ccra_drought_hazard_exploration.md](./ccra_drought_hazard_exploration.md).

Related: [ccra_new_hazard_normalization_checklist.md](./ccra_new_hazard_normalization_checklist.md), [ccra_normalization_decision.md](./ccra_normalization_decision.md), [ccra_pipeline_architecture.md](./ccra_pipeline_architecture.md), `models/{flood,heat,landslide}_hazard/model_card.md`.

---

## 1) Purpose

Extend CCRA beyond flood, heat, and landslide with a **city-AOI screening wildfire score** `H ∈ [0, 1]` that enters the same risk equation:

```text
R = (H × E × V)^(1/3)
```

This note answers the ticket for wildfire:

1. At least two global candidate datasets with URL, resolution, cadence, and access method.
2. Whether each can go through extract → regrid → 0–1 normalize → ensemble → publish.
3. A v1 methodology analogous to flood / heat / landslide.
4. A squad recommendation.

This is **hazard screening** (susceptibility + observed occurrence), not a fire-spread model, not WUI building-loss, and not a live FIRMS alert.

Ticket examples to cover: **fire-risk indices**, **historical fire occurrence**, **vegetation dryness**.

---

## 2) What we already have (do not restart)

| Asset | Role for wildfire |
|-------|-------------------|
| Knowledge-base CCRA indices | Wildfire listed as **FWI + VPD** at the ~5–10 km climate-hazard tier. See `knowledge-base/products/citycatalyst/modules/ccra.md`. |
| Indicator JSON | No dedicated wildfire block (unlike SPEI/CDD for drought). Treat FWI/VPD + occurrence + fuel as the operational set. |
| MODIS NDVI | Landslide already extracts `MODIS/061/MOD13Q1` P10 → `veg_protect`. Invert for fuel dryness. |
| Dynamic World | Landslide land-cover modifier (`GOOGLE/DYNAMICWORLD/V1`). Reuse for WUI (built next to trees/grass/shrub). |
| TerraClimate | Recommended in the drought doc (`IDAHO_EPSCOR/TERRACLIMATE`). Band `vpd` is vapor-pressure deficit — the named CCRA wildfire climate index, at ~4.6 km, GEE. |
| Heat ERA5 lesson | ~9 km air-temperature was dropped because a city is a handful of pixels. **CEMS FWI (~0.25°)** has the same problem as a *primary* intra-city layer. Keep it as fire-weather context, not the sharp map. |
| Flood GFD pattern | Event **counts** (FIRMS, burned-year count) are heavy-tailed. Prefer robust P95 + `log1p`, and do **not** let one industrial hotspot become 1.0 via city min–max. |

---

## 3) Conceptual model (v1 screening)

City wildfire for CCRA is **WUI / vegetation-fire susceptibility**, not structure-to-structure urban conflagration.

```text
H = f(historical_occurrence, fire_weather, fuel_dryness)  ×  wui_modifier
```

| Component | Physical meaning | Analog in current stack |
|-----------|------------------|-------------------------|
| Historical occurrence | Where fire has actually been detected / burned | Flood GFD counts + GFPLAIN mask |
| Fire weather (FWI / VPD) | Meteorological conditions that dry fuel and support spread | Drought SPEI/PDSI classes; heat is *not* the analog (too local) |
| Vegetation dryness / fuel | Sparse or dry live fuel | Landslide `lack_of_veg` from NDVI P10 |
| WUI modifier | Built pixels next to burnable cover | Landslide Dynamic World boost on slope |

**Spatial mix is better than drought.** Burned-area and VIIRS hotspots are 375–500 m, so intra-city edges (parks, greenbelts, metro fringe) can show up. Fire weather stays regional and blocky — same honesty rule as CHIRPS in landslide: **nearest-neighbour upsample, no fake gradients**.

**Temporal framing (match heat):** static composite over ~10 years (e.g. 2015–2024), not a daily FWI dashboard. Occurrence uses a longer MODIS record (2001–present) if the spike shows MN metros are too sparse in a 10-year window.

**Industrial false positives:** FIRMS/MODIS thermal anomalies include gas flares, steel, and persistent hotspots. Filter by confidence and, where the product provides it, fire type. MCD64A1 QA bit “persistent hot spot” should be excluded from the burn count.

---

## 4) Candidate datasets

### 4.1 Inventory (ticket: ≥2 global; NASA called out)

| # | Dataset | Publisher | Access | Native res. | Cadence | Coverage | Units / signal | Pipeline fit |
|---|---------|-----------|--------|-------------|---------|----------|----------------|--------------|
| **A** | **MCD64A1 burned area** | NASA LP DAAC | GEE `MODIS/061/MCD64A1` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD64A1) | **500 m** | Monthly, 2000-11–present | Global | `BurnDate` 1–366 = burned that month | **Yes — best NASA occurrence raster** |
| **B** | **FIRMS active fires (MODIS)** | NASA LANCE / FIRMS | GEE `FIRMS` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/FIRMS) · [FIRMS](https://firms.modaps.eosdis.nasa.gov/) | **1 km** | Daily / NRT, 2000–present | Global | Rasterized hotspots: `T21`, `confidence` | **Yes — GEE extract like MODIS LST** |
| **C** | **MODIS NDVI (fuel dryness)** | NASA | GEE `MODIS/061/MOD13Q1` (already in repo) | **250 m** | 16-day, 2000–present | Global | NDVI P10 → `1 − veg_protect` | **Yes — reuse landslide extract** |
| **D** | **TerraClimate VPD** | U. Idaho / UC Merced | GEE `IDAHO_EPSCOR/TERRACLIMATE` band `vpd` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_TERRACLIMATE) | ~4.6 km | Monthly, 1958–present | Global land | Vapor-pressure deficit (kPa, scale 0.01) | **Yes — same collection as drought PDSI** |
| **E** | **CEMS GEFF Fire Weather Index** | Copernicus EMS / ECMWF | CDS `cems-fire-historical-v1` · [overview](https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1?tab=overview) (not official GEE; Climate Engine community asset exists) | **0.25°** (~25–31 km native ERA5) | Daily, 1940–present | Global land | FWI + EFFIS danger classes | Format yes via CDS (heat ERA5 path); **too coarse as primary H** |
| F | VIIRS 375 m active fire (S-NPP) | NASA FIRMS | GEE `NASA/LANCE/SNPP_VIIRS/C2` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/NASA_LANCE_SNPP_VIIRS_C2); archive also via FIRMS | **375 m** | Daily NRT | Global | Hotspots finer than MODIS | GEE NRT window is **short (~2023+)** — not a 10-year climatology |
| G | GFED burned area | NASA / UCI | Various / not a first-class GEE city extract | ~0.25° | Monthly | Global | Burned fraction | **No** for city AOI |
| H | LANDFIRE / MTBS | USGS / USFS | US portals | 30 m | Periodic | **CONUS only** | Fuel models, burn severity | MN-only, not C40/GCoM |

Ticket bar is met by **A + B** (NASA occurrence). **C** covers vegetation dryness with an extract we already run. **D** (or **E**) covers fire-risk indices. **E** is the named FWI product; **D** is the GEE-native VPD stand-in at finer resolution than CEMS.

### 4.2 Per-dataset pipeline validation

Shared target: GeoTIFF on the city flood/heat **250 m** grid, EPSG:4326, `H ∈ [0, 1]`, COG + XYZ tiles, catalog `{city}_wildfire_hazard`.

| Check | MCD64A1 (A) | FIRMS MODIS (B) | NDVI (C) | TerraClimate VPD (D) | CEMS FWI (E) |
|-------|-------------|-----------------|----------|----------------------|--------------|
| Format | GEE ImageCollection → GeoTIFF | Same | Same (exists) | Same | CDS NetCDF → GeoTIFF (ERA5-Land pattern) |
| Clip to city boundary | Yes | Yes | Yes | Yes | Yes, almost uniform |
| Regrid to 250 m | **Nearest** (500 → 250) | Nearest | Already on ~250 m | Nearest | Nearest — 1–4 blocks / city |
| 0–1 normalization | Burn-year frequency or count classes (below) | Robust count (GFD-style), **not** raw city min–max | City or climatological invert of P10 | P90 VPD classes or percentile | **EFFIS FWI classes** |
| Nodata | Water / unmapped QA | Non-fire pixels = 0 (not nodata) | Cloud-filled composites | Water | Water |
| Update | Monthly lag | NRT daily | Ongoing | Monthly lag | Daily |
| MN + Brazil + C40 | Yes | Yes | Yes | Yes | Yes |
| Cross-city comparable | Frequency **yes**; city min–max of counts **no** | Same | City min–max **no** | Classes / percentiles **yes** | Classes **yes**, useless intra-city |

---

## 5) Normalization families (checklist)

| Input | Family | Cross-city? | Why |
|-------|--------|-------------|-----|
| MCD64A1 burn-year frequency | **Already 0–1** (`n_years_burned / n_years`) | Yes | Physical: “burned in X% of years” |
| Optional: ever-burned mask | **Binary** | Yes | GFPLAIN analog for WUI edges |
| FIRMS detection count | **Robust** P95 + `log1p` on a **regional** window, or fixed count bins — **not** city min–max | Regional/fixed: yes. City min–max: no | Same failure mode as GFD in a quiet city |
| FWI | **Fixed EFFIS classes** | Yes | Flood-depth pattern |
| VPD | **Fixed physical ramp** or climatological P90 class | Yes if classes | Named index; units kPa |
| NDVI dryness | City-domain min–max of `1 − NDVI_P10` **or** reuse landslide `lack_of_veg` | No if city min–max | Same as landslide veg |

### 5.1 MCD64A1 → occurrence score

Per month: `burned = BurnDate ≥ 1` (exclude water / persistent-hotspot QA).

```text
burn_years = count of distinct years with ≥1 burned month, 2015–2024
burn_freq  = burn_years / 10
```

`burn_freq` is already in [0, 1]. In Minnesota metros expect mostly 0; that is correct, not a bug. Do **not** stretch the city’s max burn pixel to 1.0.

Optional binary `burned_once` for QA (flood `gfd_observed_once` analog).

### 5.2 FIRMS → hotspot intensity

Count detections with `confidence ≥ 50` (tune in spike), 2015–2024, on the 1 km FIRMS grid. Then GFD-style:

```text
firms_norm = minmax_roi( log1p( min(count, P95) ) )
```

**Domain for min–max:** regional (Minnesota union, or a 50 km buffer), **not** the city AOI — otherwise one flare dominates Plymouth. If regional stats are not ready (normalization decision Option 1 still a spike), use **fixed bins** instead:

| Detections in 10 years (1 km cell) | Score |
|-------------------------------------|-------|
| 0 | 0.00 |
| 1–2 | 0.25 |
| 3–5 | 0.50 |
| 6–12 | 0.75 |
| >12 | 1.00 |

### 5.3 EFFIS FWI classes (if CEMS is used)

Daily FWI → share of days 2015–2024 at least **high**:

| FWI | EFFIS class | Score contribution |
|-----|-------------|--------------------|
| < 11.2 | very low / low | 0 |
| 11.2–21.3 | moderate | 0.25 |
| 21.3–38 | high | 0.50 |
| 38–50 | very high | 0.75 |
| > 50 | extreme | 1.00 |

```text
fwi_freq = mean( I(FWI_class ≥ 0.50) )   # share of days at least high
```

### 5.4 VPD (v1 GEE path)

TerraClimate `vpd` (apply scale 0.01 → kPa). Heat-analog: **P90 of warm-season months** (JJA in MN, DJF in southern Brazil).

Proposed ramp (literature-style dryness, tune in spike):

```text
vpd_score = clamp01( (VPD_P90 − 0.8) / 1.6 )   # 0.8–2.4 kPa
```

Or class the P90 the same way as SPEI: keep units, do not city-min-max.

### 5.5 Vegetation dryness

Reuse landslide NDVI P10 (season from site YAML: JJA in MN).

```text
fuel_dry = 1 − minmax_norm(NDVI_P10)    # or 1 − veg_protect from existing raster
```

City min–max here is acceptable for **in-city fuel contrast** (parks vs turf vs remnant woodland), matching landslide. Document: not comparable across cities.

---

## 6) v1 ensemble (analogous to flood / heat / landslide)

Mirror flood: weighted sum, **renormalize over available layers**, `min_layers`, band `n_layers_used`.

### 6.1 Recommended v1 (three ticket families)

| Layer | Source | Weight | Ticket family |
|-------|--------|--------|----------------|
| `burn_freq` | MCD64A1 | **0.35** | Historical occurrence (footprint) |
| `firms_norm` | FIRMS MODIS | **0.20** | Historical occurrence (hotspots; catches fires MCD64 misses) |
| `fuel_dry` | MODIS NDVI P10 | **0.25** | Vegetation dryness |
| `vpd_score` | TerraClimate VPD | **0.20** | Fire-risk index (VPD; FWI deferred) |

```text
H = clamp01( sum(w_i × layer_i) / sum(w_i present) )
min_layers = 2
```

Coverage rule (flood analog, inverted): occurrence may be all-zero in a wet metro. **Do not** require a burned pixel. Require at least **fuel or fire-weather** so H remains a susceptibility map.

### 6.2 Land-cover modifier (after combination)

Dynamic World mode (already extracted):

```text
if DW in {1=trees, 2=grass, 5=shrub} AND adjacent to built (class 6) within 500 m:
    H = H + 0.10          # WUI boost
if DW == 6 (built) AND no burnable neighbor:
    H = H × 0.50          # core urban dampen (not a wildland fire cell)
H = clamp01(H)
```

This is qualitative, like landslide’s +0.10 bare/built-on-slope. Thresholds belong in `models/wildfire_hazard/config.yaml`.

### 6.3 Explicitly not in v1 core

- CEMS FWI as an ensemble member until a CDS extract exists and QA shows it is not an ERA5-style smear (optional flag `include_fwi`, default off).
- VIIRS GEE NRT as the climatology (too short); optional 2023–present QA overlay.
- GFED, GRACE, LANDFIRE/MTBS as global v1 inputs.
- Fire-spread / flame-length models (FlamMap, LANDFIRE).

### 6.4 Grid, extract, publish

| Stage | Pattern to copy |
|-------|-----------------|
| Extract | Heat/landslide GEE clip to `sites/{city}/boundary`; new collections MCD64A1 + FIRMS; reuse NDVI + Dynamic World; TerraClimate VPD alongside drought PDSI |
| Compute | `compute_wildfire_hazard.py` + `models/wildfire_hazard/config.yaml` |
| Grid | 250 m (flood/heat). Nearest for MCD64A1 / FIRMS / VPD; NDVI already ~250 m |
| Risk | Existing ACS E/V; clone heat risk |
| Catalog | `{city}_wildfire_hazard`, `{city}_wildfire_risk`; note mixed comparability (freq/classes vs city NDVI) |

---

## 7) Recommendation (squad)

**Use for v1:** **NASA MCD64A1** (burned-area frequency) and **NASA FIRMS MODIS** (hotspot intensity), plus **MODIS NDVI P10** (fuel dryness, already in pipeline) and **TerraClimate VPD** (fire-weather index that is actually GEE-native at ~5 km).

**NASA datasets (ticket):** MCD64A1 + FIRMS. Both global, GEE, monthly/daily, GeoTIFF path identical to MODIS LST / NDVI.

**Named FWI product:** keep **CEMS GEFF FWI** on the shortlist behind `include_fwi`, same gate as ERA5 in heat. It is the right *index*, wrong *city resolution*. VPD is the knowledge-base partner index and does not need a new CDS pipeline.

**Why this set**

1. Covers all three ticket families (occurrence, risk index, vegetation dryness).
2. Occurrence is 500 m–1 km — usable WUI signal, unlike drought SPEIbase.
3. Reuses NDVI, Dynamic World, and TerraClimate extracts already justified for landslide/drought.
4. Normalization can stay **physical** for burns/FWI/VPD; city min–max only for NDVI fuel contrast.
5. Smallest new GEE work: two fire collections (MCD64A1, FIRMS).

**Expected limitation:** inside Twin Cities / Rochester cores, `burn_freq` and FIRMS will be near zero after hotspot filtering. `H` will be driven by **fuel + VPD + WUI modifier**. That is susceptibility, not “this pixel burned.” Do not market it as historical fire probability. Agricultural / Cerrado / Mediterranean C40 cities will show much stronger occurrence layers — the ensemble is meant to transfer without changing weights on day one, then recalibrate.

---

## 8) Spike before implementation (Minnesota)

1. Extract MCD64A1 `burn_freq` (2015–2024 and 2001–2024) and FIRMS counts for **Rochester** and **Plymouth**.
2. Count native 500 m / 1 km pixels with burns; inspect persistent industrial hotspots (Rochester / metro).
3. Overlay existing NDVI P10 and TerraClimate VPD P90 (JJA); confirm WUI fringe vs downtown.
4. Compare fixed FIRMS bins vs city min–max vs Minnesota-regional min–max.
5. Optional: one CEMS FWI raster — if it is a single blob, leave `include_fwi` off.
6. If accepted: `models/wildfire_hazard/{config.yaml,model_card.md}` and `transformation/wildfire_hazard/` per the new-hazard checklist.

---

## 9) Ticket checklist (wildfire)

- [x] ≥2 global datasets with URL, resolution, access
- [x] Pipeline compatibility (format, regrid, 0–1)
- [x] Methodology notes analogous to flood/heat/landslide
- [ ] Squad review of v1 dataset choice (this doc)

CC-648 drought + wildfire exploration docs: **complete**. Implementation is a separate ticket.

---

## 10) Sources

- MCD64A1 GEE: <https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MCD64A1>
- FIRMS GEE: <https://developers.google.com/earth-engine/datasets/catalog/FIRMS>
- FIRMS (NASA): <https://firms.modaps.eosdis.nasa.gov/>
- VIIRS NRT GEE: <https://developers.google.com/earth-engine/datasets/catalog/NASA_LANCE_SNPP_VIIRS_C2>
- TerraClimate GEE: <https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_TERRACLIMATE>
- CEMS fire danger (CDS): <https://ewds.climate.copernicus.eu/datasets/cems-fire-historical-v1?tab=overview>
- Vitolo et al. (2020), ERA5-based global meteorological wildfire danger maps, *Scientific Data*
- Giglio et al., MCD64A1 ATBD / MODIS burned area
- Sibling drought note: [ccra_drought_hazard_exploration.md](./ccra_drought_hazard_exploration.md)
