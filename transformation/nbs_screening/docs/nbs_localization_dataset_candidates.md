# Candidate datasets for NBS localization — tangible exploration list

**Companion to:** [`nbs_mechanism_dataset_matrix.md`](nbs_mechanism_dataset_matrix.md)

This doc answers: *“Ok, but **which** datasets can we actually go look up?”*

**Legend**

| Tag | Meaning |
|-----|---------|
| **In catalog** | Already in `geospatial-data/catalog/datasets.yaml` and/or OEF COGs |
| **Explore** | Open or requestable; good next step to evaluate for POA |
| **POA municipal** | Likely needs SMAM, DMAE, SEPLAG, or partner request |
| **Expert / field** | Not a map layer; workshop, survey, or geotech report |

---

## 1. Cadastre, tenure, implementable land

| Dataset | Publisher / source | What it unlocks | POA access | Tag |
|---------|-------------------|-----------------|------------|-----|
| **OSM parks, roads, schools, waterways** | OpenStreetMap (Overpass API) | Public ROW proxy, schools for greening, linear NBS space | Open | Explore (proxy only) |
| **`poa_informal_settlements`** | IBGE 2024 → OEF S3 | Informal housing context; tenure caution | [catalog GeoJSON](https://geo-test-api.s3.us-east-1.amazonaws.com/br_ibge/release/2024/porto_alegre/poa_informal_settlements.geojson) | In catalog |
| **`br_ibge` bairro indicators** | IBGE SIDRA / malhas | Socioeconomic context per bairro | In catalog (`br_ibge`) | In catalog |
| **Malha de setores censitários 2022** | IBGE | Finer population/urban form than bairro | [IBGE malhas](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html) | Explore |
| **Cadastro imobiliário / IPTU parcels** | Prefeitura POA | Legal parcel, public vs private, lot size | GeoPOA / SEPLAG (often restricted) | POA municipal |
| **Zoneamento urbano (PDOT)** | Prefeitura POA | Where parks, infiltration, conservation allowed | Plano Diretor layers | POA municipal |
| **CAR / SICAR** (rural properties) | MMA / INCRA | Rural upslope tenure (landslide reforestation) | [SICAR](https://www.car.gov.br/) — mostly rural fringe | Explore (partial) |

**Mechanisms most helped:** all; especially `low_lying`, `high_social_exposure`, schoolyard/pocket park NBS.

---

## 2. Native species & ecological fit

| Dataset | Publisher / source | What it unlocks | POA access | Tag |
|---------|-------------------|-----------------|------------|-----|
| **GBIF occurrence search** | GBIF | Native / observed species by taxon & bbox (RS, POA) | [GBIF.org](https://www.gbif.org/) API | Explore |
| **Flora do Brasil / Jabot** | Jardim Botânico / reflora | Checklist & occurrence for Brazilian native plants | [Flora do Brasil](https://floradobrasil.jbrj.gov.br/) | Explore |
| **Lista Espécies Ameacadas (MMA)** | MMA | Legal constraints on species use | MMA lists | Explore |
| **RESOLVE / WWF ecoregions** | RESOLVE | Biogeographic context for restoration | Global vectors | Explore |
| **MapBiomas Collection (land cover classes)** | MapBiomas | Forest, pasture, wetland class time series | [MapBiomas](https://mapbiomas.org/) | Explore |
| **`dynamic_world` / `hansen_treecover2000`** | Google / Hansen | Tree cover proxy (not species) | In catalog | In catalog |
| **Municipal / SMAM native species lists** | SMAM, universities | Planting palettes for POA street trees & slopes | SMAM arborização | POA municipal + expert |
| **Ramsar sites (Brazil)** | Ramsar / MMA | Legal wetland sites | [Ramsar directory](https://rsis.ramsar.org/) | Explore |
| **WDPA / UC (SNUC)** | UNEP-WCMC / ICMBio | Protected areas — exclusion or co-design | [Protected Planet](https://www.protectedplanet.net/) | Explore |

**Mechanisms most helped:** `riverine`, `vegetation_deficit`, `shade_deficit`, riparian & slope NBS.

---

## 3. Soil, infiltration, geology (flood + landslide)

| Dataset | Publisher / source | What it unlocks | POA access | Tag |
|---------|-------------------|-----------------|------------|-----|
| **`soilgrids_clay`** (`poa_clay_pct_250m`) | ISRIC SoilGrids v2 | Clay % screening — cohesion, infiltration caution | In catalog | In catalog |
| **Embrapa GeoInfo — Mapa de solos do Brasil (SiBCS)** | Embrapa Solos / CNPS | Soil **class** (Latossolo, Argissolo, Neossolo…), better Brazil-native taxonomy than clay % alone | [geoinfo.dados.embrapa.br](https://geoinfo.dados.embrapa.br/) — WFS/GeoJSON (`brasil_solos_5m_20201104`) | **Explore (priority)** |
| **Embrapa — Mapa de erodibilidade** | Embrapa Solos (2020) | Erosion susceptibility — bioengineering, slope NBS, drainage paths | GeoInfo catalog / AdaptaBrasil cites this layer | Explore |
| **SmartSolos Expert API** | Embrapa CNPTIA | Classify soil **profiles** to SiBCS level 4 from lab/point data | [agroapi.cnptia.embrapa.br](https://www.agroapi.cnptia.embrapa.br/) | Expert / field |
| **SoilGrids sand / texture classes** | ISRIC | Complement clay for infiltration NBS | [SoilGrids](https://soilgrids.org/) | Explore |
| **Field infiltration / geotech reports** | Project / municipal | Rain garden, bioswale sizing | Per site | Expert / field |
| **Geological maps (RS / Brazil)** | CPRM / SGB | Lithology, unstable formations | [GeoSGB / CPRM](https://www.cprm.gov.br/) | Explore (coarse) |
| **CEMADEN susceptibility / inventories** | CEMADEN | Landslide validation, event history | [CEMADEN](https://www.gov.br/cemaden/) — mixed open | Explore / request |
| **Global groundwater depth** | Various global products | Infiltration exclusion | Too coarse for urban POA | Major gap |

### Embrapa GeoInfo — why it matters for POA

We initially listed **SoilGrids only** (global, ~250 m clay %). **Embrapa was not in the first pass** — good catch.

| | SoilGrids (current catalog) | Embrapa GeoInfo |
|--|----------------------------|-----------------|
| **What you get** | Continuous clay % (0–30 cm) | SiBCS soil **classes** + thematic maps (erosion, etc.) |
| **Brazil fit** | Global model | National reference (Embrapa Solos) |
| **Resolution** | ~250 m resampled | National map **1:5,000,000** (~5 km) — not parcel-scale; check GeoInfo for state/municipal finer products |
| **NBS use** | `low_cohesion_wet`, infiltration caution | Interpret cohesion, erosion risk, restoration suitability by soil order |
| **License** | Open (ISRIC) | Often **CC BY-NC** on GeoInfo layers — confirm before platform tiles |
| **Integration** | In `nbs_rules.py` today | **Not in catalog yet** — top candidate to sample for POA bbox |

**Suggested next step:** CSW search on `geoinfo.dados.embrapa.br/catalogue/csw` for `solos`, `erodibilidade`, `Rio Grande do Sul`, `Porto Alegre`; clip national SiBCS map to POA; compare class distribution vs `soilgrids_clay` in mixed/landslide cells.

**Mechanisms most helped:** `pluvial`, `drainage_constrained`, `low_cohesion_wet`, `disturbed_bare_slope`, `vegetation_deficit`.

---

## 4. Urban drainage & hydrology (flood)

| Dataset | Publisher / source | What it unlocks | POA access | Tag |
|---------|-------------------|-----------------|------------|-----|
| **`merit_hydro_hnd` (HAND)** | MERIT Hydro | Height above drainage — low-lying, saturation | In catalog | In catalog |
| **`merit_hydro_upa`** | MERIT Hydro | Upslope contributing area | In catalog | In catalog |
| **OSM waterways + surface water** | OSM | Rivers, streams (misses storm drains) | Overpass | Explore |
| **`jrc_global_surface_water_*`** | JRC GSW | Historical wetness, seasonality | In catalog | In catalog |
| **`poa_depression_*`, `poa_relative_elevation`** | OEF / OEF | Depressions, low-lying POA terrain | In catalog (COGs) | In catalog |
| **`gfplain250m`, `wri_aqueduct_flood`** | WRI / GFPLAIN | Floodplain context | Referenced in recommended-datasets | Explore / catalog pending |
| **Rede de drenagem pluvial / galerias** | DMAE / SMAM POA | Drainage-constrained mechanism | Municipal — **major gap** | POA municipal |
| **INMET / ALERT-RS rain gauges** | INMET | Local rainfall extremes, IDF calibration | [INMET](https://portal.inmet.gov.br/) | Explore |
| **CHIRPS R90p / Rx1day** | CHC | Extreme rain screening (~5 km) | In catalog | In catalog |

**Mechanisms most helped:** `riverine`, `pluvial`, `low_lying`, `drainage_constrained`, `drainage_saturation`.

---

## 5. Heat — where people feel heat & where to plant

| Dataset | Publisher / source | What it unlocks | POA access | Tag |
|---------|-------------------|-----------------|------------|-----|
| **`poa_heat_hazard`, LST composites** | OEF / Landsat / MODIS | Surface heat hotspot screening | In catalog | In catalog |
| **`ghsl_built_up`, `dynamic_world`** | GHSL / Google | UHI / impervious proxy | In catalog | In catalog |
| **`hansen_treecover2000`, `modis_ndvi`** | Hansen / NASA | Shade deficit proxy | In catalog | In catalog |
| **OSM schools + parks** | OSM | Schoolyard greening, pocket park targets | Overpass | Explore |
| **Street / sidewalk width (plantable ROW)** | Municipal CAD, LiDAR, manual | Street tree feasibility | SMAM / MOVI | POA municipal |
| **Pedestrian exposure / activity** | Mobile, POI, surveys | Where cooling matters most | No standard open layer | Major gap |
| **Building registry + roof type** | Prefeitura | Green roof structural feasibility | IPTU / SMUSA | POA municipal |
| **INMET air temperature stations** | INMET | Air temp vs LST validation | Open point data | Explore |

**Mechanisms most helped:** `shade_deficit`, `uhi_built_up`, `high_social_exposure`, `high_daytime_lst`.

---

## 6. Already wired — use as baseline (don’t re-explore first)

These already feed mechanism + NBS scoring today:

| Catalog `dataset_id` | Used for |
|---------------------|----------|
| `poa_flood_hazard`, `poa_flood_risk` | Flood priority |
| `poa_heat_hazard`, `poa_heat_risk` | Heat priority |
| `poa_landslide_hazard`, `poa_landslide_risk` | Landslide priority |
| `poa_*_mechanism_type` | Dominant mechanism map |
| `merit_hydro_hnd`, `merit_hydro_upa` | Drainage / low-lying / upslope |
| `jrc_global_surface_water_*` | Wetness history |
| `ghsl_built_up`, `dynamic_world` | Built-up / land cover |
| `soilgrids_clay`, `poa_slope` | Clay, slope |
| `chirps_r90p_climatology` | Rainfall trigger |
| `modis_ndvi`, `hansen_treecover2000` | Vegetation deficit |
| `poa_exposure`, `poa_vulnerability` | Social exposure |

Full list: `geospatial-data/catalog/datasets.yaml`.

---

## 7. Suggested exploration order (POA, 4 weeks)

| Week | Focus | Concrete actions |
|------|-------|------------------|
| 1 | **Open global + Brazil soils** | Pull GBIF native tree/shrub occurrences for POA bbox; **sample Embrapa SiBCS + erodibilidade for POA**; compare vs `soilgrids_clay`; download WDPA/Ramsar for RS |
| 2 | **OSM enrichment** | Overpass extract: schools, parks, wetlands, waterways → GeoJSON; compare to mechanism_type hotspots |
| 3 | **Brazil national** | IBGE setores censitários; INMET station IDF screen; CEMADEN landslide layers for validation |
| 4 | **POA municipal outreach** | Request list from SMAM/DMAE: drainage network, arborization species list, public parcel inventory |

---

## 8. Example — reading one matrix row with this list

**Matrix row:** `riverine` → riparian buffer → P2 → “localize with floodplain zoning + wetland inventory”

| Need | Explore first | If insufficient |
|------|---------------|-----------------|
| River proximity | OSM waterways + `merit_hydro_hnd` (catalog) | — |
| Wetness signal | `jrc_global_surface_water_occurrence` (catalog) | — |
| Wetland **opportunity** | Ramsar + OSM wetlands + MapBiomas wetland class | SMAM wetland/restoration projects |
| Legal floodplain | — | PDOT / municipal floodplain zoning |
| Species for planting | GBIF + Flora do Brasil | SMAM native species palette |

---

## Related documents

- [`nbs_mechanism_dataset_matrix.md`](nbs_mechanism_dataset_matrix.md) — priority matrix
- [`recommended-datasets.md`](recommended-datasets.md) — full Step 0–6 tables per NBS type
- [`flood_nbs_dataset_lens.md`](flood_nbs_dataset_lens.md) · [`heat_nbs_dataset_lens.md`](heat_nbs_dataset_lens.md) · [`landslide_nbs_dataset_lens.md`](landslide_nbs_dataset_lens.md)
