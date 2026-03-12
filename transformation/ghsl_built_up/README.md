# GHSL Built-Up

Transformation pipeline for GHSL Built-Up Settlement Grid → Porto Alegre clipped raster, COG, and map tiles.

**Release convention:** `releases/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** GHSL Built-Up P2023A  
**Publisher:** JRC  
**License:** CC BY 4.0

## Outputs

| Output | Description |
|-------|-------------|
| `output/` | COGs, tiles, metadata |

## Usage

1. Run notebooks in `releases/v1/2024/` (requires `earthengine-api`, GDAL).
2. Color files live in `releases/v1/2024/data/`.
