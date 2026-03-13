# Copernicus EMSN194

Transformation pipeline for Copernicus EMS Risk and Recovery Mapping (EMSN194) — flood delineation and impact assessment for Porto Alegre, Brazil.

**Release convention:** `release/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** [EMSN194 - Risk and Recovery Mapping](https://mapping.emergency.copernicus.eu/activations/EMSN194/)  
**Publisher:** Copernicus Emergency Management Service (CEMS)  
**Activation:** 28 May 2024  
**Event:** Flood in Porto Alegre, Rio Grande do Sul State, Brazil  
**Products:** Delineation products and impact assessments

## Outputs

| Output | Description |
|-------|-------------|
| `output/maxwaterdepth_cog.tif` | Cloud Optimized GeoTIFF (Web Mercator) |
| `output/tiles_visual/` | XYZ tiles for map display |
| `output/tiles_values/` | Terrain RGB value tiles for hover lookup |
| `output/maxwaterdepth_metadata.json` | Encoding metadata (scale, offset, unit) |

## Usage

1. Download products from the [EMSN194 activation page](https://mapping.emergency.copernicus.eu/activations/EMSN194/).
2. Place `EMSN194_STD_AOI01_P06TMFL_MaxWaterDepth_v01.tif` in `release/v1/2024/data/`.
3. Run `transformation.ipynb` from `release/v1/2024/` (requires GDAL).
4. Outputs are written to `output/`.
