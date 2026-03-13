# Global Surface Water

Transformation pipeline for JRC Global Surface Water (occurrence, seasonality, transition) → Porto Alegre clipped rasters, COGs, and map tiles.

**Release convention:** `release/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** JRC Global Surface Water v1.4  
**Publisher:** JRC  
**License:** CC BY 4.0

## Outputs

| Output | Description |
|-------|-------------|
| `output/` | COGs, tiles, metadata |

## Usage

1. Run notebooks in `release/v1/2024/` (requires `earthengine-api`, GDAL).
2. Color files live in `release/v1/2024/data/`.
