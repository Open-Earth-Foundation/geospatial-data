---
name: s3-upload-commands
description: Generates aws s3 sync and cp commands to upload geospatial transformation outputs to geo-test-api. Use when the user asks for S3 upload commands, wants to upload a dataset to S3, or needs commands to deploy transformation outputs. Does not run commands—outputs them for the user to execute.
---

# S3 Upload Commands

Generates `aws s3` commands to upload transformation outputs to `s3://geo-test-api/`. All data is for Porto Alegre; the S3 path always ends with `porto_alegre/`.

**Do not run the commands**—output them in a copyable block for the user.

---

## Workflow

1. **Resolve release path**  
   From `transformation/{dataset_id}/`, find `release/{version}/{period}/` (e.g. `release/v1/2024` or `release/2024-10-01`).

2. **Inspect output folder**  
   List `transformation/{dataset_id}/release/{version}/{period}/output/` to see what exists.

3. **Generate commands**  
   Use the conventions below. Base S3 path:
   ```
   s3://geo-test-api/{dataset_id}/release/{version}/{period}/porto_alegre/
   ```

---

## Command conventions

### Tile directories (sync)

For any `output/tiles_*/` or `output/tiles_visual/`, `output/tiles_values/`:

```bash
aws s3 sync output/{tiles_dir}/ s3://geo-test-api/{dataset_id}/release/{version}/{period}/porto_alegre/{tiles_dir}/ --content-type "image/png"
```

Examples: `tiles_visual`, `tiles_values`, `tiles_pvout`, `tiles_pvout_values`.

### Single files (cp)

For COGs, metadata, GeoJSON:

```bash
aws s3 cp output/{filename} s3://geo-test-api/{dataset_id}/release/{version}/{period}/porto_alegre/
```

Examples: `*_cog.tif`, `*_metadata.json`, `*.geojson`, `shapes.geojson`, `stops.geojson`.

### Working directory

Prepend the `cd` command so paths resolve correctly:

```bash
cd /path/to/geospatial-data/transformation/{dataset_id}/release/{version}/{period}
```

Use the workspace root to build the path (e.g. `{workspace}/transformation/modis_ndvi/release/v1/2024`).

---

## Output format

Return a single copyable block:

```bash
cd transformation/{dataset_id}/release/{version}/{period}

# Tiles
aws s3 sync output/tiles_visual/ s3://geo-test-api/{dataset_id}/release/{version}/{period}/porto_alegre/tiles_visual/ --content-type "image/png"
aws s3 sync output/tiles_values/ s3://geo-test-api/{dataset_id}/release/{version}/{period}/porto_alegre/tiles_values/ --content-type "image/png"

# Single files
aws s3 cp output/ndvi_cog.tif s3://geo-test-api/{dataset_id}/release/{version}/{period}/porto_alegre/
aws s3 cp output/ndvi_metadata.json s3://geo-test-api/{dataset_id}/release/{version}/{period}/porto_alegre/
```

---

## Dataset-specific notes

| Dataset | Release path | Tile dirs | Single files |
|---------|--------------|-----------|--------------|
| modis_ndvi | v1/2024 | tiles_visual, tiles_values | ndvi_cog.tif, ndvi_metadata.json |
| copernicus_emsn194 | v1/2024 | tiles_visual, tiles_values | maxwaterdepth_cog.tif, maxwaterdepth_metadata.json |
| noaa_viirs_nightlights | v1/2024 | tiles_visual, tiles_values | poa_nightlights_cog.tif, nightlights_metadata.json |
| global_solar_atlas | v2 | tiles_pvout, tiles_pvout_values | poa_PVOUT_cog.tif, pvout_metadata.json |
| poa_gtfs | 2024-10-01 | — | shapes.geojson, stops.geojson, routes.geojson |

When in doubt, list the `output/` folder and generate commands for each item.
