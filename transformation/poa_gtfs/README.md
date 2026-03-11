# POA GTFS

Transformation pipeline for Porto Alegre bus transit data (GTFS) → GeoJSON.

## Source

**Dataset:** [GTFS - Dados Abertos POA](https://dadosabertos.poa.br/dataset/gtfs)  
**Publisher:** EPTC (Empresa Pública de Transporte e Circulação)  
**License:** [Creative Commons Attribution](https://creativecommons.org/licenses/by/4.0/)

The feed contains bus routes, stops, shapes, and schedules for Porto Alegre in [GTFS](https://gtfs.org/) format.

## Releases

Each release is dated by the source data update:

```text
release/
  2024-10-01/
    arquivo-gtfs/     # Raw GTFS files (from source ZIP)
    transformation.ipynb
    output/
      stops.geojson   # Point features
      shapes.geojson  # LineString features (shape_id only)
      routes.geojson  # LineStrings with route metadata
```

## Usage

1. Download the GTFS ZIP from [dadosabertos.poa.br](https://dadosabertos.poa.br/dataset/gtfs)
2. Extract into `release/<version>/arquivo-gtfs/`
3. Run the cells in `transformation.ipynb` (requires `pandas`)
4. Output GeoJSON files are written to `output/`
