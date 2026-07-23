# Flood NBS Dataset Lens

## Purpose

This document applies the general NBS dataset identification methodology to **flood-related Nature-based Solution (NBS) design**.

It is intended to be used **after** flood hazard and flood risk hotspots have already been identified through the project’s flood hazard and flood risk score methodologies:

- `../../floods/docs/flood_hazard_score_methodology.md`
- `../../floods/docs/flood_risk_score_methodology.md`

Those methodologies answer:

> **Where is flooding a priority?**

This dataset lens answers:

> **Given those priority areas, what additional evidence is needed to determine which flood-related NBS options may be suitable?**

In other words, this document does **not** aim to recreate the flood hazard or flood risk scores. Instead, it identifies additional datasets that can help translate flood hazard/risk hotspots into plausible NBS design opportunities.

Relevant flood-related NBS include:

- bioswales;
- rain gardens;
- permeable surfaces;
- wetland restoration;
- floodplain restoration;
- riparian buffers;
- retention or detention basins;
- floodable parks;
- blue-green corridors.

The goal is to identify **which datasets support which flood NBS design decisions**. This is an exploration and recommendation exercise, not a final suitability model or engineering design.

---

## Relationship with flood hazard and flood risk scores

The flood hazard and flood risk score methodologies are the **primary screening inputs** for this lens.

They should be used first to identify:

- areas with high flood hazard;
- areas with high flood risk;
- exposed populations, assets, or urban systems;
- priority locations where intervention may be needed.

This dataset lens then supports a second step: identifying what kind of NBS, if any, may be appropriate in those locations.

A useful distinction is:

| Concept | Main question | Role in workflow |
|---|---|---|
| Flood hazard | Where is flooding likely or intense? | Identifies hazard hotspots |
| Flood risk | Where could flooding cause greater impacts? | Identifies priority areas for action |
| NBS suitability | What kind of NBS could plausibly work there? | Translates priority areas into potential interventions |

This distinction matters because **priority is not the same as suitability**.

A site can have high flood risk but low suitability for a specific NBS type. For example, a dense urban area with high flood risk may not have enough open land for a floodable park, but it may still be suitable for distributed interventions such as bioswales, permeable surfaces, green streets, or green roofs. Conversely, a low-lying open area near a river may be more suitable for floodplain restoration, wetland restoration, or retention storage.

---

## Main design logic

The flood hazard/risk layers identify where action may be needed. Additional datasets help determine what may be possible.

The workflow is:

```text
Existing flood hazard/risk outputs
→ Priority flood-exposed or high-risk zones
→ Likely flood mechanism
→ Site condition
→ Geospatial proxy
→ Candidate dataset
→ NBS decision unlocked
→ Gap or caveat
```

For flood-related NBS, the core design questions are:

1. **What type of flood problem is this?**  
   For example: riverine overflow, pluvial runoff, low-lying accumulation, drainage-constrained flooding, or coastal/tidal flooding if relevant.

2. **Where and why does water collect?**  
   This helps diagnose whether the problem is driven by topography, drainage convergence, imperviousness, rainfall intensity, or proximity to rivers/water bodies.

3. **Where can water be absorbed, slowed, conveyed, or stored?**  
   This helps identify whether infiltration, storage, restoration, or conveyance-oriented NBS may be plausible.

4. **What ecological conditions does the NBS require?**  
   This helps avoid generic “green” recommendations and supports ecologically appropriate restoration or planting.

5. **Where is implementation physically and institutionally feasible?**  
   This helps distinguish theoretically suitable areas from areas where land ownership, public access, infrastructure, or maintenance constraints may limit implementation.

---

## How to use this lens

Use this lens as a bridge between flood risk screening and NBS ideation.

Recommended steps:

1. Start with high flood hazard or high flood risk areas from the project’s existing flood methodologies.
2. Identify the likely flood mechanism in each priority area:
   - riverine overflow;
   - pluvial runoff;
   - low-lying accumulation;
   - drainage-constrained flooding;
   - coastal/tidal flooding, if relevant.
3. Use additional datasets to evaluate site conditions.
4. Match those site conditions to candidate NBS types.
5. Flag gaps that require local validation before design or implementation.

This lens should support early-stage screening and project preparation. It should not be used as a substitute for hydraulic modeling, engineering design, land tenure review, field infiltration testing, ecological validation, or local stakeholder input.

---

## Dataset roles

Because the project already has flood hazard and flood risk methodologies, flood-related datasets can be grouped into three roles.

### 1. Primary inputs already covered by hazard/risk methodologies

These are not the focus of this lens, but they provide the starting point:

- flood hazard score;
- flood risk score;
- flood exposure indicators;
- flood vulnerability indicators;
- existing flood-prone or flood-exposed zones.

### 2. Diagnostic datasets

These help explain **why** flooding may occur in a hotspot and what kind of flood process may dominate:

- flow accumulation;
- drainage network;
- low-lying terrain and depressions;
- surface water history;
- rainfall intensity;
- impervious surface and built-up area;
- local drainage infrastructure, where available.

### 3. NBS suitability datasets

These help determine which NBS types may be feasible or appropriate:

- soil texture and infiltration potential;
- groundwater depth;
- open/public land;
- existing green space;
- land ownership or tenure;
- wetland/riparian species data;
- ecoregions and ecosystem maps;
- protected areas or wetland inventories;
- infrastructure constraints.

---

## Flood NBS design questions

### Decision area 1 — Understanding the flood mechanism

This helps classify the type of flood problem in a priority area before proposing an intervention.

**Terrain note:** *Low-lying / depressions* and *slope* are different proxies. **Slope** is steepness (degrees). **Low-lying** is relative position in the landscape (elevation vs surroundings, or height above drainage). **Depressions** are topographic sinks where water ponds. A flat parking lot has low slope but is not necessarily a depression; a river valley bottom is low-lying but may have moderate bank slope.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is the site affected by riverine overflow? | proximity/connectivity to river or stream | drainage network, river buffers, floodplain position | supports riparian buffers, floodplain restoration, wetland restoration, and floodable parks |
| Is the site affected by pluvial runoff? | intense rainfall over urban surfaces | rainfall intensity, imperviousness, roads/buildings | supports distributed stormwater NBS such as bioswales, rain gardens, green streets, and permeable surfaces |
| Is water collecting because the area is low-lying? | terrain depression or low relative elevation | DEM, depressions, relative elevation | supports storage-oriented NBS such as floodable parks, basins, wetlands, or detention areas |
| Is flooding linked to drainage constraints? | limited drainage capacity or blocked/modified flow paths | local drainage network, culverts, canals, flow accumulation | helps identify where NBS may need to complement grey drainage infrastructure |
| Is there existing or historical surface water? | permanent or seasonal wetness | JRC surface water, local wetland inventories, satellite-derived water occurrence | supports wetland/floodplain restoration and helps avoid unsuitable interventions |

### Decision area 2 — Where water can be absorbed, slowed, conveyed, or stored

This helps identify locations where water-managing NBS may be physically plausible.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Can the soil absorb water? | infiltration potential | soil texture, sand/clay fraction, bulk density, hydrologic soil group | supports rain gardens, bioswales, permeable surfaces, and infiltration basins |
| Is groundwater too shallow for infiltration? | groundwater constraint | groundwater depth, hydrogeology | identifies constraints for infiltration-based NBS |
| Is there available open land? | storage opportunity | parks, vacant/open land, land cover, public land | supports floodable parks, retention basins, wetlands, and floodplain restoration |
| Is there existing green space to expand or connect? | ecological/space opportunity | NDVI, tree/grass cover, parks, riparian vegetation | supports blue-green corridors and restoration of existing systems |
| Are slopes suitable? | terrain suitability | slope, curvature | filters NBS types; infiltration/storage NBS usually need low-to-moderate slope |

### Decision area 3 — What the NBS needs ecologically

This helps avoid generic “green” recommendations and supports more ecologically appropriate NBS.

Ecological screening uses three layers that apply across hazards and NBS types, independent of any single ecosystem label (forest, grassland, wetland, riparian corridor, shrubland, etc.):

1. **Regional ecological context** — ecoregions, native vegetation zones, and landscape or watershed units where they inform local function.
2. **Habitat type and condition** — land-cover class, vegetation structure, degradation or loss, and fragmentation vs connectivity.
3. **Conservation sensitivity** — protected or otherwise sensitive areas, legal or institutional restrictions, and co-benefits.

The rows below apply these layers to flood-related NBS screening. Ecosystem names in proxy columns are illustrative examples, not an exhaustive taxonomy.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| What ecosystem context is the site in? | ecological region | ecoregions, vegetation zones, watershed units | helps align NBS with local ecosystem function |
| What habitat type and condition is present? | land cover class; degradation; connectivity | Dynamic World, Hansen forest cover change, NDVI, riparian/wetland inventories where available | distinguishes restoration of existing systems from new planting or engineered storage |
| What native species match the local habitat type? | species suitability | species occurrences, native species lists, habitat-typed vegetation maps | supports planting palettes and restoration logic |
| Are there protected or sensitive areas nearby? | conservation context | protected areas, wetland inventories, Ramsar sites, local conservation layers | identifies opportunities, restrictions, and co-benefits |
| Are invasive species a concern? | ecological risk | invasive species records, local ecological inventories | avoids harmful planting/restoration choices |

### Decision area 4 — Where implementation may be feasible

This is often the biggest gap between spatial screening and real NBS implementation.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is the land public or accessible? | land governance | public land, cadastral data, parks, schools, road rights-of-way | identifies where implementation may be easier |
| Are there conflicting land uses? | land-use constraints | zoning, buildings, roads, infrastructure, utilities | prevents unrealistic recommendations |
| Who benefits? | exposed population/assets | population, critical facilities, roads, vulnerable groups | supports prioritization and equity |
| Is maintenance feasible? | institutional feasibility | municipal assets, park management, road ownership | informs whether a proposed NBS can be sustained |

---

## Recommended flood-relevant datasets

### 1. Existing flood hazard and flood risk scores

| Field | Recommendation |
|---|---|
| Dataset examples | project flood hazard score, project flood risk score |
| Source | `../../floods/docs/flood_hazard_score_methodology.md`, `../../floods/docs/flood_risk_score_methodology.md` |
| Coverage / resolution | project-specific |
| Proxy represented | flood priority areas, hazard intensity, risk priority |
| NBS decision unlocked | identifies where NBS screening should begin; distinguishes priority areas from lower-priority areas |
| Relevant NBS | all flood-related NBS |
| Gaps / caveats | hazard/risk scores identify where action may be needed, but not which NBS is suitable; additional datasets are required for design logic |

### 2. Flow accumulation and drainage network

| Field | Recommendation |
|---|---|
| Dataset examples | HydroSHEDS core products, HydroRIVERS, HydroBASINS, MERIT Hydro, OpenStreetMap waterways, local drainage network |
| Source | HydroSHEDS, MERIT Hydro, OSM, municipal drainage data |
| Coverage / resolution | Global for HydroSHEDS/MERIT/OSM; local where municipal drainage exists |
| Proxy represented | drainage convergence, river/stream network, upstream/downstream connectivity |
| NBS decision unlocked | helps diagnose where water naturally concentrates and where riparian buffers, floodplain restoration, retention basins, constructed wetlands, or blue-green corridors may be plausible |
| Relevant NBS | riparian buffers, floodplain restoration, wetlands, retention/detention basins, blue-green corridors |
| Gaps / caveats | global hydrography may miss urban drainage, culverts, stormwater pipes, channelized streams, and local modifications; local drainage data is preferred for urban design |

Reference: [HydroSHEDS data products](https://www.hydrosheds.org/products)

### 3. Low-lying terrain and depressions

| Field | Recommendation |
|---|---|
| Dataset examples | Copernicus DEM GLO-30, SRTM, FABDEM, local LiDAR |
| Source | Copernicus, NASA/USGS, FABDEM, local survey agencies |
| Coverage / resolution | Global DEMs commonly 30 m; local LiDAR may be sub-meter to few meters |
| Proxy represented | low-lying areas, slope, depressions, relative elevation |
| NBS decision unlocked | helps diagnose whether a flood hotspot has storage potential or depression-driven accumulation |
| Relevant NBS | floodable parks, retention basins, detention basins, wetlands, floodplain restoration |
| Gaps / caveats | 30 m DEMs are useful for screening but too coarse for detailed urban micro-drainage; LiDAR or local topographic data is needed for design |

### 4. Surface water history

| Field | Recommendation |
|---|---|
| Dataset examples | JRC Global Surface Water, Dynamic World water class, ESA WorldCover water class, local wetland/river inventories |
| Source | European Commission Joint Research Centre, Google/World Resources Institute, ESA, local agencies |
| Coverage / resolution | JRC Global Surface Water is global and Landsat-based; ESA WorldCover is global 10 m for 2020/2021 |
| Proxy represented | permanent water, seasonal water, historical water occurrence, water transitions |
| NBS decision unlocked | identifies potential wetland/floodplain restoration areas and helps avoid proposing unsuitable interventions in permanent water bodies |
| Relevant NBS | wetland restoration, floodplain restoration, riparian restoration, constructed wetlands, retention basins near existing water systems |
| Gaps / caveats | historical water presence does not imply land availability, ecological suitability, or legal feasibility; must be crossed with land cover, ownership, and restrictions |

References: [JRC Global Surface Water Explorer](https://global-surface-water.appspot.com/) and [ESA WorldCover](https://esa-worldcover.org/en)

### 5. Rainfall intensity and flood-generating precipitation

| Field | Recommendation |
|---|---|
| Dataset examples | CHIRPS, IMERG, ERA5-Land, TerraClimate, local rain gauges, local IDF curves |
| Source | UCSB/CHC, NASA, ECMWF, University of Idaho, national meteorological services |
| Coverage / resolution | Global/regional gridded products; local gauges and IDF curves where available |
| Proxy represented | rainfall intensity, extreme precipitation, runoff generation potential |
| NBS decision unlocked | helps determine whether flooding is likely driven by local intense rainfall and whether distributed runoff reduction or storage NBS should be prioritized |
| Relevant NBS | rain gardens, bioswales, retention basins, floodable parks, watershed restoration |
| Gaps / caveats | gridded rainfall products are useful for screening but not enough for hydraulic design; local IDF curves are needed for sizing interventions |

Reference: [TerraClimate Earth Engine catalog](https://developers.google.com/earth-engine/datasets/catalog/IDAHO_EPSCOR_TERRACLIMATE)

### 6. Impervious surface and built-up area

| Field | Recommendation |
|---|---|
| Dataset examples | GHSL built-up surface, ESA WorldCover built-up class, Dynamic World built area, OpenStreetMap roads/buildings, local imperviousness layer |
| Source | European Commission / Copernicus GHSL, ESA, Google/WRI Dynamic World, OSM, local agencies |
| Coverage / resolution | Global for GHSL, ESA WorldCover, Dynamic World, and OSM; local imperviousness varies |
| Proxy represented | runoff-generating surfaces, urban density, retrofit opportunity |
| NBS decision unlocked | identifies areas where stormwater runoff may be reduced through distributed green infrastructure or permeable retrofits |
| Relevant NBS | bioswales, rain gardens, permeable pavements, green streets, green roofs, pocket parks |
| Gaps / caveats | built-up is not identical to imperviousness; local impervious surface data is preferable where available; OSM completeness varies by city |

References: [GHSL homepage](https://ghsl.jrc.ec.europa.eu/) and [ESA WorldCover](https://esa-worldcover.org/en)

### 7. Soil texture and infiltration potential

| Field | Recommendation |
|---|---|
| Dataset examples | SoilGrids, national soil maps, hydrologic soil groups, local infiltration tests |
| Source | ISRIC SoilGrids, national soil agencies, local surveys |
| Coverage / resolution | SoilGrids is global at approximately 250 m; local soil maps vary |
| Proxy represented | infiltration potential, drainage limitations, clay/sand content, soil constraints |
| NBS decision unlocked | helps identify whether infiltration-based NBS are plausible or whether storage/conveyance-based NBS may be more appropriate |
| Relevant NBS | rain gardens, bioswales, infiltration trenches, permeable pavements, infiltration basins, retention basins |
| Gaps / caveats | SoilGrids is screening-scale and cannot replace field infiltration tests; urban soils may be compacted, filled, contaminated, or disconnected from mapped natural soil properties |

Reference: [SoilGrids](https://soilgrids.org/)

### 8. Groundwater depth and hydrogeology

| Field | Recommendation |
|---|---|
| Dataset examples | global groundwater table depth products, national hydrogeological maps, groundwater monitoring wells |
| Source | academic/global products, national geological surveys, local water agencies |
| Coverage / resolution | variable; often coarse globally, better where local monitoring exists |
| Proxy represented | constraint for infiltration or underground storage |
| NBS decision unlocked | identifies areas where infiltration-based NBS may be constrained by shallow groundwater or saturation risk |
| Relevant NBS | rain gardens, bioswales, infiltration basins, permeable pavements, constructed wetlands, retention basins |
| Gaps / caveats | groundwater is often a major data gap; global products are usually too coarse for site design; local monitoring is strongly preferred |

### 9. Open land, public land, and green space

| Field | Recommendation |
|---|---|
| Dataset examples | OpenStreetMap parks/schools/public facilities, cadastral data, municipal land use, ESA WorldCover, Dynamic World, NDVI from Sentinel-2/Landsat |
| Source | OSM, municipal cadastral/land-use data, ESA, Google/WRI, satellite imagery |
| Coverage / resolution | global proxies available; local cadastral data varies |
| Proxy represented | space availability, implementation feasibility, existing vegetation |
| NBS decision unlocked | identifies where larger storage or restoration NBS may be physically and institutionally plausible |
| Relevant NBS | floodable parks, retention basins, constructed wetlands, riparian restoration, blue-green corridors, rain gardens in public sites |
| Gaps / caveats | land cover does not indicate ownership or legal availability; public land and cadastre are critical for implementation feasibility |

Reference: [ESA WorldCover](https://esa-worldcover.org/en)

### 10. Wetland, riparian, and native species data

| Field | Recommendation |
|---|---|
| Dataset examples | GBIF occurrences, national biodiversity portals, local herbarium records, native species lists, ecoregions, wetland inventories, Ramsar/WDPA |
| Source | GBIF, national biodiversity agencies, universities/herbaria, conservation organizations |
| Coverage / resolution | global occurrence data plus local/national ecological data where available |
| Proxy represented | ecological suitability, native species presence, restoration context |
| NBS decision unlocked | supports screening of native wetland/riparian species and alignment with local ecosystem conditions |
| Relevant NBS | wetland restoration, riparian buffers, floodplain restoration, constructed wetlands, riverbank stabilization |
| Gaps / caveats | GBIF occurrence records have sampling bias and quality issues; species selection requires local ecological expertise and should distinguish native, invasive, ornamental, and restoration-appropriate species |

Reference: [GBIF](https://www.gbif.org/)

---

## NBS-specific dataset needs

### Bioswales

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Flood priority | flood hazard score, flood risk score | where bioswale screening should be prioritized |
| Runoff source | impervious surface, roads, buildings | where runoff interception is relevant |
| Linear space | roads, rights-of-way, open strips | where bioswales could physically fit |
| Suitable slope | DEM-derived slope | where flow can be slowed without erosion problems |
| Soil/infiltration | SoilGrids, local soils, infiltration tests | whether infiltration is plausible |
| Groundwater constraint | groundwater depth | whether infiltration may be limited |
| Public feasibility | road ownership, public land | where implementation may be easier |

### Rain gardens

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Flood priority | flood hazard score, flood risk score | where rain garden screening should be prioritized |
| Local runoff source | buildings, roads, imperviousness | where small distributed capture may help |
| Available small open space | parks, schools, public parcels, vacant land | where rain gardens could fit |
| Low/moderate slope | DEM-derived slope | where ponding/infiltration is feasible |
| Infiltration potential | soil texture, hydrologic soil group | whether infiltration-based design is plausible |
| Avoid saturation | groundwater depth | whether shallow groundwater is a constraint |

### Permeable surfaces

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Flood priority | flood hazard score, flood risk score | where permeable surface retrofits should be prioritized |
| Existing hard surfaces | roads, parking areas, built-up/open paved land | where retrofit opportunities may exist |
| High runoff area | imperviousness/built-up density | where benefits may be highest |
| Soil drainage | soil texture, infiltration data | whether infiltration/storage layers may function |
| Land-use feasibility | roads, public land, zoning | whether retrofit is institutionally plausible |

### Wetland restoration

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Flood priority | flood hazard score, flood risk score | where wetland restoration screening should be prioritized |
| Wetness/hydrologic connection | JRC surface water, drainage network, flood hazard | where wetland restoration may be hydrologically plausible |
| Low-lying terrain | DEM, relative elevation | where water can be stored or retained |
| Non-built/open land | land cover, built-up, public land | where restoration may be physically feasible |
| Ecological suitability | wetland inventories, ecoregions, species data | what type of restoration may be appropriate |
| Legal/conservation context | protected areas, Ramsar, local regulations | whether there are restrictions or opportunities |

### Floodplain restoration

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Flood priority | flood hazard score, flood risk score | where floodplain restoration screening should be prioritized |
| Proximity to river | HydroRIVERS, OSM waterways, local hydrography | where floodplain reconnection may be relevant |
| Low-lying adjacent land | DEM, flood hazard, terrain indices | where reconnection/storage may be plausible |
| Space availability | land cover, public land, cadastre | where implementation may be feasible |
| Existing constraints | buildings, roads, critical infrastructure | where restoration may be constrained or require hybrid solutions |
| Ecological fit | riparian species, ecoregions, protected areas | what restoration approach/species may be appropriate |

### Retention or detention basins

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Flood priority | flood hazard score, flood risk score | where storage-based NBS screening should be prioritized |
| Flood/runoff problem | flood hazard, rainfall intensity, imperviousness | where storage could reduce flood impacts |
| Storage space | open/public land, parks, vacant land | where basins could physically fit |
| Low/moderate slope | DEM-derived slope | where basin construction may be feasible |
| Drainage connection | flow accumulation, drainage network | where basins can intercept flow |
| Soil/groundwater constraints | soils, groundwater depth | whether infiltration, lining, or wet design may be needed |

---

## Example interpretation matrix

| Flood priority and site condition | Likely implication for NBS screening |
|---|---|
| High flood risk + high imperviousness + roads/public rights-of-way + low/moderate slope | good candidate for green streets, bioswales, rain gardens, permeable surfaces |
| High flood risk + near river/stream + low-lying open land | good candidate for riparian restoration, floodplain restoration, floodable park, or wetland restoration |
| High flood risk + dense built-up area + little open/public land | larger storage/restoration NBS may be limited; consider distributed retrofits, green roofs, permeable surfaces, or hybrid grey-green approaches |
| High flood risk + clayey soils or shallow groundwater | infiltration-based NBS may be constrained; storage, detention, conveyance, or wetland-oriented NBS may be more appropriate |
| High flood risk + critical infrastructure | NBS may be complementary, but engineering review and risk management measures are required |

---

## Priority gaps for flood NBS design

The most important gaps to flag are:

1. **Urban drainage data**: global hydrology does not capture storm drains, culverts, canals, or engineered drainage.
2. **Public land / ownership**: land cover can identify open space, but not whether the site is available for implementation.
3. **Groundwater depth**: often unavailable at useful urban scale, but important for infiltration-based NBS.
4. **Local IDF curves / hydrologic design data**: needed for sizing rain gardens, bioswales, and basins.
5. **Field infiltration tests**: SoilGrids and soil maps are only screening proxies.
6. **Local native species expertise**: GBIF and ecoregions are useful starting points but not sufficient for species selection.
7. **Infrastructure conflicts**: utilities, underground pipes, roads, and buildings can make otherwise suitable areas infeasible.
8. **Land tenure and governance**: suitability on a map does not mean the site is legally or institutionally available.

---

## Recommended conclusion

For this stage, the deliverable should be a flood-relevant dataset inventory, not a final NBS suitability model.

The strongest framing is:

> The flood hazard and risk methodologies identify where action may be needed. This dataset lens identifies what additional evidence is needed to determine which flood-related NBS options may be suitable in those places.

These datasets support early-stage screening and ideation by linking flood processes, site conditions, and NBS requirements. Final placement and design require local drainage data, land ownership information, field infiltration tests, engineering review, and ecological validation.
