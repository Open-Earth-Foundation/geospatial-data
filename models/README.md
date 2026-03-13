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
│   ├── model_card.md      # purpose, inputs, outputs, limitations
│   ├── config.yaml        # weights, thresholds, formula
│   └── v1/
│       └── weights.pt     # optional: serialized model
├── composite_risk/
│   └── ...
└── nbs_opportunity_zones/
    └── ...
```

- **model_card.md** — human-readable description of the model
- **config.yaml** — parameters, weights, thresholds used at inference
- **v1/, v2/** — versioned model weights or serialized artifacts (optional)

## Layer IDs

Model folder names should match `layer_id` in `collections/layers.yaml` (e.g. `flood_hazard`, `heat_hazard`, `exposure_score`, `composite_risk`, `nbs_opportunity_zones`).
