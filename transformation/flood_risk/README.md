# flood_risk

Compute screening flood risk \(R = (H \times E \times V)^{1/3}\) for Minnesota cities.

- **H**: `flood_hazard` IDW score raster  
- **E / V**: ACS block-group scores from `transformation/acs_ev`  
- E and V are burned onto the hazard grid (constant per block group), same pattern as POA bairros.

## Run (Plymouth)

```bash
# Prerequisites:
# 1) flood_hazard_score_v2.ipynb → sites/plymouth/data/output/flood_hazard_score_idw_*.tif
# 2) acs_ev/extract_acs_ev.py --site plymouth

cd /Users/admin/Desktop/OEF/geospatial-data
python transformation/flood_risk/compute_flood_risk.py --site plymouth
```

## Outputs (`sites/<city>/data/output/`)

| File | Content |
|------|---------|
| `flood_risk_score_<city>.tif` | \(R\) on hazard grid |
| `flood_exposure_score_<city>.tif` | E burned to grid |
| `flood_vulnerability_score_<city>.tif` | V burned to grid |
| `flood_risk_score_<city>.gpkg` | Block groups + zonal mean H/E/V/R |
| `map_flood_risk_score.svg` | Choropleth of BG mean risk |
| `map_flood_risk_score_grid.svg` | Risk on hazard grid (from GeoTIFF) |
| `map_flood_hazard_grid.svg` | H grid QA |
| `map_flood_exposure_grid.svg` | E burned grid QA |
| `map_flood_vulnerability_grid.svg` | V burned grid QA |
| `metadata.json` | Provenance + formula |

Formula matches catalog `poa_flood_risk`: geometric mean of H, E, V where all three are finite.

## Publish (COG + tiles → S3 → catalog)

Requires GDAL CLI (`gdal_translate`, `gdaldem`, `gdal_calc.py`, `gdal2tiles.py`) and AWS CLI when uploading.

```bash
# 1) Build COG + visual/value tiles; print catalog dry-run (no S3)
python transformation/flood_risk/flood_risk_publish.py \
  --site plymouth --product risk --build

# 2) Upload + write catalog
python transformation/flood_risk/flood_risk_publish.py \
  --site plymouth --product risk --no-build --upload --write-catalog

# Optional shared E / V (same helper)
python transformation/flood_risk/flood_risk_publish.py --site plymouth --product exposure --build
python transformation/flood_risk/flood_risk_publish.py --site plymouth --product vulnerability --build
```

| Flag | Default | Effect |
|------|---------|--------|
| `--build` / `--no-build` | build on | COG + `tiles_visual` / `tiles_values` under `sites/<city>/out/` |
| `--upload` | off | `aws s3 cp` to `geo-test-api` |
| `--write-catalog` | off (dry-run) | Upsert `catalog/datasets.yaml` |
| `--product` | `risk` | `risk` \| `exposure` \| `vulnerability` |

### S3 layout (Plymouth)

```text
s3://geo-test-api/oef_calculation/release/v1/plymouth/climate_hazards/floods/risk/
  flood_risk_score_cog.tif
  tiles_visual/{z}/{x}/{y}.png
  tiles_values/{z}/{x}/{y}.png
s3://geo-test-api/.../plymouth/climate_hazards/floods/vector/
  flood_risk_score_plymouth.gpkg
s3://geo-test-api/.../plymouth/shared/exposure/   # --product exposure
s3://geo-test-api/.../plymouth/shared/vulnerability/  # --product vulnerability
```

Catalog ids: `plymouth_flood_risk`, `plymouth_exposure`, `plymouth_vulnerability`.
