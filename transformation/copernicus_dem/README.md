# Copernicus DEM

Transformation pipeline for Copernicus DEM GLO-30 → city clipped rasters, COG, and map tiles.

**Release convention:** `release/{version}/{period}/` — see `transformation/README.md`.

## Source

**Dataset:** Copernicus DEM GLO-30  
**Publisher:** Copernicus  
**License:** Copernicus License

## CLIs

| Script | Purpose |
|--------|---------|
| `extract_slope.py` | GEE export → slope (deg) in `landslide_hazard/.../data/input/` |
| `compute_dem_diagnostics.py` | Relative elevation + depression mask/depth from local DEM |

### DEM diagnostics (NBS low-lying screening)

```bash
python transformation/copernicus_dem/compute_dem_diagnostics.py --site richfield
python transformation/copernicus_dem/compute_dem_diagnostics.py --all-configured
python transformation/copernicus_dem/compute_dem_diagnostics.py --site edina --export-dem
```

Reads `flood_hazard/sites/<site>/data/input/<prefix>_dem_glo30_30m.tif`, writes:

- `<prefix>_relative_elevation_30m.tif` (0–1, 1 = lowest)
- `<prefix>_depression_mask_30m.tif` (0/1)
- `<prefix>_depression_depth_30m.tif` (m)

to `flood_hazard/sites/<site>/data/output/`.

## Notebooks

Legacy interactive workflow: `release/v1/relative_elevation_depression_from_dem.ipynb`.

## Outputs

| Output | Description |
|-------|-------------|
| `output/` | COGs, tiles, metadata (POA publish path) |
