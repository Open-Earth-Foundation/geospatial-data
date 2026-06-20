# JRC Global River Flood Hazard Maps

Transformation pipeline for **JRC Global River Flood Hazard Maps Version 2.1** to produce Porto Alegre-clipped rasters, COGs, and web map tiles.

## Source

**Dataset:** JRC Global River Flood Hazard Maps Version 2.1  
**Earth Engine collection:** `ee.ImageCollection("JRC/CEMS_GLOFAS/FloodHazard/v2_1")`  
**Publisher:** JRC  
**License:** CC BY 4.0

### Bands used

- `RP10_depth`
- `RP50_depth`
- `RP100_depth`
- `RP500_depth`

## Release layout

- Notebook: `release/v1/jrc_global_river_flood_hazard_maps_V2_1.ipynb`
- Input/aux files: `release/v1/data/`
- Generated outputs: `release/v1/out/jrc_global_river_flood_hazard_maps_v2_1/{band}/`

## Outputs

For each band (`rp10_depth`, `rp50_depth`, `rp100_depth`, `rp500_depth`):

- COG raster
- Visual tiles (`tiles_visual/`) from color-relief styling
- Value tiles (`tiles_values/`) preserving depth values

## Usage

1. Open and run `release/v1/jrc_global_river_flood_hazard_maps_V2_1.ipynb` (requires `earthengine-api` and GDAL tools).
2. Place exported GeoTIFFs in `release/v1/data/` with names matching:
   - `poa_jrc_global_river_flood_hazard_maps_v2_1_RP10_depth_30m.tif`
   - `poa_jrc_global_river_flood_hazard_maps_v2_1_RP50_depth_30m.tif`
   - `poa_jrc_global_river_flood_hazard_maps_v2_1_RP100_depth_30m.tif`
   - `poa_jrc_global_river_flood_hazard_maps_v2_1_RP500_depth_30m.tif`
3. Keep color files in `release/v1/data/`:
   - `flood_hazard_rp10_depth_colors.txt`
   - `flood_hazard_rp50_depth_colors.txt`
   - `flood_hazard_rp100_depth_colors.txt`
   - `flood_hazard_rp500_depth_colors.txt`
