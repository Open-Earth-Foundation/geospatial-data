# landslide_risk

Compute screening landslide risk \(R = (H \times E \times V)^{1/3}\) for Minnesota cities.

- **H**: `landslide_hazard` score raster (~90 m)  
- **E / V**: ACS block-group scores from `transformation/acs_ev`  
- E and V are burned onto the landslide hazard grid (constant per block group).

## Run (Plymouth)

```bash
# Prerequisites:
# 1) landslide_hazard → sites/plymouth/data/output/landslide_hazard_score_plymouth_90m.tif
# 2) acs_ev/extract_acs_ev.py --site plymouth

cd /Users/admin/Desktop/OEF/geospatial-data
python transformation/landslide_risk/compute_landslide_risk.py --site plymouth
```

## Outputs (`sites/<city>/data/output/`)

| File | Content |
|------|---------|
| `landslide_risk_score_<city>.tif` | \(R\) on hazard grid |
| `landslide_exposure_score_<city>.tif` | E burned to grid |
| `landslide_vulnerability_score_<city>.tif` | V burned to grid |
| `landslide_risk_score_<city>.gpkg` | Block groups + zonal mean H/E/V/R |
| `map_landslide_risk_score.svg` | Choropleth of BG mean risk |
| `map_landslide_risk_score_grid.svg` | Risk on hazard grid |
| `map_landslide_hazard_grid.svg` | H grid QA |
| `map_landslide_exposure_grid.svg` | E burned grid QA |
| `map_landslide_vulnerability_grid.svg` | V burned grid QA |
| `metadata.json` | Provenance + formula |

## Publish (COG + tiles → S3 → catalog)

```bash
python transformation/landslide_risk/landslide_risk_publish.py \
  --site plymouth --product risk --build

python transformation/landslide_risk/landslide_risk_publish.py \
  --site plymouth --product risk --no-build --upload --write-catalog
```

### S3 layout (Plymouth)

```text
s3://geo-test-api/.../plymouth/climate_hazards/landslides/risk/
  landslide_risk_score_cog.tif
  tiles_visual/  tiles_values/
s3://geo-test-api/.../plymouth/climate_hazards/landslides/vector/
  landslide_risk_score_plymouth.gpkg
```

Catalog id: `plymouth_landslide_risk`.
