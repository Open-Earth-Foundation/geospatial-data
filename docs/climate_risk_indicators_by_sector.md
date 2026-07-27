# Climate risk indicators by sector

Canonical reference: [`climate_risk_indicators_by_sector.json`](climate_risk_indicators_by_sector.json)

## Structure

```text
Sector → Climatic risk → Component (Hazard | Vulnerability | Exposure) → indicators[]
```

Each indicator has:

| Field | Meaning |
|-------|---------|
| `Index` | Indicator name (place-agnostic) |
| `Description and relationship` | Why it matters for that component |
| `Attribute` | Role facet (e.g. Sensitivity, People exposure, Adaptive capacity) |
| `Kind` | Domain (Demographic, Socioeconomic, Climatic, Physical, …) |

## Design notes

- Indicators describe **what to measure**, not a single national data source.
- Operationalize per city/country (e.g. GHSL or ACS for population density; FEMA NFHL ∩ buildings for households in hazard-prone areas).
- Shared exposure core across many risks: **Population density**.

## Next (Minnesota / Plymouth)

1. P0 Exposure: Population density  
2. P1 Flood: Households in hazard-prone areas  
3. Broader sector backlog from this JSON  

See companion mapping notes when added under `docs/mn_exposure_candidates_*.md`.
