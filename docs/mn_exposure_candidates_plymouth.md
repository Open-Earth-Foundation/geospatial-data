# Minnesota exposure candidates — Plymouth

Reference indicators: [`climate_risk_indicators_by_sector.json`](climate_risk_indicators_by_sector.json)  
City focus: **Plymouth, MN** (also reusable for Edina, Richfield, Rochester, Apple Valley).

This note maps **Exposure** indicators → candidate US/MN datasets. It does **not** invent new indicators; it operationalizes the JSON for local data search.

## Priority

| Priority | Indicator (JSON `Index`) | Why first |
|----------|--------------------------|-----------|
| **P0** | Population density | Shared across most sectors/risks; same role as POA `poa_exposure`. **Preferred source for MN: ACS block group** (also unlocks Vulnerability fields). |
| **P1** | Households in hazard-prone areas | Flood (+ landslide) physical exposure; needs hazard ∩ buildings/parcels |
| **P2** | Health and basic services access; infrastructure / land-cover exposures | Sector-specific backlog |

---

## Shared datasets (apply to multiple risks / sectors)

These candidates are **cross-cutting**. Prefer them for a first shared `plymouth_exposure` layer so flood, heat, and landslide risk can reuse one E surface.

| Candidate dataset | Geometry | JSON indicators covered | Sectors / risks where it applies | Notes |
|-------------------|----------|-------------------------|----------------------------------|-------|
| **US Census ACS 5-year (block group)** | Polygon → rasterize | Population density (+ V: age, income, poverty, insurance, …) | **Floods**, **Landslides**, **Heatwaves**, **Droughts**, Food Security floods — same multi-risk E set | **Preferred for MN.** One extract serves E and V. |
| **GHSL population** (GHS-POP) | Raster ~100 m | Population density | Same multi-risk E set | Alternate global raster; no rich V attributes. Catalog: `ghsl_population` (POA). |
| **Microsoft / OSM building footprints** ∩ hazard mask | Vector → raster | Households in hazard-prone areas | **Floods** + **Landslides** | Pair with flood hazard / FEMA NFHL / landslide susceptibility. |
| **FEMA NFHL** (SFHA / flood zones) | Vector | Supports Households in hazard-prone areas (flood) | **Floods** | Hazard zoning mask, not population. |
| **CDC PLACES / HRSA** (+ ACS health fields) | Tract / BG / points | Health and basic services access | **Heatwaves**, **Floods**, **Droughts** | ACS covers many proxies at BG; facilities need HRSA points. |
| **HIFLD / EIA power plants** | Points | Power generation facilities | **Heatwaves** + **Droughts** (Energy) | Sparse in suburban Plymouth. |
| **NLCD / Dynamic World** | Raster | Natural vegetation cover | Biodiversity heat; landslide V context | Not ACS. |
| **PAD-US** | Vector | Protected areas | Biodiversity heat | Not ACS. |
| **OSM / USDOT** roads & rail | Lines → density | Road / railroad density | Infrastructures heat (+ landslide/erosion infra) | Not ACS. |

---

## ACS block groups — not the same as Porto Alegre bairros

| | Porto Alegre | Plymouth / US |
|--|--------------|---------------|
| Unit | **Bairros** (official neighbourhoods) | **Census block groups** (statistical units) |
| Role | Admin + social identity; IBGE joined to polygons | Census frames for ACS estimates |
| Stability | Relatively stable municipal units | Redrawn each decade with the Decennial Census |
| Size | ~94 inhabited bairros in POA | Typically ~600–3,000 people per block group |

ACS does **not** publish rich socioeconomic tables at **census block** (finer than block group). Blocks only get limited Decennial counts. For E+V together, **block group is the most granular practical unit**.

### Polygons inside the city (coarse → fine)

| Polygon | Granularity | Good for ACS E/V? | Use |
|---------|-------------|-------------------|-----|
| City / Census **Place** (Plymouth) | Whole city | Totals only | AOI / reporting |
| ZIP / ZCTA | Coarse, crosses edges | Weak | Avoid for CCRA grids |
| Census **tract** | Neighbourhood-ish | Yes | Fallback if BG margins too wide |
| Census **block group** | Finest for ACS detailed tables | **Yes — preferred** | Shared E + V attributes |
| Census **block** | Finest geometry | No (ACS socioeconomic) | Optional dasymetric refine with Decennial pop only |
| City neighbourhoods / wards (if any) | Local narrative | Only via areal interpolation from ACS | Labels / outreach, not primary stats |
| Parcels / buildings | Ultra-local | No ACS | P1 physical exposure ∩ hazard |

### What ACS has for our JSON (same pull = E + V)

Use **ACS 5-year Detailed Tables** at block group (e.g. latest `acs/acs5`). ACS 1-year does **not** go to block group.

| JSON indicator | Component | Example ACS vars / tables | Multi-risk? |
|----------------|-----------|---------------------------|-------------|
| Population density | Exposure | `B01003_001E` / BG land area (`ALAND`) | Shared E |
| Age Distribution | Vulnerability | `B01001` → share &lt;5 and 65+ (or 60+ aggregated) | Flood, landslide, heat |
| Income | Vulnerability | `B19013_001E` median HH income; `B17001` / `C17002` poverty | Flood, landslide, heat, energy |
| Health and basic services access | E (often V too) | `B27001` insurance; `B18101` disability; `B25047` plumbing | Heat, flood, drought |
| Inadequate water / sanitation proxies | Vulnerability | Plumbing / kitchen (`B25047`, `B25048`) | Water, health |
| Energy poverty (proxy) | Vulnerability | Cost burden `B25070`; no vehicle `B08201`; limited English `B16004` | Energy / heat |
| Urban infra social vulnerability | E/V | Tenure `B25003`, commute `B08301`, housing quality | Infrastructure / heat |

**Not in ACS** (other sources): stormwater drainage coverage, natural vegetation, health facility points, power plants.

### Best extraction (most granular)

1. **Geometries:** TIGER/Line block groups (or `pygris` / `tigris`).  
2. **Attributes:** Census API `acs/acs5`, or tidycensus / cenpy.  
3. **Scope:** `state:27` (MN), `county:053` (Hennepin) for Plymouth; then **intersect** BGs with `sites/plymouth/boundary/site.geojson`.  
4. **Density:** `population / (ALAND_m² / 1e6)` → people/km².  
5. **Normalize** 0–1 within Plymouth (local percentiles or min–max).  
6. **Burn to hazard grid** (~250 m), same pattern as POA bairro → raster.  
7. **Optional:** dasymetric redistribute BG totals with buildings/GHSL *inside* each BG for smoother maps.

API sketch:

```text
https://api.census.gov/data/2023/acs/acs5
  ?get=NAME,B01003_001E,B19013_001E,...
  &for=block+group:*
  &in=state:27+county:053
  &key=YOUR_KEY
```

Join on GEOID = STATE+COUNTY+TRACT+BLKGRP to TIGER.

---

## Indicator → candidate mapping (Plymouth)

| Priority | Indicator (`Index`) | Kind | Applies to (sector → risk) | MN / US candidate(s) | Multi-risk? | Status |
|----------|---------------------|------|----------------------------|----------------------|-------------|--------|
| P0 | Population density | Demographic | Floods; Landslides; Heatwaves; Droughts; Food Security floods | **ACS block-group density (preferred)**; GHSL alternate | **Yes — shared E** | Ready |
| P1 | Households in hazard-prone areas | Socioeconomic / Physical | Floods; Landslides | Buildings ∩ flood hazard / NFHL / susceptibility | **Yes — floods + landslides** | Needs hazard + buildings |
| P2 | Health and basic services access | Socioeconomic | Heatwaves; Floods; Droughts | ACS insurance/disability/plumbing; CDC PLACES; HRSA | **Yes** | Same ACS pull |
| P2 | Power generation facilities | Infrastructure | Energy heat (+ drought) | HIFLD / EIA | **Yes (Energy)** | Optional |
| P2 | Protected areas | Physical | Biodiversity heat | PAD-US | No | Optional |
| P2 | Natural vegetation cover | Physical | Biodiversity heat | NLCD / Dynamic World | Partial | Optional |
| P2 | Road / railroad density | Physical | Infrastructures heat | OSM / USDOT | Reusable for infra landslide/erosion | Optional |
| P2 | Urban infrastructure social vulnerability | Physical | Infrastructures heat | ACS housing + commute | Partial | Optional |
| P2 | Agricultural * | Agriculture | Food Security floods/droughts | CDL / NASS | Multi-risk Food | Low in city AOI |

---

## Recommended first build (Plymouth)

1. **ACS block groups (P0)** — density for exposure; pull age + income/poverty (+ plumbing) in the same extract for vulnerability. Intersect city boundary → normalize within Plymouth → choropleth maps.  
   - Script: [`transformation/acs_ev/extract_acs_ev.py`](../transformation/acs_ev/extract_acs_ev.py)  
   - `export CENSUS_API_KEY=...` then `python transformation/acs_ev/extract_acs_ev.py --site plymouth`  
2. **P1** — buildings/parcels ∩ flood hazard (separate physical exposure).  
3. **Defer** agriculture / power plants until sector scope expands.  
4. **Flood risk H×E×V:** [`transformation/flood_risk/compute_flood_risk.py`](../transformation/flood_risk/compute_flood_risk.py)  
   (`python transformation/flood_risk/compute_flood_risk.py --site plymouth`)

---

## Link back to catalog / code (later)

| Product | Suggested id | Depends on |
|---------|--------------|------------|
| Shared exposure score | `plymouth_exposure` | ACS BG density → role of `poa_exposure` |
| Shared vulnerability | `plymouth_vulnerability` | ACS age / income (and optional insurance) |
| Vector companion | BG GeoPackage | Like POA bairro GPKG |
| Catalog | `catalog/datasets.yaml` | After COG/tiles publish |

JSON remains the indicator spec; this file is the **MN operationalization**.
