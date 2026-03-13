# NOAA VIIRS Night Lights

Transformation pipeline for NOAA VIIRS DNB monthly composites → Porto Alegre clipped raster, COG, and map tiles.

**Release convention:** The release folder is the **dataset version** (e.g. `v1`), not the data collection period. Time period (e.g. 2024) lives in a subdirectory: `release/v1/2024/`.

## Source

**Dataset:** [NOAA VIIRS DNB Monthly V1 VCMSLCFG](https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMSLCFG)  
**Publisher:** NOAA  
**License:** Public domain  
**Band:** `avg_rad` — average DNB radiance (nanoWatts/cm²/sr)

Stray-light corrected monthly composites. Pixel size ~464 m. Data from 2014 to present.

## Inputs

| Input | Description |
|------|-------------|
| GEE ImageCollection | `NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG` |
| Porto Alegre bounds | `[-51.40, -30.42, -50.82, -29.88]` (expanded to cover full boundary) |

## Outputs

| Output | Description |
|-------|-------------|
| `output/poa_nightlights_cog.tif` | Cloud Optimized GeoTIFF |
| `output/tiles_visual/` | Colorized XYZ tiles for map display |
| `output/tiles_values/` | Terrain RGB encoded tiles for hover lookup |
| `output/nightlights_metadata.json` | Encoding metadata for frontend |

## Usage

1. Run `release/v1/2024/transformation.ipynb` (requires `earthengine-api`, GDAL).
2. **Step 1 (GEE):** Exports annual mean composite to Google Drive. Poll task status, then download the GeoTIFF to `release/v1/2024/data/`.
3. **Step 2 (GDAL):** Run the COG + tiles cells. Requires the GeoTIFF in `data/`.
