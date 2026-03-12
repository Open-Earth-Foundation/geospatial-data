---
name: add-geospatial-dataset
description: Adds a new dataset to the geospatial-data repository with transformation pipeline, catalog entry, and collection. Use when adding a new GEE ImageCollection, raster, or vector dataset, or when the user asks to create a transformation, add a dataset to the catalog, or generate COGs and tiles.
---

# Add Geospatial Dataset

Adds a new dataset to geospatial-data: transformation folder, pipeline, catalog entry, and collection. Supports GEE ImageCollections, manual-download rasters, and vector sources.

## Checklist

Track progress when adding a dataset:

- [ ] Create transformation folder with README and notebook
- [ ] Implement pipeline (GEE export and/or GDAL)
- [ ] Add catalog entry to `catalog/datasets.yaml`
- [ ] Add dataset to `collections/collections.yaml`
- [ ] Document in transformation README

---

## 1. Folder structure

```
transformation/{dataset_slug}/
├── README.md
└── releases/{version}/{period}/
    ├── transformation.ipynb
    ├── data/
    │   ├── {layer}_visual_colors.txt
    │   └── {layer}_value_encoding_colors.txt   # if numeric raster
    └── output/
```

- **dataset_slug**: snake_case (e.g. `noaa_viirs_nightlights`)
- **version**: dataset release (e.g. `v1`, `v2`)
- **period**: data collection period (e.g. `2024`)

Release = version, not time period. Time period lives in the subdir.

---

## 2. GEE ImageCollection workflow

For sources like `ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG")`:

1. **Export from GEE** — filter bounds, filter date, reduce (mean/mode), select band, export to Drive:

```python
poa = ee.Geometry.Rectangle([minLon, minLat, maxLon, maxLat])
img = (ee.ImageCollection("...")
    .filterBounds(poa)
    .filterDate("2024-01-01", "2025-01-01")
    .select("band_name")
    .mean()
    .clip(poa)
    .reproject(crs="EPSG:3857", scale=500))

task = ee.batch.Export.image.toDrive(
    image=img, description="...", folder="gee_exports",
    fileNamePrefix="...", region=poa, scale=500, crs="EPSG:3857",
    maxPixels=1e13, fileFormat="GeoTIFF")
task.start()
```

2. Download GeoTIFF from Drive to `data/`
3. Run GDAL pipeline (Step 3)

Reference: `transformation/land_cover/dynamic_world_10m_v1.ipynb`, `meed/test-api/geo-data.ipynb`

---

## 3. GDAL pipeline (COG + tiles)

For any GeoTIFF producing web map tiles:

**3a. Reproject** (if not EPSG:3857):
```bash
gdalwarp -t_srs EPSG:3857 -r near input.tif input_3857.tif
```

**3b. Convert to COG**:
```bash
gdal_translate -of COG input_3857.tif output_cog.tif \
  -co COMPRESS=DEFLATE -co OVERVIEWS=AUTO \
  -co RESAMPLING=AVERAGE   # numeric
  # -co RESAMPLING=NEAREST  # categorical
```

**3c. Colorize for visual tiles**:
```bash
gdaldem color-relief output_cog.tif colors.txt colorized.tif
```

**3d. Generate XYZ tiles**:
```bash
gdal2tiles.py -r near -z 8-15 --xyz -w none colorized.tif output/tiles_visual/
```

**3e. Value tiles** (for hover lookup):
- **Numeric (Terrain RGB)**: Create value-encoding colors file. `encoded = round((value - offset) / scale)` → R,G,B. Run `gdaldem color-relief` then `gdal2tiles.py` on that output.
- **Categorical**: R=class_id, G=0, B=0.

**3f. Metadata**: Write `metadata.json` with `encoding` (scale, offset, unit, decode_formula) for numeric rasters.

Reference: `transformation/global_solar_atlas/v2/raster_transformation.ipynb`

---

## 4. Catalog entry

Add to `catalog/datasets.yaml`:

```yaml
- dataset_id: {slug}
  dataset_name: {Human Name}
  publisher: {Publisher}
  license: {License}
  resolution: {e.g. 500m, vector}
  crs: EPSG:3857   # or EPSG:4326
  access_type: gee
  source_url: {GEE catalog URL}
  dataset_type: {night_lights, land_cover, solar, etc.}
  type: numeric_raster   # or categorical_raster, vector
  data_quality:
    temporal_coverage: "..."
    accuracy: "..."
    limitations: "..."
  value_encoding:     # only for numeric rasters
    type: terrain_rgb
    scale: 0.1
    offset: 0.0
    unit: "nW/cm²/sr"
    decode_formula: "value = (R * 256 * 256 + G * 256 + B) * scale + offset"
  assets:
    visual_tiles:
      url_template: https://geo-test-api.s3.../tiles_visual/{z}/{x}/{y}.png
    value_tiles:
      url_template: https://geo-test-api.s3.../tiles_values/{z}/{x}/{y}.png
    download:
      cog_url: https://geo-test-api.s3.../output_cog.tif
    metadata:
      url: https://geo-test-api.s3.../metadata.json
  description: |
    ...
```

---

## 5. Collection entry

Add dataset to `collections/collections.yaml` under the appropriate category:

```yaml
- id: night_lights
  name: Night lights
  datasets:
    - noaa_viirs_nightlights
```

Create a new collection if needed.

---

## 6. S3 upload

```bash
aws s3 sync output/tiles_values/ s3://geo-test-api/{dataset_slug}/release/{version}/{period}/tiles_values/ --content-type "image/png"
aws s3 sync output/tiles_visual/ s3://geo-test-api/{dataset_slug}/release/{version}/{period}/tiles_visual/ --content-type "image/png"
aws s3 cp output/cog.tif s3://geo-test-api/{dataset_slug}/release/{version}/{period}/
aws s3 cp output/metadata.json s3://geo-test-api/{dataset_slug}/release/{version}/{period}/
```

Use `aws s3 cp` for single files, `aws s3 sync` for directories.
