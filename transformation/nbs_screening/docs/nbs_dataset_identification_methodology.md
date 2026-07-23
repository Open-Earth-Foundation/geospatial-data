# Methodology for Identifying Relevant Datasets for Nature-based Solution Design

## Purpose

This document provides a general methodology for identifying geospatial datasets that can support early-stage Nature-based Solution (NBS) design. It is intended for screening and ideation, not for final engineering design or site-level implementation.

The core idea is simple: **do not start by collecting datasets. Start by identifying the design decisions that need to be made.** Datasets are only useful when they help answer a specific question about where an NBS could work, where it should not be proposed, or what additional information is needed before implementation.

This methodology can be applied across hazards such as flooding, extreme heat, landslides, drought, coastal flooding, erosion, or multi-hazard urban risk.

## Scope

This methodology supports:

- identifying candidate datasets for NBS suitability screening;
- translating hazard information into NBS design questions;
- defining geospatial proxies for physical, ecological, and social site conditions;
- documenting which decision each dataset supports;
- identifying gaps between screening-scale analysis and design-scale implementation.

It does **not** produce final NBS recommendations by itself. Final NBS design requires local validation, field information, engineering review where relevant, and engagement with local stakeholders.

## Conceptual framing

Nature-based Solutions should not be treated as generic green interventions. A credible NBS should respond to a societal challenge while being suitable for the local ecological, physical, social, and governance context.

Useful reference frameworks include:

- [IUCN Global Standard for Nature-based Solutions](https://portals.iucn.org/library/node/49070)
- [Catalogue of Nature-based Solutions for Urban Resilience](https://www.gfdrr.org/en/publication/catalogue-nature-based-solutions-urban-resilience)

For dataset identification, the most useful framing is:

```text
Hazard → Possible NBS → Site conditions → Geospatial indicators → Candidate datasets → Decision supported → Gaps
```

The objective is not to find datasets that directly say “put this NBS here”. In most cases, such datasets do not exist. Instead, the objective is to find datasets that help assess whether the conditions required by a given NBS are present or absent.

## Recommended workflow

### Step 1 — Define the hazard and planning question

Start with a clear hazard-specific question.

Examples:

- For flood-exposed areas, what data are needed to identify where water-managing NBS may be feasible?
- For heat-exposed areas, what data are needed to identify where cooling NBS may be most useful and feasible?
- For landslide-exposed areas, what data are needed to identify where vegetation-based stabilization or restoration may be appropriate?

At this stage, avoid jumping directly to datasets. First define the design problem.

### Step 2 — Define a short NBS typology

Create a short list of NBS types relevant to the hazard. The list should be specific enough to guide data needs, but not so detailed that it becomes a final design catalogue.

Example typology:

| Hazard | Example NBS types |
|---|---|
| Flooding | bioswales, rain gardens, permeable surfaces, retention basins, wetland restoration, floodplain restoration, riparian buffers |
| Heat | urban trees, green corridors, pocket parks, green roofs, riparian cooling corridors, schoolyard greening |
| Landslides | slope revegetation, bioengineering, erosion control vegetation, riparian stabilization, forest restoration |
| Multi-hazard | blue-green corridors, urban forests, watershed restoration, restored wetlands |

### Step 3 — Translate each NBS into site conditions

For each NBS, define the conditions that make it potentially suitable, unsuitable, or uncertain.

Use four categories:

1. **Required conditions**: conditions that must be present for the NBS to make sense.
2. **Preferred conditions**: conditions that increase suitability or expected benefit.
3. **Exclusion conditions**: conditions that should prevent or strongly limit recommendation.
4. **Uncertainty conditions**: conditions that cannot be assessed reliably with available global datasets and require local validation.

Example:

| NBS | Required conditions | Preferred conditions | Exclusion / caution conditions |
|---|---|---|---|
| Rain garden | runoff source, space for infiltration, low/moderate slope | infiltrable soil, public/open land, near roads or buildings | high groundwater, very steep slope, underground infrastructure conflicts |
| Urban tree planting | heat exposure, lack of shade/vegetation, available planting space | public right-of-way, high pedestrian exposure, suitable water availability | insufficient rooting space, water scarcity, conflict with utilities |
| Slope revegetation | erosion/landslide-prone slope, degraded vegetation | moderate slope, suitable soil depth, native species availability | active slope failure, extreme slope, need for grey infrastructure |

### Step 4 — Identify geospatial proxies

Most design conditions are not directly observable in global datasets. Translate each condition into one or more geospatial proxies.

Examples:

| Design condition | Possible geospatial proxy |
|---|---|
| Runoff generation | impervious surface, built-up density, roads, rainfall intensity |
| Water accumulation | flow accumulation, drainage network, depressions, low elevation |
| Infiltration potential | soil texture, clay/sand fraction, bulk density, hydrologic soil group |
| Storage opportunity | open land, public land, parks, vacant land, floodplain extent |
| Heat exposure | land surface temperature, air temperature, built-up density, low NDVI |
| Ecological fit | ecoregion, species occurrence, native vegetation maps, protected areas |
| Implementation feasibility | land tenure, zoning, public land, road rights-of-way, maintenance responsibility |

This step is where the methodology becomes spatially explicit.

### Step 5 — Search candidate datasets

Once the proxies are defined, search for datasets that can represent them. Candidate datasets should be documented with source, coverage, resolution, temporal coverage, accessibility, and limitations.

Useful dataset categories include:

| Dataset category | Example sources | Typical use |
|---|---|---|
| Elevation / terrain | Copernicus DEM, SRTM, FABDEM, local LiDAR | slope, low-lying terrain, depressions, hydrological conditioning |
| Hydrology | HydroSHEDS, HydroRIVERS, HydroBASINS, MERIT Hydro, local drainage networks | flow accumulation, river proximity, catchments, drainage corridors |
| Land cover | ESA WorldCover, Dynamic World, Copernicus Land Cover, local land use | vegetation, built-up areas, open land, water, bare ground |
| Built environment | GHSL, OpenStreetMap, building footprints, roads | imperviousness proxy, exposure, retrofit opportunities |
| Soils | SoilGrids, national soil maps, hydrologic soil groups | infiltration potential, erosion susceptibility, soil suitability |
| Climate | CHIRPS, ERA5-Land, IMERG, WorldClim, TerraClimate, local gauges | rainfall intensity, climate zone, water balance, species suitability |
| Biodiversity / species | GBIF, national biodiversity portals, IUCN Red List, ecoregions, local ecological inventories | native species screening, ecological suitability, restoration context |
| Governance / feasibility | cadastre, zoning, public land, protected areas, infrastructure networks | implementation feasibility and constraints |
| Social exposure | population grids, census data, vulnerable groups, critical facilities | prioritization and equity considerations |

### Step 6 — Document the decision each dataset unlocks

This is the most important part of the dataset inventory. Each dataset should be linked to a practical NBS design decision.

Avoid generic descriptions such as:

> “SoilGrids provides soil data.”

Prefer decision-oriented language:

> “SoilGrids can be used as a screening proxy for infiltration potential, helping distinguish areas where infiltration-based NBS such as rain gardens or bioswales may be plausible from areas where field testing is required before recommendation.”

Recommended documentation fields:

| Field | Description |
|---|---|
| Dataset | Dataset name |
| Source | Provider or institution |
| Coverage | Global, regional, national, or local |
| Resolution / scale | Spatial resolution or feature scale |
| Temporal coverage | Year, period, or update frequency |
| Proxy represented | The site condition approximated by the dataset |
| NBS decision unlocked | The decision the dataset helps support |
| Relevant NBS | NBS types informed by this dataset |
| Caveats / gaps | What the dataset cannot answer |
| Design-stage requirement | Local data or field validation needed before implementation |

### Step 7 — Classify data gaps

Not all missing data have the same importance. Classify gaps according to how they affect the workflow.

| Gap type | Meaning | Example |
|---|---|---|
| Screening gap | Weakens early spatial prioritization | no reliable imperviousness layer |
| Design gap | Prevents site-level design | no local drainage, no infiltration tests |
| Governance gap | Prevents implementation feasibility assessment | no land ownership or public land layer |
| Ecological gap | Weakens species or restoration recommendations | no validated native species list |
| Risk-control gap | Could lead to unsafe recommendations | no geotechnical data in landslide-prone areas |

### Step 8 — Separate screening from design

A recurring risk is overinterpreting global datasets. The output of this workflow should be framed as **screening-level suitability**, not final design.

Recommended distinction:

| Analysis level | Purpose | Typical data | What it can say | What it cannot say |
|---|---|---|---|---|
| Screening | Identify candidate zones and data needs | global/regional geospatial datasets | where an NBS may be plausible | exact site design or engineering dimensions |
| Pre-feasibility | Compare options and constraints | local land use, drainage, parcels, field checks | which NBS options deserve further assessment | final construction design |
| Design | Engineer and implement site-specific intervention | surveys, hydrology, soils, utilities, stakeholder input | what to build, where, and how | broader prioritization without strategic context |

## General dataset inventory template

Use this template when adding datasets to a shared documentation file.

```markdown
| Decision area | Dataset | Source | Coverage / resolution | Proxy represented | NBS decision unlocked | Relevant NBS | Gaps / caveats |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |
```

## Recommended decision language

Use action-oriented language that connects datasets to decisions.

Examples:

| Dataset type | Decision-oriented interpretation |
|---|---|
| DEM / slope | Identifies terrain constraints and potential drainage/storage areas |
| Flow accumulation | Identifies where water naturally concentrates |
| Land cover | Identifies open, green, built-up, water, or degraded areas |
| Built-up / imperviousness | Identifies likely runoff-generating areas and retrofit opportunities |
| Soil texture | Screens infiltration potential and soil constraints |
| Groundwater depth | Identifies possible constraints for infiltration-based NBS |
| Species occurrence | Supports native species screening, but requires expert validation |
| Public land | Identifies where implementation may be more feasible |

## Quality control questions

Before adding a dataset, ask:

1. What NBS design question does this dataset help answer?
2. What site condition does it represent?
3. Is it a direct measurement or a proxy?
4. Is the spatial resolution appropriate for screening?
5. Is the dataset global, regional, or local?
6. Is it current enough for the decision?
7. What are its known limitations?
8. What local data would be needed before implementation?
9. Could this dataset lead to misleading recommendations if used alone?
10. Does the dataset help with feasibility, suitability, prioritization, or only context?

## Recommended output

The recommended output is a documented dataset inventory, not a final suitability map.

Minimum output:

- list of candidate datasets;
- source and coverage;
- spatial/temporal resolution;
- NBS design decision supported;
- relevant NBS types;
- caveats and gaps.

Optional next-stage output:

- NBS suitability criteria table;
- exclusion masks;
- preliminary suitability scoring logic;
- data confidence ranking;
- validation plan.

## Key principle

A dataset is relevant only if it helps answer a specific design question.

The strongest workflow is:

```text
Start with NBS decisions, not datasets.
Then identify spatial conditions.
Then identify proxies.
Then identify datasets.
Then document gaps.
```

