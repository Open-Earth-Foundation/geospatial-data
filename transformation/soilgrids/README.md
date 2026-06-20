# SoilGrids

Transformation pipeline for SoilGrids World Reference Base (2006) Soil Groups (MostProbable) -> Porto Alegre clipped raster, COG, and map tiles.

**Release convention:** `release/{version}/` — see `transformation/README.md`.

## Source

**Dataset:** SoilGrids WRB MostProbable (World Reference Base 2006 Soil Groups)  
**Publisher:** ISRIC - World Soil Information  
**License:** CC BY 4.0

## Outputs

| Output | Description |
|-------|-------------|
| `out/world_reference_base_2006_soil_groups_2006/` | COG plus `tiles_visual/` and `tiles_values/` |

## Usage

1. Run `release/2006/world_reference_base_2006_soil_groups.ipynb` (requires GDAL CLI tools).
2. Input raster should be at `release/2006/data/world_reference_base_2006_soil_groups.tif`.
3. Keep color files in `release/2006/data/`:
   - `world_reference_base_2006_soil_groups_colors.txt`
   - `world_reference_base_2006_soil_groups_value_encoding_colors.txt`
