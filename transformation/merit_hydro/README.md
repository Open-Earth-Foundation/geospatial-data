# MERIT Hydro

Transformation pipeline for MERIT Hydro (elevation, flow accumulation, HAND) → Porto Alegre clipped rasters, COGs, and map tiles.

**Release convention:** `release/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** MERIT Hydro v1.0.1  
**Publisher:** JAXA/UT  
**License:** CC BY 4.0

## Outputs

| Output | Description |
|-------|-------------|
| `output/` | COGs, tiles, metadata |

## Usage

1. Run notebooks in `release/v1/2024/` (requires `earthengine-api`, GDAL).
2. Color files live in `release/v1/2024/data/`.
