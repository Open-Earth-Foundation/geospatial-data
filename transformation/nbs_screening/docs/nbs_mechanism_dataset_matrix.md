# NBS localization matrix — mechanism → NBS → layers

**Audience:** Product, NBS experts, OEF team  
**City:** Porto Alegre (POA)  
**Scale:** 250 m (flood, heat) · 90 m (landslide, hazard-active cells only)

**Sources:** [`flood_nbs_dataset_lens.md`](flood_nbs_dataset_lens.md) · [`heat_nbs_dataset_lens.md`](heat_nbs_dataset_lens.md) · [`landslide_nbs_dataset_lens.md`](landslide_nbs_dataset_lens.md) · [`recommended-datasets.md`](recommended-datasets.md) · [`nbs_recommendation_rules_expert_review.md`](nbs_recommendation_rules_expert_review.md) · [`poa_mechanism_type_layer.md`](poa_mechanism_type_layer.md) · [`nbs_rules.py`](../scripts/nbs_rules.py)

---

## Purpose

The **lens documents** define the decision chain:

```text
hazard/risk → mechanism → site condition → geospatial proxy → dataset → NBS decision → gap
```

This matrix is the **next step** after the POA `*_mechanism_type` layer:

> Given a **dominant mechanism** in a cell, which **candidate NBS types** apply, which **additional layers** are needed to localize the recommendation, and what is already in the **catalog + rules** vs **application-only (POA local)**?

**Priority legend**

| Label | Meaning |
|-------|---------|
| **P1** | Blocks a credible localized recommendation today |
| **P2** | Major uplift with POA-specific or finer data |
| **P3** | Refinement; avoid over-prescribing |

**Data status legend**

| Status | Meaning |
|--------|---------|
| **Catalog + rules** | Layer in `datasets.yaml` and used in `nbs_rules.py` / `grid_screening.py` |
| **Catalog only** | In catalog or OEF exports; not yet wired into NBS scoring filters |
| **Local POA** | Municipal, expert, or project-specific — application layer |
| **Major gap** | No adequate open global layer at urban POA scale |

---

## Decision flow — today vs next

| Step | Question | Implemented today | Next focus |
|------|----------|-------------------|------------|
| 0 | Where is priority high? | H/E/V/R COGs + bairro vectors | Keep as entry gate |
| 1 | What mechanism dominates? | POA `*_mechanism_type` + GeoJSON strengths | Use `mixed_tied_mechanisms` |
| 2 | Which NBS types? | 8 flood · 6 heat · 4 landslide typologies scored | Bundle rules for `mixed` |
| 3–4 | Site conditions? | Global proxies (HAND, clay, NDVI, built-up…) | Add POA application filters |
| 5–6 | Datasets + gaps? | Documented in `recommended-datasets.md` | Prioritize P1 local layers |

---

## Top P1 layers (cross-hazard)

| Rank | Layer / dataset | Unlocks | Home |
|------|-----------------|---------|------|
| 1 | Cadastre / land tenure / public ROW | Most ground-based NBS siting | Local POA |
| 2 | Native species + planting constraints | All vegetation NBS | Local POA + expert |
| 3 | Municipal storm-drain network | Drainage-constrained flood NBS | Local POA |
| 4 | Geotechnical / geology (site) | Slope bioengineering & revegetation | Local POA |
| 5 | Schoolyard / parcel plantable area | Schoolyard greening, pocket parks | Local POA |
| 6 | Local IDF + field infiltration | Sizing bioswales, rain gardens, basins | Local POA |

---

## Flood (250 m grid)

| Dominant mechanism | Candidate NBS | Layers to localize | Data status | Priority | Notes |
|--------------------|---------------|-------------------|-------------|----------|-------|
| `riverine` | Riparian buffer · floodplain restoration | OSM waterways (dist), MERIT HAND/UPA, JRC GSW wetness, open/green land | Catalog + rules | P2 | Spatial mechanism layer done. Localize with municipal floodplain zoning + wetland inventory. |
| `riverine` | Wetland restoration | JRC occurrence/seasonality + municipal wetland opportunity map | Local POA | P1 | Split rule: wetness in catalog; legal opportunity only local. |
| `pluvial` | Rain garden · bioswale · permeable surfaces | GHSL/DW built-up, CHIRPS extremes, slope, soil infiltration proxy | Catalog + rules | P2 | Runoff proxy works at 250 m. Parcel-scale placement needs cadastre/ROW. |
| `pluvial` | Distributed stormwater NBS | True imperviousness · local IDF curves · field infiltration | Major gap | P1 | CHIRPS ~5 km is screening only; sizing and siting need municipal hydrology. |
| `low_lying` | Floodable park · retention basin | HAND, depression mask/depth, relative elevation, open/public land | Catalog + rules | P2 | OEF terrain COGs in catalog. Confirm implementable public land per parcel. |
| `low_lying` | Storage-oriented NBS | Land ownership / cadastre · underground utilities | Major gap | P1 | Topographic suitability ≠ feasible intervention footprint. |
| `drainage_constrained` | Any urban flood NBS (complement grey) | Municipal storm-drain network · culverts · capacity models | Major gap | P1 | Flag exists as proxy gap today; no open global layer. |
| `drainage_constrained` | Infiltration NBS | Groundwater depth · urban soil compaction surveys | Major gap | P1 | SoilGrids clay is coarse screening; urban hydrogeology required. |
| `mixed` | Bundled portfolio (e.g. bioswale + storage) | Per-cell tied mechanisms (GeoJSON strengths) + parcel constraints | Catalog + rules | P2 | POA mechanism_type + `mixed_tied_mechanisms` export supports this; portfolio rules TBD. |
| `none` / weak signal | Defer specific NBS | Higher-res hazard/context or field validation | Catalog + rules | P3 | Below `min_strength` — avoid over-recommending. |

---

## Heat (250 m grid)

| Dominant mechanism | Candidate NBS | Layers to localize | Data status | Priority | Notes |
|--------------------|---------------|-------------------|-------------|----------|-------|
| `shade_deficit` | Urban / street trees · green corridor | Hansen tree cover, MODIS NDVI, DW trees, planting-space proxy, slope | Catalog + rules | P2 | Tree cover ≠ pit width or species. OSM streets as weak placement proxy. |
| `shade_deficit` | Street trees (localized) | Plantable ROW width · native species list · irrigation/water supply | Local POA | P1 | Highest-value local uplift for dense POA cores. |
| `uhi_built_up` | Green roof / wall · permeable surfaces | Built-up density, LST composites, roof type & structural capacity | Major gap | P1 | Built-up layers cannot distinguish load-bearing roofs. |
| `high_daytime_lst` | Green roof · street trees | LST P90 (catalog) · pedestrian heat exposure · air temp/comfort | Major gap | P2 | Hazard uses surface temperature, not where people feel heat. |
| `limited_nocturnal_cooling` | Riparian cooling corridor · increased canopy | MODIS night/day LST, OSM waterways, riparian vegetation | Catalog + rules | P2 | Good screening combo; validate riparian access and maintenance. |
| `high_social_exposure` | Pocket park · schoolyard greening | E/V/R scores, OSM schools/parks, schoolyard plantable area | Local POA | P1 | Social priority known; site footprint needs municipal parcel / imagery. |
| `mixed` | Combined cooling package | `mixed_tied_mechanisms` + microclimate + water for irrigation | Catalog + rules | P2 | Common in POA (~28% heat cells mixed in prior runs). |
| `without_clear_dominant` | Low-specificity greening | Finer LST/built/tree cover or participatory site assessment | Catalog + rules | P3 | Use as watchlist, not strong NBS prescription. |

---

## Landslide (90 m grid, hazard > 0)

| Dominant mechanism | Candidate NBS | Layers to localize | Data status | Priority | Notes |
|--------------------|---------------|-------------------|-------------|----------|-------|
| `steep_activatable_slope` + `rainfall_trigger` | Slope revegetation · drainage works | Slope 90 m, R90p, clay %, NDVI P10, hazard > 0 gate | Catalog + rules | P2 | Dominant POA pattern; many `mixed` cells include this combo. |
| `vegetation_deficit` | Slope revegetation · forest restoration | NDVI P10, DW trees/bare, deep-rooted native species | Local POA | P1 | NDVI ≠ root architecture; species list is application-layer. |
| `disturbed_bare_slope` | Bioengineering · erosion-control vegetation | DW bare/built, slope, geotechnical class, species/root traits | Major gap | P1 | Global geology too coarse; geotech survey gates design. |
| `drainage_saturation` | Riparian / gully protection | HAND, dist to water, MERIT UPA, riparian vegetation | Catalog + rules | P2 | Good hydro-topographic screening; check flood–landslide trade-off. |
| `low_cohesion_wet` | Cover + drainage-sensitive planting | SoilGrids clay, soil texture/sand, antecedent moisture | Catalog only | P2 | Clay in rules; sand fraction & moisture dynamics mostly absent. |
| `upslope_convergence` | Upslope reforestation | MERIT UPA, upslope land tenure, fire/land-use constraints | Local POA | P1 | Hydrology proxy OK; implementation land often private upslope. |
| `high_social_exposure` | Downslope protection (any slope NBS) | E/V/R, buildings downslope, evacuation / multi-hazard context | Catalog + rules | P2 | Prioritize interventions protecting exposed settlements. |
| `mixed` | Portfolio by tied mechanisms | `mixed_tied_mechanisms` + geotech + species per tied driver | Catalog + rules | P1 | ~54% of hazard-active POA cells; highest product attention area. |

---

## Cross-cutting — catalog vs application

| Context | Candidate NBS | Layers to localize | Data status | Priority | Notes |
|---------|---------------|-------------------|-------------|----------|-------|
| All hazards | Vegetation-based NBS | Native species / ecoregions / GBIF | Major gap | P1 | Listed in lens + recommended-datasets; not wired into scoring. |
| All hazards | Ground-based NBS | Cadastre · land tenure · public ROW | Major gap | P1 | OSM parks/roads are weak proxy only. |
| Flood + heat riparian | Riparian buffer / cooling corridor | Multi-hazard trade-off review (flood vs landslide on banks) | Local POA | P2 | Same geometry, different scoring per hazard today. |
| All hazards | POA mechanism_type layer | COG/tiles + GeoJSON strengths (published) | Catalog + rules | P2 | Spatial WHERE done; next is mechanism → localized NBS filters. |

---

## Proposed decisions for review session

| Decision | Options |
|----------|---------|
| **Catalog vs application split** | Keep global COGs in catalog rules; POA plugins for species, cadastre, drainage |
| **Mixed cells** | Expose tied mechanisms → recommend bundles, not single winner |
| **First 3 POA datasets to wire** | Pick from P1 table: species guide, implementable public land, storm drains |
| **Expert gates** | Which NBS never surface without local validation (geotech, structural roofs) |

---

## Relationship to lens docs (short answer)

| Artifact | Role |
|----------|------|
| **Lens docs** | Exploratory methodology — what decisions matter and what datasets could support them |
| **recommended-datasets.md** | Full inventory tables (Steps 0–6) per NBS type |
| **This matrix** | Prioritized bridge: **mechanism → NBS → gap** for POA product work |
| **POA mechanism_type + GeoJSON** | Spatial implementation of Step 1 |
| **nbs_rules.py** | Implemented Step 2 scoring with catalog layers only |

The lens work is **not redundant** — this matrix operationalizes it against what is already built and what product should fund next.

**Tangible dataset names to explore:** see [`nbs_localization_dataset_candidates.md`](nbs_localization_dataset_candidates.md) (GBIF, IBGE, INMET, CEMADEN, OSM, SoilGrids, municipal POA sources, etc.).
