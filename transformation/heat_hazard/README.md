# heat_hazard

Transformation that applies `models/heat_hazard` to produce the Level 2 heat hazard score per city.

## Status

Scaffold (PR-A). Notebooks and shared site loader arrive in a later PR.

## Layout

```text
heat_hazard/
├── README.md
├── config/
│   └── sites/
│       ├── README.md
│       └── {city_slug}.yaml    # one file per city
├── sites/                      # local runtime data (gitignored except small boundaries)
│   └── {city_slug}/
│       ├── boundary/site.geojson
│       ├── data/
│       ├── cache/
│       └── out/
├── styles/                     # color tables / value-tile templates (later)
└── release/                    # optional packaged releases (later)
```

## Site selection

City configs live under `config/sites/`. Use a city-level `site_slug` (not statewide regions).

Expected env var (to be wired when notebooks land):

```bash
export HEAT_SITE=porto_alegre
```

## Model

Default weights and methodology: `models/heat_hazard/`.
