# CCRA — extending to a new hazard (normalization checklist)

**Status:** Working guide  
**Related decision:** [ccra_normalization_decision.md](./ccra_normalization_decision.md)  
**Date:** 2026-08-12

Use this when adding a hazard beyond flood / heat / landslide. Default product remains **city-AOI screening**. Cross-city comparability is a separate product (see Options 1–3 in the decision doc).

---

## 1. Inventory inputs

For each source dataset that will enter the hazard ensemble:

- [ ] Units and native scale (physical units, counts, classes, binary mask, index)
- [ ] Spatial resolution and nodata behavior
- [ ] Global / regional availability (can it run for MN, Brazil, C40 cities?)
- [ ] Whether the signal is absolute (depth m, °C) or relative (event counts, vegetation index)

## 2. Choose a normalization family per input

Pick **one** primary family; document why. Prefer the leftmost option that still preserves interpretability:

| Family | When to use | Examples already in stack | Cross-city portable? |
|--------|-------------|---------------------------|----------------------|
| **Fixed physical classes / thresholds** | Clear units + literature or standards | Flood JRC/Aqueduct depth bins; landslide slope/clay/HAND | Yes (within model) |
| **Binary / categorical map** | Mask or presence/absence | GFPLAIN 0/1 | Yes |
| **City-domain min–max** (or robust P95 + log1p + min–max) | Continuous intensity with no stable global cutoffs; need in-city contrast | Heat LST; GFD counts; landslide R90p / NDVI | No |
| **Regional / climatological** (Options 1 or 3) | Only if the product must rank cities or express local anomalies | Not default for v1 screening | Yes (by design) |

Rules of thumb:

1. If the variable has **meters / °C / mm** and defensible bins → **fixed classes** (do not min–max away the units).
2. If the variable is a **count or relative index** and planners need hotspots inside one city → **city-domain min–max**.
3. If distributions are heavy-tailed → prefer **robust** scaling (e.g. GFD P95 + `log1p`) over raw min–max.
4. Do **not** mix families silently: every input’s family must appear in the model card and in the layer table in the [decision doc](./ccra_normalization_decision.md).

## 3. Decide where normalization runs

| Stage | Prefer when | Pattern in repo |
|-------|-------------|-----------------|
| **Extract** | Norm needs GEE ROI reducers or source-specific transforms | `minmax_norm_roi`, GFD robust pipeline |
| **Compute** | Norm needs the hazard grid / multi-layer alignment | `minmax_norm` on city grid (landslide) |

Default domain for min–max families: **city boundary** (`sites/{city}/boundary`). Do not introduce state/global domains in the default `{city}_*_hazard` product without an explicit dual-product plan.

## 4. Wire the hazard into the CCRA shape

Mirror an existing hazard (flood / heat / landslide):

- [ ] `models/{hazard}_hazard/{model_card.md,config.yaml}` — formulas, weights, norm family per input, limitations
- [ ] `transformation/{hazard}_hazard/` — `extract_*`, `compute_*`, site YAML, publish
- [ ] Output **H ∈ [0, 1]** on a documented grid; ensemble weights renormalize over available layers (flood pattern)
- [ ] Risk (if in scope): \(R = (H \times E \times V)^{1/3}\) with the same city-domain meaning for E/V unless stated otherwise
- [ ] Catalog IDs / QA: `{city}_{hazard}_hazard`, metadata notes `normalization_domain: city`

## 5. Document in the decision file

Before calling the hazard “CCRA-ready”:

- [ ] Add one row per normalized component to **Layers that use city-domain min–max today** in [ccra_normalization_decision.md](./ccra_normalization_decision.md) (or a sibling “fixed-threshold” note if none are domain-scaled)
- [ ] Link the model-card section that states the formula
- [ ] State explicitly: comparable across cities? **Yes / No / Only for fixed-threshold inputs**
- [ ] If stakeholders will need ranking later: note the intended path (Option 1 regional constants vs Option 2 thresholds vs Option 3 climatology) — do not block city screening on that

## 6. Smoke-test interpretation

- [ ] In-city map: hotspots align with known physical / historical intuition inside the pilot city
- [ ] Mild city still shows a usable 0–1 stretch if using city-domain min–max (expected)
- [ ] Score is **not** marketed as absolute risk vs another city unless a regional/fixed product exists
- [ ] Edge case: tiny AOI + min–max → check sensitivity to a few extreme cells; use robust norm if needed

## Template blurb (copy into new model card)

```text
Normalization domain: city AOI (CCRA default).
Inputs using fixed physical classes: …
Inputs using city-domain min–max: …
Cross-city comparable: no for domain-scaled inputs; yes for fixed-class inputs.
See docs/ccra_normalization_decision.md and docs/ccra_new_hazard_normalization_checklist.md.
```

---

## Related docs

- Normalization decision / options: [ccra_normalization_decision.md](./ccra_normalization_decision.md)
- Pipeline architecture: [ccra_pipeline_architecture.md](./ccra_pipeline_architecture.md)
- Model configs / cards: `models/{flood,heat,landslide}_hazard/`
