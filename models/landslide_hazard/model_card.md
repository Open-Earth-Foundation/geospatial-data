# Landslide Hazard Score — Model Card

## 1) Purpose and scope

This document describes how the **landslide hazard score (`H`)** is computed in `transformation/landslide_hazard/landslide_hazard_score.ipynb`.

Default ensemble parameters live in `models/landslide_hazard/config.yaml`; city overrides live in `transformation/landslide_hazard/config/sites/<city_slug>.yaml`.

It was first implemented for Porto Alegre (POA) and is now organized as a reusable multi-city workflow under `transformation/landslide_hazard/sites/<city_slug>/`. Season for NDVI/R90p is city-configured (DJF for POA; JJA for Minnesota cities).

`H` represents the spatial distribution of landslide susceptibility based on an ensemble of terrain, climate, soil, vegetation, and drainage layers. It is used as the hazard component of the broader risk framework:

```
R = (H × E × V)^(1/3)
```

This is a **screening-level composite susceptibility index** for prioritization and communication — not a formal hazard model with return periods or failure probability estimates. It identifies areas where terrain and environmental conditions are most conducive to shallow landslides and debris flows.

---

## 2) Relationship to the previous methodology

The prior offline scoring methodology (`recalc-scores-v3.ts`) was audited in `NBS-Project-Preparation/docs/landslide-risk-scoring-methodology-audit.md`. Key limitations identified:

| Issue | Previous approach | This methodology |
|-------|------------------|-----------------|
| Slope resolution | Effective ~1 km (elevation range from 1 km cells) | Copernicus GLO-30 DEM slope at **30 m**, aggregated to 90 m |
| Precip metric | `rx1day` (single extreme event) with arbitrary thresholds (40–120 mm) | **R90p climatology** (90th percentile of daily precip, multi-year) from CHIRPS |
| Vegetation proxy | `vegetation_pct` (mixed 1 km / Dynamic World) | MODIS NDVI **P10** (10th percentile DJF) — captures persistently low vegetation cover |
| Drainage proxy | `1 - low_lying_pct` (crude elevation proxy) | MERIT Hydro **HAND** (Height Above Nearest Drainage) — geomorphologically correct drainage distance |
| H / E / V separation | Not separated — all components collapsed into a single score | Explicit H / E / V framework; hazard-only score here |
| Weight justification | No documented source | Weights documented with geotechnical rationale below |

---

## 3) Conceptual model

Landslide susceptibility is the result of **predisposing factors** (slope, soil, vegetation) combined with **triggering factors** (precipitation) and **amplifying conditions** (drainage convergence, land cover). The score is structured as:

```
H = f(slope_risk, precip_risk, soil_cohesion, vegetation_protection, drainage_accumulation)
  × land_cover_modifier
```

The **slope is the primary gate**: all terrain-interaction terms are multiplied by `slope_risk`, so areas with slope < 15° score zero regardless of other inputs. This is consistent with standard geotechnical activation thresholds for shallow landslides (15–35° range).

### Input layers summary

| # | Component | Layer | Source | Native res. | Role |
|---|-----------|-------|--------|-------------|------|
| 1 | Slope risk | Copernicus GLO-30 slope | GEE `COPERNICUS/DEM/GLO30` | 30 m | Primary driver and activation gate (45%) |
| 2 | Precipitation trigger | CHIRPS R90p climatology | CHIRPS via GEE | ~5 km | Rainfall detonator — high R90p = frequent extreme events (20%) |
| 3 | Soil cohesion | SoilGrids clay % (0–30 cm) | GEE `OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M` | 250 m | Pore pressure amplifier — high clay = lower effective cohesion when saturated (15%) |
| 4 | Vegetation protection | MODIS NDVI P10 DJF 2015–2024 | GEE `MODIS/061/MOD13Q1` | 250 m | Root reinforcement — low NDVI = less slope stabilization (10%) |
| 5 | Drainage accumulation | MERIT Hydro HAND | GEE `MERIT/Hydro/v1_0_1` | 90 m | Soil saturation from upslope drainage — low HAND = near drainage network (10%) |
| 6 | Land cover modifier | Dynamic World mode 2023 | GEE `GOOGLE/DYNAMICWORLD/V1` | 10 m | Qualitative amplifier/dampener based on land use |

---

## 4) Canonical grid — 90 m resolution

All layers are reprojected and resampled to a common **90 m grid** in EPSG:4326 covering the configured city bounding box (`bbox` in the site YAML).

> **Why 90 m?** Landslide initiation zones in Porto Alegre are typically 30–200 m wide. At 250 m, a steep hillslope is averaged out and may fall below the 15° activation threshold, rendering the score insensitive to the actual terrain structure. 90 m matches the native resolution of MERIT HAND and preserves meaningful slope variation derived from the 30 m Copernicus DEM.

For the downstream risk score, the 90 m hazard raster is aggregated to bairro level and combined with the shared 250 m E/V layers.

---

## 5) Input datasets and processing

### 5.1 Slope — Copernicus GLO-30 DEM (30 m → 90 m)

| Item | Detail |
|------|--------|
| Source | GEE `COPERNICUS/DEM/GLO30` |
| Processing | Slope computed in GEE using `ee.Terrain.slope()` on the DEM (degrees from horizontal) |
| Metric | Slope in degrees at 30 m resolution |
| Export | `poa_slope_deg_30m.tif` — 30 m GeoTIFF |
| Script | `slope_from_dem.ipynb` |
| Resampling to grid | `average` (mean slope within each 90 m cell) |

Slope is computed directly in GEE before export to avoid processing the raw DEM locally. Averaging to 90 m is appropriate: it represents the mean slope of the terrain within each analysis cell, rather than the slope at a single point.

### 5.2 Precipitation trigger — CHIRPS R90p climatology (~5 km → 90 m)

| Item | Detail |
|------|--------|
| Source | CHIRPS daily precipitation (1981–present) |
| Metric | **R90p climatology** — the long-run 90th percentile of daily precipitation across all DJF days |
| Spatial coverage | ~5 km native resolution |
| File | `poa_r90p_climatology.tif` |
| Resampling to grid | `nearest` (repeats 5 km pixel value — no interpolation) |

**Why R90p instead of Rx1day?** R90p is a climatological threshold representing recurrent extreme rainfall intensity. It captures the chronic precipitation regime that drives soil saturation and landslide initiation better than a single event maximum (Rx1day), which is highly variable year-to-year.

**Why `nearest` resampling?** Bilinear interpolation from ~5 km to 90 m would create smooth artificial gradients between coarse pixels, implying spatial detail that does not exist in the data. Nearest-neighbour repeats the 5 km value across all 90 m cells within it, honestly representing the resolution limit.

### 5.3 Soil cohesion — SoilGrids clay % (250 m → 90 m)

| Item | Detail |
|------|--------|
| Source | GEE `OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M` |
| Metric | Clay weight fraction (%) at 0–30 cm depth |
| Native resolution | 250 m |
| Export | `poa_clay_pct_250m.tif` |
| Script | `clay_soilgrids.ipynb` |
| Resampling to grid | `bilinear` (upsampling continuous soil variable) |

### 5.4 Vegetation protection — MODIS NDVI P10 (250 m → 90 m)

| Item | Detail |
|------|--------|
| Source | GEE `MODIS/061/MOD13Q1` |
| Band | `NDVI` |
| Period | DJF seasons 2015–2024 (10 summers) |
| Metric | **10th percentile (P10)** of NDVI over all valid DJF composites |
| Export | `poa_ndvi_p10_djf_2015_2024.tif` (250 m) |
| Script | `ndvi_modis.ipynb` |
| Resampling to grid | `bilinear` (upsampling continuous index) |

**Why P10 instead of mean NDVI?** P10 captures the minimum persistent vegetation cover — it identifies areas that are consistently sparsely vegetated even in the most favourable season. Mean NDVI could be elevated by occasional regrowth that does not provide structural root reinforcement.

### 5.5 Drainage accumulation — MERIT Hydro HAND (90 m → 90 m)

| Item | Detail |
|------|--------|
| Source | GEE `MERIT/Hydro/v1_0_1` |
| Band | `hnd` (Height Above Nearest Drainage, meters) |
| Native resolution | 90 m |
| Export | `poa_hand_90m.tif` |
| Script | `hand_merit.ipynb` |
| Resampling to grid | `bilinear` (aligns to canonical grid with no resolution change) |

HAND measures the vertical distance from each pixel to its nearest drainage network cell. Low HAND (0–5 m) indicates proximity to drainage convergence zones where soil saturation from upslope water is most likely. HAND replaces the `low_lying_pct` proxy used in the previous methodology, which was a crude elevation threshold and not geomorphologically related to drainage connectivity.

### 5.6 Land cover modifier — Dynamic World mode composite (10 m → 90 m)

| Item | Detail |
|------|--------|
| Source | GEE `GOOGLE/DYNAMICWORLD/V1` |
| Metric | Mode (most frequent) land cover class in 2023 |
| Classes used | 1=trees, 2=grass, 3=flooded_veg, 5=shrub, 6=built, 7=bare |
| Native resolution | 10 m |
| Export | `poa_dw_mode_2023.tif` |
| Script | `dynamic_world_landslide.ipynb` |
| Resampling to grid | `nearest` (preserves majority class at 90 m) |

---

## 6) Component formulas

Each input is transformed to a 0–1 contribution before combining.

### 6.1 Slope risk (primary gate)

```
slope_risk = clamp01((slope_deg - 15) / 20)
```

- **0** for all slopes below **15°** (stable, no initiation expected)
- **linearly increasing** from 0 to 1 between 15° and **35°**
- **1** at 35° and above (saturation — extremely steep, unconsolidated slopes)

The 15° threshold is a standard geotechnical minimum for shallow landslide initiation in tropical soils (as documented in the existing codebase comments and consistent with literature on tropical debris flows). The 20° ramp width reflects typical failure conditions in Porto Alegre's weathered granite hillslopes.

All other components are **multiplied by `slope_risk`**, ensuring that flat areas score zero regardless of other conditions.

### 6.2 Precipitation trigger

```
precip_risk = minmax_norm(R90p_climatology)
```

Min-max normalization across the POA domain, so the wettest area scores 1 and driest scores 0. This preserves relative spatial variation in chronic extreme rainfall.

### 6.3 Soil cohesion (as lack-of-cohesion amplifier)

```
soil_risk   = clamp01(clay_pct / 40)
low_cohesion = 1 - soil_risk
```

Clay content above **40%** saturates to maximum pore pressure risk. The inverse (`1 - soil_risk`) is used in the combination formula so that low-clay (sandy, low-cohesion) soils amplify slope susceptibility.

### 6.4 Vegetation protection (as lack-of-protection amplifier)

```
veg_protect = minmax_norm(NDVI_P10)
lack_of_veg = 1 - veg_protect
```

Higher P10 NDVI = more root reinforcement = lower susceptibility. The inverse is used in combination.

### 6.5 Drainage accumulation (HAND factor)

```
hand_factor = clamp01(1 - HAND_m / 50)
```

- **HAND = 0 m** (directly on drainage) → `hand_factor = 1.0` (maximum drainage convergence risk)
- **HAND = 50 m** → `hand_factor = 0.0` (ridgetop, no drainage contribution)
- **HAND > 50 m** → clamped to 0

### 6.6 NaN gap filling

Before computing components, missing values are filled with conservative defaults to prevent data gaps from propagating through the formula:

| Layer | Fill value | Resulting component value | Rationale |
|-------|-----------|--------------------------|-----------|
| HAND | 25 m | `hand_factor = 0.50` | Neutral — neither near-drainage nor ridge |
| Clay | 35 % | `soil_risk = 0.875` | Slightly cohesive — conservative for unknown soils |
| NDVI | 0.3 | `veg_protect ≈ 0.3` | Light vegetation — moderate protection |
| R90p | regional median | `precip_risk ≈ 0.5` | Regional average for missing edge pixels |

Slope NaN values are **not filled** — they define the valid data extent. Pixels with no slope data are masked as no-data in the final output.

---

## 7) Weighted combination

```
H = clamp01(
    0.45 × slope_risk
  + 0.20 × precip_risk   × slope_risk
  + 0.15 × low_cohesion  × slope_risk
  + 0.10 × lack_of_veg   × slope_risk
  + 0.10 × hand_factor   × slope_risk
)
```

### Weight rationale

| Component | Weight | Rationale |
|-----------|--------|-----------|
| Slope risk | **0.45** | Dominant physical control on gravitational driving force; primary gate for initiation |
| Precip trigger | **0.20** | Rainfall saturation is the main detonator for shallow landslides; second only to slope |
| Low cohesion (clay) | **0.15** | Soil type controls effective strength reduction under saturation |
| Lack of vegetation | **0.10** | Root reinforcement provides measurable slope stabilization but secondary to soil and precip |
| Drainage accumulation | **0.10** | Subsurface flow convergence amplifies pore pressure in low-HAND zones |

The weights sum to **1.0**. All secondary components are interaction terms (`× slope_risk`), ensuring they only contribute where slope is above the activation threshold.

### Land cover modifiers (applied after combination)

Two qualitative adjustments are applied based on Dynamic World land cover class:

**Bare soil / built-up on slope (+0.10 additive boost):**
```
if DW_class ∈ {6=built, 7=bare} AND slope_deg ≥ 15°:
    H = H + 0.10
```
Impervious or bare surfaces on slopes eliminate infiltration buffering and increase runoff concentration, raising initiation likelihood.

**Dense vegetated areas (×0.85 dampening factor):**
```
if DW_class ∈ {1=trees, 2=grass, 3=flooded_veg, 5=shrub} AND NDVI_P10 > 0.4:
    H = H × 0.85
```
Areas confirmed by both land cover classification and NDVI threshold as persistently vegetated receive a 15% reduction to account for structural root reinforcement not fully captured by the NDVI component alone.

After modifiers, `H` is clamped to [0, 1].

---

## 8) Bairro aggregation

The pixel-level hazard score is spatially averaged (mean zonal statistic) within each POA bairro using Censo 2022 neighborhood boundaries (n = 94). The resulting per-bairro `H` value is used as input to the risk equation `R = (H × E × V)^(1/3)`.

---

## 9) Limitations

| Limitation | Notes |
|------------|-------|
| Susceptibility ≠ hazard frequency | The score captures static predisposing conditions, not the probability of a landslide event in a given year. It does not incorporate return periods or failure probability. |
| Precipitation resolution | CHIRPS R90p has ~5 km native resolution. Spatial variability of extreme rainfall at the neighborhood scale (e.g., orographic enhancement on individual hillslopes) is not resolved. Nearest-neighbor resampling correctly represents this limitation without creating false gradients. |
| Static soil data | SoilGrids provides a single snapshot of clay content. Anthropogenic land use change (excavation, fill, compaction) is not captured. |
| MERIT HAND tile gaps | MERIT Hydro has NoData over water bodies and some tile boundaries. These are filled with a neutral 25 m default, which may under- or over-estimate drainage influence in those areas. |
| Dynamic World vintage | The land cover modifier uses 2023 DW mode composite. Rapid hillslope deforestation or urbanization after 2023 is not reflected. |
| No validation | The score has not been validated against the historical landslide inventory for Porto Alegre (CEMADEN or INMET records). Calibration of the 15°/35° thresholds and component weights to local failure data is recommended as a next step. |
| Equal treatment of failure modes | The formula does not distinguish between shallow translational slides (slope + precip dominant) and rotational failures (soil cohesion dominant) or debris flows (HAND + precip dominant). A multi-mode model would require separate scoring tracks. |

---

## 10) Web tile outputs (COG + XYZ tiles)

After the raster is exported, a second pipeline converts `outputs.landslide_hazard_score` from the city YAML into formats optimized for web map delivery. All outputs are written to `sites/<city>/out/landslide_hazard_score/`.

### Pipeline steps

| Step | Tool | Output |
|------|------|--------|
| 1 | `gdal_translate -of COG` | `landslide_hazard_score_90m_cog.tif` — float32 COG, DEFLATE compressed, with auto overviews |
| 2 | `gdaldem color-relief` | `landslide_hazard_90m_colorized.tif` — RGBA raster using `landslide_hazard_colors.txt` |
| 3 | `gdal2tiles.py -z 8-15 --xyz` | `tiles_visual/` — PNG XYZ tiles for visual rendering |
| 4 | `gdal_calc.py` + `gdal2tiles.py` | `landslide_hazard_90m_value_encoded_rgb.tif` + `tiles_values/` — value-encoded tiles for hover lookup |

### Color palette (`landslide_hazard_colors.txt`)

RdYlGn reversed: green (low susceptibility) → yellow (medium) → red (high susceptibility).

| Score | Color |
|-------|-------|
| 0.00 | `#1a9850` (green) |
| 0.25 | `#a6d96a` (light green) |
| 0.50 | `#ffffbf` (yellow) |
| 0.75 | `#fdae61` (orange) |
| 1.00 | `#d73027` (red) |

### Value-encoding formula

To enable pixel-value lookup on hover in a web map without a server, the float score is packed into three RGB bytes:

```
encoded_int = round(clip(score, 0, 1) × 10000)

R = encoded_int         & 0xFF
G = (encoded_int >>  8) & 0xFF
B = (encoded_int >> 16) & 0xFF
```

**Decode in the front-end application:**

```javascript
score = (R + 256 * G + 65536 * B) / 10000
```

This gives a precision of 0.0001 (4 decimal places), sufficient for a 0–1 score.

---

## 11) Traceability

| Script | Input | Output |
|--------|-------|--------|
| `slope_from_dem.ipynb` | GEE `COPERNICUS/DEM/GLO30` | `poa_slope_deg_30m.tif` |
| `hand_merit.ipynb` | GEE `MERIT/Hydro/v1_0_1` | `poa_hand_90m.tif` |
| `ndvi_modis.ipynb` | GEE `MODIS/061/MOD13Q1` | `poa_ndvi_p10_djf_2015_2024.tif` |
| `clay_soilgrids.ipynb` | GEE `OpenLandMap/SOL/SOL_CLAY-WFRACTION_USDA-3A1A1A_M` | `poa_clay_pct_250m.tif` |
| `dynamic_world_landslide.ipynb` | GEE `GOOGLE/DYNAMICWORLD/V1` | `poa_dw_mode_2023.tif` |
| `landslide_hazard_score.ipynb` §1–9 | The six input TIFs above | `outputs.landslide_hazard_score` from the city YAML, `landslide_hazard_score_poa.gpkg` |
| `landslide_hazard_score.ipynb` §10–11 | `outputs.landslide_hazard_score` from the city YAML, `landslide_hazard_colors.txt` | `landslide_hazard_score/landslide_hazard_score_90m_cog.tif`, `landslide_hazard_score/tiles_visual/`, `landslide_hazard_score/tiles_values/` |
