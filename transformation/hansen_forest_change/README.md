# Hansen Global Forest Change

Site-scoped export of Hansen tree cover 2000 for NBS mechanism screening.

## Source

**Dataset:** Hansen Global Forest Change v1.12 (2024 release)  
**GEE:** `UMD/hansen/global_forest_change_2024_v1_12` · band `treecover2000` (0–100%)

## CLI (D6)

Export to paths referenced in `nbs_screening/config/sites/{city}.yaml`:

```bash
python transformation/hansen_forest_change/extract_treecover2000.py --site richfield
python transformation/hansen_forest_change/extract_treecover2000.py --country "United States"
python transformation/hansen_forest_change/extract_treecover2000.py --site richfield --dry-run
```

**Output:** `sites/{site}/data/output/{prefix}_hansen_treecover2000_30m.tif`  
**QA SVGs:** `sites/{site}/data/intermediate/qa_inputs/`

## NBS usage

Heat and landslide grid screening use `treecover2000_mean` from this layer.

## Notebooks

Legacy Porto Alegre workflow: `release/v1/Hansen_treecover2000_30m_v1_12.ipynb`
