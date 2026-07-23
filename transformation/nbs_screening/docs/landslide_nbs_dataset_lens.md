# Landslide NBS Dataset Lens

## Purpose

This document applies the general NBS dataset identification methodology to **landslide-related Nature-based Solution (NBS) design**.

It is intended to be used **after** landslide hazard and landslide risk hotspots have already been identified through the project’s landslide hazard and landslide risk score methodologies:

- `../../landslides/docs/landslide_hazard_score_methodology.md`
- `../../landslides/docs/landslide_risk_score_methodology.md`

Those methodologies answer:

> **Where is landslide susceptibility a priority?**

This dataset lens answers:

> **Given those priority areas, what additional evidence is needed to determine which landslide-related NBS options may be suitable?**

In other words, this document does **not** aim to recreate the landslide hazard or landslide risk scores. Instead, it identifies additional datasets that can help translate landslide hazard/risk hotspots into plausible NBS design opportunities.

Relevant landslide-related NBS include:

- slope revegetation and grassing;
- bioengineering (live stakes, brush layers, coir logs, vegetated retaining structures);
- erosion-control vegetation on gullies and cut slopes;
- riparian stabilization and gully-head protection;
- forest restoration and upslope reforestation;
- terraced planting and root-reinforced drainage strips (where combined with engineering review).

The goal is to identify **which datasets support which landslide NBS design decisions**. This is an exploration and recommendation exercise, not a slope stability model, geotechnical design, or early-warning system.

---

## Relationship with landslide hazard and landslide risk scores

The landslide hazard and landslide risk score methodologies are the **primary screening inputs** for this lens.

They should be used first to identify:

- areas with high landslide susceptibility on activatable slopes (slope ≥ 15°);
- areas with high landslide risk where steep terrain coincides with exposed or vulnerable populations;
- bairros where mean hazard and risk are elevated despite flat lowlands scoring zero;
- priority hillslopes, ravines, and drainage-adjacent slopes where vegetation-based stabilization may be relevant.

This dataset lens then supports a second step: identifying what kind of NBS, if any, may be appropriate in those locations.

A useful distinction is:

| Concept | Main question | Role in workflow |
|---|---|---|
| Landslide hazard | Where are predisposing and triggering conditions most conducive to shallow landslides? | Identifies susceptibility hotspots on slopes |
| Landslide risk | Where could landslides cause greater impacts on people? | Identifies priority areas for action |
| NBS suitability | What kind of vegetation-based stabilization could plausibly help there? | Translates priority areas into potential interventions |

This distinction matters because **priority is not the same as suitability**.

A site can have high landslide risk but low suitability for a specific NBS type. For example, a steep cut slope above a road with shallow clay soils and high rainfall may be a priority for action, but large-scale forest restoration may be impossible where the slope is built over or owned privately. Conversely, a moderately steep hillslope with low vegetation cover, moderate HAND, and public open land may be more suitable for slope revegetation or riparian stabilization than for bioengineering structures that require engineered anchors.

**Important caveats from the hazard methodology:**

- The operational hazard score is a **static susceptibility index**, not a failure probability or return period.
- **Slope is the primary gate:** areas with slope < 15° score `H = 0` regardless of rainfall, soil, or vegetation. Flat lowlands therefore show zero landslide hazard by design.
- The hazard grid operates at **90 m** — finer than flood and heat (250 m) — but still too coarse for individual cut slopes or narrow ravines (< 30 m).
- **CHIRPS R90p** (~5 km native) provides regional precipitation context; it does not resolve orographic enhancement on individual hillslopes.
- The score has **not been validated** against the CEMADEN or INMET historical landslide inventory for Porto Alegre.

---

## Main design logic

The landslide hazard/risk layers identify where action may be needed on slopes. Additional datasets help determine what may be possible.

The workflow is:

```text
Existing landslide hazard/risk outputs
→ Priority slope-exposed or high-risk zones
→ Likely susceptibility mechanism (slope + trigger + soil + vegetation + drainage)
→ Site condition
→ Geospatial proxy
→ Candidate dataset
→ NBS decision unlocked
→ Gap or caveat
```

For landslide-related NBS, the core design questions are:

1. **What type of slope instability context is this?**  
   For example: steep bare slope, gully erosion, drainage-convergence saturation, vegetation-deficit hillslope, disturbed built/bare land on slope, or riparian bank instability.

2. **What are the predisposing and triggering factors?**  
   This helps distinguish whether the problem is driven primarily by slope angle, chronic extreme rainfall, low soil cohesion when wet, lack of root reinforcement, or upslope drainage convergence (low HAND).

3. **Where can root reinforcement, surface cover, or bioengineering be added?**  
   This helps identify whether revegetation, erosion-control planting, or riparian stabilization may be physically plausible.

4. **What ecological conditions does the NBS require?**  
   This helps avoid generic “plant trees on slopes” recommendations and supports deep-rooted, drought-tolerant, and locally appropriate species choices.

5. **Where is implementation physically, geotechnically, and institutionally feasible?**  
   This helps distinguish theoretically suitable hillslopes from areas where buildings, roads, utilities, land tenure, or geotechnical conditions require engineered solutions rather than vegetation alone.

---

## How to use this lens

Use this lens as a bridge between landslide risk screening and NBS ideation.

Recommended steps:

1. Start with high landslide hazard or high landslide risk areas from the project’s existing landslide methodologies (focus on pixels/bairros where `H > 0`, i.e., slope ≥ 15°).
2. Identify the likely susceptibility mechanism in each priority area:
   - steep slope with low vegetation;
   - drainage-convergence / low HAND saturation;
   - high clay content and rainfall trigger;
   - bare or built-up slope (Dynamic World modifier);
   - gully or riparian bank erosion;
   - upslope contributing area (UPA).
3. Use additional datasets to evaluate site conditions.
4. Match those site conditions to candidate NBS types.
5. Flag gaps that require geotechnical investigation, local validation, or multi-hazard review before design or implementation.

This lens should support early-stage screening and project preparation. It should not be used as a substitute for geotechnical investigation, slope stability analysis, landslide early warning, engineering design, land tenure review, or stakeholder consultation.

---

## Dataset roles

Because the project already has landslide hazard and landslide risk methodologies, landslide-related datasets can be grouped into three roles.

### 1. Primary inputs already covered by hazard/risk methodologies

These are not the focus of this lens, but they provide the starting point:

- landslide hazard score (`poa_landslide_hazard`);
- landslide risk score (`poa_landslide_risk`);
- exposure score (shared with flood and heat risk);
- vulnerability score (shared with flood and heat risk);
- bairro-level landslide risk summaries from OEF outputs.

The hazard ensemble already incorporates: Copernicus DEM slope, CHIRPS R90p, SoilGrids clay %, MODIS NDVI P10, MERIT HAND, and Dynamic World land cover modifier.

### 2. Diagnostic datasets

These help explain **why** a slope may be susceptible and what process may dominate:

- slope angle and terrain curvature;
- precipitation trigger context (R90p, antecedent rainfall where available);
- soil texture and clay content;
- vegetation cover deficit (NDVI P10, tree cover, bare land);
- drainage convergence (HAND, UPA);
- land cover disturbance (bare, built, deforestation);
- historical landslide events or geohazard maps (validation);
- geology and lithology (where available).

### 3. NBS suitability datasets

These help determine which NBS types may be feasible or appropriate:

- open/public land on slopes;
- distance to buildings, roads, and critical infrastructure;
- riparian/gully proximity;
- species suitability and root architecture;
- ecoregions and native vegetation context;
- protected areas;
- land ownership or tenure;
- multi-hazard conflicts (floodplain, heat, fire);
- maintenance responsibility and water availability for establishment.

---

## Landslide NBS design questions

### Decision area 1 — Understanding the susceptibility mechanism

This helps classify the type of slope problem in a priority area before proposing an intervention.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is the slope steep enough to initiate shallow failures? | activatable slope range | Copernicus DEM slope (15–35° gate in methodology) | filters where any slope NBS is relevant; flat areas score zero hazard |
| Is chronic extreme rainfall a trigger? | precipitation regime | CHIRPS R90p climatology | supports prioritization where rainfall saturation is a chronic driver |
| Is soil cohesion low when wet? | clay-rich surface soil | SoilGrids clay % (0–30 cm) | high clay may require drainage + species with appropriate root strategy; not only “more vegetation” |
| Is vegetation protection lacking? | persistently low cover | MODIS NDVI P10; Hansen tree cover; Dynamic World (bare/grass) | supports revegetation, reforestation, erosion-control planting |
| Is drainage convergence amplifying saturation? | low HAND; upslope area | MERIT HAND; MERIT UPA | supports riparian stabilization, gully protection, drainage-strip planting |
| Is the slope disturbed or bare? | built/bare land on slope | Dynamic World (built, bare); forest cover change | supports bioengineering + rapid cover; built slopes may need hybrid grey-green |
| Has the slope failed before? | historical instability | CEMADEN/municipal landslide inventory; event points | validation and exclusion of repeat-failure zones without engineering |

### Decision area 2 — Where stabilization can be delivered

This helps identify locations where vegetation-based NBS may be physically plausible.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is there plantable area on the slope? | open or vegetated-but-degraded slope | Dynamic World (grass, shrub, bare); slope mask | distinguishes bare cut slopes from forested but unstable slopes |
| Is the slope accessible for planting/maintenance? | proximity to roads, trails, public land | OSM roads; OSM parks; cadastre | supports feasibility of bioengineering and maintenance |
| Is the feature a gully, ravine, or riparian bank? | drainage proximity | MERIT HAND; OSM waterways; UPA | supports gully-head protection and riparian stabilization |
| Are buildings or roads downslope? | exposed assets | OSM buildings/roads; exposure score | supports prioritization; also raises consequence if NBS fails without engineering |
| Is upslope contributing area large? | upslope flow accumulation | MERIT UPA | larger upslope area may require upslope reforestation, not only toe planting |

### Decision area 3 — What the NBS needs ecologically

This helps avoid generic recommendations and supports locally appropriate planting.

Ecological screening uses three layers that apply across hazards and NBS types, independent of any single ecosystem label (forest, grassland, wetland, riparian corridor, shrubland, etc.):

1. **Regional ecological context** — ecoregions, native vegetation zones, and landscape or watershed units where they inform local function.
2. **Habitat type and condition** — land-cover class, vegetation structure, degradation or loss, and fragmentation vs connectivity.
3. **Conservation sensitivity** — protected or otherwise sensitive areas, legal or institutional restrictions, and co-benefits.

The rows below apply these layers to landslide-related NBS screening. Ecosystem names in proxy columns are illustrative examples, not an exhaustive taxonomy.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| What ecosystem context is the site in? | ecological region | ecoregions; native vegetation zones | aligns species with local ecology and drought tolerance |
| What habitat type and condition is on the slope? | bare, shrub, forest; degraded vs intact | Dynamic World, Hansen forest cover change, NDVI P10 | distinguishes revegetation, upslope reforestation, and protection of existing cover |
| What deep-rooted or slope-suitable species may work? | species suitability | GBIF; local native species lists; municipal arboriculture guides | root architecture matters more than canopy cover alone |
| Is the slope sun-exposed or drought-prone? | aspect; aridity (screening) | DEM aspect; climate indices | favors drought-tolerant natives over lawn or shallow-rooted ornamentals |
| Are there protected or sensitive areas upslope? | conservation context | WDPA, local conservation layers | upslope planting may be restricted, prioritized, or a co-benefit |
| Are invasive species a concern? | ecological risk | invasive species records | avoids planting that worsens erosion or fire risk |
| Will restored vegetation conflict with fire management? | land cover; urban-wildland interface | Dynamic World; built-up adjacency | multi-hazard screening in peri-urban slopes |

### Decision area 4 — Where implementation may be feasible

This is often the biggest gap between spatial screening and real NBS implementation.

| Design question | Site condition | Geospatial proxy | Why it matters for NBS |
|---|---|---|---|
| Is the land public or manageable? | land governance | public land; cadastre; parks; municipal slope assets | identifies where implementation may be easier |
| Are there buildings or infrastructure on the slope? | conflicting land uses | Dynamic World (built); OSM buildings/roads | built slopes often require engineered retaining + vegetation, not planting alone |
| Who is exposed downslope? | population; vulnerable groups | exposure score; vulnerability score; schools | supports equitable prioritization |
| Is geotechnical investigation available? | slope stability unknown | field investigation; geology maps | **required** before design on high-consequence slopes |
| Are there multi-hazard trade-offs? | floodplain, riparian, heat | flood hazard; heat hazard; JRC surface water | riparian planting may help landslide and heat but interact with flood storage design |

---

## Recommended landslide-relevant datasets

### 1. Existing landslide hazard and landslide risk scores

| Field | Recommendation |
|---|---|
| Dataset examples | `poa_landslide_hazard`, `poa_landslide_risk` |
| Source | `../../landslides/docs/landslide_hazard_score_methodology.md`, `../../landslides/docs/landslide_risk_score_methodology.md` |
| Coverage / resolution | POA; hazard/risk **90 m**; E/V constant within bairro (burned to 90 m grid) |
| Proxy represented | susceptibility priority on slopes; risk priority where steep terrain meets exposed populations |
| NBS decision unlocked | identifies where slope-stabilization NBS screening should begin |
| Relevant NBS | all landslide-related NBS |
| Gaps / caveats | susceptibility ≠ failure probability; does not indicate which NBS is suitable; not validated against event inventory |

### 2. Slope and terrain

| Field | Recommendation |
|---|---|
| Dataset examples | Copernicus GLO-30 DEM slope (`poa_slope_deg_30m`); curvature; aspect (derived) |
| Source | Copernicus / OEF |
| Coverage / resolution | 30 m slope exported; aggregated to 90 m hazard grid |
| Proxy represented | gravitational driving force; activation gate (≥ 15°); terrain constraints |
| NBS decision unlocked | filters NBS to activatable slopes; identifies cut/fill slopes vs natural hillsides |
| Relevant NBS | slope revegetation, bioengineering, erosion-control vegetation |
| Gaps / caveats | DEM alone does not indicate geology, bedding planes, or internal weakness; LiDAR preferred for site design |

### 3. Precipitation trigger (CHIRPS R90p)

| Field | Recommendation |
|---|---|
| Dataset examples | CHIRPS R90p climatology (`poa_r90p_climatology`) |
| Source | CHC / OEF |
| Coverage / resolution | ~5 km native → nearest resample to 90 m |
| Proxy represented | chronic extreme rainfall regime; soil saturation trigger context |
| NBS decision unlocked | supports prioritization where rainfall is a recurrent detonator; context for drainage + cover NBS |
| Relevant NBS | all slope NBS; especially bioengineering and drainage-strip planting in high-R90p zones |
| Gaps / caveats | coarse spatial resolution; not antecedent rainfall or real-time warning; local rain gauges preferred for design |

### 4. Soil cohesion (SoilGrids clay)

| Field | Recommendation |
|---|---|
| Dataset examples | SoilGrids clay weight fraction 0–30 cm (`poa_clay_pct_250m`) |
| Source | ISRIC / GEE OpenLandMap |
| Coverage / resolution | 250 m → bilinear to 90 m |
| Proxy represented | pore-pressure sensitivity; effective cohesion reduction when wet |
| NBS decision unlocked | distinguishes sandy vs clayey slope contexts; informs species and drainage strategy |
| Relevant NBS | slope revegetation, bioengineering, riparian stabilization |
| Gaps / caveats | global map ≠ site geotechnical survey; anthropogenic fill/excavation not captured |

Reference: [SoilGrids](https://soilgrids.org/)

### 5. Vegetation protection (MODIS NDVI P10)

| Field | Recommendation |
|---|---|
| Dataset examples | MODIS NDVI P10 DJF 2015–2024 (`poa_ndvi_p10_djf_2015_2024`) |
| Source | NASA MODIS / OEF |
| Coverage / resolution | 250 m → bilinear to 90 m |
| Proxy represented | persistently low vegetation cover; lack of root reinforcement |
| NBS decision unlocked | identifies vegetation-deficit slopes where revegetation may add protection |
| Relevant NBS | slope revegetation, forest restoration, erosion-control vegetation |
| Gaps / caveats | NDVI ≠ root depth, species, or root tensile strength; P10 is screening-scale |

### 6. Drainage convergence (MERIT HAND and UPA)

| Field | Recommendation |
|---|---|
| Dataset examples | MERIT HAND (`poa_hand_90m`); MERIT UPA; OSM waterways |
| Source | MERIT Hydro; OSM |
| Coverage / resolution | 90 m (HAND); vector (OSM) |
| Proxy represented | proximity to drainage network; upslope contributing area; gully/riparian context |
| NBS decision unlocked | supports riparian stabilization, gully-head protection, and upslope reforestation targeting |
| Relevant NBS | riparian stabilization, forest restoration, bioengineering on drainage paths |
| Gaps / caveats | HAND ≠ urban storm drains; tile gaps filled with neutral default in hazard score |

Reference: [MERIT Hydro](http://hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_Hydro/)

### 7. Land cover disturbance (Dynamic World)

| Field | Recommendation |
|---|---|
| Dataset examples | Dynamic World mode 2023 (`poa_dw_mode_2023`); Hansen forest cover change |
| Source | Google/WRI; Hansen/UMD |
| Coverage / resolution | 10 m → mode to 90 m |
| Proxy represented | bare/built slopes; degraded vs forested hillsides |
| NBS decision unlocked | identifies disturbed slopes needing cover; dampens hazard where persistent tree/grass cover confirmed |
| Relevant NBS | slope revegetation, bioengineering, erosion-control vegetation |
| Gaps / caveats | 2023 vintage; rapid deforestation or construction after 2023 not reflected |

### 8. Shared exposure and vulnerability scores

| Field | Recommendation |
|---|---|
| Dataset examples | OEF exposure score, OEF vulnerability score |
| Source | IBGE Censo 2022 → OEF shared E/V pipeline |
| Coverage / resolution | bairro attributes burned to 90 m for landslide risk |
| Proxy represented | population density exposure; age-based social vulnerability |
| NBS decision unlocked | prioritizes slopes where more people or vulnerable groups are downslope |
| Relevant NBS | all landslide-related NBS where consequence is high |
| Gaps / caveats | age-only V; no informal housing on slopes, housing quality, or early-warning access |

### 9. Public land, infrastructure, and assets

| Field | Recommendation |
|---|---|
| Dataset examples | OSM roads, buildings, schools; cadastre; municipal geohazard maps |
| Source | OSM; municipal agencies |
| Coverage / resolution | vector |
| Proxy represented | implementation access; downslope assets; institutional feasibility |
| NBS decision unlocked | identifies slopes manageable by public agencies vs private tenure; prioritizes slopes above critical infrastructure |
| Relevant NBS | bioengineering, slope revegetation, riparian stabilization |
| Gaps / caveats | OSM incomplete; cadastre and geohazard inventories often not open |

### 10. Species, ecology, and validation inventories

| Field | Recommendation |
|---|---|
| Dataset examples | GBIF occurrences; ecoregions; CEMADEN landslide inventory; municipal event points |
| Source | GBIF; national agencies; civil defense |
| Coverage / resolution | point/vector; variable |
| Proxy represented | ecological suitability; historical failure locations; calibration context |
| NBS decision unlocked | supports native/deep-rooted planting palettes; validates or challenges susceptibility hotspots |
| Relevant NBS | slope revegetation, forest restoration, riparian stabilization, bioengineering |
| Gaps / caveats | GBIF sampling bias; event inventories often incomplete; species selection requires local geotech + ecology |

Reference: [GBIF](https://www.gbif.org/)

---

## NBS-specific dataset needs

### Slope revegetation

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Landslide priority | landslide hazard score, landslide risk score | where revegetation screening should be prioritized |
| Activatable slope | Copernicus DEM slope (≥ 15°) | whether the methodology considers the slope landslide-relevant |
| Vegetation deficit | MODIS NDVI P10; Dynamic World (bare/grass) | where root reinforcement is likely lacking |
| Soil context | SoilGrids clay/sand | whether species and drainage strategy should account for cohesive soils |
| Rainfall trigger | CHIRPS R90p | whether chronic wetting is a major driver |
| Asset exposure | exposure score; OSM buildings/roads downslope | whether consequence justifies intervention |
| Geotechnical clearance | geology maps; site investigation | whether vegetation alone is credible or engineering is required |

### Bioengineering / erosion-control vegetation

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Landslide priority | landslide hazard score, landslide risk score | where bioengineering screening should begin |
| Active erosion / bare soil | Dynamic World (bare); low NDVI | where surface cover is urgently needed |
| Drainage path | MERIT HAND; UPA; OSM waterways | where gully or drainage-path bioengineering may fit |
| Slope severity | Copernicus DEM slope | whether bioengineering structures are feasible vs too steep for vegetation alone |
| Access/maintenance | OSM roads; public land | whether installation and maintenance are realistic |
| Species context | GBIF; ecoregions; local native lists | which deep-rooted or fibrous-root species may be appropriate |

### Riparian stabilization / gully-head protection

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Landslide priority | landslide hazard score, landslide risk score | where riparian/gully interventions should be screened |
| Drainage proximity | MERIT HAND; OSM waterways | where bank or gully-head stabilization is relevant |
| Upslope contribution | MERIT UPA | whether upslope reforestation is needed in addition to toe works |
| Existing riparian cover | Hansen tree cover; Dynamic World (trees) | where restoration vs new planting applies |
| Multi-hazard context | flood hazard; JRC surface water | whether riparian works align with or conflict with flood management |
| Public access | parks; public land; cadastre | whether riparian corridors are manageable |

### Forest restoration / upslope reforestation

| Requirement | Useful datasets | Decision unlocked |
|---|---|---|
| Landslide priority | landslide hazard score, landslide risk score | where upslope restoration should be prioritized |
| Forest loss / degradation | Hansen forest cover change; Dynamic World | where reforestation restores lost protection |
| Large upslope area | MERIT UPA | where catchment-scale planting may reduce saturation |
| Ecological fit | ecoregions; GBIF; native species lists | what to plant for root reinforcement and drought tolerance |
| Land tenure | cadastre; protected areas (WDPA) | whether upslope land is available and permissible |
| Fire / multi-hazard | built-up adjacency; regional fire context | whether dense planting is appropriate |

---

## Example interpretation matrix

| Landslide priority and site condition | Likely implication for NBS screening |
|---|---|
| High risk + steep slope + low NDVI P10 + moderate HAND + public open slope | good candidate for slope revegetation or upslope reforestation |
| High risk + bare/built slope + road below + high clay + high R90p | bioengineering + drainage review likely needed; vegetation alone may be insufficient |
| High hazard + low HAND + riparian bare bank + park access | good candidate for riparian stabilization and gully-head protection |
| High risk + dense buildings on slope + high exposure | prioritize consequence reduction; geotechnical/engineered solution likely required before NBS |
| High hazard in zone also flagged for floodplain storage | multi-hazard review needed; riparian NBS may help both or require hybrid design |
| High hazard but flat/lowland bairro mean | bairro mean may be driven by peripheral hillslopes; site-scale slope check required |

---

## Priority gaps for landslide NBS design

The most important gaps to flag are:

1. **Susceptibility ≠ stability:** the hazard score is not a slope stability analysis and does not replace geotechnical investigation.
2. **Geology and lithology:** global datasets rarely resolve POA-specific weathered granite, colluvium, or fill materials.
3. **Landslide event inventory:** CEMADEN/municipal inventories are critical for validation but often not open or complete.
4. **Root architecture:** NDVI and land cover cannot infer root depth, tensile strength, or appropriate species for shear resistance.
5. **CHIRPS R90p resolution:** ~5 km native limits spatial detail for individual hillslopes; antecedent rainfall not modeled.
6. **Informal housing on slopes:** not captured in vulnerability score; major landslide consequence driver in POA periphery.
7. **Built slopes and retaining structures:** Dynamic World built class does not distinguish engineered vs unstable cut slopes.
8. **Multi-hazard trade-offs:** riparian and floodplain NBS may interact with flood and heat priorities.
9. **Maintenance and establishment water:** drought stress during establishment is a common failure mode; rarely mapped openly.
10. **90 m grid limits:** narrow ravines and cut slopes may be under-represented; LiDAR needed for site design.

---

## Recommended conclusion

For this stage, the deliverable should be a landslide-relevant dataset inventory, not a final NBS suitability or stability model.

The strongest framing is:

> The landslide hazard and risk methodologies identify where action may be needed on slopes. This dataset lens identifies what additional evidence is needed to determine which landslide-related NBS options may be suitable in those places.

These datasets support early-stage screening and ideation by linking susceptibility mechanisms, site conditions, and NBS requirements. Final placement and design require geotechnical investigation, species selection by local ecologists, land tenure review, multi-hazard assessment, and stakeholder input.

---

## Related documents

- `docs/nbs_dataset_identification_methodology.md` — shared workflow (Steps 1–8)
- `docs/recommended-datasets.md` — POA dataset inventory organized by hazard (flood, heat, landslides)
- `docs/flood_nbs_dataset_lens.md` — parallel lens for flood NBS
- `docs/heat_nbs_dataset_lens.md` — parallel lens for heat NBS
- `../../landslides/docs/landslide_hazard_score_methodology.md` — operational landslide hazard score
- `../../landslides/docs/landslide_risk_score_methodology.md` — operational landslide risk score
- `../../../../geospatial-data/catalog/datasets.yaml` — POA catalog assets (`poa_landslide_hazard`, `poa_landslide_risk`, component layers where published)
