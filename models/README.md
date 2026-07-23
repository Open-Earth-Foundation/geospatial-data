# models

Model artifacts and configuration used to produce Level 2–3 analytical layers (hazards, exposure scores, composite risk, NbS opportunity zones).

## Purpose

- Store trained model weights, configs, and model cards
- Document how composite indices and scoring models are defined
- Version model artifacts alongside transformations for reproducibility

## How models fit in the pipeline

```
Level 0 (raw data) → transformation/ → Level 1 (indicators)
                                          ↓
Level 2–3 (composite layers) ← models/ ←──┘
```

- **Transformations** produce Level 1 indicators (slope, flow accumulation, canopy cover, etc.).
- **Models** consume those indicators (and sometimes Level 0 data) to produce Level 2–3 layers.
- Model outputs are published via the same transformation pipeline and S3.

## Directory convention

Use one subfolder per layer that has a model:

```text
models/
├── README.md
├── flood_hazard/
│   ├── README.md
│   ├── model_card.md      # purpose, inputs, outputs, limitations
│   ├── config.yaml        # weights, thresholds, formula
│   └── v1/                # optional: versioned artifacts
├── heat_hazard/
│   └── ...
├── nbs_opportunity_zones/
├── nbs_flood_mechanism_type/
├── nbs_heat_mechanism_type/
├── nbs_landslide_mechanism_type/
└── ...
```

- **model_card.md** — human-readable description of the model
- **config.yaml** — parameters, weights, thresholds used at inference
- **v1/, v2/** — versioned model weights or serialized artifacts (optional)
- **NbS docs** (matrices, rules, recommendation notes) live under `models/nbs_*`

## Site-specific runtime config

Default model parameters stay in `models/{layer_id}/config.yaml`.

Per-city paths, bbox, season, and filenames live next to the score transformation:

```text
transformation/{score}/config/sites/{city_slug}.yaml
```

Use **city-level** slugs only (e.g. `porto_alegre`, `minneapolis`), not statewide regions.

See `docs/cougar-migration.md` for the migration plan and PR sequence.

## Layer IDs

Model folder names should match `layer_id` in `collections/layers.yaml` (e.g. `flood_hazard`, `heat_hazard`, `nbs_opportunity_zones`).
