# Heat NBS Dataset Lens

## Purpose

This document applies the general NBS dataset identification methodology to **heat-related Nature-based Solution (NBS) design**.

It is intended to be used **after** heat hazard and heat risk hotspots have already been identified through the project’s heat hazard and heat risk score methodologies:

- `../../heat/docs/heat_hazard_score_methodology.md`
- `../../heat/docs/heat_risk_score_methodology.md`

Those methodologies answer:

> **Where is heat a priority?**

This dataset lens answers:

> **Given those priority areas, what additional evidence is needed to determine which heat-related NBS options may be suitable?**

In other words, this document does **not** aim to recreate the heat hazard or heat risk scores. Instead, it identifies additional datasets that can help translate heat hazard/risk hotspots into plausible NBS design opportunities.

Relevant heat-related NBS include:

- urban trees and street trees;
- urban forests and tree clusters;
- green corridors and blue-green corridors;
- pocket parks and shaded public space;
- schoolyard and courtyard greening;
- green roofs and green walls;
- riparian or waterfront cooling corridors;
- bioswales and vegetated strips where they also reduce hard-surface heat.

The goal is to identify **which datasets support which heat NBS design decisions**. This is an exploration and recommendation exercise, not a final suitability model, microclimate model, or engineering design.

---

## Relationship with heat hazard and heat risk scores

The heat hazard and heat risk score methodologies are the **primary screening inputs** for this lens.

They should be used first to identify:

- areas with high chronic heat hazard (LST-based ensemble);
- areas with high heat risk (H × E × V);
- exposed populations and socially vulnerable groups;
- priority locations where cooling interventions may be needed.

This dataset lens then supports a second step: identifying what kind of NBS, if any, may be appropriate in those locations.

A useful distinction is:

| Concept | Main question | Role in workflow |
|---|---|---|
| Heat hazard | Where is chronic summer heat exposure high? | Identifies thermal hazard hotspots |
| Heat risk | Where could heat cause greater impacts? | Identifies priority areas for action |
| NBS suitability | What kind of NBS could plausibly cool there? | Translates priority areas into potential interventions |

This distinction matters because **priority is not the same as suitability**.

A site can have high heat risk but low suitability for a specific NBS type. For example, a dense downtown block with high heat risk may not have enough rooting space or public land for a large pocket park, but it may still be suitable for street trees, green roofs, shaded corridors, or schoolyard greening. Conversely, a low-built peripheral area with moderate heat hazard may be more suitable for green corridors or larger tree clusters than for rooftop interventions.

**Important caveat from the hazard methodology:** the operational heat hazard score uses a Landsat + MODIS LST ensemble at 250 m. It measures **surface temperature**, not pedestrian air temperature or thermal comfort. ERA5-Land extreme-temperature indices exist in the catalog for regional screening but were **excluded from the hazard ensemble** because their native resolution (~9 km) is too coarse for intra-urban POA analysis.

---

## Main design logic

The heat hazard/risk layers identify where action may be needed. Additional datasets help determine what may be possible.

The workflow is:

```text
Existing heat hazard/risk outputs
→ Priority heat-exposed or high-risk zones
→ Likely heat mechanism / exposure context
→ Site condition
→ Geospatial proxy
→ Candidate dataset
→ NBS decision unlocked
→ Gap or caveat
```

For heat-related NBS, the core design questions are:

1. **What type of heat problem is this?**  
   For example: high built-up / low vegetation (urban heat island), lack of shade, high daytime surface heating, limited nocturnal cooling, high pedestrian exposure, or heatwave-prone context.

2. **Who is exposed and where do people actually experience heat?**  
   This helps distinguish map hotspots from places where cooling NBS would benefit daily life — streets, schools, transit stops, markets, outdoor work areas.

3. **Where can shade, evapotranspiration, or surface cooling be added?**  
   This helps identify whether tree planting, green roofs, vegetated strips, or larger green spaces may be physically plausible.

4. **What can grow and be maintained in the local context?**  
   This helps avoid generic “plant trees everywhere” recommendations and supports drought-tolerant, ecologically appropriate species choices.

5. **Where is implementation physically and institutionally feasible?**  
   This helps distinguish theoretically suitable areas from areas where land ownership, utilities, water supply, or maintenance constraints may limit implementation.

---

## How to use this lens

Use this lens as a bridge between heat risk screening and NBS ideation.

Recommended steps:

1. Start with high heat hazard or high heat risk areas from the project’s existing heat methodologies.
2. Identify the likely heat exposure context in each priority area:
   - high built-up / low vegetation;
   - lack of shade or tree cover;
   - high daytime LST;
   - limited nocturnal cooling;
   - high pedestrian or social exposure;
   - heatwave-prone regional context.
3. Use additional datasets to evaluate site conditions.
4. Match those site conditions to candidate NBS types.
5. Flag gaps that require local validation before design or implementation.

This lens should support early-stage screening and project preparation. It should not be used as a substitute for microclimate modeling, thermal comfort assessment, species selection by local ecologists, water-balance analysis, engineering review, or stakeholder consultation.

---

## Dataset roles

Because the project already has heat hazard and heat risk methodologies, heat-related datasets can be grouped into three roles.

### 1. Primary inputs already covered by hazard/risk methodologies

These are not the focus of this lens, but they provide the starting point:

- heat hazard score (`poa_heat_hazard`);
- heat risk score (`poa_heat_risk`);
- exposure score (shared with flood risk);
- vulnerability score (shared with flood risk);
- bairro-level heat risk summaries from OEF outputs.

### 2. Diagnostic datasets

These help explain **why** heat may be a problem in a hotspot and what kind of thermal process may dominate:

- built-up density and impervious surfaces;
- vegetation cover, tree cover, and NDVI;
- land cover classes (grass, trees, bare, built);
- daytime vs nocturnal thermal context (where available);
- population and pedestrian exposure proxies;
- regional extreme-temperature and heatwave indices (screening only).

### 3. NBS suitability datasets

These help determine which NBS types may be feasible or appropriate:

- open/public land and parks;
- street rights-of-way and planting space;
- roof availability (proxy via built-up + building height where available);
- soil and water availability;
- native / drought-tolerant species data;
- land ownership or tenure;
- infrastructure constraints (utilities, underground services);
- maintenance responsibility.

---

## Heat NBS design questions

### Decision area 1 — Understanding the heat exposure context

This helps classify the type of heat problem in a priority area before proposing an intervention.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is the area highly built-up with little vegetation? | urban heat island pattern | GHSL built-up, Dynamic World (built), low NDVI/tree cover | supports urban trees, green corridors, pocket parks, green roofs |
| Is there a lack of shade where people move or wait? | pedestrian exposure + low tree cover | tree cover, parks, schools, OSM streets/transit stops | supports street trees, shaded corridors, schoolyard greening |
| Is daytime surface heating high? | high LST / low vegetation | heat hazard score, MODIS/Landsat-derived layers, built-up inverse | supports surface cooling via vegetation, green roofs, vegetated strips |
| Is nocturnal heat retention a concern? | limited night cooling | MODIS night LST (methodology input), built-up density, low vegetation | supports vegetation and surface interventions that improve overnight recovery |
| Is the area regionally heatwave-prone? | extreme heat frequency | ERA5-Land TX90p/TX99p/TXx, HWM (catalog; coarse) | supports prioritization context, not parcel-scale design |
| Are socially vulnerable groups concentrated here? | vulnerability + exposure | vulnerability score, population, schools, health facilities | supports equitable targeting of cooling NBS |

### Decision area 2 — Where cooling can be delivered

This helps identify locations where cooling NBS may be physically plausible.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is there space to plant trees? | planting space along streets or open land | OSM streets/ROW, parks, Dynamic World (grass/bare), low built-up fraction | supports street trees, pocket parks, corridors |
| Is there roof area available? | built surfaces suitable for retrofit | GHSL built-up, Dynamic World (built), building footprints if available | supports green roofs and rooftop vegetation |
| Is there existing green to expand or connect? | fragmented or continuous vegetation | NDVI, Hansen tree cover, Dynamic World (trees/grass), parks | supports green corridors and cluster planting |
| Is soil and water sufficient for vegetation? | planting feasibility | SoilGrids, local water supply, drought indicators | filters species choice and maintenance burden |
| Are slopes or terrain constraints present? | terrain suitability | Copernicus DEM slope | steep or unstable slopes may limit some planting designs |

### Decision area 3 — What the NBS needs ecologically

This helps avoid generic recommendations and supports locally appropriate planting.

Ecological screening uses three layers that apply across hazards and NBS types, independent of any single ecosystem label (forest, grassland, wetland, riparian corridor, shrubland, etc.):

1. **Regional ecological context** — ecoregions, native vegetation zones, and landscape or watershed units where they inform local function.
2. **Habitat type and condition** — land-cover class, vegetation structure, degradation or loss, and fragmentation vs connectivity.
3. **Conservation sensitivity** — protected or otherwise sensitive areas, legal or institutional restrictions, and co-benefits.

The rows below apply these layers to heat-related NBS screening. Ecosystem names in proxy columns are illustrative examples, not an exhaustive taxonomy.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| What ecosystem context is the site in? | ecological region | ecoregions, native vegetation zones | helps align species with local ecology |
| Is there existing habitat to conserve, restore, or connect? | fragmented, degraded, or intact vegetation | Hansen forest cover change, Dynamic World (trees/shrub/grass), NDVI, park and corridor networks | separates expand-and-connect strategies from greenfield urban planting; relevant for urban forests and corridors |
| What native or drought-tolerant species may be suitable? | species suitability | GBIF, local native species lists, herbarium records | supports planting palettes and survival screening |
| Are there protected or sensitive areas nearby? | conservation context | WDPA, local APP or conservation layers, municipal park reserves | identifies restrictions and co-benefits for forest patches, corridors, and riparian cooling |
| Are invasive species a concern? | ecological risk | invasive species records, local ecological inventories | avoids harmful planting choices |
| Is water scarcity a constraint? | drought / irrigation need | climate aridity, local water stress, maintenance capacity | favors drought-tolerant trees and low-water greening |

### Decision area 4 — Where implementation may be feasible

This is often the biggest gap between spatial screening and real NBS implementation.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is the land public or accessible? | land governance | public land, cadastre, parks, schools, road ROW | identifies where implementation may be easier |
| Are there conflicting land uses? | land-use constraints | zoning, buildings, roads, utilities | prevents unrealistic recommendations |
| Who benefits? | exposed population/assets | population, schools, transit stops, outdoor workers | supports prioritization and equity |
| Is maintenance feasible? | institutional feasibility | municipal parks, school ownership, street maintenance | informs whether proposed NBS can be sustained |

---

## Recommended heat-relevant datasets

### 1. Existing heat hazard and heat risk scores

| Field | Recommendation |
|---|---|
| Dataset examples | `poa_heat_hazard`, `poa_heat_risk` |
| Source | `../../heat/docs/heat_hazard_score_methodology.md`, `../../heat/docs/heat_risk_score_methodology.md` |
| Coverage / resolution | POA; hazard/risk ~250 m; E/V constant within bairro |
| Proxy represented | heat priority areas, chronic summer thermal hazard, risk priority |
| NBS decision unlocked | identifies where cooling NBS screening should begin; distinguishes priority areas from lower-priority areas |
| Relevant NBS | all heat-related NBS |
| Gaps / caveats | hazard/risk scores identify where action may be needed, but not which NBS is suitable; LST ≠ air temperature or thermal comfort |

### 2. Shared exposure and vulnerability scores

| Field | Recommendation |
|---|---|
| Dataset examples | OEF exposure score, OEF vulnerability score |
| Source | IBGE Censo 2022 → OEF shared E/V pipeline |
| Coverage / resolution | ~250 m rasterized from bairro attributes |
| Proxy represented | population density exposure; age-based social vulnerability |
| NBS decision unlocked | helps prioritize cooling interventions where more people or more vulnerable groups are exposed |
| Relevant NBS | all heat-related NBS, especially schoolyard greening and public-space cooling |
| Gaps / caveats | age-only vulnerability proxy; no heat-specific modifiers such as outdoor occupation, housing quality, or access to cooling |

### 3. Built-up area and impervious surfaces

| Field | Recommendation |
|---|---|
| Dataset examples | GHSL built-up, Dynamic World (built), OSM roads/buildings |
| Source | JRC GHSL; Google/WRI Dynamic World; OSM |
| Coverage / resolution | 100 m; 10 m; vector |
| Proxy represented | hard surfaces, urban density, UHI drivers, retrofit opportunity |
| NBS decision unlocked | identifies areas where vegetation, shade, or green roofs may reduce surface heating |
| Relevant NBS | urban trees, green corridors, pocket parks, green roofs, vegetated strips |
| Gaps / caveats | built-up ≠ measured imperviousness; roof suitability and existing green roofs not directly observable |

References: [GHSL homepage](https://ghsl.jrc.ec.europa.eu/)

### 4. Vegetation cover, tree cover, and NDVI

| Field | Recommendation |
|---|---|
| Dataset examples | Dynamic World (trees/grass), Hansen tree cover 2000, MODIS NDVI, forest cover change |
| Source | Google/WRI; Hansen/UMD; NASA MODIS |
| Coverage / resolution | 10 m; 30 m; 250 m |
| Proxy represented | existing shade, vegetation deficit, green connectivity opportunity |
| NBS decision unlocked | distinguishes already-green areas from shade-deficit hotspots; supports corridor and cluster planting |
| Relevant NBS | urban trees, green corridors, pocket parks, riparian cooling corridors |
| Gaps / caveats | NDVI and tree cover are proxies, not species composition or canopy health; MODIS NDVI is coarse for street-scale design |

### 5. Land cover and open space

| Field | Recommendation |
|---|---|
| Dataset examples | Dynamic World (grass, bare, shrub), OSM parks/schools, GHSL built-up inverse |
| Source | Google/WRI; OSM |
| Coverage / resolution | 10 m; vector |
| Proxy represented | open land, potential planting space, public green space |
| NBS decision unlocked | identifies where pocket parks, schoolyard greening, or corridor expansion may fit |
| Relevant NBS | pocket parks, schoolyard greening, green corridors, urban forests |
| Gaps / caveats | land cover ≠ ownership; park presence ≠ plantable or maintainable space |

### 6. Regional extreme temperature and heatwave indices

| Field | Recommendation |
|---|---|
| Dataset examples | ERA5-Land TX90p, TX99p, TXx, TNx, HWM (2024 and climatology) |
| Source | ECMWF/Copernicus via OEF catalog |
| Coverage / resolution | ~11 km (ERA5-Land derived) |
| Proxy represented | extreme heat frequency, heatwave magnitude, regional thermal stress context |
| NBS decision unlocked | supports screening-level prioritization and climate-change context; useful for narrative and regional comparison |
| Relevant NBS | all cooling NBS at screening stage |
| Gaps / caveats | too coarse for intra-urban POA design; excluded from operational heat hazard ensemble for this reason; not a substitute for local LST or comfort metrics |

### 7. Terrain and slope

| Field | Recommendation |
|---|---|
| Dataset examples | Copernicus DEM GLO-30 |
| Source | Copernicus |
| Coverage / resolution | 30 m |
| Proxy represented | slope, terrain constraints, relative elevation |
| NBS decision unlocked | filters planting locations; steep slopes may constrain some greening or require bioengineering |
| Relevant NBS | green corridors, riparian cooling corridors, slope planting |
| Gaps / caveats | DEM alone does not indicate microclimate, aspect, or wind exposure |

### 8. Soil and water availability

| Field | Recommendation |
|---|---|
| Dataset examples | SoilGrids, local water supply layers, drought indicators |
| Source | ISRIC; municipal water agencies |
| Coverage / resolution | ~250 m globally; local where available |
| Proxy represented | planting feasibility, irrigation need, soil constraints |
| NBS decision unlocked | helps distinguish drought-tolerant street-tree designs from irrigation-dependent green roofs or lawns |
| Relevant NBS | urban trees, green roofs, schoolyard greening, vegetated strips |
| Gaps / caveats | SoilGrids is screening-scale; urban soils often compacted or filled; water availability is a major local gap |

Reference: [SoilGrids](https://soilgrids.org/)

### 9. Public land, schools, and rights-of-way

| Field | Recommendation |
|---|---|
| Dataset examples | OSM parks, schools, streets; cadastral/public land layers |
| Source | OSM; municipal cadastre |
| Coverage / resolution | vector |
| Proxy represented | implementation feasibility, institutional access |
| NBS decision unlocked | identifies where schoolyard greening, street trees, or pocket parks may be more feasible |
| Relevant NBS | street trees, schoolyard greening, pocket parks, green corridors |
| Gaps / caveats | OSM is incomplete; cadastre and legal tenure remain major gaps |

### 10. Species and ecological context

| Field | Recommendation |
|---|---|
| Dataset examples | GBIF occurrences, ecoregions, local native species lists |
| Source | GBIF; national/local ecological agencies |
| Coverage / resolution | point/vector; variable locally |
| Proxy represented | ecological suitability, native species screening |
| NBS decision unlocked | supports drought-tolerant and native planting palettes |
| Relevant NBS | urban trees, green corridors, riparian cooling corridors |
| Gaps / caveats | GBIF has sampling bias; species selection requires local ecological expertise |

Reference: [GBIF](https://www.gbif.org/)

---

## NBS-specific dataset needs

### Urban trees / street trees

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Heat priority | heat hazard score, heat risk score | where tree planting screening should be prioritized |
| Shade deficit | low tree cover, low NDVI, high built-up | where additional canopy may reduce surface/pedestrian heat |
| Planting space | streets, ROW, parks, open land | where trees could physically fit |
| Exposure context | population, schools, transit stops | where shade benefits more people |
| Soil/water | SoilGrids, local water supply | whether irrigation-dependent species are realistic |
| Maintenance feasibility | public land, road ownership | where implementation may be easier |

### Green corridors / blue-green corridors

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Heat priority | heat hazard score, heat risk score | where corridor screening should begin |
| Existing green fragments | NDVI, tree cover, parks, Dynamic World | where corridors can connect existing vegetation |
| Built-up barriers | GHSL, Dynamic World (built) | where continuous corridors are blocked |
| Drainage/water context | OSM waterways, MERIT HAND, JRC surface water | where riparian cooling corridors may add co-benefits |
| Public feasibility | parks, public land, cadastre | whether corridor land may be accessible |

### Pocket parks / shaded public space

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Heat priority | heat hazard score, heat risk score | where public-space cooling should be prioritized |
| Open land availability | Dynamic World (grass/bare), OSM parks | where small parks or plaza greening may fit |
| High exposure | population, vulnerability, schools | where cooling benefits are highest |
| Built-up constraint | GHSL built-up | whether enough open space exists in dense blocks |

### Schoolyard greening

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Heat priority | heat hazard score, heat risk score | where school interventions should be screened |
| School locations | OSM schools, municipal education facilities | where interventions could be targeted |
| Exposure | vulnerability score, child-age share in V | whether vulnerable age groups benefit |
| Open space on site | high-resolution imagery, local parcel data | whether schoolyards have plantable area |
| Maintenance | school ownership, municipal education authority | whether interventions can be sustained |

### Green roofs / green walls

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Heat priority | heat hazard score, heat risk score | where rooftop cooling may be most valuable |
| Built surfaces | GHSL built-up, Dynamic World (built), building footprints | where retrofit potential exists |
| Structural feasibility | building height/type, local regulations | whether roofs/walls can support vegetation |
| Water demand | drought indicators, local water supply | whether irrigation-dependent designs are viable |

### Riparian / waterfront cooling corridors

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Heat priority | heat hazard score, heat risk score | where waterfront cooling corridors may be prioritized |
| Proximity to water | OSM waterways, JRC surface water, MERIT HAND | where riparian vegetation may improve thermal comfort |
| Existing vegetation | Dynamic World (trees), NDVI | where restoration or expansion is plausible |
| Public access | parks, trails, public land | whether people can actually benefit from the cooling corridor |

---

## Example interpretation matrix

| Heat priority and site condition | Likely implication for NBS screening |
|---|---|
| High heat risk + high built-up + low tree cover + street ROW | good candidate for street trees, vegetated strips, shaded corridors |
| High heat risk + school nearby + some open schoolyard space | good candidate for schoolyard greening |
| High heat risk + dense downtown + limited open land | large pocket parks may be limited; consider green roofs, street trees, facade greening |
| High heat risk + existing park fragments + low connectivity | good candidate for green corridor expansion |
| High heat risk + water-scarce context + public maintenance uncertainty | favor drought-tolerant native trees over irrigation-heavy lawn or intensive green roofs |
| High heat risk + riparian/open waterfront access | good candidate for riparian cooling corridor or waterfront shade planting |

---

## Priority gaps for heat NBS design

The most important gaps to flag are:

1. **LST ≠ thermal comfort:** hazard scores use surface temperature, not air temperature, shade fraction, humidity, or wind — all critical for human heat exposure.
2. **Pedestrian exposure layers:** no standard open dataset identifies where people actually experience outdoor heat (sidewalks, transit stops, markets, outdoor work).
3. **Roof suitability:** built-up layers do not distinguish roof type, structural capacity, or existing green roofs.
4. **Water availability and irrigation:** major constraint for trees and green roofs in dry periods; rarely available as open urban layers.
5. **Species and maintenance:** GBIF and global land cover cannot replace local arborist / ecological input.
6. **Public land / cadastre:** land cover can show open space but not legal availability or maintenance responsibility.
7. **Underground utilities:** conflict with tree pits, green walls, and planting trenches.
8. **Coarse climate indices:** ERA5-Land TX/HWM products in the catalog are useful for regional context but not for parcel-scale cooling design.
9. **Heat-health calibration:** the risk score is not calibrated to mortality, hospitalization, or productivity loss.
10. **Microclimate feedback:** planting one tree does not automatically cool a block; canopy design, orientation, and surrounding materials matter and require local assessment.

---

## Recommended conclusion

For this stage, the deliverable should be a heat-relevant dataset inventory, not a final NBS suitability model.

The strongest framing is:

> The heat hazard and risk methodologies identify where action may be needed. This dataset lens identifies what additional evidence is needed to determine which heat-related NBS options may be suitable in those places.

These datasets support early-stage screening and ideation by linking thermal exposure patterns, site conditions, and NBS requirements. Final placement and design require microclimate assessment, species selection, water and maintenance planning, land tenure review, and stakeholder input.

---

## Related documents

- `docs/nbs_dataset_identification_methodology.md` — shared workflow (Steps 1–8)
- `docs/flood_nbs_dataset_lens.md` — parallel lens for flood NBS
- `docs/recommended-datasets.md` — POA dataset inventory organized by hazard (flood, heat, landslides)
- `../../heat/docs/heat_hazard_score_methodology.md` — operational heat hazard score
- `../../heat/docs/heat_risk_score_methodology.md` — operational heat risk score
- `../../../../geospatial-data/catalog/datasets.yaml` — POA catalog assets (`poa_heat_hazard`, `poa_heat_risk`, ERA5-Land indices, GHSL, Dynamic World, MODIS NDVI)
