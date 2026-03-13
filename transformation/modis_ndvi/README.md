# MODIS NDVI

Transformation pipeline for MODIS MOD13Q1 NDVI → Porto Alegre clipped raster, COG, and map tiles.

**Release convention:** `release/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** [MODIS/061/MOD13Q1](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1)  
**Publisher:** NASA LP DAAC / USGS EROS  
**License:** No restrictions on use, sale, or redistribution  
**Resolution:** 250 m  
**Temporal:** 16-day composites

## Outputs

| Output | Description |
|-------|-------------|
| `output/ndvi_cog.tif` | Cloud Optimized GeoTIFF (Web Mercator) |
| `output/tiles_visual/` | XYZ tiles for map display |
| `output/tiles_values/` | Terrain RGB value tiles for hover lookup |
| `output/ndvi_metadata.json` | Encoding metadata (scale, offset, unit) |

## Usage

1. Run the GEE export cell in `transformation.ipynb` (requires `earthengine-api`, project `citycatalyst`).
2. Download the GeoTIFF from Google Drive to `release/v1/2024/data/poa_modis_ndvi_2024.tif`.
3. Run the GDAL cells to produce COG and tiles.
4. Outputs are written to `output/`.

## S3 upload

```bash
cd release/v1/2024
aws s3 sync output/tiles_visual/ s3://geo-test-api/modis_ndvi/release/v1/2024/tiles_visual/ --content-type "image/png"
aws s3 sync output/tiles_values/ s3://geo-test-api/modis_ndvi/release/v1/2024/tiles_values/ --content-type "image/png"
aws s3 cp output/ndvi_cog.tif s3://geo-test-api/modis_ndvi/release/v1/2024/
aws s3 cp output/ndvi_metadata.json s3://geo-test-api/modis_ndvi/release/v1/2024/
```
