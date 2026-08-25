# CCRA drought hazard — methodology and dataset exploration

**Status:** Exploration (recommendation for v1, not implemented)  
**Ticket:** [CC-648](https://linear.app/openearth/issue/CC-648/explore-methodology-and-datasets-for-2-additional-hazards-droughts-and)  
**Date:** 2026-08-17  
**Scope of this file:** drought only. Wildfire sibling: [ccra_wildfire_hazard_exploration.md](./ccra_wildfire_hazard_exploration.md).

Related: [ccra_new_hazard_normalization_checklist.md](./ccra_new_hazard_normalization_checklist.md), [ccra_normalization_decision.md](./ccra_normalization_decision.md), [ccra_pipeline_architecture.md](./ccra_pipeline_architecture.md), `models/{flood,heat,landslide}_hazard/model_card.md`.

---



## 1) Purpose

Extend CCRA beyond the three implemented hazards (flood, heat, landslide) with a **city-AOI screening drought score** `H ∈ [0, 1]` that can enter the same risk equation:

```text
R = (H × E × V)^(1/3)
```

This note answers the ticket acceptance criteria for drought:

1. At least two global candidate datasets with URL, resolution, cadence, and access method.
2. Whether each can go through the existing extract → regrid → 0–1 normalize → ensemble → publish path.
3. A v1 methodology analogous to flood / heat / landslide.
4. A squad recommendation.

This is **hazard screening**, not reservoir operations, crop-loss modeling, or a declared drought product.

---



## 2) What we already have (do not restart)


| Asset                       | Role for drought                                                                                                                                                                                                                                                                                                |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CCRA indicator JSON         | Water-resources drought hazard is **SPEI** (present / 2030 / 2050) + **CDD** (max consecutive dry days). See `docs/climate_risk_indicators_by_sector.json`.                                                                                                                                                     |
| `CCRADiscovery/drought/`    | City pilots (Porto Alegre, Manaus, Extrema) on a **~5 km CHIRPS grid**. Monthly `hazard_score` combines `cdd_norm`, `spi3_norm`, `spi12_norm`. From the published CSVs the combination is the arithmetic mean of dry-spell intensity and inverted wetness: `H ≈ mean(cdd_norm, 1 − spi3_norm, 1 − spi12_norm)`. |
| CHIRPS in `geospatial-data` | Already extracted for landslide R90p (`UCSB-CHG/CHIRPS/DAILY` via GEE). Same Level-0 source can yield CDD and SPI.                                                                                                                                                                                              |
| Heat model card §4          | ERA5-Land (~9 km) was **dropped** from the heat ensemble because a city AOI only contains a handful of pixels and bilinear upsampling invents false intra-urban detail. The same constraint applies even more strongly to 0.5° SPEIbase.                                                                        |
| Normalization decision      | Default product stays **city-AOI screening**. Prefer **fixed physical classes** when units are standard (flood depth pattern). City min–max only when there is no defensible cutoff.                                                                                                                            |


---



## 3) Conceptual model (v1 screening)

City drought for CCRA is **chronic meteorological + agricultural water-balance stress**, not a neighborhood-scale process like urban heat or slope failure.

```text
H = f(water_balance_deficit, dry_spell_duration, soil_moisture_deficit)
```


| Component                               | Physical meaning                                     | Analog in current stack                           |
| --------------------------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| Water-balance index (SPEI / PDSI / SPI) | How dry vs the local climate (P − PET, standardized) | Flood depth classes (fixed, literature bins)      |
| CDD                                     | Longest rain-free run (ETCCDI)                       | Heat P90: recurrent extreme, not the mean         |
| Soil moisture (optional NASA)           | Root-zone wetness / agricultural drought             | Landslide clay: independent biophysical amplifier |


**Design constraint (must state in any model card):** meteorological drought is spatially smooth at 4–10 km. A 250 m publish grid (flood/heat) will look blocky if we upsample with **nearest neighbour** — that is honest, same as CHIRPS R90p in landslide. Do **not** bilinear-smooth SPEI/PDSI/SMAP to imply street-level drought.

Intra-city contrast in `R` will come mainly from **E/V** (ACS), not from H. That is acceptable for water-supply / agricultural screening and different from heat (Landsat 30 m UHI).

**Temporal framing (match heat, not a live drought monitor):** composite over ~10 years (e.g. 2015–2024), not a single month. Frequency or upper-tail severity of drought months, then one static `H` raster per city.

Projections (SPEI 2030/2050 in the indicator JSON) are **out of scope for v1 screening**, same as flood/heat/landslide present-day layers.

---



## 4) Candidate datasets



### 4.1 Inventory (ticket: ≥2 global; NASA called out)


| #     | Dataset                                  | Publisher            | Access                                                                                                                             | Native res.             | Cadence                                    | Coverage                                         | Units / signal                                                   | Pipeline fit                                          |
| ----- | ---------------------------------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ------------------------------------------ | ------------------------------------------------ | ---------------------------------------------------------------- | ----------------------------------------------------- |
| **A** | **CHIRPS Daily**                         | UCSB CHG / USGS      | GEE `UCSB-CHG/CHIRPS/DAILY` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)         | ~0.05° (~5.5 km)        | Daily, 1981–present                        | Global 50°S–50°N (covers MN + Brazil + most C40) | Precip mm/day → **SPI-3, SPI-12, CDD**                           | **Yes — already in repo**                             |
| **B** | **TerraClimate**                         | U. Idaho / UC Merced | GEE `IDAHO_EPSCOR/TERRACLIMATE` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_TERRACLIMATE) | ~1/24° (~4.6 km)        | Monthly, 1958–2024                         | Global land                                      | **PDSI**, climate water deficit `def`, soil moisture `soil`, PET | **Yes — same GEE extract pattern as MODIS/CHIRPS**    |
| **C** | **NASA SMAP L4 SPL4SMGP**                | NASA NSIDC           | GEE `NASA/SMAP/SPL4SMGP/008` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008)       | ~9–11 km                | 3-hourly (use monthly/seasonal composites) | Global (post-2015)                               | `sm_rootzone`, `sm_rootzone_pctl` (0–100)                        | **Yes**, but coarse (heat ERA5 lesson)                |
| **D** | **SPEIbase v2.11**                       | CSIC                 | GEE `CSIC/SPEI/2_11` · [catalog](https://developers.google.com/earth-engine/datasets/catalog/CSIC_SPEI_2_11)                       | **0.5° (~55 km)**       | Monthly, 1901–2024                         | Global                                           | SPEI 1–48 month, already standardized                            | Format yes; **city screening no** (1–4 pixels / city) |
| E     | WRI Aqueduct water risk / drought        | WRI                  | Already used for flood `inunriver`; Aqueduct 4 has water-stress / drought indicators                                               | Basin / ~1 km hydrology | Periodic releases                          | Global                                           | Composite water risk, not meteorological drought                 | Partial — different construct                         |
| F     | NASA GRACE / GRACE-FO drought indicators | NASA                 | GEE / Giovanni                                                                                                                     | ~300 km                 | Monthly                                    | Global                                           | Terrestrial water storage anomaly                                | **No** for city AOI                                   |
| G     | US Drought Monitor / GRIDMET             | NOAA / U. Idaho      | CONUS only                                                                                                                         | Fine (GRIDMET ~4 km)    | Weekly / daily                             | **Not global**                                   | Operational US drought                                           | MN-only fallback, not C40/GCoM                        |


Ticket bar is met by **A + B** (and **C** as the NASA soil-moisture dataset). **D** is the named CCRA indicator but fails the city-scale test that already killed ERA5-Land for heat.

### 4.2 Per-dataset pipeline validation

Shared target: GeoTIFF on the city flood/heat **250 m** grid, EPSG:4326, `H ∈ [0, 1]`, COG + XYZ tiles, catalog `{city}_drought_hazard`.


| Check                                  | CHIRPS (A)                                                                     | TerraClimate (B)                 | SMAP L4 (C)                                    | SPEIbase (D)                 |
| -------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------- | ---------------------------------------------- | ---------------------------- |
| Format                                 | GEE ImageCollection → GeoTIFF                                                  | Same                             | Same                                           | Same                         |
| Clip to city boundary                  | Yes (`reduceRegion` / `clip`)                                                  | Yes                              | Yes                                            | Yes, but almost uniform      |
| Regrid to 250 m                        | **Nearest** (do not invent gradients) — same as landslide R90p                 | Nearest                          | Nearest                                        | Nearest — one or two blocks  |
| 0–1 normalization                      | SPI: **WMO classes** (below). CDD: climatological percentile or robust min–max | PDSI: **Palmer classes** (below) | `1 − pctl/100` or drought-class on percentile  | SPEI: WMO classes (portable) |
| Nodata                                 | Oceans / 50°N–S edge                                                           | Water / Antarctica caveats       | Frozen soil / retrieval flags                  | Land only                    |
| Update                                 | Ongoing daily                                                                  | Monthly lag ~months              | Near-real-time                                 | Annual SPEIbase releases     |
| MN + Brazil + C40                      | MN yes (south of 50°N); Brazil yes                                             | Yes                              | Yes (2015+)                                    | Yes                          |
| Cross-city comparable if using classes | SPI/SPEI **yes**; CDD city min–max **no**                                      | PDSI **yes**                     | Percentile **yes** (already local climatology) | Yes, but useless intra-city  |


---



## 5) Normalization families (checklist)

Do **not** city-min-max SPEI/PDSI/SPI. They are already anomalies vs local climate. Stretching them inside Plymouth would destroy the physical meaning (“−1.5 = moderate drought everywhere”).


| Input                     | Family                                                                                                                 | Cross-city?                                   | Why                                              |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------ |
| SPI / SPEI                | **Fixed classes** (WMO-style)                                                                                          | Yes                                           | Same as flood depth bins                         |
| PDSI                      | **Fixed Palmer classes**                                                                                               | Yes                                           | Literature cutoffs                               |
| CDD                       | **Climatological percentile** (per cell or city P90 of annual max CDD), optional city min–max only for in-city stretch | Percentile: locally extreme. City min–max: no | ETCCDI has no universal urban cutoff             |
| SMAP root-zone percentile | **Already 0–100 vs local climatology** → `drought = 1 − pctl/100` or class on pctl                                     | Yes (“dry for this pixel”)                    | Option 3 in the normalization decision, for free |




### 5.1 Proposed SPI / SPEI impact classes

Standardized index z (negative = dry):


| Condition                    | Score |
| ---------------------------- | ----- |
| z > -0.5 (near normal / wet) | 0.00  |
| -1.0 < z \le -0.5 mild       | 0.25  |
| -1.5 < z \le -1.0 moderate   | 0.50  |
| -2.0 < z \le -1.5 severe     | 0.75  |
| z \le -2.0 extreme           | 1.00  |




### 5.2 Proposed PDSI impact classes

Palmer (scale applied after TerraClimate `pdsi * 0.01`):


| PDSI                    | Score |
| ----------------------- | ----- |
| > -1                    | 0.00  |
| -2 < \text{PDSI} \le -1 | 0.25  |
| -3 < \text{PDSI} \le -2 | 0.50  |
| -4 < \text{PDSI} \le -3 | 0.75  |
| \le -4                  | 1.00  |




### 5.3 From monthly index → static city `H`

Heat uses **P90 over 10 summers**. Drought analog (pick one and document):

**Recommended:** drought **frequency** 2015–2024:

```text
spei3_freq = mean( I(SPI3_class ≥ 0.50) )   # share of months at least moderate
pdsi_freq  = mean( I(PDSI_class  ≥ 0.50) )
cdd_score  = climatological P90 of annual maximum CDD, then
             clamp01((CDD_P90 − 10) / 40)   # 10–50 dry days ramp; tune in spike
smap_score = mean( I(sm_rootzone_pctl ≤ 20) )  # share of pentads/months in lowest quintile
```

Frequency is already in [0, 1] and comparable across cities. A P90-of-class alternative is closer to heat but less intuitive for SPEI.

---



## 6) v1 ensemble (analogous to flood / heat / landslide)

Mirror flood: weighted sum, **renormalize over available layers**, `min_layers`, transparency band `n_layers_used`.

### 6.1 Recommended v1 (three inputs)


| Layer       | Source            | Weight   | Notes                                                                |
| ----------- | ----------------- | -------- | -------------------------------------------------------------------- |
| `spi3_freq` | CHIRPS SPI-3      | **0.40** | Agricultural / short water-balance; CCRADiscovery already used SPI-3 |
| `pdsi_freq` | TerraClimate PDSI | **0.35** | Independent PET-aware drought (SPEI-like without 0.5° SPEIbase)      |
| `cdd_score` | CHIRPS CDD        | **0.25** | Named CCRA indicator; duration, not just deficit                     |


```text
H = clamp01( sum(w_i × layer_i) / sum(w_i present) )
min_layers = 2
```

Optional NASA add-on (config flag, like heat `include_era5`):


| Layer           | Source                      | Weight if on                            |
| --------------- | --------------------------- | --------------------------------------- |
| `smap_dry_freq` | SPL4SMGP `sm_rootzone_pctl` | 0.20, then renormalize the four weights |


Default **off** for v1 until a Rochester/Plymouth QA map shows it is not a 2×2 smear. Same gate that excluded ERA5 from heat.

### 6.2 Explicitly not in v1 core

- **SPEIbase 0.5°** as an ensemble member (QA / country dashboard only).
- GRACE TWS.
- Aqueduct basin water-risk as a substitute for meteorological drought (can be a *related* catalog layer later).
- 2030/2050 SPEI (needs CMIP; separate product).



### 6.3 Grid, extract, publish


| Stage   | Pattern to copy                                                                                                                            |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Extract | `transformation/heat_hazard/extract_heat_inputs.py` / landslide CHIRPS extract — GEE clip to `sites/{city}/boundary`                       |
| Compute | `compute_*_hazard.py` + `models/drought_hazard/config.yaml`                                                                                |
| Grid    | 250 m (flood/heat), nearest for all drought inputs                                                                                         |
| Risk    | Existing ACS E/V; `compute_drought_risk.py` clone of heat risk                                                                             |
| Catalog | `{city}_drought_hazard`, `{city}_drought_risk`; `normalization_domain: city` for CDD if min–max; `comparability: class-based` for SPI/PDSI |


SPEI/PDSI classes are **portable across cities**. CDD may not be. Document that split in the future model card (checklist §5).

---



## 7) Recommendation (squad)

**Use for v1:** **CHIRPS Daily (SPI-3 + CDD)** and **TerraClimate PDSI**.  
**NASA dataset to keep on the shortlist:** **SMAP L4 root-zone percentile**, behind a flag until city-scale QA.

**Do not use SPEIbase as the city screening raster.** It is the right *index family* (and should be cited as the CCRA indicator), but at 0.5° it fails the same spatial test as ERA5-Land in heat. TerraClimate PDSI + CHIRPS SPI is the operational SPEI/CDD pair at ~5 km.

**Why this pair**

1. Two independent physics (precip-only SPI vs PET-aware PDSI).
2. Both global, GEE, monthly/daily, already-compatible GeoTIFF path.
3. Aligns with the indicator JSON (SPEI conceptually, CDD literally) and with `CCRADiscovery/drought`.
4. Normalization can be **fixed classes** — stronger scientific story than city min–max, and closer to flood than to heat.
5. Smallest engineering delta: CHIRPS extract exists; TerraClimate is one new GEE collection.

**Expected limitation to present honestly:** drought `H` will be nearly uniform inside a Minnesota metro. The map still has value as a **city-to-city / regional** drought context and as an input to `R` via E/V. If GCoM/C40 need intra-urban drought, the only finer proxies are vegetation stress (MODIS NDVI anomaly, 250 m — overlaps landslide veg) or water-infrastructure exposure (not hazard).

---



## 8) Spike before implementation (Minnesota)

1. Extract CHIRPS SPI-3 frequency and CDD P90, plus TerraClimate PDSI frequency, for **Rochester** and **Plymouth**.
2. Count native pixels inside each boundary (expect tens of CHIRPS/TerraClimate cells, not thousands).
3. Compare class-based `H` vs a city min–max stretch — confirm classes do not collapse MN summers to ~0.
4. Optional: overlay SMAP `sm_rootzone_pctl`; drop if the pattern is a single blob.
5. Then, if accepted: `models/drought_hazard/{config.yaml,model_card.md}` and `transformation/drought_hazard/` following the new-hazard checklist.

---



## 9) Ticket checklist (drought)

- [x] ≥2 global datasets with URL, resolution, access
- [x] Pipeline compatibility (format, regrid, 0–1)
- [x] Methodology notes analogous to flood/heat/landslide
- [x] Squad review of v1 dataset choice (this doc)
- [x] Wildfire exploration — [ccra_wildfire_hazard_exploration.md](./ccra_wildfire_hazard_exploration.md)

---



## 10) Sources

- SPEIbase GEE: [https://developers.google.com/earth-engine/datasets/catalog/CSIC_SPEI_2_11](https://developers.google.com/earth-engine/datasets/catalog/CSIC_SPEI_2_11)
- TerraClimate GEE: [https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_TERRACLIMATE](https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_TERRACLIMATE)
- CHIRPS Daily GEE: [https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
- NASA SMAP L4 GEE: [https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008](https://developers.google.com/earth-engine/datasets/catalog/NASA_SMAP_SPL4SMGP_008)
- Vicente-Serrano et al. (2010), SPEI, *J. Climate*
- Abatzoglou et al. (2018), TerraClimate, *Scientific Data*
- Prior OEF drought CSVs: `CCRADiscovery/drought/data/*_drought_hazard_monthly.csv`

