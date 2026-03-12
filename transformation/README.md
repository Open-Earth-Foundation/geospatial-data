# transformation

`transformation/` holds scripts that convert Level 0 datasets into analytical outputs (Levels 1-3).

## Directory convention

Use `releases/{version}/{period}/` for each dataset:

```text
transformation/{dataset_slug}/
├── README.md
└── releases/
    └── {version}/           # e.g. v1, v2 (dataset/transformation release)
        └── {period}/        # e.g. 2024 (data collection period)
            ├── *.ipynb      # transformation notebooks
            ├── data/        # color files, source GeoTIFFs
            └── output/      # COGs, tiles, metadata.json
```

- **version** = dataset release (v1, v2), not the time period
- **period** = data collection period (year or date)
- Run notebooks from `releases/{version}/{period}/`; they expect `data/` and write to `output/`

## Typical script responsibilities

- load and validate source data
- reproject and harmonize grids
- clip or mask to target city boundaries
- compute indicators or composite indices
- export outputs (`cog`, `geojson`, `pmtiles`)
- publish artifacts and metadata to S3


## Output artifacts

- raster COGs
- visual PNG tiles (optional)
- vector GeoJSON or PMTiles
- `metadata.json` with provenance and processing information

All processing should remain offline; the platform API serves only precomputed products.
