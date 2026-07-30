# CCRA normalization decision — city-level domain

**Status:** Accepted (working decision)  
**Ticket:** [CC-579](https://linear.app/openearth/issue/CC-579/structure-the-ccra-data-catalog-and-optimize-the-layer-generation)  
**Date:** 2026-07-29 · **Updated:** 2026-07-30

## Decision (current)

**Extract and normalize CCRA screening layers at the city AOI.**  
For each `city_name`, inputs are clipped to the city boundary and scores that use domain scaling (min–max / robust min–max within the ROI) are computed **relative to that city’s mapped range**, not relative to a state, country, or global domain.

State-, country-, and global-level normalization schemes have **not been implemented** yet. Comparability across cities (or across nested scales) is therefore **not guaranteed** for domain-scaled layers.

See also: **Options for cross-city comparison** (below) and **Recommended path**.

---

## What this means in practice

| Stage | Behavior |
|-------|----------|
| Extract | GEE / Census / other sources clipped to `sites/{city}/boundary` |
| Hazard inputs | Some use **fixed physical classes** (e.g. flood depth impact bins in meters) → more portable across cities |
| Hazard / E/V domain scales | Others use **ROI min–max** (or robust min–max) inside the city → “1.0” = highest *within that city* |
| Risk | \(R = (H \times E \times V)^{1/3}\) inherits the same city-relative meaning of H/E/V |

Runtime configs stay **city-level slugs only** (e.g. `plymouth`, `rochester`), not statewide regions. See `models/README.md` and `docs/cougar-migration.md`.

### Layers that use city-domain min–max today

| Product | Component | Where normalized | Cross-city comparable? |
|---------|-----------|------------------|------------------------|
| Heat | Landsat / MODIS P90 LST | Extract (`minmax_norm_roi` on city boundary) | No |
| Flood | GFD event count | Extract (P95 + log1p + min–max in ROI) | No |
| Flood | JRC / Aqueduct depth | Fixed depth impact classes (m) | Yes (more portable) |
| Flood | GFPLAIN | Binary 0/1 | Yes |
| Landslide | R90p → `precip_risk` | Compute (`minmax_norm` on city grid) | No |
| Landslide | NDVI → `veg_protect` | Compute (`minmax_norm` on city grid) | No |
| Landslide | slope, clay, HAND | Fixed physical thresholds | Yes (within model) |
| ACS E/V | exposure, vulnerability | Min–max across city block groups | No |

Cross-city ranking is mainly blocked by **heat, GFD, landslide precip/veg, and ACS** — not the entire stack.

---

## Advantages (city-level domain)

1. **Matches the product unit** — CCRA maps are consumed per city; relative hotspots inside the AOI are what planners need first.
2. **Stable pipeline** — one YAML + boundary → extract → score → publish; no dependency on a larger region run finishing first.
3. **Fair local contrast** — flat or uniformly mild cities still get a full 0–1 stretch for screening, instead of collapsing near zero against a mountainous/wetter neighbor.
4. **Operationally cheap** — smaller AOIs, faster GEE exports, simpler QA SVGs and catalog IDs (`{city}_flood_hazard`, etc.).
5. **Clear provenance** — every published layer’s domain is the city named in `dataset_id` / site config.

## Limitations (city-level domain)

1. **Cross-city scores are not absolute** — a “high” pixel in City A is not the same physical intensity as “high” in City B for domain-scaled layers.
2. **Nested-scale inconsistency** — if the same area were later scored inside a state AOI, city “low/high” labels can change because the min/max window changes.
3. **Ranking cities against each other** needs a different product or a shared reference domain — not this pipeline’s current output.
4. **Edge effects** — very small AOIs can make min–max sensitive to a few extreme cells (partially mitigated by robust norms where used).
5. **Future global rollout** (C40/GCoM) will likely need an explicit policy: keep city-relative screening, add a regional/comparable index, or both.

---

## Options for cross-city / state / country comparison

When stakeholders need to compare cities (e.g. rank Minnesota metros, or report at state level), the city-domain product alone is insufficient. Three viable approaches:

### Option 1 — Regional reference domain (state / country min–max)

**Idea:** Define one normalization window per layer for a region (e.g. Minnesota, Brazil South). All cities in that region use the same `vmin` / `vmax` (or robust equivalents); each city run still clips to its boundary but scales scores against regional stats.

**Pipeline fit:** Strong. Normalization already happens via ROI reducers in GEE (`minmax_norm_roi`) and local `minmax_norm` / `minmax_01`. Change the ROI from city boundary → regional bbox (or union of city boundaries), store constants in e.g. `config/regions/minnesota.yaml`, and apply at extract/compute time. ACS E/V: min–max across all block groups in the state (or county union), then clip to city.

| | |
|--|--|
| **Code change** | Low–medium: regional config + pass reference stats into existing norm functions; optional second catalog product |
| **Compute cost** | Low: one regional stats job per layer per region, then reuse constants for every city |
| **Complexity** | Low: same formulas, different domain |
| **Credibility** | Good for **within-region** city ranking and state dashboards; defensible as “relative to Minnesota (or state X), not relative to this city alone”. Weak for cross-country comparison (MN vs Brazil) unless each country has its own regional reference |
| **Trade-offs** | Flat/mild cities may score lower overall (compressed range) — which is often *correct* for cross-city comparison but worse for in-city hotspot maps |

---

### Option 2 — Fixed physical thresholds

**Idea:** Replace domain min–max with absolute bins tied to physical units (e.g. LST °C, depth m, population density hab/km², R90p mm/day), similar to existing JRC/Aqueduct depth classes.

**Pipeline fit:** Partial. Flood depth already uses this pattern. Heat, GFD, landslide precip/veg, and ACS would need new threshold tables per climate zone / country in `models/*/config.yaml`.

| | |
|--|--|
| **Code change** | Medium–high: new threshold configs, QA against literature, per-zone calibration |
| **Compute cost** | Low (no extra historical processing) |
| **Complexity** | Medium: expert input and documentation; risk of arbitrary cutoffs |
| **Credibility** | High **if** thresholds are cited and zone-specific (e.g. health-relevant heat stress); low if bins are ad hoc. Best where standards exist (flood depth) |
| **Trade-offs** | Mild climates may rarely use the full 0–1 range; thresholds don’t transfer cleanly across continents without regional variants |

---

### Option 3 — Grid-cell historical normalization (climatological percentiles)

**Idea:** For each grid cell (or coarse ~5–30 km cell), build a long-term reference (e.g. 20–30 years). Score the current value as a local percentile or anomaly (e.g. 0.01–0.99 = “extreme for this location”). Heat: LST P90 vs cell climatology; precip: already partly climatological (CHIRPS R90p) but today re-min-maxed inside the city.

**Pipeline fit:** Medium. Requires **precomputed reference COGs** (global or regional percentile surfaces) ingested once; city runs become lookup + rescale instead of ROI min–max. Does not map cleanly to ACS (vector, not pixel time series).

| | |
|--|--|
| **Code change** | Medium–high: new reference assets, extract/compute paths, catalog entries for reference layers |
| **Compute cost** | High **once** (build percentile surfaces in GEE); low per city thereafter if references are cached on S3 |
| **Complexity** | High: storage, versioning, interpretation docs (“high” = locally extreme, not absolutely hot) |
| **Credibility** | Strong for **“unusual relative to local climate”** narratives (drought in wet places, heat in cool places). Weaker if stakeholders expect absolute physical intensity. Aligns with common climate-index practice |
| **Trade-offs** | Needs historical data and upfront investment; interpretation must be communicated clearly |

---

## Recommended path (given the current pipeline)

**Do not replace the city-level screening product.** Keep it as the default CCRA deliverable (`{city}_*_hazard`, `{city}_*_risk`) — it matches how maps are used and how the pipeline is built today.

**For cross-city comparison, adopt a dual-product strategy:**

| Product | Normalization | Primary use |
|---------|---------------|-------------|
| `{city}_heat_hazard` (current) | City AOI | In-city hotspots, planning maps |
| `{region}_heat_hazard_regional` or `{city}_heat_hazard_regional` | Regional reference (Option 1) | Rank cities, state summaries |

### Why Option 1 is the best near-term choice

Option 1 is the best **next step** for Minnesota (and similar multi-city batches) when weighing all four criteria against the current codebase:

1. **Smallest change** — Normalization is already parameterized by ROI in `heat_hazard/input_common.py` (`minmax_norm_roi`), `landslide_hazard/compute_landslide_hazard.py` (`minmax_norm`), `acs_ev/extract_acs_ev.py` (`minmax_01`), and GFD extract. Swapping “city ROI” for “regional ROI + stored constants” is incremental, not a rewrite.

2. **Lowest compute cost** — One regional pass per layer (or one GEE `reduceRegion` on Minnesota) vs building and maintaining global percentile cubes (Option 3).

3. **Lowest operational complexity** — No new reference dataset lifecycle beyond a small YAML/JSON of `{layer: {vmin, vmax}}` per region; city batch scripts stay the same.

4. **Good enough credibility for the immediate ask** — Stakeholders comparing Plymouth vs Rochester vs Apple Valley care about **ranking within Minnesota**, not whether a pixel matches a pixel in Porto Alegre. Regional min–max is easy to explain: *“0.8 = among the highest values observed across Minnesota for this layer.”* That is scientifically modest but **honest and sufficient** for state-level CCRA screening.

Option 1 is **not** a bad compromise — it is the right first comparability layer for a pipeline that was intentionally optimized for city screening.

### When to add Option 3

Consider Option 3 (grid-cell climatology) **later**, for layers where:

- Cross-**climate-zone** comparison matters (national/global rollout), or  
- “Extreme for this place” is the narrative (heat waves, chronic wetness), and  
- You can afford one-time reference COG production (LST, precip).

CHIRPS R90p is a natural candidate: it is already climatological; removing the city-level `minmax_norm` on `precip_risk` and scaling against a fixed regional or per-cell reference would be a focused improvement.

Option 2 remains valuable **where it already exists** (flood depth) and for future health-linked heat thresholds — but it is not the fastest path to comparable scores across all min–max layers.

### Suggested implementation order (Minnesota)

1. **Spike:** Compute regional `vmin`/`vmax` for heat LST norms and ACS E/V over Minnesota; re-score one city (e.g. Rochester) with regional constants; compare rank vs city-relative maps.  
2. **Config:** Add `config/regions/minnesota.yaml` (or `transformation/_shared/regions/`) referenced from site YAMLs via `normalization_domain: minnesota`.  
3. **Catalog:** Publish optional `{city}_*_regional` or a single state-wide reference layer with metadata `comparability: regional`.  
4. **Defer** Option 3 until C40/GCoM scope requires cross-country or “local anomaly” framing.

---

## Out of scope (for now)

- Grid-cell climatological percentiles (Option 3) — design only; no reference COGs in repo  
- Country-global single min–max without regional tiers  
- Formal crosswalk so city and state scales produce identical labels  
- Replacing city-relative screening as the default product  

---

## Related docs

- Pipeline architecture: `docs/ccra_pipeline_architecture.md`  
- Model configs / cards: `models/{flood,heat,landslide}_hazard/`  
- Migration / city sites: `docs/cougar-migration.md`  
- Command cheat sheet: Notion [pipeline](https://app.notion.com/p/3abeb557728b80b2ad12e81365978c60)
