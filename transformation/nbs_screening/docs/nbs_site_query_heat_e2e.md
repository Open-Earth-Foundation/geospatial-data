# NBS site query — heat E2E (Porto Alegre)

**Notebook:** [`scripts/nbs_site_query_heat_e2e.ipynb`](../scripts/nbs_site_query_heat_e2e.ipynb)  
**Rules:** [`scripts/nbs_rules.py`](../scripts/nbs_rules.py)  
**Lens:** [`heat_nbs_dataset_lens.md`](heat_nbs_dataset_lens.md)  
**Default site:** Cidade Baixa

---

## Structure

| Section | Unit | Purpose |
|---------|------|---------|
| **Bairro** | Bairro polygon | Step 0 priority + Step 1 mechanism + Step 2 heat NBS |
| **Grid** | 250 m analysis cell | Per-cell heat mechanism type + dominant NBS; bairro % rollup (ON-5991) |

Grid cell = primary unit for intra-bairro differentiation; bairro polygon is only a spatial filter. See [`grid_screening.py`](../scripts/grid_screening.py).

---

## Workflow

```text
Step 0  bairro attributes     → heat_risk_score_poa.gpkg / catalog poa_heat_*
Step 1  catalog COGs          → LST, built-up, tree cover, NDVI, H/E/V/R
Step 1  mechanism inference   → UHI, shade deficit, daytime LST, nocturnal cooling, social exposure
Step 2  NBS typology scores   → street trees, green corridor, pocket park, …
Grid    screen_bairro_grid    → per 250 m cell dominant heat_mechanism_type + GeoJSON export
```

**Dominant heat mechanism types:** `uhi_built_up`, `shade_deficit`, `high_daytime_lst`, `limited_nocturnal_cooling`, `high_social_exposure`, `mixed`, `without_clear_dominant` (codes 0–6).

---

## Run

```bash
transformation/floods/.venv/bin/python transformation/nbs_screening/scripts/run_e2e.py --hazard heat
```

**Outputs:**
- `output/nbs_site_query_heat_cidade_baixa.json` — bairro report
- `output/nbs_grid_heat_cidade_baixa.geojson` / `.json` — grid screening (notebook)
- `output/heat_mechanism_type_cidade_baixa_250m.tif` — bairro GeoTIFF export
- `output/heat_mechanism_type_poa_250m.*` — full POA layer (`BUILD_POA_HEAT_LAYER = True`)

**POA methodology (observed + IDW, limitations):** [`poa_mechanism_type_layer.md`](poa_mechanism_type_layer.md)

Change `HEAT_SITE_NAME` in the notebook Setup cell to try another bairro.
