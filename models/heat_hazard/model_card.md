# Heat Hazard Score — Model Card

## 1) Purpose and scope

This document describes how the **heat hazard score (`H`)** is computed in `transformation/heat_hazard/heat_hazard_score.ipynb`. It was first implemented for Porto Alegre (POA) and is now organized as a reusable multi-city workflow under `transformation/heat_hazard/sites/<city_slug>/`.

Default ensemble parameters live in `models/heat_hazard/config.yaml`; city overrides live in `transformation/heat_hazard/config/sites/<city_slug>.yaml`.

`H` represents the spatial distribution of chronic heat exposure during the austral summer (December–February, DJF) based on an ensemble of remotely-sensed and modelled thermal products. It is used as the hazard component of the broader risk framework:

```
R = (H × E × V)^(1/3)
```

This is a **screening-level composite index** for prioritization and communication — not a full IPCC-style hazard metric (no return-period analysis, no modelled heat stress thresholds linked to health outcomes).

---

## 2) Conceptual model

Heat hazard is captured through multiple complementary data sources operating at different spatial scales. Each source is independently normalized to [0, 1] and then combined into a single ensemble score.

| Component | Symbol | Temporal scope | Native resolution | Role |
|-----------|--------|----------------|-------------------|------|
| Landsat 8 P90 LST | `LST_L8` | DJF 2015–2024 | 30 m | High-resolution surface temperature; captures fine-grained urban heat patterns |
| MODIS Day P90 LST | `LST_MD` | DJF 2015–2024 | ~1 km | Daytime thermal stress; broader spatial context for peak surface temperatures |
| MODIS Night P90 LST | `LST_MN` | DJF 2015–2024 | ~1 km | Nocturnal heat stress; critical for health recovery; captures urban heat island effect at night |

The ensemble score per pixel is the arithmetic mean of all valid normalized layers:

```
H_pixel = mean(LST_L8_norm, LST_MD_norm, LST_MN_norm)
```

Pixels with fewer than 2 valid layers are masked as no-data.

---

## 3) Input datasets and processing

### 3.1 Landsat 8 Land Surface Temperature (30 m)

| Item | Detail |
|------|--------|
| Source | Google Earth Engine — `LANDSAT/LC08/C02/T1_L2` |
| Band | `ST_B10` (surface temperature, Band 10) |
| Period | DJF seasons 2015–2024 (10 summers) |
| Preprocessing | Scale factor applied (`0.00341802 × DN + 149.0`); cloud mask via `QA_PIXEL` bits 1–4 (cloud, cloud shadow, snow) |
| Metric | **90th percentile (P90)** composite over all valid DJF observations |
| Anomaly | P90 minus the POA-wide mean P90 value |
| Normalization | Min-max normalization of the P90 layer to [0, 1] |
| Output | `lst_lc08_norm_djf_2015_2024_poa.tif` (30 m GeoTIFF, EPSG:4326) |
| Script | `lst_landsat8.ipynb` |

The P90 composite is used instead of a temporal mean to emphasize the recurrent peak-heat signal that drives health impacts, rather than average conditions.

### 3.2 MODIS LST Day and Night (~1 km)

| Item | Detail |
|------|--------|
| Source | Google Earth Engine — `MODIS/061/MOD11A2` |
| Bands | `LST_Day_1km`, `LST_Night_1km` |
| Period | DJF seasons 2015–2024 (10 summers) |
| Preprocessing | Scale factor applied (`× 0.02`); quality mask via `QC_Day` / `QC_Night` bits 0–1 (only "good quality" retained) |
| Metric | **P90 composite** over all valid DJF observations |
| Anomaly | P90 minus the POA-wide mean P90 |
| Normalization | Min-max normalization of each P90 layer to [0, 1] |
| Outputs | `mod11a2_lst_day_norm_djf_2015_2024_poa.tif`, `mod11a2_lst_night_norm_djf_2015_2024_poa.tif` (1 km GeoTIFF, EPSG:4326) |
| Script | `MOD11A2.ipynb` |

Day and night LST are treated as separate independent layers in the ensemble. Night temperature captures the absence of thermal recovery — a key health risk factor — that is not visible in daytime-only products.

---

## 4) Layer excluded from the ensemble — ERA5-Land

An earlier version of the methodology included ERA5-Land hourly 2-m air temperature (`t2m`) from the Copernicus CDS to compute an **extreme heat frequency** metric (annual fraction of DJF days where daily T_max exceeds the local P90 threshold).

**ERA5-Land was ultimately excluded from the ensemble** for the following reason:

> ERA5-Land has a native spatial resolution of approximately **9 km**. Over the Porto Alegre metropolitan area, this translates to only **3 × 3 pixels**. Resampling these 9 coarse pixels to a 250 m working grid does not create new spatial information — it simply tiles or smoothly interpolates the same few values across thousands of fine pixels, producing a spatially-uniform or banded pattern that does not reflect real intra-urban thermal variability. This artefact — where an interpolated smooth gradient masks the absence of real spatial signal — would dilute the sharper urban heat contrasts captured by Landsat and MODIS, reducing the overall discriminating power of the hazard score at the neighborhood level.

ERA5-Land remains a valid product for regional-scale or national analyses. For this city-scale application in Porto Alegre, Landsat 8 (30 m) and MODIS (1 km) provide sufficient coverage and spatial resolution.

| Product | Native res. | POA pixel count | Included |
|---------|-------------|-----------------|----------|
| Landsat 8 | 30 m | ~1.3 M | Yes |
| MODIS MOD11A2 | 1 km | ~1,250 | Yes |
| ERA5-Land | ~9 km | ~9 | **No** |

---

## 5) Resampling to common grid

All active layers are reprojected and resampled to a common **250 m grid** consistent with the flood hazard score grid, covering the POA bounding box (lon: −51.303° to −51.019°, lat: −30.269° to −29.932°).

| Layer | Direction | Method | Rationale |
|-------|-----------|--------|-----------|
| Landsat 8 (30 m → 250 m) | Downsampling | Bilinear | Averages sub-pixel values; appropriate when aggregating fine to coarse |
| MODIS Day/Night (1 km → 250 m) | Upsampling | Nearest neighbour | Repeats the original coarse pixel value; does not invent intermediate values |

Nearest-neighbour resampling for MODIS ensures that the blocky appearance of 1 km pixels is preserved at 250 m, making it visually clear where the original spatial resolution limits the data — rather than implying false precision through smooth interpolation.

---

## 6) Ensemble combination

Once all layers are on the 250 m grid, the ensemble score is computed pixel-by-pixel:

```python
H_pixel = nanmean(LST_L8_norm, LST_MD_norm, LST_MN_norm)
```

- Equal weights are applied to all three layers.
- Pixels with fewer than 2 valid layers are masked as no-data.
- The result is clipped to [0, 1].

### Output rasters

| File | Description |
|------|-------------|
| `heat_hazard_score_poa.tif` | Pixel-level ensemble score (0–1), 250 m, EPSG:4326 |
| `heat_hazard_n_layers_poa.tif` | Valid layer count per pixel (QA band), 250 m |
| `heat_hazard_score_poa.gpkg` | Bairro-level mean hazard score (Censo 2022 boundaries, n = 94) |

---

## 7) Barrio aggregation

The pixel-level ensemble is spatially averaged (mean zonal statistic) within each POA bairro using Censo 2022 neighborhood boundaries (n = 94). The resulting per-bairro `H` value is used as input to the risk equation `R = (H × E × V)^(1/3)`.

---

## 8) Limitations

| Limitation | Notes |
|------------|-------|
| Land Surface Temperature ≠ Air Temperature | LST (radiometric skin temperature of the surface) differs from the 2-m air temperature experienced by people. High LST in paved or industrial areas does not automatically translate to the same air temperature for pedestrians. |
| Summer-only period | The analysis covers DJF only. Spring or early autumn heat events are not captured. |
| Cloud cover | Optical/thermal sensors (Landsat, MODIS) cannot observe through clouds. The P90 composite mitigates this by using multi-year data, but areas with persistent DJF cloud cover will have fewer valid observations. |
| Spatial resolution | MODIS pixels (1 km) cannot resolve individual streets or buildings. The 250 m working grid preserves but does not improve the 1 km spatial detail. |
| No air temperature validation | The score has not been validated against in-situ meteorological station records or health outcome data for Porto Alegre. |

---

## 9) Web tile outputs (COG + XYZ tiles)

After the raster is exported, a second pipeline converts `heat_hazard_score_<site>.tif` into formats optimized for web map delivery. All outputs are written to `sites/<site_slug>/out/heat_hazard_score/`.

### Pipeline steps

| Step | Tool | Output |
|------|------|--------|
| 1 | `gdal_translate -of COG` | `heat_hazard_score_cog.tif` — float32 COG, DEFLATE compressed, with auto overviews |
| 2 | `gdaldem color-relief` | `heat_hazard_score_colorized.tif` — RGBA raster using `heat_hazard_colors.txt` |
| 3 | `gdal2tiles.py -z 8-15 --xyz` | `tiles_visual/` — PNG XYZ tiles for visual rendering |
| 4 | `gdal_calc.py` + `gdal2tiles.py` | `heat_hazard_score_value_encoded_rgb.tif` + `tiles_values/` — value-encoded tiles for hover lookup |

### Color palette (`heat_hazard_colors.txt`)

RdYlGn reversed: green (low hazard) → yellow (medium) → red (high hazard), consistent with the visual representation in the interactive map.

| Score | Color |
|-------|-------|
| 0.00 | `#1a9641` (green) |
| 0.25 | `#a6d96a` (light green) |
| 0.50 | `#ffffbf` (yellow) |
| 0.75 | `#fdae61` (orange) |
| 1.00 | `#d7191c` (red) |

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

## 10) Traceability

| Script | Input | Output |
|--------|-------|--------|
| `transformation/landsat_lst/release/v1/lst_landsat8.ipynb` | GEE `LANDSAT/LC08/C02/T1_L2` | site-specific Landsat normalized LST |
| `transformation/modis_lst/release/v1/MOD11A2.ipynb` | GEE `MODIS/061/MOD11A2` | site-specific MODIS day/night normalized LST |
| `transformation/era_land/release/v1/era5_land.ipynb` | Copernicus CDS `reanalysis-era5-land` | site-specific ERA5 heat-wave frequency *(optional)* |
| `transformation/heat_hazard/heat_hazard_score.ipynb` | The normalized TIFs above | `transformation/heat_hazard/sites/<city>/data/output/` |
| `models/heat_hazard/config.yaml` | defaults | weights, min_layers, include_era5, target resolution |
