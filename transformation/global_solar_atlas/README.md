# Global Solar Atlas

Transformation pipeline for Global Solar Atlas Brazil data → Porto Alegre clipped rasters and neighbourhood-level solar indicators.

## Source

**Dataset:** [Global Solar Atlas — Brazil](https://globalsolaratlas.info/download/brazil)  
**Publisher:** World Bank Group and Solargis  
**License:** Free for non-commercial use (see [terms](https://globalsolaratlas.info/download))

Download the **Brazil LTAy AvgDailyTotals** GeoTIFF package (v2). Extract into `Brazil_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/`.

## Inputs

| Input | Description |
|-------|-------------|
| `Brazil_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/{GHI,PVOUT,DNI,GTI,DIF}.tif` | Brazil-wide solar raster layers |
| `../br_ibge/releases/2010/output/porto_alegre_neighbourhoods.geojson` | Neighbourhood boundaries for zonal stats |

## Outputs

| Output | Description |
|--------|-------------|
| `output/poa_GHI.tif`, `poa_PVOUT.tif`, … | Clipped GeoTIFFs for Porto Alegre extent |
| `output/poa_solar_pixels.csv` | Pixel-level lat/lon + layer values |
| `output/poa_solar_neighbourhoods.csv` | Neighbourhood mean/max per layer |
| `output/poa_solar_neighbourhoods.geojson` | Neighbourhood polygons with solar attributes |
| `output/poa_solar_preview.png` | Visual preview |

## Layers

- **GHI** — Global Horizontal Irradiance (kWh/m²/day), ~250 m resolution
- **PVOUT** — PV Output (kWh/kWp/day), ~930 m resolution
- **DNI** — Direct Normal Irradiance (kWh/m²/day)
- **GTI** — Global Tilted Irradiance (kWh/m²/day)
- **DIF** — Diffuse Horizontal Irradiance (kWh/m²/day)

## Usage

1. Download the Brazil GeoTIFF package from [globalsolaratlas.info](https://globalsolaratlas.info/download/brazil)
2. Extract into `Brazil_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/`
3. Ensure `porto_alegre_neighbourhoods.geojson` exists in `../br_ibge/releases/2010/output/`
4. Run the cells in `transformation.ipynb` (requires `numpy`, `pandas`, `imageio`, `matplotlib`)
