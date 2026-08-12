# CCRA multi-city batch pipeline

**Status:** Implemented (orchestrator + JSON contract)  
**Depends on:** single-city CLI by `--site` (Maureen / CC-579)  
**Module:** `transformation/ccra_batch/`  
**Schema / examples:** `docs/examples/ccra_batch_*.json`

## 1. Goal

Scale the CCRA layer-generation pipeline from **one city per invocation** to **many cities from a single JSON input**, for GCoM/C40 / CityCatalyst network runs.

This does **not** change the per-city product contract:

| Artifact | Still true |
|---|---|
| Hazard grids H | GeoTIFF per city × hazard |
| Exposure / vulnerability | ACS E/V per city |
| Risk scores R | \(R=(H\times E\times V)^{1/3}\) per hazard × city |
| Publish | COG + tiles → optional S3 + catalog |

City-domain normalization remains the scoring decision (`docs/ccra_normalization_decision.md`). Batch mode optimizes **orchestration and shared prep**, not cross-city score comparability.

## 2. Input format

JSON object with a `cities` array. Each city may identify itself by:

| Field | Role |
|---|---|
| `slug` | Preferred — must match `config/sites/{slug}.yaml` |
| `id` | Treated as slug when onboarded |
| `name` | Slugified / fuzzy-matched to configured sites |
| `coordinates.lat/lon` | Nearest configured site bbox centroid (≤75 km) |

Optional top-level keys: `batch_id`, `region`, `stages`, `hazards`, `options`.

Full schema: [`docs/examples/ccra_batch_input.schema.json`](examples/ccra_batch_input.schema.json)

### Example (5 Minnesota cities)

```json
{
  "batch_id": "minnesota-metro-5",
  "region": "minnesota",
  "stages": ["extract", "compute", "acs", "risk", "publish"],
  "hazards": ["flood", "heat", "landslide"],
  "options": {
    "continue_on_error": true,
    "max_workers": 2,
    "skip_existing": false,
    "prepare_regional_cache": true
  },
  "cities": [
    { "slug": "plymouth", "name": "Plymouth, MN" },
    { "slug": "edina" },
    { "slug": "richfield" },
    { "slug": "apple_valley" },
    { "slug": "rochester" }
  ]
}
```

Ready-to-run copies:

- `docs/examples/ccra_batch_minnesota.json` — explicit slugs + coordinates  
- `docs/examples/ccra_batch_resolve_demo.json` — name / coords / id resolution  

## 3. Usage

From `geospatial-data/` (venv active; EE + `CENSUS_API_KEY` as needed):

```bash
# Plan only (resolve cities, write regional cache, no GEE)
python transformation/ccra_batch/run_batch.py \
  --input docs/examples/ccra_batch_minnesota.json \
  --dry-run --jobs 4 --report /tmp/ccra_batch_dry.json

# Real run — keep --jobs low (Earth Engine quotas)
python transformation/ccra_batch/run_batch.py \
  --input docs/examples/ccra_batch_minnesota.json \
  --jobs 2 --continue-on-error \
  --report /tmp/ccra_batch_run.json

# Skip extracts when inputs already on disk; only compute + risk
python transformation/ccra_batch/run_batch.py \
  --input docs/examples/ccra_batch_minnesota.json \
  --stages compute,acs,risk --skip-existing --jobs 2
```

List onboarded slugs:

```bash
python transformation/ccra_batch/run_batch.py --list-configured
```

## 4. Efficiency model

| Lever | What it does |
|---|---|
| **Regional flood fetch** (`fetch_regional_layers`) | One GEE export of GFPLAIN / JRC / Aqueduct for `union_bbox` → `cache/regions/.../layers/` |
| **Per-city clip** (`materialize_from_regional`) | Window/mask regional TIFFs into each `flood_hazard/sites/{city}/data/input/` |
| **Extract fallback** | `extract_flood_inputs.py` skips GEE for cached sources when `CCRA_REGIONAL_CACHE` is set; **GFD** still per-city (ROI norm) |
| **Parallel cities** (`max_workers` / `--jobs`) | Independent city pipelines concurrently |
| **`skip_existing`** | Avoids re-running stages whose primary outputs already exist |
| **Partial failure** | One city failure does not abort the batch when `continue_on_error` is true |

```text
prepare_regional_cache (union_bbox + manifest)
        │
        ▼
fetch_regional_flood_layers  ── GEE once ──► layers/gfplain_250m.tif
                                             layers/jrc_rp100_depth*.tif
                                             layers/aqueduct_depth_rp100*.tif
        │
        ▼
materialize_sites_from_regional  ── clip ──► sites/{city}/data/input/*.tif
        │
        ▼
parallel city pipelines (GFD extract + compute + ACS + risk + publish)
```

Heat / landslide extracts stay per-city for now (city-domain norms or finer grids).

**Benchmark (acceptance):** run **5+ cities** (not `--dry-run`) and compare `wall_seconds` vs `sequential_estimate_seconds` in the JSON report (`efficiency_ratio = wall/sum`; <1 ⇒ parallel speedup). Dry-run validates resolution/orchestration only. With `--skip-existing`, stages are skipped (no regeneration).

## 5. Output structure (unchanged per city)

```text
transformation/{flood,heat,landslide}_hazard/sites/{city}/data/output/*_hazard_score_{city}.tif
transformation/acs_ev/sites/{city}/data/output/acs_ev_block_groups.gpkg
transformation/{flood,heat,landslide}_risk/sites/{city}/data/output/*_risk_score_{city}.tif
transformation/*/sites/{city}/out/          # COG + tiles after publish
catalog/datasets.yaml                       # optional --write-catalog
cache/regions/{region}/{batch_id}/manifest.json
cache/regions/{region}/{batch_id}/union_bbox.json
cache/regions/{region}/{batch_id}/layers/*.tif   # regional flood fetch
cache/regions/{region}/{batch_id}/layers_manifest.json
```

Aggregate risk is still **per hazard × city**, not a single multi-city mosaic.

## 6. Error handling

| Case | Behavior |
|---|---|
| Unknown slug / unresolvable name|coords | City marked `failed`; others continue if `continue_on_error` |
| Stage CLI non-zero exit | City stops at failed stage; remaining cities continue (default) |
| `--fail-fast` | Stop scheduling further cities after first failure |
| Process crash in a worker | Captured as city `failed` with exception text |

Exit code: `0` if all cities ok/skipped; `1` if any failed.

## 7. Onboarding a new city into a batch

1. Add site YAMLs + boundary (same as single-city path in `docs/ccra_pipeline_architecture.md` §4.1).  
2. Add the city object to the batch JSON (`slug` preferred).  
3. Re-run `run_batch.py`.

Batch JSON **does not** auto-create site YAMLs. Coordinates only match **already onboarded** sites.

## 8. Tests

```bash
cd geospatial-data
python -m unittest transformation.ccra_batch.tests.test_batch -v
# or:
python transformation/ccra_batch/tests/test_batch.py -v
```

## 9. Related

| Doc | Role |
|---|---|
| `docs/ccra_pipeline_architecture.md` | Single-city stage map |
| `docs/ccra_normalization_decision.md` | City-domain norms |
| `docs/demo_rochester.sh` | Single-city shell orchestrator |
| `transformation/nbs_screening/*/batch_mechanism.py` | NbS multi-city pattern (mechanism only) |
