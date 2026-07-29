# heat_risk

Compute screening heat risk \(R = (H \times E \times V)^{1/3}\) for Minnesota cities.

- **H**: `heat_hazard` score raster  
- **E / V**: ACS block-group scores from `transformation/acs_ev`  
- E and V are burned onto the heat hazard grid (constant per block group).

## Run (Plymouth)

```bash
# Prerequisites:
# 1) heat_hazard → sites/plymouth/data/output/heat_hazard_score_plymouth.tif
# 2) acs_ev/extract_acs_ev.py --site plymouth

cd /Users/admin/Desktop/OEF/geospatial-data
python transformation/heat_risk/compute_heat_risk.py --site plymouth
```

## Outputs (`sites/<city>/data/output/`)

| File | Content |
|------|---------|
| `heat_risk_score_<city>.tif` | \(R\) on hazard grid |
| `heat_exposure_score_<city>.tif` | E burned to grid |
| `heat_vulnerability_score_<city>.tif` | V burned to grid |
| `heat_risk_score_<city>.gpkg` | Block groups + zonal mean H/E/V/R |
| `map_heat_risk_score.svg` | Choropleth of BG mean risk |
| `map_heat_risk_score_grid.svg` | Risk on hazard grid (from GeoTIFF) |
| `map_heat_hazard_grid.svg` | H grid QA |
| `map_heat_exposure_grid.svg` | E burned grid QA |
| `map_heat_vulnerability_grid.svg` | V burned grid QA |
| `metadata.json` | Provenance + formula |

Formula: geometric mean of H, E, V where all three are finite.

## Publish (COG + tiles → S3 → catalog)

Requires GDAL CLI (`gdal_translate`, `gdaldem`, `gdal_calc.py`, `gdal2tiles.py`) and AWS CLI when uploading.

```bash
# 1) Build COG + visual/value tiles; print catalog dry-run (no S3)
python transformation/heat_risk/heat_risk_publish.py \
  --site plymouth --product risk --build

# 2) Upload + write catalog
python transformation/heat_risk/heat_risk_publish.py \
  --site plymouth --product risk --no-build --upload --write-catalog

# Optional E / V on the heat grid (not the flood shared paths)
python transformation/heat_risk/heat_risk_publish.py --site plymouth --product exposure --build
python transformation/heat_risk/heat_risk_publish.py --site plymouth --product vulnerability --build
```

| Flag | Default | Effect |
|------|---------|--------|
| `--build` / `--no-build` | build on | COG + `tiles_visual` / `tiles_values` under `sites/<city>/out/` |
| `--upload` | off | `aws s3 cp` to `geo-test-api` |
| `--write-catalog` | off (dry-run) | Upsert `catalog/datasets.yaml` |
| `--product` | `risk` | `risk` \| `exposure` \| `vulnerability` |

### S3 layout (Plymouth)

```text
s3://geo-test-api/oef_calculation/release/v1/plymouth/climate_hazards/heat/risk/
  heat_risk_score_cog.tif
  tiles_visual/{z}/{x}/{y}.png
  tiles_values/{z}/{x}/{y}.png
s3://geo-test-api/.../plymouth/climate_hazards/heat/vector/
  heat_risk_score_plymouth.gpkg
s3://geo-test-api/.../plymouth/climate_hazards/heat/exposure/   # --product exposure
s3://geo-test-api/.../plymouth/climate_hazards/heat/vulnerability/  # --product vulnerability
```

Catalog ids: `plymouth_heat_risk`, `plymouth_heat_exposure`, `plymouth_heat_vulnerability`.
