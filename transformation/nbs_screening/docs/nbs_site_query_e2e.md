# NBS site query — E2E exercises (Porto Alegre)

End-to-end geospatial queries on real climate-exposed bairros, NBS screening rules, query patterns, and gaps discovered in practice.

Each hazard has its **own notebook and notes**:

| Hazard | Notebook | Notes | Default site |
|--------|----------|-------|--------------|
| **Flood** | [`nbs_site_query_flood_e2e.ipynb`](../scripts/nbs_site_query_flood_e2e.ipynb) | [`nbs_site_query_flood_e2e.md`](nbs_site_query_flood_e2e.md) | Humaitá |
| **Heat** | [`nbs_site_query_heat_e2e.ipynb`](../scripts/nbs_site_query_heat_e2e.ipynb) | [`nbs_site_query_heat_e2e.md`](nbs_site_query_heat_e2e.md) | Cidade Baixa |
| **Landslide** | [`nbs_site_query_landslide_e2e.ipynb`](../scripts/nbs_site_query_landslide_e2e.ipynb) | [`nbs_site_query_landslide_e2e.md`](nbs_site_query_landslide_e2e.md) | Glória |

**Shared helpers:** [`catalog_layers.py`](../scripts/catalog_layers.py), [`nbs_rules.py`](../scripts/nbs_rules.py), [`grid_screening.py`](../scripts/grid_screening.py)  
**CLI:** [`run_e2e.py`](../scripts/run_e2e.py)  
**Dataset inventory:** [`recommended-datasets.md`](recommended-datasets.md)

---

## How to run

```bash
cd transformation/nbs_screening/scripts
../../floods/.venv/bin/python run_e2e.py --hazard flood
../../floods/.venv/bin/python run_e2e.py --hazard heat
../../floods/.venv/bin/python run_e2e.py --hazard landslide
```

Or open the hazard-specific notebook with cwd = `scripts/`.

---

## Related lens documents

- [`flood_nbs_dataset_lens.md`](flood_nbs_dataset_lens.md)
- [`heat_nbs_dataset_lens.md`](heat_nbs_dataset_lens.md)
- [`landslide_nbs_dataset_lens.md`](landslide_nbs_dataset_lens.md)
- [`nbs_recommendation_rules_expert_review.md`](nbs_recommendation_rules_expert_review.md) — **logic-focused brief for NBS expert review** ([ON-5993](https://openearth.atlassian.net/browse/ON-5993))
