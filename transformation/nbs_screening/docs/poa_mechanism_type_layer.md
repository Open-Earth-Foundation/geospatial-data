# POA `*_mechanism_type` layer — methodology, gap-fill, and limitations

**Notebooks:** [`nbs_site_query_flood_e2e.ipynb`](../scripts/nbs_site_query_flood_e2e.ipynb) · [`nbs_site_query_heat_e2e.ipynb`](../scripts/nbs_site_query_heat_e2e.ipynb) · [`nbs_site_query_landslide_e2e.ipynb`](../scripts/nbs_site_query_landslide_e2e.ipynb)  
**Code:** [`grid_screening.py`](../scripts/grid_screening.py) · [`nbs_rules.py`](../scripts/nbs_rules.py) · [`catalog_layers.py`](../scripts/catalog_layers.py)  
**Catalog:** `geospatial-data/catalog/datasets.yaml` (`poa_flood_mechanism_type`, `poa_heat_mechanism_type`, `poa_landslide_mechanism_type`)

---

## 1. What this layer is

A **categorical raster** that assigns each pixel a **dominant risk mechanism** used in NBS screening (not flood depth or absolute temperature).

| Hazard | Attribute | Grid | Classes |
|--------|-----------|------|---------|
| Flood | `flood_mechanism_type` | 250 m | `none`, `riverine`, `pluvial`, `low_lying`, `drainage_constrained`, `mixed` (0–5) |
| Heat | `heat_mechanism_type` | 250 m | `without_clear_dominant`, `uhi_built_up`, `shade_deficit`, `high_daytime_lst`, `limited_nocturnal_cooling`, `high_social_exposure`, `mixed` (0–6) |
| Landslide | `landslide_mechanism_type` | **90 m** | `without_clear_dominant`, `steep_activatable_slope`, `rainfall_trigger`, `low_cohesion_wet`, `vegetation_deficit`, `drainage_saturation`, `disturbed_bare_slope`, `upslope_convergence`, `high_social_exposure`, `mixed` (0–9) |

**Spatial unit:** one pixel on the OEF reference hazard grid (`flood_hazard` / `heat_hazard` / `landslide_hazard` COGs).

**Landslide screening gate:** only pixels with **landslide hazard > 0** (slope activation gate in OEF methodology).

**Intended use:** **screening / prioritization** layer on the platform (tiles + COG), consistent with ON-5990. It does not replace hydrological studies, municipal drainage networks, or thermal comfort models.

---

## 2. Two-phase pipeline (observed + gap-fill)

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE A — Direct screening (hazard-valid pixels only)                   │
│   enumerate_raster_cells → screen_grid → rule-based classification      │
│   Output: observed.tif + per-mechanism strength grids                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PHASE B — IDW gap-fill (pixels outside hazard coverage)                 │
│   Interpolate 0–1 strengths from neighbors → reclassify dominant type   │
│   Output: filled.tif (tile product) + is_interpolated.tif               │
└─────────────────────────────────────────────────────────────────────────┘
```

### POA scale (flood, current reference grid)

| Metric | Approx. value |
|--------|----------------|
| Pixels on 250 m grid | **19,328** (128 × 151) |
| Hazard-valid pixels (direct screening) | **~15,394** (~80%) |
| Gaps (IDW only, no per-cell screening) | **~3,934** (~20%) |
| Heat POA | ~19,177 hazard-valid; IDW gaps ≈ 0 |
| Landslide POA | ~3,716 hazard-active (H > 0) on 90 m grid; IDW fills flat/lowland gaps |

**Publication product:** always use the **filled** raster (`flood_mechanism_type_poa_250m.tif`), not observed alone.

---

## 3. Cell enumeration (one pixel = one cell)

Previously, `rasterio.features.shapes()` merged contiguous pixels with the same hazard value into **mega-polygons** (~4,900 “cells” instead of ~19,300 pixels). That caused:

- A few classified cells “painting” large areas of the TIF.
- GeoJSON counts inconsistent with the map.

**Fix:** `enumerate_raster_cells()` walks every pixel in the AOI window on the reference grid. Each cell has `row`, `col`, `cell_id` (`r{row}_c{col}`), pixel polygon, and `hazard_valid` flag.

TIF export indexes by `(row, col)` — **not** polygon rasterization — so codes stay 1:1 with the hazard grid.

---

## 4. Phase A — Direct screening

### 4.1 Which cells are screened

For POA (`screen_poa_*_mechanism_grid`):

- `require_hazard_valid=True` → only pixels where the reference hazard has a valid value.
- Gap cells are **not** screened one-by-one (avoids hours of redundant S3 reads; IDW gap-fill covers them).

For bairros (`screen_bairro_grid`): same default criterion within the bairro polygon.

### 4.2 Layers sampled per cell

**Required (VALUE_RASTERS):** hazard, exposure, vulnerability, risk, and hazard-specific proxies (`gfplain`, `depression_mask` for flood; heat equivalents for heat).

**Optional with `sample_catalog=True` (POA flood):** HAND, GHSL built-up, Dynamic World 250 m, JRC occurrence/seasonality.

**Shared AOI context:** e.g. CHIRPS heavy-rain signal (`flood_grid_shared_context`).

**Water:** distance to nearest OSM waterway (`porto-alegre-rivers.json`), with STRtree spatial index.

### 4.3 Classification rules

Per cell:

1. **Continuous 0–1 strengths** per mechanism (`flood_mechanism_strengths` / heat equivalent) from proxies.
2. **Dominant type** (`classify_from_strengths`): highest strength if ≥ `min_strength` (heat/landslide default **0.15**, flood **0.2**); if two are within `mixed_band` (**0.15**) → `mixed`; if none meet threshold → heat/landslide `without_clear_dominant` / flood `none`.

Flood examples (see [`nbs_rules.py`](../scripts/nbs_rules.py) for exact thresholds):

| Mechanism | Primary signals |
|-----------|-----------------|
| Riverine | OSM waterway &lt; 500 m or intersection |
| Pluvial | Built-up / impervious + CHIRPS signal |
| Low-lying | Floodplain, DEM depression, low HAND, JRC water |
| Drainage constrained | Runoff proxy + moderate HAND, weak riverine |

**Important:** `riverine=True` (boolean flag) and `flood_mechanism_type=none` can coexist: the flag uses distance &lt; 500 m; the dominant type requires strength ≥ 0.2.

### 4.4 Performance optimization (preload)

POA screening preloads **one in-memory window** per COG (`RasterLayerCache`) for the city bbox (~0.1 MB/band for 250 m layers). Each cell is then an index lookup — **~15k cells in ~1–2 min** after the initial S3 preload.

Default POA parameters:

- `preload_layers=True`
- `zonal_fallback=False` (no per-cell `mask()` over S3)
- `include_nbs=False` in `BUILD_POA_LAYER` (mechanism only, no NBS ranking)

---

## 5. Phase B — IDW gap-fill

### 5.1 Why gaps exist

The OEF **hazard** raster does not cover 100% of the POA bbox (nodata on ~20% of flood pixels). Those pixels remain on the 250 m grid but **have no direct screening** because the reference cell has no valid hazard.

For **heat**, hazard coverage is ~100%; IDW adds few or zero pixels.

### 5.2 What is interpolated (and what is not)

We **do not** interpolate the categorical code directly.

1. Build **strength** grids (float 0–1) per mechanism on observed pixels only.
2. For each gap pixel, interpolate all **four** flood strengths (or five heat strengths) with **IDW** in local metric coordinates.
3. Apply the **same** `classify_from_strengths` function as direct screening.
4. Write the resulting code to `filled.tif`; `is_interpolated.tif = 1` marks filled pixels.

### 5.3 IDW parameters (defaults in `grid_screening.py`)

| Parameter | Value | Role |
|-----------|-------|------|
| `MECHANISM_IDW_MAX_DIST_M` | 750 m | Max distance to observed neighbors |
| `MECHANISM_IDW_MIN_NEIGHBORS` | 3 | Minimum neighbors within radius |
| `MECHANISM_IDW_K_NEIGHBORS` | 32 | Neighbors queried in k-d tree |
| `MECHANISM_IDW_POWER` | 2.0 | Weight ∝ 1 / dist² |

If a gap has fewer than 3 neighbors within 750 m, it **stays nodata** (255) in the filled raster.

### 5.4 Gap-fill assumptions

- Mechanism at the hazard edge is **spatially continuous** in strength space (nearby neighbors are representative).
- Gaps are **small and peripheral**, not large interior areas with unobserved distinct mechanisms.
- Post-IDW reclassification uses the same thresholds (0.2 / mixed 0.15) as direct screening — no relaxed rules in gaps.

---

## 6. Output products

| File | Content |
|------|---------|
| `*_poa_250m_observed.tif` | Direct screening only (hazard-valid) |
| `*_poa_250m.tif` | **Observed + IDW** — use for maps and tiles |
| `*_is_interpolated_poa_250m.tif` | 1 = IDW pixel; 0 = observed |
| `*_poa_250m.geojson` | Screened cells (attributes + strengths); IDW gap cells may not appear as features until a later export step |

**Raster nodata:** `255` (`MECHANISM_RASTER_NODATA`). Code **0 = `none`** is a valid class, not nodata.

**Open-water mask:** Before IDW and on final exports, permanent open water (Lago Guaíba and other JRC GSW water bodies) is set to nodata. The mask aligns JRC GSW **transition class 1** (permanent water) and **occurrence ≥ 90%** to the 250 m reference grid (same convention as WRI Aqueduct POA hazard layers). Masked pixels are excluded from IDW as both sources and fill targets.

**Publication:** `PUBLISH_POA_*_COG_TILES` cell → COG EPSG:3857 + visual/value tiles + GeoJSON upload to S3. Catalog `assets.download` includes `cog_url` (map product) and `geojson_url` (screened-cell attributes).

**Symbology:** `mixed` uses `MECHANISM_MIXED_COLOR` (`#8e0152`, dark magenta) in `nbs_rules.py` — signals multiple competing mechanisms, not a neutral “low concern” gray.

---

## 7. Limitations and caveats

### Data and rules

- **Exploratory screening**, not engineering: rules from global/catalog proxies, not calibrated to POA events.
- **`drainage_constrained`** is a proxy until municipal drainage data exists.
- **OSM waterways** is a local sample; distances are approximate (degrees × 111 km).
- **Risk / exposure / vulnerability** COGs may be nodata at centroids; POA runs skip zonal fallback (mechanism may be `none` or rely on other proxies).
- Layers at different resolutions (30 m, 90 m, 250 m) are sampled at the 250 m pixel centroid.

### IDW and coverage

- Filled gaps have **no local hazard evidence**; they inherit context from observed neighbors.
- IDW can **smooth** transitions and produce `mixed` in bands where direct screening would be more binary.
- Pixels without enough neighbors remain nodata 255 in filled.
- Does not extrapolate “new” mechanisms — only combines strengths already observed in the city.

### Product and platform

- POA GeoJSON lists ~15k observed cells; the **filled TIF** is the source of truth for full coverage (~19k).
- Comparing GeoJSON vs TIF counts without filtering `is_interpolated` can be misleading.
- Heat: layer is almost entirely observed; flood: distinguish observed vs interpolated in QA.

### Performance (lesson learned)

Screening **19k cells** with **per-cell** S3 reads and zonal fallback took **~16 s/cell** (~85 h total). The current architecture (preload + hazard-valid only + IDW) reduces that to **minutes**.

---

## 8. Recommended QA

1. Compare `observed` vs `filled`: `filled_n - observed_n` ≈ IDW pixel count (~3.9k flood).
2. Inspect `is_interpolated` at the hazard edge — should not appear as large interior patches.
3. Sample cells with `mechanism_type=none` but `riverine=True` in attributes — expected due to 0.2 threshold.
4. Verify the TIF has no single-mechanism “blobs” in heterogeneous areas (mega-polygon bug regression).
5. After publishing, decode value tiles with the catalog formula (`mechanism_code = encoded - 1`).
6. Confirm open-water areas (Lago Guaíba) are nodata 255 in filled TIF, not mechanism classes.

---

## 9. How to reproduce

```text
# Flood POA
Notebook → BUILD_POA_LAYER = True
         → export_poa_flood_mechanism_layers()
         → PUBLISH_POA_COG_TILES = True

# Heat POA (same cascade; IDW usually marginal)
Heat notebook → BUILD_POA_HEAT_LAYER = True

# Landslide POA (90 m; hazard > 0 gate)
Landslide notebook → BUILD_POA_LANDSLIDE_LAYER = True
```

Advanced overrides in `screen_poa_flood_mechanism_grid()`:

```python
screen_poa_flood_mechanism_grid(
    sample_catalog=True,       # False = fewer layers, faster, less pluvial/low_lying detail
    require_hazard_valid=True, # False = not recommended; re-screens gaps with no benefit
    preload_layers=True,
    zonal_fallback=False,
)
```

---

## 10. Cross-references

- [`nbs_site_query_flood_e2e.md`](nbs_site_query_flood_e2e.md) — bairro + grid workflow
- [`flood_nbs_dataset_lens.md`](flood_nbs_dataset_lens.md) — flood mechanism proxies
- [`heat_nbs_dataset_lens.md`](heat_nbs_dataset_lens.md) — heat proxies
- [`nbs_recommendation_rules_expert_review.md`](nbs_recommendation_rules_expert_review.md) — thresholds for expert review
