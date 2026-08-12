# CCRA layer-generation pipeline architecture

**Repo:** `geospatial-data`  
**Ticket:** [CC-579](https://linear.app/openearth/issue/CC-579/structure-the-ccra-data-catalog-and-optimize-the-layer-generation)  
**Related:** `architecture.md` (catalog/S3 platform), `docs/ccra_normalization_decision.md`, Notion [pipeline](https://app.notion.com/p/3abeb557728b80b2ad12e81365978c60)

## 1. Purpose

Scale the Porto Alegre CCRA workflow from hand-built, single-city processing to a **parameterized, city-level batch pipeline**:

```text
input:  city_name + boundary (+ site YAML)
        OR batch JSON with cities[] (slug / name / coordinates)
output: screening hazard (H), exposure (E), vulnerability (V), risk (R)
        → COG + XYZ tiles → S3 + catalog/datasets.yaml
```

Single-city CLI: `--site {slug}` (see `docs/demo_rochester.sh`).  
Multi-city JSON: `transformation/ccra_batch/run_batch.py` (see `docs/ccra_batch_pipeline.md`).

Hazard families in scope today: **flood · heat · landslide**.  
NbS **mechanism** layers remain modeled under `models/nbs_*` / POA publish paths; they are **not** yet in the same multi-city CLI batch as H/E/V/R.

## 2. Design principles

| Principle | Implementation |
|-----------|----------------|
| City is the unit of run | `site_slug` / `--site city_name`; configs under `config/` or `config/sites/` |
| Offline precompute | Extract → score → publish; apps read catalog + S3 only |
| Low-code / CLI-first | Prefer `extract_*`, `compute_*`, `*_publish.py` over notebooks |
| Models vs runtime | Weights/thresholds in `models/{layer}/`; paths/bbox/S3 in site YAML |
| City-domain normalization | Extract + domain min–max inside city AOI (see normalization doc) |
| Catalog as registry | Every published product upserts `catalog/datasets.yaml` |

## 3. End-to-end flow

```text
                    ┌─────────────────────────────┐
                    │  site YAML + boundary       │
                    │  (--site city_name)         │
                    └──────────────┬──────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   flood extract            heat extract            landslide extract
          │                        │                        │
          ▼                        ▼                        ▼
   compute flood H          compute heat H          compute landslide H
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                                   ▼
                    ACS E/V (once per city)
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   flood risk R             heat risk R             landslide risk R
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   ▼
              publish: COG + tiles_visual + tiles_values
                     → optional S3 + catalog upsert
```

**Risk formula** (all hazards):  
\(R = (H \times E \times V)^{1/3}\) on cells where H, E, V are finite (screening index 0–1, not loss modeling).

## 4. Stages (inputs → outputs)

| Stage | Role | Typical inputs | Typical outputs |
|-------|------|----------------|-----------------|
| **0. Config** | Parameterize the city | `config/sites/{city}.yaml` or `config/{city}.yaml`, `boundary/site.geojson` | Resolved paths, bbox, `s3_prefix`, layer filenames |
| **1. Extract** | Pull/clip source rasters (+ local SVG QA) | GEE / remote APIs, city boundary | `sites/{city}/data/input/*.tif`, `…/intermediate/qa_inputs/` |
| **2. Compute hazard** | Ensemble / gated score → **H** | Input TIFs + `models/{hazard}/config.yaml` | `…/data/output/{hazard}_*_{city}.tif`, QA SVGs, `metadata.json` |
| **3. ACS E/V** | Socioeconomic **E** and **V** (once per city) | Census API + TIGER BGs ∩ boundary | `acs_ev/…/acs_ev_block_groups.gpkg` (+ choropleth SVGs) |
| **4. Compute risk** | Burn E/V onto H grid → **R** | Hazard TIF + ACS GPKG | `{hazard}_risk_score_{city}.tif`, E/V burned TIFs, BG GPKG, QA SVGs |
| **5. Publish** | Package for apps | Score GeoTIFF (+ optional GPKG) | `sites/{city}/out/…` COG, `tiles_visual`, `tiles_values`; optional S3 + `catalog/datasets.yaml` |

### 4.1 Parameterization

Replace `city_name` with the site slug (`plymouth`, `apple_valley`, `edina`, `richfield`, `rochester`, `porto_alegre`, …).

| Knob | Where |
|------|--------|
| Boundary / bbox / seasons / filenames | `transformation/{module}/config/sites/{city}.yaml` (hazards) |
| ACS county FIPS, overlap rules | `transformation/acs_ev/config/{city}.yaml` |
| Risk paths + S3 prefixes | `transformation/{flood,heat,landslide}_risk/config/{city}.yaml` |
| Model weights / gates | `models/{flood,heat,landslide}_hazard/config.yaml` (+ optional city overrides in site YAML) |

Adding a city: copy site YAMLs → set boundary → run the stage sequence (no code change if sources already supported).

### 4.2 Module map

| Product | Extract | Compute | Publish |
|---------|---------|---------|---------|
| Flood hazard | `flood_hazard/extract_flood_inputs.py` | `compute_flood_hazard.py` | `flood_hazard_publish.py` |
| Heat hazard | `heat_hazard/extract_heat_inputs.py` | `compute_heat_hazard.py` | `heat_hazard_publish.py` |
| Landslide hazard | `landslide_hazard/extract_landslide_inputs.py` | `compute_landslide_hazard.py` | `landslide_hazard_publish.py` |
| ACS E/V | — | `acs_ev/extract_acs_ev.py` | (consumed by risk; shared flood E/V may also publish) |
| Flood / heat / landslide risk | — | `compute_*_risk.py` | `*_risk_publish.py --product risk` |

Command templates (generic): Notion [pipeline](https://app.notion.com/p/3abeb557728b80b2ad12e81365978c60).  
Example orchestrator script: `docs/demo_rochester.sh` (`SITE=city_name`).

## 5. Repository layout (CCRA path)

```text
geospatial-data/
├── architecture.md                 # platform catalog + S3 conventions
├── catalog/datasets.yaml           # registered products + asset URLs
├── collections/layers.yaml         # layer_id ↔ model / transformation
├── models/
│   ├── flood_hazard/               # weights, model_card
│   ├── heat_hazard/
│   ├── landslide_hazard/
│   └── nbs_*                       # mechanism / opportunity (separate track)
├── transformation/
│   ├── flood_hazard|heat_hazard|landslide_hazard/
│   ├── flood_risk|heat_risk|landslide_risk/
│   ├── acs_ev/
│   └── {source extracts: jrc, aqueduct, modis, …}
└── docs/
    ├── ccra_pipeline_architecture.md   # this file
    └── ccra_normalization_decision.md
```

Per-city runtime data (gitignored):  
`transformation/{module}/sites/{city}/{boundary,data,out,cache}/`.

## 6. Publish & catalog

Local build (always safe for QA):

```bash
python transformation/<module>/<module>_publish.py --site city_name --build
```

Upload + register:

```bash
python transformation/<module>/<module>_publish.py \
  --site city_name --no-build --upload --write-catalog
```

| Artifact | Role |
|----------|------|
| `*_cog.tif` | Analysis download |
| `tiles_visual/{z}/{x}/{y}.png` | Map display |
| `tiles_values/{z}/{x}/{y}.png` | Encoded numeric queries (RGB scale) |
| Vector GPKG (risk / some hazards) | Block-group or bairro zonal means |
| `catalog/datasets.yaml` | `dataset_id` e.g. `{city}_flood_risk` |

S3 layout follows site `s3_prefix`, typically:  
`oef_calculation/release/v1/{city}/climate_hazards/{floods|heat|landslides}/…`  
Bucket used in current MN/POA work: `geo-test-api`.

## 7. Normalization (summary)

**Decision:** extract and domain-normalize inside the **city AOI**. State/country/global domains are not implemented.

- Fixed physical class transforms (e.g. flood depth bins) are more portable across cities.  
- ROI min–max (LST, some counts, ACS E/V) makes “high” = high *within that city*.  

Full rationale, advantages, limitations: `docs/ccra_normalization_decision.md`.

## 8. Catalog structure (CCRA products)

Products are registered in `catalog/datasets.yaml` with metadata (resolution, CRS, license, `data_quality`, `assets`).

| Dimension | Examples |
|-----------|----------|
| Hazard | `{city}_flood_hazard`, `{city}_heat_hazard`, `{city}_landslide_hazard` |
| Exposure / vulnerability | `{city}_exposure`, `{city}_vulnerability` (flood shared path); heat/landslide may publish grid-burned variants under hazard prefixes |
| Risk | `{city}_flood_risk`, `{city}_heat_risk`, `{city}_landslide_risk` |
| Mechanism (POA today) | `poa_*_mechanism_type` — not yet batch-generated for MN cities |

**Global vs region-specific:** globally reusable sources (JRC, MODIS, ACS for US, etc.) feed the parameterized path. Brazil-only NBS supporting layers stay out of the shared catalog until validated (see COUGAR check-in / migration notes).

## 9. Cities configured

| `city_name` | Hazard site YAML | ACS + risk YAML | Published E2E (approx.) |
|-------------|------------------|-----------------|-------------------------|
| `porto_alegre` | legacy / POA | POA products in catalog | Yes (pre-CLI era + catalog) |
| `plymouth` | ✅ | ✅ | Yes (hazard + risk) |
| `apple_valley` | ✅ | ✅ | Hazard + risk (in progress / partial) |
| `edina` | ✅ | ✅ | Config only |
| `richfield` | ✅ | ✅ | Config only |
| `rochester` | ✅ | ✅ | Config only |

## 10. Runtime prerequisites

- Python env: `geospatial-data/.venv`  
- Earth Engine auth for hazard extracts (`earthengine authenticate`; optional `EE_PROJECT`)  
- `CENSUS_API_KEY` for ACS  
- GDAL CLI (`gdal_translate`, `gdaldem`, `gdal_calc.py`, `gdal2tiles.py`) for publish  
- AWS CLI + credentials for `--upload`

## 11. Multi-city batch (JSON)

Beyond single `--site` runs, use the batch orchestrator:

```bash
python transformation/ccra_batch/run_batch.py \
  --input docs/examples/ccra_batch_minnesota.json \
  --jobs 2 --continue-on-error
```

- **Input:** JSON array of cities (`slug` / `name` / `coordinates` / `id`) — see `docs/examples/`  
- **Efficiency:** parallel city workers + regional cache manifest (`cache/regions/…`)  
- **Failures:** one city can fail while others complete (`continue_on_error`)  
- **Docs:** `docs/ccra_batch_pipeline.md`

Per-city H/E/V/R outputs stay identical to the single-city path.

## 12. Related documents

| Doc | Content |
|-----|---------|
| `architecture.md` | Platform-level catalog + S3 design |
| `docs/ccra_normalization_decision.md` | City-domain normalization decision |
| `docs/ccra_batch_pipeline.md` | Multi-city JSON batch + examples |
| `docs/cougar-migration.md` | Migration from `projects/cougar` |
| `models/*/model_card.md` | Per-hazard methodology |
| Notion [pipeline](https://app.notion.com/p/3abeb557728b80b2ad12e81365978c60) | Copy-paste CLI with `city_name` |
| `docs/demo_rochester.sh` | Optional shell orchestrator (`SITE=…`) |
