# transformation

`transformation/` holds scripts that convert Level 0 datasets into analytical outputs (Levels 1-3).

## Score transformations (Level 2–3)

Hazard/risk score pipelines (e.g. `flood_hazard`, `heat_hazard`) use:

```text
transformation/{score}/
├── config/sites/{city_slug}.yaml   # one YAML per city
├── sites/{city_slug}/              # local runtime data (mostly gitignored)
└── ... notebooks / scripts
```

Default model parameters live in `models/{score}/`. See `docs/cougar-migration.md`.

## NbS mechanism screening (N10)

Rule-based **grid** screening for dominant Nature-based Solutions mechanism types
(flood / heat / landslide). Unlike hazard **score** modules above, `nbs_screening/`
is multi-hazard: one shared config index per city, with hazard-specific CLIs and
runtime data under each hazard submodule.

```text
transformation/nbs_screening/
├── site_config.py, catalog_layers.py, grid_screening.py   # shared screening core
├── config/sites/{city_slug}.yaml                          # multi-hazard layer catalog
├── extract_common.py                                      # shared input-orchestrator helpers
├── flood/          compute / publish / batch CLIs + sites/{city_slug}/
├── heat/           extract + (planned compute/publish) + sites/{city_slug}/
└── landslide/      extract + (planned compute/publish) + sites/{city_slug}/
```

Per-hazard runtime layout (same flat pattern as `flood_hazard/`):

```text
transformation/nbs_screening/{hazard}/sites/{city_slug}/
├── data/input/     OSM waterways (flood), extracted catalog rasters
├── data/output/    mechanism GeoTIFF, GeoJSON, QA SVG, metadata.json
└── out/            COG + tile publish staging
```

City boundaries are shared with hazard scores:
`transformation/flood_hazard/sites/{city_slug}/boundary/site.geojson`.

Typical workflow per city:

1. **Input layers** — `{hazard}/extract_mechanism_inputs.py` (GEE extractors, OSM, DEM diagnostics)
2. **Mechanism grid** — `{hazard}/compute_mechanism.py` (requires upstream hazard score COGs in site YAML)
3. **Publish** — `{hazard}/publish_mechanism.py` (COG/tiles + catalog)
4. **Orchestrators** — `flood/run_pipeline.py`, `flood/batch_mechanism.py` for end-to-end / batch

Layer readiness: `python transformation/nbs_screening/check_nbs_layers.py --site {city} --hazard flood`

Full CLI reference, Minnesota pilot, and roadmap: `transformation/nbs_screening/README.md`.

## Directory convention

Use `release/{version}/{period}/` for each dataset:

```text
transformation/{dataset_slug}/
├── README.md
└── release/
    └── {version}/           # e.g. v1, v2 (dataset/transformation release)
        └── {period}/        # e.g. 2024 (data collection period)
            ├── *.ipynb      # transformation notebooks
            ├── data/        # color files, source GeoTIFFs
            └── output/      # COGs, tiles, metadata.json
```

- **version** = dataset release (v1, v2), not the time period
- **period** = data collection period (year or date)
- Run notebooks from `release/{version}/{period}/`; they expect `data/` and write to `output/`

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
