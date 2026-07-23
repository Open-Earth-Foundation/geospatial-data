# Recommended Datasets for NBS Design

Exploratory inventory for **Porto Alegre (POA)**. Links each candidate dataset to an NBS design decision, following the workflow in `docs/nbs_dataset_identification_methodology.md`.

**Scope:** multi-hazard NBS screening for POA. Tables are organized **by hazard** below. Hazard-specific rationale lives in the lens documents (`flood`, `heat`, `landslide`).

---

## Hazard index

| Hazard | Lens document | E2E notebook | Tables in this doc |
|---|---|---|---|
| **Flood** | `docs/flood_nbs_dataset_lens.md` | `scripts/nbs_site_query_flood_e2e.ipynb` | Steps 0–6 populated |
| **Heat** | `docs/heat_nbs_dataset_lens.md` | `scripts/nbs_site_query_heat_e2e.ipynb` | Steps 0–6 populated |
| **Landslides** | `docs/landslide_nbs_dataset_lens.md` | `scripts/nbs_site_query_landslide_e2e.ipynb` | Steps 0–6 populated |

Use the lens doc for hazard-specific design logic; use this doc for the **dataset inventory tables** (proxy → dataset → gap).

---

## Shared workflow (Steps 0–6)

Each row in the hazard tables traces one link in this chain:

```text
Step 0  Priority screening     → hazard/risk scores (where to start)
Step 1  Hazard context         → where/why the problem occurs (before choosing NBS)
Step 2  NBS typology           → e.g. rain garden, street trees, slope revegetation
Step 3  Site condition         → Required | Preferred | Exclusion | Uncertainty
Step 4  Geospatial proxy        → measurable spatial concept for that condition
Step 5  Candidate dataset       → data source that represents the proxy
Step 6  Gap / caveat            → what the dataset cannot answer
```

**How to read a row:** for NBS *X*, site condition *Y* needs proxy *Z*; dataset *D* is a candidate to assess it; note the gap.

Step 1 is hazard-specific:

| Hazard | Step 1 question |
|---|---|
| Flood | Where / why does water collect or overflow? |
| Heat | What thermal exposure pattern dominates (UHI, shade deficit, LST, social exposure)? |
| Landslides | What predisposing and triggering factors combine (slope, rain, soil, vegetation, drainage)? |

---

## Flood

> Detail: `docs/flood_nbs_dataset_lens.md` · Methodology: `../../floods/docs/flood_hazard_score_methodology.md`

### Step 0 — Priority screening

Flood hazard and risk scores identify **where** to start. They do not indicate **which** NBS fits.

| Hazard | Role | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|
| Flood | Priority area | Flood susceptibility / hazard intensity | Flood hazard score (`poa_flood_hazard`) | OEF / geospatial-data | ~250 m | Screening only; does not indicate NBS type |
| Flood | Priority area | Hazard × exposure × vulnerability | Flood risk score (`poa_flood_risk`) | OEF / geospatial-data | ~250 m | Priority ≠ suitability |
| Flood | Exposure context | Population density | Exposure score | IBGE → OEF grid | ~250 m | Constant within bairro |
| Flood | Vulnerability context | Age share (social vulnerability) | Vulnerability score | IBGE → OEF grid | ~250 m | Age-only proxy |
| Flood | Socioeconomic context | Poverty, infrastructure | IBGE neighbourhood indicators | IBGE | vector (bairros) | Census 2010 indicators |
| Flood | Validation context | Observed flood depth | Copernicus EMSN194 (May 2024) | Copernicus EMS | event raster | Event-specific; not primary hazard score |

### Step 1 — Flood mechanism: where / why water collects

Read this **before** the NBS tables below. These rows diagnose the type of flood problem in a priority zone — they apply to **all** water-managing NBS, not one type in particular.

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | *(mechanism)* | Required | Riverine overflow / drainage convergence | Flow accumulation; drainage network | MERIT UPA; OSM waterways | MERIT; OSM | 90 m; vector | Misses storm drains |
| Flood | *(mechanism)* | Required | Low-lying near drainage | HAND; low relative elevation | MERIT HAND; `poa_relative_elevation` | MERIT; geospatial-data / catalog | 90 m; 30 m | HAND ≠ engineered drainage |
| Flood | *(mechanism)* | Required | Topographic depressions | Depression mask; depression depth | `poa_depression_mask`; `poa_depression_depth` | geospatial-data / catalog | 30 m | Topographic sink only; not hydraulic modeling |
| Flood | *(mechanism)* | Required | Pluvial / urban runoff | Imperviousness; rainfall intensity | GHSL built-up; Dynamic World; CHIRPS | GHSL; Google/WRI; CHC | 100 m; 10 m; ~5 km | No true imperviousness layer |
| Flood | *(mechanism)* | Required | Historical / existing surface water | Water occurrence; seasonality | JRC GSW (occurrence, seasonality, transition) | JRC / Google EE | 30 m | Does not show land availability |
| Flood | *(mechanism)* | Required | Drainage-constrained flooding | Urban drainage network | Local storm drains; culverts; canals | municipal | — | **Major gap** — not in catalog |
| Flood | *(mechanism)* | Preferred | Design-intensity rainfall | IDF curves; rain gauges | Local rain gauges / IDF | municipal | point | Needed for sizing; not available |

### Steps 2–6 — By NBS type

Once the flood mechanism is understood (Step 1), use the tables below to match **site conditions → proxies → datasets** for each candidate NBS type.

#### Bioswales

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Bioswale | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | Where to screen, not whether bioswale fits |
| Flood | Bioswale | Required | Runoff source | Impervious surface; built-up density; roads | GHSL built-up; Dynamic World (built); OSM roads | GHSL; Google/WRI; OSM | 100 m; 10 m; vector | Built-up ≠ imperviousness; OSM not in catalog |
| Flood | Bioswale | Required | Linear space along flow path | Roads; rights-of-way; open strips | OSM roads; OSM parks (adjacent) | OSM | vector | Proxy for public ROW; not legal tenure |
| Flood | Bioswale | Required | Low/moderate slope | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m | DEM derivative; field geotech may still be needed |
| Flood | Bioswale | Preferred | Infiltrable soil | Soil texture; clay/sand fraction | `soilgrids_clay` | ISRIC / catalog | ~250 m | Screening proxy; field tests needed |
| Flood | Bioswale | Exclusion | Shallow groundwater | Groundwater depth | Global groundwater depth | various | — | Not available at useful urban scale |
| Flood | Bioswale | Preferred | Public feasibility | Public land; road ownership | OSM parks; OSM roads; cadastre | OSM; municipal | vector / parcel | Cadastre incomplete; OSM is proxy only |

#### Rain gardens

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Rain garden | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | Priority screening only |
| Flood | Rain garden | Required | Runoff source | Impervious surface; built-up density; roads; rainfall intensity | GHSL built-up; Dynamic World (built); OSM roads; CHIRPS R90p/Rx1day | GHSL; Google/WRI; OSM; CHC | 100 m; 10 m; vector; ~5 km | No local IDF curves |
| Flood | Rain garden | Required | Space for infiltration | Open / non-built land | Dynamic World (grass, bare, shrub); GHSL built-up (inverse) | Google/WRI; GHSL | 10 m; 100 m | Land cover ≠ ownership |
| Flood | Rain garden | Required | Low/moderate slope | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m | Same layer as bioswale screening |
| Flood | Rain garden | Preferred | Infiltrable soil | Soil texture; hydrologic soil group | `soilgrids_clay` | ISRIC / catalog | ~250 m | Screening proxy; field tests required before design |
| Flood | Rain garden | Preferred | Near runoff sources | Buildings; roads | OSM roads; Dynamic World (built) | OSM; Google/WRI | vector; 10 m | Parcel-scale placement needs local data |
| Flood | Rain garden | Preferred | Public / accessible land | Parks; schools; public parcels | OSM parks; OSM schools | OSM | vector | Overpass proxy; not legal tenure |
| Flood | Rain garden | Exclusion | High groundwater | Groundwater depth | Global groundwater depth | various | — | Major gap for infiltration NBS |
| Flood | Rain garden | Exclusion | Very steep slope | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m | Same layer as above |
| Flood | Rain garden | Uncertainty | Underground infrastructure | Utilities; pipes | — | — | — | No open geospatial layer |

#### Permeable surfaces

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Permeable surfaces | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | Retrofit prioritization only |
| Flood | Permeable surfaces | Required | Existing hard surfaces | Roads; parking; built-up | OSM roads; GHSL built-up; Dynamic World (built) | OSM; GHSL; Google/WRI | vector; 100 m; 10 m | Cannot distinguish paved vs permeable existing |
| Flood | Permeable surfaces | Required | High runoff area | Imperviousness; built-up density | GHSL built-up; Dynamic World (built) | GHSL; Google/WRI | 100 m; 10 m | Proxy, not measured imperviousness |
| Flood | Permeable surfaces | Preferred | Soil drainage | Soil texture; infiltration | `soilgrids_clay`; field infiltration tests | ISRIC / catalog; field | ~250 m; point | Field tests required before design |
| Flood | Permeable surfaces | Preferred | Institutional feasibility | Public land; zoning; roads | OSM roads; OSM parks; cadastre | OSM; municipal | vector | Zoning not in catalog |
| Flood | Permeable surfaces | Exclusion | High groundwater | Groundwater depth | Global groundwater depth | various | — | Major gap for infiltration retrofits |
| Flood | Permeable surfaces | Exclusion | Very steep slope | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m | DEM derivative |
| Flood | Permeable surfaces | Uncertainty | Underground infrastructure | Utilities; pipes | — | — | — | No open geospatial layer |

#### Wetland restoration

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Wetland restoration | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | — |
| Flood | Wetland restoration | Required | Wetness / hydrologic connection | Surface water history; drainage network | JRC GSW (occurrence, seasonality, transition); OSM surface water; OSM waterways | JRC; OSM | 30 m; vector | JRC ≠ land availability; OSM not in catalog |
| Flood | Wetland restoration | Required | Low-lying terrain | Relative elevation; depressions; HAND | `poa_relative_elevation`; `poa_depression_mask`; `poa_depression_depth`; MERIT HAND | geospatial-data / catalog; MERIT | 30 m; 90 m | Local geospatial-data exports; S3 tiles pending |
| Flood | Wetland restoration | Required | Non-built / open land | Land cover; built-up | Dynamic World; GHSL built-up | Google/WRI; GHSL | 10 m; 100 m | Land cover ≠ tenure |
| Flood | Wetland restoration | Preferred | Ecological suitability | Ecoregion; species; wetland inventory | Ecoregions; GBIF; OSM wetlands; Ramsar | various; OSM | vector / point | Mostly not in catalog; needs expert validation |
| Flood | Wetland restoration | Exclusion | Protected / sensitive areas | Conservation designations | WDPA; Ramsar | UNEP-WCMC | vector | Not in catalog for POA |

#### Floodplain restoration

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Floodplain restoration | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | — |
| Flood | Floodplain restoration | Required | Proximity to river | Drainage network; river buffers | OSM waterways; MERIT UPA/HAND; MERIT elevation | OSM; MERIT | vector; 90 m | Misses urban storm drains |
| Flood | Floodplain restoration | Required | Low-lying adjacent land | Relative elevation; floodplain position | `poa_relative_elevation`; `gfplain250m`; `wri_aqueduct_flood` | geospatial-data / catalog | 30 m; 250 m | GFPLAIN/Aqueduct also feed `poa_flood_hazard`; local COG pending S3 |
| Flood | Floodplain restoration | Preferred | Space availability | Open land; public land | Dynamic World; OSM parks; cadastre | Google/WRI; OSM | 10 m; vector | Cadastre gap |
| Flood | Floodplain restoration | Exclusion | Conflicting infrastructure | Buildings; roads; critical facilities | Dynamic World (built); OSM roads; MapBiomas infra | Google/WRI; OSM; MapBiomas | 10 m; vector | No underground utilities layer |
| Flood | Floodplain restoration | Preferred | Ecological fit | Riparian species; ecoregions | GBIF; ecoregions; Dynamic World (trees) | various | point / vector | Species selection needs local expertise |

#### Retention / detention basins

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Retention / detention basin | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | — |
| Flood | Retention / detention basin | Required | Runoff / flood problem | Rainfall intensity; imperviousness; hazard | CHIRPS R90p/Rx5day; GHSL built-up; flood hazard | CHC; GHSL; OEF | ~5 km; 100 m; ~250 m | Gridded rainfall; not local hydrology |
| Flood | Retention / detention basin | Required | Storage space | Open / public land | Dynamic World (grass, bare); OSM parks | Google/WRI; OSM | 10 m; vector | Ownership unknown |
| Flood | Retention / detention basin | Required | Low/moderate slope | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m | DEM derivative |
| Flood | Retention / detention basin | Preferred | Drainage connection | Flow accumulation; drainage network | MERIT UPA; OSM waterways; HAND | MERIT; OSM | 90 m; vector | Urban drainage not captured |
| Flood | Retention / detention basin | Preferred | Soil / groundwater | Soil texture; groundwater depth | `soilgrids_clay`; global groundwater | ISRIC / catalog; various | ~250 m | Wet vs dry basin design needs field data |

#### Riparian buffers & blue-green corridors

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Riparian buffer; blue-green corridor | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | — |
| Flood | Riparian buffer; blue-green corridor | Required | River/stream proximity | Drainage network; distance to water | OSM waterways; MERIT HAND; OSM surface water | OSM; MERIT | vector; 90 m | Vector rivers not in catalog |
| Flood | Riparian buffer; blue-green corridor | Preferred | Existing green to connect | NDVI; tree cover; parks | MODIS NDVI; Hansen tree cover; Dynamic World; OSM parks | NASA; Hansen; Google/WRI; OSM | 250 m; 30 m; 10 m; vector | NDVI coarse for corridor design |
| Flood | Riparian buffer; blue-green corridor | Preferred | Ecological context | Riparian vegetation; species | Dynamic World (trees, flooded vegetation); GBIF | Google/WRI; GBIF | 10 m; point | Not species-level |
| Flood | Riparian buffer; blue-green corridor | Exclusion | Protected / sensitive areas | Conservation designations | WDPA; Ramsar | UNEP-WCMC | vector | Not in catalog for POA |
| Flood | Riparian buffer; blue-green corridor | Exclusion | Dense built environment | Built-up density; lack of corridor space | GHSL built-up; Dynamic World (built) | GHSL; Google/WRI | 100 m; 10 m | Continuous corridor rarely feasible in urban core |
| Flood | Riparian buffer; blue-green corridor | Uncertainty | Underground infrastructure | Utilities; pipes along riparian ROW | — | — | — | No open geospatial layer |

#### Floodable parks

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Flood | Floodable park | Required | Flood priority | Flood hazard; flood risk | `poa_flood_hazard`; `poa_flood_risk` | OEF / geospatial-data | ~250 m | — |
| Flood | Floodable park | Required | Low-lying / storage potential | Relative elevation; depressions; HAND | `poa_relative_elevation`; `poa_depression_depth`; MERIT HAND | geospatial-data / catalog; MERIT | 30 m; 90 m | Local geospatial-data exports; S3 tiles pending |
| Flood | Floodable park | Required | Available open land | Parks; non-built land cover | OSM parks; Dynamic World (grass) | OSM; Google/WRI | vector; 10 m | Park ≠ automatically floodable or available |
| Flood | Floodable park | Preferred | Near drainage / floodplain | Flow accumulation; floodplain | MERIT UPA; `gfplain250m`; JRC GSW | MERIT; catalog; JRC | 90 m; 30 m; 250 m | — |
| Flood | Floodable park | Exclusion | Dense built environment | Built-up density | GHSL built-up; Dynamic World (built) | GHSL; Google/WRI | 100 m; 10 m | Large open parcels rare in urban core |

---

## Heat

> Detail: `docs/heat_nbs_dataset_lens.md` · Methodology: `../../heat/docs/heat_hazard_score_methodology.md`

### Step 0 — Priority screening

Heat hazard and risk scores identify **where** cooling action may be needed. They do not indicate **which** cooling NBS fits.

| Hazard | Role | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|
| Heat | Priority area | Chronic summer thermal hazard (LST ensemble) | Heat hazard score (`poa_heat_hazard`) | OEF / geospatial-data | ~250 m | LST ≠ air temperature or thermal comfort |
| Heat | Priority area | Hazard × exposure × vulnerability | Heat risk score (`poa_heat_risk`) | OEF / geospatial-data | ~250 m | Priority ≠ suitability; not calibrated to heat-health outcomes |
| Heat | Exposure context | Population density | Exposure score | IBGE → OEF grid | ~250 m | Constant within bairro; no outdoor-occupation proxy |
| Heat | Vulnerability context | Age share (social vulnerability) | Vulnerability score | IBGE → OEF grid | ~250 m | Age-only proxy; no housing quality or cooling access |
| Heat | Regional context | Extreme heat frequency / heatwave magnitude | ERA5-Land TX90p, TX99p, TXx, HWM | ECMWF / catalog | ~11 km | Too coarse for intra-urban design; excluded from hazard ensemble |
| Heat | Diagnostic context | Built-up / vegetation drivers | GHSL built-up; Dynamic World; MODIS NDVI | GHSL; Google/WRI; NASA | 100 m; 10 m; 250 m | Proxies for UHI drivers, not pedestrian exposure |
| Heat | Diagnostic context | LST inputs to hazard ensemble | `landsat8_lst_djf`; `modis_mod11a2_lst_djf` | USGS/NASA / catalog | 30 m; 1 km | Used in `poa_heat_hazard`; LST ≠ air temperature |

### Step 1 — Heat exposure context: what type of heat problem?

Read this **before** the NBS tables below. These rows classify the thermal exposure pattern in a priority zone — they apply to **all** cooling NBS, not one type in particular.

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Heat | *(mechanism)* | Required | Urban heat island (high built-up, low vegetation) | Built-up density; low NDVI/tree cover | GHSL built-up; Dynamic World (built); MODIS NDVI; Hansen tree cover | GHSL; Google/WRI; NASA; Hansen | 100 m; 10 m; 250 m; 30 m | Built-up ≠ measured imperviousness |
| Heat | *(mechanism)* | Required | Shade deficit where people move or wait | Low tree cover + street/transit exposure | Dynamic World (trees); Hansen tree cover; OSM streets/transit stops | Google/WRI; Hansen; OSM | 10 m; 30 m; vector | No standard pedestrian heat-exposure layer |
| Heat | *(mechanism)* | Required | High daytime surface heating | High LST; low vegetation | `poa_heat_hazard`; built-up inverse; NDVI | OEF / geospatial-data; GHSL; MODIS | ~250 m; 100 m; 250 m | Surface temperature ≠ shade fraction or comfort |
| Heat | *(mechanism)* | Preferred | Limited nocturnal cooling | Night LST; built-up density; low vegetation | `modis_mod11a2_lst_djf` (night); GHSL; Dynamic World | NASA / catalog; GHSL; Google/WRI | 1 km; 100 m; 10 m | Night band in catalog; excluded as separate hazard layer |
| Heat | *(mechanism)* | Preferred | Socially vulnerable groups concentrated | Vulnerability + population + schools | Vulnerability score; exposure score; OSM schools | OEF; OSM | ~250 m; vector | No heat-specific vulnerability modifiers |
| Heat | *(mechanism)* | Preferred | Regionally heatwave-prone context | Extreme heat frequency | ERA5-Land TX90p/TX99p/TXx, HWM | ECMWF / catalog | ~11 km | Screening context only; not parcel-scale |

### Steps 2–6 — By NBS type

Once the heat exposure context is understood (Step 1), use the tables below for each candidate cooling NBS type.

#### Urban trees / street trees

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Heat | Urban / street trees | Required | Heat priority | Heat hazard; heat risk | `poa_heat_hazard`; `poa_heat_risk` | OEF / geospatial-data | ~250 m | Where to screen, not whether trees fit |
| Heat | Urban / street trees | Required | Shade deficit | Low tree cover; low NDVI; high built-up | Hansen tree cover; MODIS NDVI; Dynamic World (trees); GHSL built-up | Hansen; NASA; Google/WRI; GHSL | 30 m; 250 m; 10 m; 100 m | Tree cover ≠ species, canopy health, or pit space |
| Heat | Urban / street trees | Required | Planting space | Streets; ROW; parks; open land | OSM streets; OSM parks; Dynamic World (grass/bare) | OSM; Google/WRI | vector; 10 m | ROW ≠ legal planting permission |
| Heat | Urban / street trees | Preferred | High pedestrian exposure | Population; schools; transit stops | Exposure score; OSM schools; OSM transit | OEF; OSM | ~250 m; vector | Pedestrian flows not mapped openly |
| Heat | Urban / street trees | Preferred | Soil / water feasibility | Soil texture; drought context | `soilgrids_clay`; local water supply | ISRIC / catalog; municipal | ~250 m | Urban soils compacted; irrigation need often unknown |
| Heat | Urban / street trees | Preferred | Maintenance feasibility | Public land; road ownership | OSM parks; OSM roads; cadastre | OSM; municipal | vector | Cadastre gap; maintenance responsibility unknown |
| Heat | Urban / street trees | Exclusion | Very steep or unstable slope | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m | Steep slopes may limit pit stability |
| Heat | Urban / street trees | Uncertainty | Underground utilities | Utilities; pipes | — | — | — | Conflicts with tree pits and root zones |

#### Green corridors / blue-green corridors

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Heat | Green corridor; blue-green corridor | Required | Heat priority | Heat hazard; heat risk | `poa_heat_hazard`; `poa_heat_risk` | OEF / geospatial-data | ~250 m | — |
| Heat | Green corridor; blue-green corridor | Required | Existing green fragments | NDVI; tree cover; parks | MODIS NDVI; Hansen tree cover; Dynamic World (trees/grass); OSM parks | NASA; Hansen; Google/WRI; OSM | 250 m; 30 m; 10 m; vector | MODIS NDVI coarse for corridor width design |
| Heat | Green corridor; blue-green corridor | Required | Built-up barriers | Built-up density; lack of continuous open land | GHSL built-up; Dynamic World (built) | GHSL; Google/WRI | 100 m; 10 m | Continuous corridors rare in urban core |
| Heat | Green corridor; blue-green corridor | Preferred | Riparian / water adjacency (co-benefit) | Drainage network; surface water; HAND | OSM waterways; JRC GSW; MERIT HAND | OSM; JRC; MERIT | vector; 30 m; 90 m | Water proximity adds cooling potential but ≠ access |
| Heat | Green corridor; blue-green corridor | Preferred | Ecological connectivity | Ecoregions; native vegetation context | Ecoregions; GBIF; Dynamic World | various; GBIF | vector / point | Species selection needs local expertise |
| Heat | Green corridor; blue-green corridor | Preferred | Public feasibility | Public land; parks; cadastre | OSM parks; cadastre | OSM; municipal | vector | Land tenure major gap |
| Heat | Green corridor; blue-green corridor | Exclusion | Protected / sensitive areas | Conservation designations | WDPA | UNEP-WCMC | vector | Not in catalog for POA |

#### Pocket parks / shaded public space

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Heat | Pocket park; shaded public space | Required | Heat priority | Heat hazard; heat risk | `poa_heat_hazard`; `poa_heat_risk` | OEF / geospatial-data | ~250 m | — |
| Heat | Pocket park; shaded public space | Required | Open land availability | Grass/bare land cover; existing parks | Dynamic World (grass/bare); OSM parks | Google/WRI; OSM | 10 m; vector | Land cover ≠ ownership or plantable area |
| Heat | Pocket park; shaded public space | Required | High exposure | Population; vulnerability | Exposure score; vulnerability score | OEF | ~250 m | Does not map where people gather outdoors |
| Heat | Pocket park; shaded public space | Preferred | Built-up constraint (inverse) | Low built-up fraction in block | GHSL built-up; Dynamic World (built) | GHSL; Google/WRI | 100 m; 10 m | Dense blocks may lack parcel-scale open space |
| Heat | Pocket park; shaded public space | Preferred | Soil / water | Soil texture; irrigation need | `soilgrids_clay`; drought indicators | ISRIC / catalog; various | ~250 m | Lawn-heavy designs may need unsustainable water |
| Heat | Pocket park; shaded public space | Exclusion | Dense built environment | Very high built-up; no open parcels | GHSL built-up | GHSL | 100 m | Large pocket parks rare in downtown cores |
| Heat | Pocket park; shaded public space | Uncertainty | Underground infrastructure | Utilities; basements | — | — | — | No open geospatial layer |

#### Schoolyard greening

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Heat | Schoolyard greening | Required | Heat priority | Heat hazard; heat risk | `poa_heat_hazard`; `poa_heat_risk` | OEF / geospatial-data | ~250 m | — |
| Heat | Schoolyard greening | Required | School locations | Schools; education facilities | OSM schools; municipal education GIS | OSM; municipal | vector | OSM incomplete for POA |
| Heat | Schoolyard greening | Preferred | Child / youth exposure | Vulnerability score; age share in V | Vulnerability score | OEF | ~250 m | Age-only vulnerability proxy |
| Heat | Schoolyard greening | Required | On-site open space | Schoolyard plantable area | High-resolution imagery; local parcel data | municipal; commercial imagery | sub-meter | **Major gap** — not in open catalog |
| Heat | Schoolyard greening | Preferred | Shade deficit near school | Low tree cover around school buffer | Hansen tree cover; Dynamic World (trees) | Hansen; Google/WRI | 30 m; 10 m | Buffer analysis not standardized in E2E yet |
| Heat | Schoolyard greening | Preferred | Maintenance feasibility | School ownership; municipal education authority | municipal cadastre; education registry | municipal | vector | Institutional feasibility not inferable from OSM alone |
| Heat | Schoolyard greening | Uncertainty | Play surface / safety constraints | Hard courts; underground rooms | — | field / school | — | Requires site visit |

#### Green roofs / green walls

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Heat | Green roof; green wall | Required | Heat priority | Heat hazard; heat risk | `poa_heat_hazard`; `poa_heat_risk` | OEF / geospatial-data | ~250 m | Rooftop cooling benefit depends on design |
| Heat | Green roof; green wall | Required | Built surfaces for retrofit | Built-up density; building footprints | GHSL built-up; Dynamic World (built); OSM buildings | GHSL; Google/WRI; OSM | 100 m; 10 m; vector | Built-up ≠ roof area or structural capacity |
| Heat | Green roof; green wall | Preferred | Dense areas with limited ground space | High built-up; low open land | GHSL built-up; Dynamic World (grass inverse) | GHSL; Google/WRI | 100 m; 10 m | Ground-space constraint is indirect proxy |
| Heat | Green roof; green wall | Preferred | Water demand context | Drought; local water supply | drought indicators; municipal water | various; municipal | — | Irrigation-dependent designs may be unsustainable |
| Heat | Green roof; green wall | Exclusion | Structural infeasibility | Building height/type; load capacity | local building registry; regulations | municipal | vector | **Major gap** — no open structural-capacity layer |
| Heat | Green roof; green wall | Uncertainty | Existing green roofs | Current rooftop vegetation | aerial imagery; municipal permits | commercial / municipal | — | Not in catalog |

#### Riparian / waterfront cooling corridors

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Heat | Riparian cooling corridor | Required | Heat priority | Heat hazard; heat risk | `poa_heat_hazard`; `poa_heat_risk` | OEF / geospatial-data | ~250 m | — |
| Heat | Riparian cooling corridor | Required | Proximity to water | Drainage network; surface water; HAND | OSM waterways; JRC GSW; MERIT HAND | OSM; JRC; MERIT | vector; 30 m; 90 m | Water proximity ≠ public thermal benefit |
| Heat | Riparian cooling corridor | Preferred | Existing riparian vegetation | Tree cover; NDVI; Dynamic World (trees) | Hansen tree cover; MODIS NDVI; Dynamic World | Hansen; NASA; Google/WRI | 30 m; 250 m; 10 m | Riparian species and canopy health not mapped |
| Heat | Riparian cooling corridor | Preferred | Public access | Parks; trails; public land | OSM parks; cadastre | OSM; municipal | vector | Access paths not fully mapped in OSM |
| Heat | Riparian cooling corridor | Preferred | Ecological fit | Riparian species; ecoregions | GBIF; ecoregions; Dynamic World (trees) | GBIF; various | point / vector | Local ecological expertise required |
| Heat | Riparian cooling corridor | Exclusion | Flood / erosion conflict | Flood hazard; steep unstable banks | `poa_flood_hazard`; `poa_slope` | OEF / catalog | ~250 m; 30 m | Multi-hazard trade-offs need local review |

---

## Landslides

> Detail: `docs/landslide_nbs_dataset_lens.md` · Methodology: `../../landslides/docs/landslide_hazard_score_methodology.md`, `../../landslides/docs/landslide_risk_score_methodology.md`

### Step 0 — Priority screening

Landslide hazard and risk scores identify **where** slope stabilization or revegetation screening may start. They do not indicate **which** NBS fits.

| Hazard | Role | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|
| Landslide | Priority area | Landslide susceptibility ensemble | Landslide hazard score (`poa_landslide_hazard`) | OEF / geospatial-data | ~90 m (→ bairro for risk) | Susceptibility index; not failure probability; slope < 15° → H = 0 |
| Landslide | Priority area | Hazard × exposure × vulnerability | Landslide risk score (`poa_landslide_risk`) | OEF / geospatial-data | ~90 m; E/V from bairro | Priority ≠ suitability |
| Landslide | Exposure context | Population density | Exposure score | IBGE → OEF grid | burned to 90 m | Constant within bairro; total area denominator |
| Landslide | Vulnerability context | Age share (social vulnerability) | Vulnerability score | IBGE → OEF grid | burned to 90 m | Age-only proxy; no informal housing on slopes |
| Landslide | Validation context | Observed landslide events / inventories | CEMADEN; municipal geohazard maps; event points | civil defense; municipal | vector / point | Often not open; hazard not validated against inventory |

### Step 1 — Landslide susceptibility context: predisposing + triggering factors

These rows diagnose **why** a priority zone may be landslide-prone — they apply to **all** slope-stabilization NBS, not one type in particular. Mirrors the OEF hazard ensemble inputs.

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Landslide | *(mechanism)* | Required | Steep slopes (activation gate) | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m → 90 m | Slope alone ≠ stability without geology |
| Landslide | *(mechanism)* | Required | Frequent extreme rainfall | R90p precipitation climatology | `chirps_r90p_climatology` | CHC / catalog | ~5 km → 90 m | Gridded; not antecedent rainfall or local gauges |
| Landslide | *(mechanism)* | Required | Low soil cohesion when wet | Clay content | `soilgrids_clay` | ISRIC / catalog | 250 m → 90 m | Global soil map ≠ site geotechnical survey |
| Landslide | *(mechanism)* | Required | Low vegetation protection | Persistently low NDVI | MODIS NDVI P10 DJF | NASA / OEF | 250 m → 90 m | NDVI ≠ root depth or species |
| Landslide | *(mechanism)* | Required | Drainage convergence / low HAND | Height above nearest drainage | MERIT HAND | MERIT / OEF | 90 m | HAND ≠ engineered drainage or pipes |
| Landslide | *(mechanism)* | Preferred | Disturbed or bare slopes | Built/bare on slope | Dynamic World (built, bare); forest cover change | Google/WRI; Hansen | 10 m; 30 m | 2023 vintage; land cover ≠ failure history |
| Landslide | *(mechanism)* | Preferred | Upslope contributing area | Flow accumulation | MERIT UPA | MERIT | 90 m | Urban drainage networks not captured |

### Steps 2–6 — By NBS type

Once the susceptibility context is understood (Step 1), use the tables below for each candidate slope-stabilization NBS type.

#### Slope revegetation

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Landslide | Slope revegetation | Required | Landslide priority | Landslide hazard; landslide risk | `poa_landslide_hazard`; `poa_landslide_risk` | OEF / geospatial-data | ~90 m / bairro | Screening only |
| Landslide | Slope revegetation | Required | Activatable slope range | Slope 15–35° (methodology gate) | `poa_slope` | geospatial-data / catalog | 30 m | Geotechnical review still required |
| Landslide | Slope revegetation | Required | Vegetation deficit | Low NDVI P10; bare/cleared land cover | MODIS NDVI P10; Dynamic World (bare/grass) | NASA; Google/WRI | 250 m; 10 m | Species and root architecture not mapped |
| Landslide | Slope revegetation | Preferred | Soil context | Clay/sand fraction | `soilgrids_clay` | ISRIC / catalog | ~250 m | Informs species/drainage strategy; not stability analysis |
| Landslide | Slope revegetation | Preferred | Rainfall trigger | Chronic extreme rainfall | CHIRPS R90p | CHC / OEF | ~5 km | Regional context only |
| Landslide | Slope revegetation | Preferred | Downslope exposure | Population; buildings/roads below | Exposure score; OSM buildings/roads | OEF; OSM | ~90 m; vector | Consequence screening |
| Landslide | Slope revegetation | Preferred | Public feasibility | Public land; manageable slope | OSM parks; cadastre | OSM; municipal | vector | Cadastre gap |
| Landslide | Slope revegetation | Exclusion | Built infrastructure on slope | Buildings; roads on steep slopes | Dynamic World (built); OSM roads | Google/WRI; OSM | 10 m; vector | May need engineered retaining, not planting alone |
| Landslide | Slope revegetation | Uncertainty | Geotechnical stability | Geology; site investigation | geology maps; field survey | municipal; field | — | **Required** before design on high-consequence slopes |

#### Bioengineering / erosion-control vegetation

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Landslide | Bioengineering; erosion control vegetation | Required | Landslide priority | Landslide hazard; landslide risk | `poa_landslide_hazard`; `poa_landslide_risk` | OEF / geospatial-data | ~90 m / bairro | — |
| Landslide | Bioengineering; erosion control vegetation | Required | Active erosion / bare soil | Bare land cover; low NDVI | Dynamic World (bare); MODIS NDVI P10 | Google/WRI; NASA | 10 m; 250 m | Erosion rate not directly measured |
| Landslide | Bioengineering; erosion control vegetation | Required | Drainage path on slope | Low HAND; UPA; channel proximity | MERIT HAND; MERIT UPA; OSM waterways | MERIT; OSM | 90 m; vector | Urban gullies may be missing from OSM |
| Landslide | Bioengineering; erosion control vegetation | Required | Slope severity | Slope angle | `poa_slope` | geospatial-data / catalog | 30 m | Very steep slopes may exceed vegetation-only capacity |
| Landslide | Bioengineering; erosion control vegetation | Preferred | Access for installation | Roads; public land | OSM roads; cadastre | OSM; municipal | vector | Maintenance access critical |
| Landslide | Bioengineering; erosion control vegetation | Preferred | Native / deep-rooted species | Ecoregions; GBIF | ecoregions; GBIF | various | vector / point | Local geotech + ecology required |
| Landslide | Bioengineering; erosion control vegetation | Exclusion | Critical infrastructure on slope | Buildings; utilities | OSM buildings; — | OSM | vector | Engineering survey required |

#### Riparian stabilization / gully-head protection

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Landslide | Riparian stabilization; gully-head protection | Required | Landslide priority | Landslide hazard; landslide risk | `poa_landslide_hazard`; `poa_landslide_risk` | OEF / geospatial-data | ~90 m / bairro | — |
| Landslide | Riparian stabilization; gully-head protection | Required | Stream / gully proximity | Drainage network; low HAND | OSM waterways; MERIT HAND | OSM; MERIT | vector; 90 m | OSM waterways incomplete |
| Landslide | Riparian stabilization; gully-head protection | Preferred | Upslope contributing area | Flow accumulation | MERIT UPA | MERIT | 90 m | Large upslope area may need upslope reforestation |
| Landslide | Riparian stabilization; gully-head protection | Preferred | Degraded riparian cover | Low tree cover near drainage | Hansen tree cover; Dynamic World (trees) | Hansen; Google/WRI | 30 m; 10 m | Species composition not mapped |
| Landslide | Riparian stabilization; gully-head protection | Preferred | Public access / manageability | Parks; public land | OSM parks; cadastre | OSM; municipal | vector | Riparian tenure often unclear |
| Landslide | Riparian stabilization; gully-head protection | Preferred | Multi-hazard context | Flood hazard; surface water | `poa_flood_hazard`; JRC GSW | OEF; JRC | ~250 m; 30 m | Flood + landslide trade-offs need review |
| Landslide | Riparian stabilization; gully-head protection | Exclusion | Protected areas | Conservation designations | WDPA | UNEP-WCMC | vector | Not in catalog for POA |

#### Forest restoration / upslope reforestation

| Hazard | NBS type | Condition | Site condition | Geospatial proxy | Candidate dataset | Source | Coverage (POA) | Gap / caveat |
|---|---|---|---|---|---|---|---|---|
| Landslide | Forest restoration; upslope reforestation | Required | Landslide priority | Landslide hazard; landslide risk | `poa_landslide_hazard`; `poa_landslide_risk` | OEF / geospatial-data | ~90 m / bairro | — |
| Landslide | Forest restoration; upslope reforestation | Required | Forest loss / degradation | Deforestation; bare/shrub on slope | Hansen forest cover change; Dynamic World | Hansen; Google/WRI | 30 m; 10 m | Degradation history incomplete |
| Landslide | Forest restoration; upslope reforestation | Required | Large upslope catchment | Upslope contributing area | MERIT UPA | MERIT | 90 m | Catchment-scale action needs land tenure clarity |
| Landslide | Forest restoration; upslope reforestation | Preferred | Vegetation protection deficit | Low NDVI P10 | MODIS NDVI P10 | NASA / OEF | 250 m | NDVI ≠ forest structure |
| Landslide | Forest restoration; upslope reforestation | Preferred | Ecological fit | Riparian/native species; ecoregions | GBIF; ecoregions | GBIF; various | point / vector | Deep-rooted natives preferred |
| Landslide | Forest restoration; upslope reforestation | Preferred | Land availability | Public/protected forest land | cadastre; WDPA; municipal forest | municipal; UNEP-WCMC | vector | Upslope land often private or protected |
| Landslide | Forest restoration; upslope reforestation | Exclusion | Fire / urban-wildland conflict | Built adjacency; fire risk context | Dynamic World (built); local fire maps | Google/WRI; municipal | 10 m | Multi-hazard screening needed |

---

## Open data vs gaps (Step 6 summary)

Gaps are listed **by hazard** where they differ; shared gaps appear once under **All hazards**.

### All hazards

| Gap | Affects | Open alternative? | Notes |
|---|---|---|---|
| Land ownership / cadastre | Most ground-based NBS | Partial (OSM parks/roads as proxy) | Legal tenure not inferable from land cover |
| Native species / ecoregions | Vegetation-based NBS | GBIF, ecoregions (incomplete for POA) | Local ecological expertise required |
| Underground utilities | Linear / planting NBS | None open at city scale | Engineering survey required |
| Exposure / vulnerability modifiers | All risk-based prioritization | Shared E/V only | Age-only V; no hazard-specific social layers in catalog |

### Flood

| Gap | Affects | Open alternative? | Notes |
|---|---|---|---|
| Urban drainage network | All urban flood NBS | No good open global layer | Municipal data required |
| Groundwater depth | Infiltration NBS | Global layers too coarse for urban POA | Field or local hydrogeology |
| Local IDF / rain gauges | Sizing bioswales, basins, rain gardens | CHIRPS as screening proxy only | ~5 km gridded |
| Field infiltration tests | All infiltration-based NBS | `soilgrids_clay` as screening proxy | Required before design |
| OEF terrain / flood inputs (local only) | Multiple NBS | `poa_slope`, `poa_relative_elevation`, `poa_depression_*`, `gfplain250m`, `jrc_gloflor_v2`, `wri_aqueduct_flood`, `global_flood_database` in catalog | Local exports exist; S3 tiles pending |

### Heat

| Gap | Affects | Open alternative? | Notes |
|---|---|---|---|
| LST ≠ thermal comfort | All cooling NBS prioritization | None at city scale | Hazard uses surface temperature, not air temp, shade, humidity, wind |
| Pedestrian exposure layers | Street trees, pocket parks, schoolyard greening | OSM streets/schools as weak proxy | No standard map of where people experience outdoor heat |
| Roof suitability / structural capacity | Green roofs, green walls | Built-up layers only | Cannot distinguish roof type, load capacity, existing green roofs |
| Water availability / irrigation | Trees, green roofs, lawns | `soilgrids_clay` + drought indices as weak proxy | Major local constraint in dry periods |
| Microclimate feedback | All vegetation cooling NBS | — | Canopy design and surrounding materials need local assessment |
| Coarse ERA5-Land indices | Regional heatwave context | Catalog indices at ~11 km; `era5_land_heatwave_freq_djf` (local geospatial-data) | Excluded from operational heat hazard ensemble |

### Landslides

| Gap | Affects | Open alternative? | Notes |
|---|---|---|---|
| Geotechnical / geology | All slope NBS | Global geology maps too coarse | Site investigations required |
| Landslide event inventory | Validation and calibration | Municipal geohazard maps | Often not open |
| CHIRPS R90p resolution | Trigger context | Nearest resample to 90 m | ~5 km native; honest limit on spatial detail |
| Root architecture / species suitability | Revegetation, bioengineering | NDVI, Dynamic World as proxies | Cannot infer root depth or shear strength contribution |
| Multi-hazard conflicts | Riparian NBS on floodplains | Separate hazard scores | Flood + landslide trade-offs need integrated review |

---

## Related documents

- [`nbs_mechanism_dataset_matrix.md`](nbs_mechanism_dataset_matrix.md) — mechanism → NBS → layers priority matrix (POA product review)
- `docs/nbs_recommendation_rules_expert_review.md` — hazard mechanism → NBS scoring rules (expert review, ON-5993)
- `docs/nbs_dataset_identification_methodology.md` — shared workflow (Steps 1–8)
- `docs/nbs_site_query_e2e.md` — E2E exercise index (links to per-hazard notebooks)
- `scripts/nbs_site_query_flood_e2e.ipynb` — flood E2E notebook (bairro + 250 m grid)
- `scripts/nbs_site_query_heat_e2e.ipynb` — heat E2E notebook
- `scripts/nbs_site_query_landslide_e2e.ipynb` — landslide E2E notebook
- `docs/flood_nbs_dataset_lens.md` — flood-specific exploration and NBS requirements
- `docs/heat_nbs_dataset_lens.md` — heat-specific exploration and NBS requirements
- `docs/landslide_nbs_dataset_lens.md` — landslide-specific exploration and NBS requirements
- `../../landslides/docs/landslide_hazard_score_methodology.md` — operational landslide hazard score
- `../../landslides/docs/landslide_risk_score_methodology.md` — operational landslide risk score
- `../../geospatial-data/catalog/datasets.yaml` — POA catalog assets (72 datasets incl. local geospatial-data inputs)
