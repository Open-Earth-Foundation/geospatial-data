# Copernicus DEM

Transformation pipeline for Copernicus DEM GLO-30 → Porto Alegre clipped raster, COG, and map tiles.

**Release convention:** `releases/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** Copernicus DEM GLO-30  
**Publisher:** Copernicus  
**License:** Copernicus License

## Outputs

| Output | Description |
|-------|-------------|
| `output/` | COGs, tiles, metadata |

## Usage

1. Run notebooks in `releases/v1/2024/` (requires `earthengine-api`, GDAL).
2. Color files live in `releases/v1/2024/data/`.
