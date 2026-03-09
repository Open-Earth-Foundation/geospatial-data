# transformation

`transformation/` holds scripts that convert Level 0 datasets into analytical outputs (Levels 1-3).

## Typical script responsibilities

- load and validate source data
- reproject and harmonize grids
- clip or mask to target city boundaries
- compute indicators or composite indices
- export outputs (`cog`, `geojson`, `pmtiles`)
- publish artifacts and metadata to S3

## Suggested layout

```text
transformation/
  dem/
  exposure/
  hazard/
  ecosystem/
  decision/
```

## Output artifacts

- raster COGs
- visual PNG tiles (optional)
- vector GeoJSON or PMTiles
- `metadata.json` with provenance and processing information

All processing should remain offline; the platform API serves only precomputed products.
