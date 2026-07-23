# NBS Recommendation Rules — Expert Review Brief

**Ticket:** [ON-5993](https://openearth.atlassian.net/browse/ON-5993)  
**Audience:** NBS Solution Expert joining OEF (review with Maureen + Joaquin)  
**Status:** Draft for discussion — rules are **exploratory screening**, not engineering suitability

---

## Why this document exists

OEF already has detailed **data-engineering** documentation (hazard score methodologies, dataset lenses, catalog COGs). That material answers *what data exists and how it was processed*.

This brief answers a different question for an NBS expert:

> **Given a hazard priority area, what logic do we use today to infer a hazard *mechanism* and score candidate NBS types — and where should that logic live long term?**

Implementation reference: [`scripts/nbs_rules.py`](../scripts/nbs_rules.py)  
Live exercises: [`nbs_site_query_e2e.md`](nbs_site_query_e2e.md) (flood, heat, landslide notebooks)

**Related docs (deeper detail, not required for this review):**

| Doc | Role |
|-----|------|
| [`nbs_dataset_identification_methodology.md`](nbs_dataset_identification_methodology.md) | Shared Steps 0–8 workflow |
| [`flood_nbs_dataset_lens.md`](flood_nbs_dataset_lens.md) / [`heat_…`](heat_nbs_dataset_lens.md) / [`landslide_…`](landslide_nbs_dataset_lens.md) | Hazard-specific dataset needs |
| [`recommended-datasets.md`](recommended-datasets.md) | Full dataset inventory tables by hazard |

---

## Overall logic (all hazards)

Every hazard follows the same two-step pattern:

```text
Step 0  Hazard / risk scores     →  WHERE to start (already computed by OEF)
Step 1  Mechanism inference       →  WHAT KIND of problem (diagnostic flags)
Step 2  NBS typology scoring      →  WHICH interventions to surface (ranked list)
```

**Important framing:**

- **Priority ≠ suitability.** High flood/heat/landslide risk does not mean every NBS type fits.
- Scores are **additive rule weights** on a 0–1 scale, clamped and labeled:
  - **≥ 0.55 → plausible** (worth further screening)
  - **≥ 0.35 → weak** (possible but thin evidence)
  - **< 0.35 → unlikely**
- Each recommendation carries explicit **gaps** (data we know we cannot assess globally).

---

## Scoring model (shared)

| Component | Rule |
|-----------|------|
| Base priority gate | Most NBS types require minimum hazard/risk before adding points (threshold varies by hazard — see below) |
| Mechanism bonuses | +0.10 to +0.45 when diagnostic flags align with NBS design logic |
| Site-condition bonuses | +0.10 to +0.35 for proxies like open land, built-up fraction, distance to water |
| Penalties | Negative adjustments for steep slope, dense built environment, built-on-slope, etc. |
| Final score | `clamp(sum(bonuses) − penalties, 0, 1)` — **not** a calibrated probability |

Scores are **heuristic weights for ideation**, not calibrated benefit or feasibility indices. Thresholds (e.g. “built-up ≥ 0.35”) are initial screening defaults subject to expert calibration.

---

# Flood

## Mechanisms modeled (Step 1)

Four diagnostic flags plus one documented gap:

| Flag | Meaning | Current rule (summary) |
|------|---------|------------------------|
| **Riverine** | Connected to drainage network / near channel | OSM waterway intersects site **or** distance to nearest waterway **< 500 m** |
| **Pluvial** | Urban runoff / intense rain on impervious surfaces | Built/impervious proxy **≥ 0.35**, **or** **≥ 0.25** with CHIRPS heavy-rain signal (Rx1day ≥ 50 mm or Rx5day ≥ 100 mm) |
| **Low-lying** | Terrain / wetness accumulation | Any of: floodplain adjacency ≥ 0.5, depression fraction ≥ 0.15, HAND ≤ 5 m, JRC surface-water occurrence ≥ 10, JRC seasonality ≥ 1 |
| **Drainage-constrained** | Engineered drainage limits capacity | **Always flagged as a gap** — no open urban storm-drain layer in catalog |

Multiple flags can be true simultaneously (e.g. riverine + pluvial in a dense riverside bairro).

## Mechanism → candidate NBS (design intent)

| If mechanism dominates… | NBS types we expect to score higher |
|-------------------------|-------------------------------------|
| **Pluvial** (+ high imperviousness) | Rain gardens, bioswales, permeable surfaces |
| **Low-lying** (+ open land) | Floodable parks, retention basins, wetland restoration |
| **Riverine** (+ proximity to water) | Riparian buffers, floodplain restoration, wetland restoration, floodable parks |
| **Dense built, limited open land** | Permeable surfaces, bioswales (distributed); large storage NBS score lower |
| **Drainage gap** | Any NBS may need to **complement** grey infrastructure — not replace it |

## NBS types scored (Step 2)

| NBS type | Key scoring logic |
|----------|-------------------|
| **Rain garden** | +0.35 if pluvial; +0.20 if runoff proxy ≥ 0.30; +0.10 if heavy rain; −0.20 if mean slope > 8° |
| **Bioswale** | +0.30 pluvial; +0.25 runoff ≥ 0.25; −0.15 slope > 8° |
| **Permeable surfaces** | +0.40 if runoff proxy ≥ 0.40 |
| **Floodable park** | +0.30 low-lying; +0.25 open/green land ≥ 0.25; +0.15 riverine |
| **Wetland restoration** | +0.35 riverine or river < 800 m; +0.25 low-lying/depression; +0.15 JRC/Dynamic World wetness history |
| **Floodplain restoration** | +0.40 riverine; +0.20 floodplain adjacency ≥ 0.40; +0.10 open land |
| **Retention basin** | +0.25 low-lying; +0.25 open/green land; +0.10 heavy rain |
| **Riparian buffer** | +0.45 if river < 300 m; +0.30 riverine; +0.10 existing green ≥ 0.25 |

**Priority gate:** `risk_mean ≥ 0.15` → +0.25 base score; otherwise flagged as low flood priority.

**Known gaps always attached:** soil infiltration, groundwater depth, cadastre/ROW, species inventories, local IDF for sizing.

---

# Heat

## Exposure context modeled (Step 1)

| Flag | Meaning | Current rule (summary) |
|------|---------|------------------------|
| **UHI / built-up** | High imperviousness, low vegetation | Built proxy **≥ 0.35** and vegetation proxy **< 0.30** |
| **Shade deficit** | Lack of tree cover where cooling needed | Tree fraction < 0.15, or Hansen tree cover < 20%, or (green < 0.25 and built ≥ 0.25) |
| **High daytime LST** | Surface heating hotspot | Heat hazard ≥ 0.45, or Landsat LST norm ≥ 0.55, or MODIS day LST norm ≥ 0.55 |
| **Limited nocturnal cooling** | Night heat retention | MODIS night ≥ 0.5 and (night − day) ≥ 0.05 |
| **High social exposure** | People / vulnerable groups | Risk ≥ 0.35, or exposure ≥ 0.5, or vulnerability ≥ 0.5 |

**Caveat:** Hazard scores use **land surface temperature**, not pedestrian air temperature or thermal comfort.

## Context → candidate NBS (design intent)

| If context dominates… | NBS types we expect to score higher |
|-----------------------|-------------------------------------|
| **Shade deficit + UHI** | Urban/street trees, green corridors |
| **High LST + dense built** | Green roofs/walls, street trees |
| **Open land + social exposure** | Pocket parks, schoolyard greening |
| **Near waterway + shade deficit** | Riparian cooling corridors |
| **Dense core, little open land** | Green roofs/walls over large pocket parks |

## NBS types scored (Step 2)

| NBS type | Key scoring logic |
|----------|-------------------|
| **Urban / street trees** | +0.35 shade deficit; +0.20 UHI; +0.10 planting-space proxy; −0.15 slope > 12° |
| **Green corridor** | +0.30 existing green ≥ 0.20; +0.20 shade deficit; −0.10 if built ≥ 0.35 |
| **Pocket park** | +0.25 social exposure; +0.30 open land ≥ 0.20 (or green ≥ 0.25) |
| **Schoolyard greening** | +0.30 social exposure; +0.15 open land ≥ 0.15 |
| **Green roof / wall** | +0.35 built ≥ 0.45; +0.20 high daytime LST |
| **Riparian cooling corridor** | +0.35 river < 400 m; +0.15 riparian vegetation; +0.10 limited nocturnal cooling |

**Priority gate:** `risk_mean ≥ 0.15` **or** `hazard_mean ≥ 0.35` → +0.25 base score.

**Cross-hazard note:** High clay (≥ 35%) triggers a drainage/irrigation caution for planting-heavy NBS.

---

# Landslide

## Susceptibility context modeled (Step 1)

Aligned with the OEF landslide hazard ensemble (slope gate, R90p, clay, NDVI P10, HAND):

| Flag | Meaning | Current rule (summary) |
|------|---------|------------------------|
| **Steep / activatable slope** | Methodology activation gate | Mean slope **≥ 15°** or landslide hazard **> 0** |
| **Rainfall trigger** | Chronic extreme precipitation | CHIRPS R90p climatology **≥ 200 mm** |
| **Low cohesion when wet** | Clay-rich soils | SoilGrids clay **≥ 35%** |
| **Vegetation deficit** | Lack of root reinforcement | NDVI P10 < 0.35, or green < 0.25, or tree < 0.15 |
| **Drainage saturation** | Convergence near drainage | HAND ≤ 5 m or distance to water **< 200 m** |
| **Disturbed / bare slope** | Bare or built on slope | Dynamic World bare ≥ 0.15 or built ≥ 0.25 |
| **Upslope convergence** | Large contributing area | MERIT UPA **≥ 1.0 km²** |
| **High social exposure** | Downslope population | Lower thresholds than flood/heat (risk ≥ 0.03, exposure ≥ 0.15, vulnerability ≥ 0.25) |

**Caveats:** Susceptibility **≠** slope stability analysis. Flat areas (slope < 15°) score **H = 0** by design in the hazard methodology.

## Context → candidate NBS (design intent)

| If context dominates… | NBS types we expect to score higher |
|-----------------------|-------------------------------------|
| **Vegetation deficit on activatable slope** | Slope revegetation |
| **Bare/disturbed + drainage path** | Bioengineering / erosion-control vegetation |
| **Low HAND / near gully** | Riparian / gully-head protection |
| **Large upslope area + degraded cover** | Forest restoration / upslope reforestation |
| **Built on steep slope** | Penalize vegetation-only options — geotechnical review required |

## NBS types scored (Step 2)

| NBS type | Key scoring logic |
|----------|-------------------|
| **Slope revegetation** | +0.35 vegetation deficit; +0.15 activatable slope; +0.10 existing green; −0.15 built ≥ 0.35 |
| **Bioengineering / erosion control** | +0.35 disturbed/bare; +0.20 drainage/HAND ≤ 8; −0.20 slope > 35° |
| **Riparian / gully protection** | +0.35 river < 300 m; +0.20 drainage saturation; +0.10 riparian vegetation |
| **Forest restoration (upslope)** | +0.30 UPA ≥ 1 km²; +0.20 vegetation deficit; +0.10 degraded cover |

**Priority gate:** Below slope gate → flagged unlikely. Otherwise `risk ≥ 0.02` or `hazard ≥ 0.02` → +0.25 base (landslide scores are numerically smaller than flood/heat).

**Always flagged gaps:** geology, geotechnical survey, species/root architecture, land tenure on upslope land, multi-hazard (flood) trade-offs.

---

# Proposed split: catalog rules vs application filters

We propose separating **portable rule logic** from **city- or project-specific context**:

| Layer | What belongs here | Examples |
|-------|-------------------|----------|
| **Data catalog (global rule sets)** | Mechanism flags and NBS scoring using **catalog COGs and globally available layers** — same rules reusable in any city with those layers | GHSL built-up, Dynamic World, MERIT HAND/UPA, JRC surface water, CHIRPS extremes, Copernicus slope, hazard/risk COGs, SoilGrids, MODIS NDVI |
| **Application layer (ad-hoc context filters)** | Rules that depend on **local datasets, governance, or expert judgment** not in the global catalog | Wetland restoration only where JRC occurrence + municipal wetland inventory agree; schoolyard greening only where OSM schools exist; exclude cadastre-private slopes; require CEMADEN event history; POA storm-drain network; informal-settlement vulnerability overlay |

### Examples for expert input

| Rule | Proposed home | Rationale |
|------|---------------|-----------|
| “Riparian buffer scores higher within 300 m of OSM waterway” | **Catalog** | Uses global/OSM hydrography |
| “Wetland restoration requires historical wetness **and** municipally mapped wetland opportunity” | **Split** — wetness in catalog; municipal map in application |
| “Do not recommend infiltration NBS where groundwater < 2 m” | **Application** (until open global urban groundwater exists) |
| “Schoolyard greening requires confirmed school parcel + plantable yard area” | **Application** |
| “Slope revegetation excluded where geotechnical class = unstable fill” | **Application** |
| “Flood mechanism flags at 250 m cell vs bairro mean” | **Design choice** — see open question below |

**Ask for the expert:** Which of today’s rules should be **canonical catalog rules** vs **optional application plugins**?

---

# Intra-neighborhood differentiation (flood — open question)

Today we run flood screening at **two spatial units**:

| Unit | What it does | Implemented |
|------|--------------|-------------|
| **Bairro polygon** | Single mechanism assessment + NBS ranking for the whole neighborhood | ✅ Notebooks + `run_e2e.py` |
| **250 m grid cell** | Per-cell mechanism flags (riverine / pluvial / low-lying) + dominant NBS; bairro rollup (% cells per mechanism) | ✅ Flood grid path in [`grid_screening.py`](../scripts/grid_screening.py) |

**Why we added grid cells:** A bairro like Humaitá can combine riverside storage potential (low-lying, riverine cells) with dense pluvial runoff (built-up interior cells). A single bairro-level label hides that mix.

**Cost:** Extra pipeline complexity — per-cell sampling of hazard, HAND, JRC water, OSM distance, and full NBS scoring for every cell in the bairro.

### Question for the expert

> **Does intra-neighborhood flood-mechanism differentiation (250 m cells) add enough recommendation value to justify the extra complexity — or is bairro-level screening sufficient for early NBS ideation?**

Possible answers we can implement based on feedback:

1. **Keep grid for flood only** — highest mechanism heterogeneity
2. **Bairro-only everywhere** — simplify; report mechanism mix qualitatively
3. **Grid for flood + heat** — UHI/shade varies block-to-block in dense cores
4. **Grid only when mixed mechanisms detected** — adaptive detail

Heat and landslide grid screening use the same POA mechanism-type pipeline as flood (see [`poa_mechanism_type_layer.md`](poa_mechanism_type_layer.md)); landslide uses the native **90 m** hazard grid and `require_positive_hazard=True`.

---

# Additional questions for the review session

1. **Mechanism thresholds** — Are defaults (e.g. riverine < 500 m, pluvial built ≥ 0.35) reasonable for POA, or should they be calibrated per typology?
2. **Multi-mechanism sites** — Should we recommend **bundled** NBS portfolios when multiple flags fire (e.g. bioswales + floodable park), or always rank individual types?
3. **Exclusion rules** — Should certain combinations hard-exclude NBS (e.g. wetland restoration without any wetness signal), or only score low?
4. **Multi-hazard** — How should we handle riparian NBS that appear in flood, heat, and landslide lists with different scoring?
5. **Evidence bar** — Is the plausible / weak / unlikely labeling useful for stakeholders, or should we switch to qualitative tiers only?
6. **Expert-only gates** — Which NBS types should **never** surface without mandatory local validation (e.g. bioengineering on slopes > 35°, green roofs without structural review)?

---

# What we explicitly do not claim

- These rules **do not** produce final NBS designs or placement maps.
- Scores are **not** validated against implemented NBS outcomes or historical performance.
- Hazard scores (flood, heat, landslide) remain **screening indices** — see respective OEF methodology docs.
- Missing layers (urban drainage, cadastre, groundwater, geotechnical geology, pedestrian heat exposure, roof structure) are **documented gaps**, not hidden assumptions.

---

# Traceability

| Artifact | Path |
|----------|------|
| Rule implementation | [`scripts/nbs_rules.py`](../scripts/nbs_rules.py) |
| Flood grid screening | [`scripts/grid_screening.py`](../scripts/grid_screening.py) |
| E2E CLI | [`scripts/run_e2e.py`](../scripts/run_e2e.py) |
| Flood exercise | [`nbs_site_query_flood_e2e.md`](nbs_site_query_flood_e2e.md) |
| Heat exercise | [`nbs_site_query_heat_e2e.md`](nbs_site_query_heat_e2e.md) |
| Landslide exercise | [`nbs_site_query_landslide_e2e.md`](nbs_site_query_landslide_e2e.md) |
| Jira ticket | [ON-5993](https://openearth.atlassian.net/browse/ON-5993) |
