# Flood Mechanism Type — Model Card

## Purpose

Dominant flood mechanism type per cell for NbS screening and typology recommendation.

Canonical executable code: `transformation/nbs_screening/` (`nbs_rules.py`, `grid_screening.py`, site-query notebooks).

## Status

Migrated from Cougar NbS E2E into geospatial-data (PR-H). Thresholds and scoring live in `nbs_rules.py`; seed defaults in `config.yaml`.

## Methodology references

- `transformation/nbs_screening/docs/poa_mechanism_type_layer.md`
- `transformation/nbs_screening/docs/flood_nbs_dataset_lens.md`
- `transformation/nbs_screening/docs/nbs_mechanism_dataset_matrix.md`
- `transformation/nbs_screening/docs/recommended-datasets.md`

## Multi-city note

Published S3 catalog URLs in `catalog_layers.py` are currently Porto Alegre–centric.
For Minnesota cities, prefer local COGs under `transformation/{flood,heat,landslide}_hazard/sites/<city>/`
and DEM diagnostics from `relative_elevation_depression_from_dem.ipynb`.
Exposure / vulnerability / risk layers are optional until shared E/V is migrated.
