---
name: add-catalog-entry
description: Adds a dataset entry to catalog/datasets.yaml in the geospatial-data repository. Use when the user asks to add a dataset to the catalog, create a catalog entry, or register a new dataset in datasets.yaml.
---

# Add Catalog Entry

Adds a new dataset entry to `catalog/datasets.yaml`. Use when a transformation exists (or will exist) and you need to register it in the catalog for discovery and API integration.

## When to use

- User asks to add a dataset to the catalog
- A new transformation pipeline exists and needs a catalog entry
- Registering a dataset for the first time

## Dataset slug naming

Use **snake_case**. Prefer `{source}_{descriptor}` or `{source}_{product}`:

| Pattern | Examples |
|---------|----------|
| Publisher/source + descriptor | `ghsl_degree_urbanization`, `ghsl_built_up`, `jrc_global_surface_water` |
| Publisher + product name | `copernicus_dem`, `merit_hydro`, `noaa_viirs_nightlights` |
| Product name (well-known) | `dynamic_world`, `global_solar_atlas` |
| Geographic + product | `poa_gtfs`, `br_ibge` |

- **Source abbreviations:** `ghsl`, `jrc`, `noaa`, `copernicus`, `hansen`, `merit`
- **Avoid:** resolution in slug (e.g. prefer `copernicus_dem` not `dem_copernicus_30m`)

---

## Entry template

Add to `catalog/datasets.yaml` under the `datasets:` list. **Append new entries to the end of the document** (after the last dataset entry).

### Raster (numeric)

```yaml
  - dataset_id: {slug}
    dataset_name: {Human Name}
    publisher: {Publisher}
    license: {License}
    resolution: {e.g. 100m, 30m}
    crs: EPSG:3857
    access_type: gee   # or manual_download
    source_url: {URL}
    dataset_type: {built_up, land_cover, night_lights, solar, elevation, etc.}
    type: numeric_raster
    data_quality:
      temporal_coverage: "..."
      accuracy: "..."
      limitations: "..."
    value_encoding:
      type: terrain_rgb   # or rgb_packed
      scale: 0.1
      offset: 0.0
      unit: "..."
      decode_formula: "value = (R * 256 * 256 + G * 256 + B) * scale + offset"
    assets:
      visual_tiles:
        url_template: https://geo-test-api.s3.us-east-1.amazonaws.com/{slug}/release/{version}/{period}/tiles_visual/{z}/{x}/{y}.png
      value_tiles:
        url_template: https://geo-test-api.s3.us-east-1.amazonaws.com/{slug}/release/{version}/{period}/tiles_values/{z}/{x}/{y}.png
      download:
        cog_url: https://geo-test-api.s3.us-east-1.amazonaws.com/{slug}/release/{version}/{period}/{output}_cog.tif
      metadata:
        url: []   # or URL if metadata.json exists
    description: |
      ...
```

### Raster (categorical)

```yaml
  - dataset_id: {slug}
    dataset_name: {Human Name}
    publisher: {Publisher}
    license: {License}
    resolution: {e.g. 10m}
    access_type: gee
    source_url: {URL}
    dataset_type: land_cover
    type: categorical_raster
    value_encoding:
      type: class_lookup
      classes:
        0: { name: Water, color: "#419BDF" }
        1: { name: Trees, color: "#397D49" }
        2: { name: Grass, color: "#88B053" }
        # ... value → { name, color }
    assets:
      visual_tiles:
        url_template: []
      value_tiles:
        url_template: []
      download:
        cog_url: []
      metadata:
        url: []
    description: |
      ...
```

**Categorical value encoding:** No formula — pixel value (or R channel if value tiles encode R=class_id) is looked up in `classes` to get name and color. Use `type: class_lookup` and a `classes` map.

### Vector

```yaml
  - dataset_id: {slug}
    dataset_name: {Human Name}
    publisher: {Publisher}
    license: {License}
    resolution: vector
    crs: EPSG:4326
    access_type: manual_download   # or public_api
    source_url: {URL}
    dataset_type: {transport, census, buildings, etc.}
    type: vector
    assets:
      {asset_name}:   # e.g. bus_routes, shapes, stops
        url_template: https://geo-test-api.s3.us-east-1.amazonaws.com/...
    description: |
      ...
```

---

## Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `dataset_id` | Yes | snake_case slug |
| `dataset_name` | Yes | Human-readable name |
| `publisher` | Yes | |
| `license` | Yes | |
| `resolution` | Yes | e.g. `100m`, `30m`, `vector` |
| `crs` | Raster | `EPSG:3857` for web tiles |
| `access_type` | Yes | `gee`, `manual_download`, `public_api`, `internal_storage` |
| `source_url` | Yes | GEE catalog URL or source page |
| `dataset_type` | Yes | `land_cover`, `elevation`, `transport`, `census`, etc. |
| `type` | Yes | `numeric_raster`, `categorical_raster`, `vector` |
| `data_quality` | Optional | `temporal_coverage`, `accuracy`, `limitations` |
| `value_encoding` | Raster | Numeric: `scale`, `offset`, `unit`, `decode_formula`. Categorical: `type: class_lookup`, `classes` (value → { name, color }) |
| `assets` | Yes | Use `[]` for URLs not yet deployed |
| `description` | Yes | One or two sentences |

---

## Value encoding: numeric vs categorical

| Type | `value_encoding` | Decode |
|------|------------------|--------|
| **Numeric** | `terrain_rgb` or `rgb_packed` with `scale`, `offset`, `decode_formula` | Formula: `value = (R*256² + G*256 + B) * scale + offset` |
| **Categorical** | `class_lookup` with `classes` map | Dictionary lookup: pixel value → `classes[value]` → `{ name, color }` |

## Asset URLs

- **Deployed:** Use full S3 URLs. Pattern: `https://geo-test-api.s3.us-east-1.amazonaws.com/{dataset_id}/release/{version}/{period}/...`
- **Not yet deployed:** Use `url_template: []` or `cog_url: []` so the catalog is valid but apps know assets are pending.

---

## Checklist

- [ ] Use correct `dataset_id` (snake_case, matches naming pattern)
- [ ] Match `type` to data (numeric_raster, categorical_raster, vector)
- [ ] Add `value_encoding` for rasters: numeric (formula) or categorical (class_lookup)
- [ ] Use `[]` for assets not yet on S3
- [ ] Append new entry to the end of the document
