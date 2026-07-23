# NBS site query — landslide E2E (Porto Alegre)

**Notebook:** [`scripts/nbs_site_query_landslide_e2e.ipynb`](../scripts/nbs_site_query_landslide_e2e.ipynb)  
**Lens:** [`landslide_nbs_dataset_lens.md`](landslide_nbs_dataset_lens.md)  
**Default site:** Glória

---

## Structure

Bairro-level + **90 m grid** landslide screening (mechanism type layer aligned with flood/heat).

| Step | Purpose |
|------|---------|
| **0** | Landslide hazard / risk priority from `landslide_risk_score_poa.gpkg` |
| **1a** | Diagnostic layers — slope, clay, NDVI P10, HAND, R90p, Dynamic World |
| **1b** | Susceptibility context — steep slope, rain trigger, vegetation deficit, drainage |
| **2** | Slope-stabilization NBS typology scores |
| **Grid** | Per-cell `landslide_mechanism_type` on 90 m cells (`BUILD_POA_LANDSLIDE_LAYER`) |

**Dominant landslide mechanism types:** `steep_activatable_slope`, `rainfall_trigger`, `low_cohesion_wet`, `vegetation_deficit`, `drainage_saturation`, `disturbed_bare_slope`, `upslope_convergence`, `high_social_exposure`, `mixed`, `without_clear_dominant` (codes 0–9; `min_strength = 0.15`).

---

## Workflow

```text
Step 0  bairro attributes     → landslide_risk_score_poa.gpkg
Step 1  catalog + local rasters → 90 m hazard, slope, clay, NDVI P10, HAND, R90p, Dynamic World
Step 1  mechanism inference   → steep slope, rainfall trigger, clay, veg deficit, drainage, bare slope, UPA
Step 2  NBS typology scores   → slope revegetation, bioengineering, riparian/gully, forest restoration
```

**Mechanism flags:** `steep_activatable_slope`, `rainfall_trigger`, `low_cohesion_wet`, `vegetation_deficit`, `drainage_saturation`, `disturbed_bare_slope`, `upslope_convergence`, `high_social_exposure`

**NBS types:** `slope_revegetation`, `bioengineering_erosion_control`, `riparian_gully_protection`, `forest_restoration_upslope`

---

## Run

```bash
transformation/floods/.venv/bin/python transformation/nbs_screening/scripts/run_e2e.py --hazard landslide --site "Glória"
```

**Output:** `output/nbs_site_query_landslide_gloria.json`

Change `LANDSLIDE_SITE_NAME` in the notebook Setup cell to try another bairro.

**Caveats (from hazard methodology):** slope ≥ 15° activation gate; H = 0 on flat land; 90 m grid; susceptibility ≠ geotechnical stability.
