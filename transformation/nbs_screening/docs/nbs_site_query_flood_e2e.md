# NBS site query — flood E2E (Porto Alegre)

**Notebook:** [`scripts/nbs_site_query_flood_e2e.ipynb`](../scripts/nbs_site_query_flood_e2e.ipynb)  
**Lens:** [`flood_nbs_dataset_lens.md`](flood_nbs_dataset_lens.md)  
**Default site:** Humaitá

---

## Structure

| Section | Unit | Purpose |
|---------|------|---------|
| **Bairro** | Bairro polygon | Step 0 priority + Step 1 mechanism + Step 2 flood NBS |
| **Grid** | 250 m analysis cell | Per-cell mechanism flags + dominant NBS; bairro % rollup |

Grid cell = primary unit for intra-bairro differentiation; bairro polygon is only a spatial filter. See [`grid_screening.py`](../scripts/grid_screening.py).

**ON-5990:** each cell exports `flood_mechanism_type` (dominant: riverine / pluvial / low_lying / drainage_constrained / mixed / none) + `flood_mechanism_code` (0–5) as GeoJSON and GeoTIFF.

**Full POA catalog layer:** see [`poa_mechanism_type_layer.md`](poa_mechanism_type_layer.md) — observed screening + IDW gap-fill, assumptions, and limitations.

---

## Workflow

```text
Step 0  bairro attributes     → flood_risk_score_poa.gpkg
Step 1  catalog + local rasters → hazard, HAND, UPA, built-up, JRC water, etc.
Step 1  mechanism inference   → riverine, pluvial, low-lying, drainage gap
Step 2  NBS typology scores   → rain garden, bioswale, wetland restoration, …
Grid    screen_bairro_grid    → per 250 m cell flags + GeoJSON export
```

**Mechanism flags:** `riverine`, `pluvial`, `low_lying`, `drainage_constrained_gap`

---

## Run

```bash
transformation/floods/.venv/bin/python transformation/nbs_screening/scripts/run_e2e.py --hazard flood
```

**Outputs:**
- `output/nbs_site_query_humaita.json` — bairro report
- `output/nbs_grid_flood_humaita.geojson` / `.json` — grid screening (notebook only)

Change `SITE_NAME` in the notebook Setup cell to try another bairro.
