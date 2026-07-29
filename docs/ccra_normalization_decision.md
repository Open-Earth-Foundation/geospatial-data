# CCRA normalization decision — city-level domain

**Status:** Accepted (working decision)  
**Ticket:** [CC-579](https://linear.app/openearth/issue/CC-579/structure-the-ccra-data-catalog-and-optimize-the-layer-generation)  
**Date:** 2026-07-29

## Decision

**Extract and normalize CCRA screening layers at the city AOI.**  
For each `city_name`, inputs are clipped to the city boundary and scores that use domain scaling (min–max / robust min–max within the ROI) are computed **relative to that city’s mapped range**, not relative to a state, country, or global domain.

State-, country-, and global-level normalization schemes have **not been designed or tested** yet. Comparability across cities (or across nested scales) is therefore **not guaranteed** for domain-scaled layers.

## What this means in practice

| Stage | Behavior |
|-------|----------|
| Extract | GEE / Census / other sources clipped to `sites/{city}/boundary` |
| Hazard inputs | Some use **fixed physical classes** (e.g. flood depth impact bins in meters) → more portable across cities |
| Hazard / E/V domain scales | Others use **ROI min–max** (or robust min–max) inside the city → “1.0” = highest *within that city* |
| Risk | \(R = (H \times E \times V)^{1/3}\) inherits the same city-relative meaning of H/E/V |

Runtime configs stay **city-level slugs only** (e.g. `plymouth`, `rochester`), not statewide regions. See `models/README.md` and `docs/cougar-migration.md`.

## Advantages

1. **Matches the product unit** — CCRA maps are consumed per city; relative hotspots inside the AOI are what planners need first.
2. **Stable pipeline** — one YAML + boundary → extract → score → publish; no dependency on a larger region run finishing first.
3. **Fair local contrast** — flat or uniformly mild cities still get a full 0–1 stretch for screening, instead of collapsing near zero against a mountainous/wetter neighbor.
4. **Operationally cheap** — smaller AOIs, faster GEE exports, simpler QA SVGs and catalog IDs (`{city}_flood_hazard`, etc.).
5. **Clear provenance** — every published layer’s domain is the city named in `dataset_id` / site config.

## Limitations

1. **Cross-city scores are not absolute** — a “high” pixel in City A is not the same physical intensity as “high” in City B for domain-scaled layers (e.g. LST ensemble, ACS E/V burned to the grid, some event-count norms).
2. **Nested-scale inconsistency** — if the same area were later scored inside a state AOI, city “low/high” labels can change because the min/max window changes. Multi-scale comparability is **unresolved**.
3. **Ranking cities against each other** (which city is “worse”) needs a different product or a shared reference domain — not this pipeline’s current output.
4. **Edge effects** — very small AOIs or thin boundaries can make min–max sensitive to a few extreme cells (mitigated somewhat by robust norms where used, not eliminated).
5. **Future global rollout** (C40/GCoM) will likely need an explicit policy: keep city-relative screening, add a second absolute/regional index, or redefine normalization windows — **TBD**.

## Out of scope (for now)

- State-wide Minnesota (or other) single-domain min–max  
- Country- or global-domain reference histograms  
- Formal crosswalk so a city’s rating is identical at city and state scale  

## Related docs

- Pipeline architecture: `docs/ccra_pipeline_architecture.md`  
- Model configs / cards: `models/{flood,heat,landslide}_hazard/`  
- Migration / city sites: `docs/cougar-migration.md`  
- Command cheat sheet: Notion [pipeline](https://app.notion.com/p/3abeb557728b80b2ad12e81365978c60)
