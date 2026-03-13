# Hansen Tree Cover & Loss

Transformation pipeline for Hansen Global Forest Change (tree cover, loss) → Porto Alegre clipped rasters, COGs, and map tiles.

**Release convention:** `release/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** Hansen Global Forest Change v1.12  
**Publisher:** UMD/Google  
**License:** CC BY 4.0

## Outputs

| Output | Description |
|-------|-------------|
| `output/` | COGs, tiles, metadata |

## Usage

1. Run notebooks in `release/v1/2024/` (requires `earthengine-api`, GDAL).
2. Color files live in `release/v1/2024/data/`.
