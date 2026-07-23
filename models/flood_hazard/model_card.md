# Flood Hazard Score — Model Card (v2)

## 1) Purpose and scope

This document defines the methodology used to compute `flood_hazard_score` by combining externally produced flood-hazard datasets into a single 0-1 screening index. It was first validated for Porto Alegre (POA) and is now organized as a reusable multi-city workflow under `transformation/flood_hazard/sites/<city_slug>/`.

Default ensemble weights and IDW parameters live in `models/flood_hazard/config.yaml`; city overrides live in `transformation/flood_hazard/config/sites/<city_slug>.yaml`.

This is a **hazard-screening** product (not full flood risk in the IPCC sense), because exposure and vulnerability are not included in the score.

## 2) Methodological basis (updated from audit section 10)

Following the strategy in `NBS-Project-Preparation/docs/flood-risk-scoring-methodology-audit.md` section 10, this implementation prioritizes:

- externally documented flood-hazard products,
- transparent harmonization and normalization,
- a simple, explainable weighted ensemble.

The current implementation updates the MVP combination with a balanced weighting scheme that gives more influence to continuous hazard layers and lower influence to binary layers.

## 3) Input datasets and role in the ensemble

The score combines the following normalized inputs:

1. `jrc_norm`  
   Source: JRC Global River Flood Hazard Maps v2.1 (`RP100_depth`, impact-class normalization).  
   Role: modeled fluvial hazard severity.

2. `gfd_count_norm`  
   Source: Global Flood Database v1 (event count excluding permanent water, robust normalized).  
   Role: observed historical flood occurrence intensity (catalog-based, not probability).

3. `aqueduct_norm`  
   Source: WRI Aqueduct Flood Hazard Maps v2 (`inunriver`, historical, RP100, impact-class normalization).  
   Role: external flood hazard screening signal.

4. `gfplain_norm` (`gfplain_250m`)  
   Source: GFPLAIN250m (`0/1` floodplain geomorphic mask).  
   Role: structural floodplain susceptibility constraint.

Auxiliary layer (not part of the weighted core score):

- `gfd_observed_once` (`0/1`): observed flooded at least once in the GFD catalog; useful for QA/sanity checks and masking rules.

## 4) Normalization approach by dataset

### 4.1 JRC normalization (`jrc_norm`)

Input: `RP100_depth` from JRC Global River Flood Hazard Maps v2.1.

Depth is converted to a 0-1 impact-oriented hazard class:

- `0 <= d <= 0.15` m -> `0.00`
- `0.15 < d <= 0.5` m -> `0.25`
- `0.5 < d <= 1.0` m -> `0.50`
- `1.0 < d <= 2.0` m -> `0.75`
- `d > 2.0` m -> `1.00`

`nodata` from depth is preserved in the normalized output mask.

### 4.2 Aqueduct normalization (`aqueduct_norm`)

Input: WRI Aqueduct v2 (`inunriver`, `historical`, `returnperiod=100`), variable `inundation_depth`.

The same impact-class transform is applied for methodological consistency across modeled depth products:

- `0 <= d <= 0.15` m -> `0.00`
- `0.15 < d <= 0.5` m -> `0.25`
- `0.5 < d <= 1.0` m -> `0.50`
- `1.0 < d <= 2.0` m -> `0.75`
- `d > 2.0` m -> `1.00`

`nodata` from depth is preserved (`no score where depth has no value`).

This approach keeps interpretability in meters while ensuring stable 0-1 comparability with other ensemble terms.

### 4.3 Global Flood Database event count

`flood_event_count_no_perm_water` is normalized to 0-1 using a robust pipeline:

1. p95 winsorization (cap outliers),
2. `log1p` compression (reduce right-skew),
3. min-max scaling in ROI.

Interpretation: normalized observed event intensity within the mapped event catalog, not a physical flood probability.

### 4.4 GFPLAIN250m

Used as binary susceptibility (`0/1`), representing geomorphic floodplain presence/absence.

## 5) Harmonization and scoring grid

Because input rasters have different native resolutions, all layers are reprojected to a common analysis grid before scoring.

Current implementation in `transformation/flood_hazard/flood_hazard_score_v2.ipynb` uses:

- reference grid: `gfplain_250m` (~250 m),
- CRS: `EPSG:4326`,
- resampling:
  - continuous layers -> bilinear,
  - binary layers -> nearest neighbor.

## 6) Composite score formula (balanced option)

Base weights (sum to 1.0):

| Layer | Weight |
|-------|--------|
| `jrc_norm` | 0.45 |
| `gfd_count_norm` | 0.30 |
| `aqueduct_norm` | 0.15 |
| `gfplain_250m` | 0.10 |

At each pixel, only layers with finite values enter the sum; weights are **renormalized** over available layers:

```text
flood_score = clamp01( sum(w_i * layer_i) / sum(w_i present) )
```

Where `gfd_count_norm` is `gfd_norm` in earlier notes and `gfplain_250m` is binary 0/1.

### 6.1 Coverage rule (primary score)

The operational score (`flood_hazard_score_poa.tif`) uses a **partial coverage** rule to retain river-adjacent screening where GFD is often nodata:

1. **>= 3 of 4** predictor layers must be valid at the pixel.
2. At least one **fluvial** layer must be present: `jrc_norm` **or** `aqueduct_norm`.
3. Weights are renormalized over the layers that pass (1)-(2).

A transparency band `flood_hazard_n_layers_used_poa.tif` stores how many layers contributed (3 or 4).

### 6.2 Strict score (comparison)

For sensitivity analysis, a **strict** raster requires **all four** layers (`flood_hazard_score_strict_poa.tif`). In POA this mask is much smaller (~3k pixels vs a larger partial mask); use the comparison map in `transformation/flood_hazard/flood_hazard_score_v2.ipynb` to inspect gains near rivers.

### 6.3 Optional IDW gap-fill (derived product)

After `flood_score_base` is computed, the notebook can optionally fill **nearby gaps** using **inverse-distance weighting (IDW)** with a **distance cap**. This is a **separate derived layer** for mapping and continuity; it does **not** replace the operational observed score.

**Design principles**

1. **`flood_score_base` is unchanged** — still the primary product for validation (§10) and catalog entry `poa_flood_hazard`.
2. **`flood_score_idw`** — copy of the base score on observed pixels; gap pixels receive an IDW estimate from neighbors with valid base scores.
3. **Transparency** — auxiliary rasters flag interpolated pixels and report distance to the contributing neighborhood.

**Gap candidates**

A pixel is eligible for fill only if:

- it has **no** `flood_score_base` value (failed the >=3/4 + fluvial rule), and
- by default (`USE_GFPLAIN_MASK = False`) it lies within **`MAX_DIST_M`** of at least **`MIN_NEIGHBORS`** observed pixels.

Optional stricter mask (`USE_GFPLAIN_MASK = True`): limit candidates to `gfplain_250m == 1` **or** fluvial layer presence (`jrc_norm` or `aqueduct_norm`). This yields far fewer fills (~150 pixels in POA vs ~1,500 with the default).

**IDW formula**

For each gap pixel `p`, let `N(p)` be observed neighbors within `MAX_DIST_M` (meters, local equirectangular approximation at grid center latitude):

```text
score_idw(p) = clamp01( Σ w_i · score_i / Σ w_i )
w_i = n_layers_i / d_i^β
```

Where:

- `score_i` — `flood_score_base` at neighbor `i`
- `d_i` — distance from `p` to `i` (m)
- `n_layers_i` — number of ensemble layers used at neighbor `i` (3 or 4; floored at 3 for weighting)
- `β` — `IDW_POWER` (default `2`)

If fewer than `MIN_NEIGHBORS` valid neighbors exist within `MAX_DIST_M`, the pixel remains `nodata`.

**Default parameters (POA implementation)**

| Parameter | Default | Role |
|-----------|---------|------|
| `MAX_DIST_M` | 750 m | Maximum search radius |
| `MIN_NEIGHBORS` | 3 | Minimum observed neighbors required |
| `IDW_POWER` | 2 | Inverse-distance exponent |
| `K_NEIGHBORS` | 32 | kNN pool before radius filter |
| `USE_GFPLAIN_MASK` | False | Optional gfplain/fluvial candidate mask |

**POA coverage (reference run)**

| Product | Finite pixels (of 19,328) | Notes |
|---------|---------------------------|--------|
| `flood_score_base` | ~13,894 | Observed ensemble score |
| `flood_score_idw` | ~15,394 | Base + IDW fill |
| Interpolated only | ~1,500 | With default parameters |

**Outputs**

| File | Description |
|------|-------------|
| `flood_hazard_score_poa.tif` | Operational **observed** score (`flood_score_base`) |
| `flood_hazard_score_idw_poa.tif` | Observed + IDW-filled score |
| `flood_hazard_is_interpolated_poa.tif` | `1` = interpolated pixel, `0` = observed |
| `flood_hazard_interp_distance_m_poa.tif` | Distance (m) to nearest contributing neighbor |
| `flood_hazard_score_interpolated_only_poa.tif` | IDW values only (NaN elsewhere; map QA) |

**Web publishing (COG + XYZ tiles)**

Same GDAL pipeline as the base hazard product (`flood_hazard_colors.txt`, decode `score = (R + 256*G + 65536*B) / 10000`):

- COG: `out/flood_hazard_score_idw/flood_hazard_score_idw_cog.tif`
- Visual tiles: `out/flood_hazard_score_idw/tiles_visual/`
- Value tiles: `out/flood_hazard_score_idw/tiles_values/`

**Interpretation and limits**

- Interpolated values are **inferred screening scores**, not new observations from JRC/GFD/Aqueduct/GFPLAIN.
- IDW smooths locally and can **understate sharp hazard gradients** at product boundaries.
- **§10 validation metrics apply to `flood_score_base` only**, not to the IDW layer, unless a separate validation exercise is run.
- Downstream risk (`flood_risk_score.ipynb`) should treat IDW hazard as **optional**; prefer `flood_hazard_score_poa.tif` for official screening unless gap continuity is explicitly required.

## 7) Why this weighting scheme

This balanced option intentionally emphasizes continuous hazard gradients:

- JRC (`0.45`) + GFD count (`0.30`) + Aqueduct (`0.15`) carry most spatial variability,
- GFPLAIN (`0.10`) is kept lower to avoid binary step-changes dominating the score.

This makes the ensemble more stable and interpretable while retaining floodplain structure as a contextual constraint.

## 8) Assumptions

1. **Hazard-only framing**: the score estimates hazard/susceptibility, not full risk.
2. **Cross-product comparability**: normalized layers can be meaningfully combined after harmonization.
3. **Return period comparability**: RP100-based hazard proxies are treated as compatible screening inputs.
4. **Binary floodplain role**: geomorphic floodplain presence is relevant but secondary to continuous hazard severity/occurrence signals.
5. **Observed count relevance**: historical event count contains useful signal for relative hotspot ranking in the ROI.

## 9) Key considerations and limitations

1. **Not a probabilistic flood model**: the composite score is an index, not annual probability of inundation.
2. **Observed-event bias (GFD)**: event coverage/sensor limitations can affect observed counts.
3. **Resolution effects**: final map precision is limited by harmonization choices and source data quality.
4. **Weight transferability**: weights are priors for current context; re-calibration is required for new cities/regimes.
5. **Event-family overlap in validation**: SkySat and EMSN194 both describe the May 2024 Rio Grande do Sul floods; metrics measure agreement with that event, not transferability to other events or cities without re-validation.
6. **Expected non-perfect overlap with May 2024 flooded grids**: this score is designed primarily for **fluvial (river) hazard screening** and does not explicitly model a dedicated **pluvial-only flooding factor** (e.g., urban drainage exceedance from local rainfall intensity/duration). Therefore, 100% spatial coincidence with observed May 2024 inundation footprints is not expected.
7. **IDW gap-fill is not independently validated**: interpolated pixels inherit information from nearby observed scores within 750 m; they should be flagged (`is_interpolated`) and not conflated with direct ensemble outputs in reporting.

## 10) External validation (Porto Alegre)

Validation was run in `transformation/flood_hazard/flood_hazard_score_v2.ipynb` against references **not used as predictors** in the balanced ensemble (`jrc_norm`, `gfd_count_norm`, `aqueduct_norm`, `gfplain_250m`). All metrics in §10.3 refer to the **operational partial score** (`flood_score_base`, >=3/4 layers + fluvial requirement), not the strict 4/4 comparison raster.

### 10.1 Validation references

| Reference | Source | Format | Validation role |
|-----------|--------|--------|-----------------|
| **SkySat / Planet (May 2024)** | `NBS-Project-Preparation/client/public/sample-data/porto-alegre-flood-2024.json` (197 polygons, 2024-05-06; Zenodo [10.5281/zenodo.14662897](https://doi.org/10.5281/zenodo.14662897)) | GeoJSON (rasterized to score grid) | Binary footprint agreement |
| **Copernicus EMSN194 max water depth** | [maxwaterdepth_cog.tif](https://geo-test-api.s3.us-east-1.amazonaws.com/copernicus_emsn194/release/v1/2024/porto_alegre/maxwaterdepth_cog.tif) | COG (~30 m, depth in m) | Severity / rank consistency |

SkySat is the same layer used in the NBS app as `flood_2024_extent` / grid label `in_flood_2024`. EMSN194 is cataloged as `copernicus_emsn194` in `geospatial-data/catalog/datasets.yaml`.

### 10.2 Validation protocol

1. Align validation layers to the scoring grid (`gfplain_250m` reference, ~250 m, `EPSG:4326`).
2. Rasterize SkySat polygons (`all_touched=True`) to a binary observed-flood mask.
3. Read EMSN194 depth from the S3 COG and reproject (bilinear).
4. **Footprint test:** classify `flood_score_base >= 0.45` as predicted flooded; compare to SkySat mask (TP/FP/FN/TN, Precision, Recall, F1, IoU). Uses the **partial** score raster (>=3/4 layers); re-run the notebook after coverage-rule changes to update metrics.
5. **Severity test:** on pixels with EMSN194 depth > 0, compute Spearman rank correlation between score and depth; summarize median depth by score bin.

### 10.3 Results (POA ROI)

Results below use **`flood_score_base`** with the **partial coverage rule** (>=3 of 4 layers + at least one fluvial layer), evaluated on the expanded valid mask (~13.9k score pixels vs ~3.2k under strict 4/4).

**Footprint agreement vs SkySat/Planet** (threshold = 0.45):

| Metric | Value |
|--------|-------|
| True positives (TP) | 3,021 |
| False positives (FP) | 94 |
| False negatives (FN) | 1,107 |
| True negatives (TN) | 9,672 |
| **Precision** | **0.970** |
| **Recall** | **0.732** |
| **F1** | **0.834** |
| **IoU** | **0.716** |

**Severity consistency vs EMSN194 depth** (3,902 pixels with depth > 0):

| Metric | Value |
|--------|-------|
| Spearman(score, depth) | **0.769** |

Median observed depth (m) by score bin:

| Score bin | Pixel count (n) | Median depth (m) | Mean depth (m) |
|-----------|-----------------|------------------|----------------|
| 1 (lowest) | 247 | 0.53 | 0.82 |
| 2 | 947 | 1.53 | 1.66 |
| 3 | 1,617 | 2.76 | 2.65 |
| 4 (highest) | 169 | 3.80 | 3.79 |

### 10.4 Interpretation

**SkySat footprint (F1 ≈ 0.83, IoU ≈ 0.72)**

- **High precision (0.97):** predicted flooded pixels still align well with the observed SkySat footprint; false alarms remain limited (94 FP).
- **Moderate recall (0.73):** with river-adjacent coverage restored, more pixels enter evaluation; omission increases (1,107 FN) relative to the strict 4/4 mask. The score is **more conservative on extent** at threshold 0.45 while covering a wider screening area.
- **Screening read:** strong for **prioritizing where inundation is likely** when the score is high; threshold tuning or post-filtering may be needed if maximizing recall of the May 2024 footprint is the primary goal.

**EMSN194 severity (Spearman ≈ 0.77)**

- **Stronger rank agreement** than under strict coverage: higher `flood_score_base` more consistently coincides with greater EMSN194 depth over ~75% more valid depth pixels (3,902 vs 2,243).
- **Monotonic depth by bin:** median depth still increases from ~0.5 m (bin 1) to ~3.8 m (bin 4), with more stable sample sizes in bins 1–3 after partial coverage.

**Combined read**

The partial-coverage ensemble trades some **binary footprint recall** for **broader spatial screening** and **improved severity ordering** against EMSN194. It remains appropriate as an **urban flood hazard screening layer** in Porto Alegre, with explicit reporting of precision–recall at the chosen threshold.

### 10.5 Validation caveats (still apply)

1. **Same event family:** SkySat and EMSN194 describe May 2024 flooding; this is not out-of-sample validation in time or city.
2. **Resolution mismatch:** 250 m score grid vs ~3 m SkySat polygons and ~30 m EMSN194; boundary effects can inflate FN/FP at edges.
3. **Rasterization choices:** `all_touched` on SkySat polygons can modestly increase overlap metrics.
4. **Single threshold:** footprint metrics reported at 0.45; a threshold sensitivity sweep (e.g., 0.35–0.60) is recommended for reporting.
5. **Not decision-grade alone:** strong screening metrics do not replace hydraulic modeling, exposure/vulnerability integration, or regulatory flood-risk assessment.

### 10.6 Validation conclusion

| Use case | Supported by current validation? |
|----------|----------------------------------|
| Urban screening and prioritization in POA | **Yes**, with documented limits above |
| Official / regulatory flood-risk decisions | **No** — requires broader validation and risk framing |
| Transfer to other cities or future events without re-validation | **No** |

## 11) Recommended use

Use this score for:

- urban flood hazard screening,
- hotspot prioritization,
- comparative exploration across neighborhoods/zones.

Use **`flood_hazard_score_idw_poa.tif`** only when:

- map continuity near river corridors is needed for communication or web tiles,
- interpolated pixels are explicitly labeled and excluded from validation claims.

Do not use it alone for:

- regulatory-grade flood risk decisions,
- insurance-grade loss estimation,
- official claims of fully validated flood risk without independent calibration/validation.

## 12) Traceability

Primary implementation notebook:

- `transformation/flood_hazard/flood_hazard_score_v2.ipynb` (score, IDW gap-fill, COG/tiles, validation maps)

Model artifacts:

- `models/flood_hazard/config.yaml` — default weights, coverage rules, IDW parameters
- `models/flood_hazard/model_card.md` — this document

**Published raster outputs** (`transformation/flood_hazard/sites/<city_slug>/data/output/`):

- `flood_hazard_score_poa.tif` — operational observed score
- `flood_hazard_score_strict_poa.tif` — strict 4/4 sensitivity
- `flood_hazard_n_layers_used_poa.tif` — layer-count transparency
- `flood_hazard_score_idw_poa.tif` — IDW-filled derivative
- `flood_hazard_is_interpolated_poa.tif`, `flood_hazard_interp_distance_m_poa.tif` — IDW QA bands

**Tile packages** (`transformation/flood_hazard/sites/<city_slug>/out/`):

- `flood_hazard_score/` — COG + tiles for observed score
- `flood_hazard_score_idw/` — COG + tiles for IDW-filled score

Supporting source notebooks:

- `transformation/wri_aqueduct/release/v1/WRI_aqueduct.ipynb`
- `transformation/global_flood_database/release/v1/global_flood_database.ipynb`
- `transformation/gfplain250m/release/v1/GFPLAIN250m.ipynb`
- `transformation/jrc_global_river_flood_hazard_maps/release/v1/jrc_global_river_flood.ipynb`
