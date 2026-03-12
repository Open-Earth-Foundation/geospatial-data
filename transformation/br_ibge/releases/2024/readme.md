# IBGE 2024 — Informal Settlements (Favelas e Comunidades Urbanas)

Vector data from the 2022 Census on favelas and urban communities (FCUs) in Brazil.

## Source

**Dataset:** Favelas e comunidades urbanas — Resultados do universo  
**Publisher:** IBGE (Instituto Brasileiro de Geografia e Estatística)  
**Census:** Censo Demográfico 2022  
**License:** Public domain (IBGE open data)

**Download:** [IBGE FTP — arquivos vetoriais](https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Favelas_e_comunidades_urbanas_Resultados_do_universo/arquivos_vetoriais/)

## Available files

| File | Format | Description |
|------|--------|-------------|
| `poligonos_FCUs_shp.zip` | Shapefile | FCU polygon boundaries |
| `poligonos_FCUs.kml` | KML | FCU polygon boundaries |
| `concentracoes_urbanas_shp.zip` | Shapefile | Urban concentration areas |
| `concentracoes_urbanas_kml.zip` | KML | Urban concentration areas |
| `FCUs_nao_setorizadas_shp.zip` | Shapefile | FCUs not yet sectorized |
| `FCUs_nao_setorizadas.kml` | KML | FCUs not yet sectorized |
| `FCUs_Brasil_cartograma_shp.zip` | Shapefile | Brazil FCU cartogram |

## Usage

1. Download the desired file(s) from the FTP link above
2. Extract into this release folder (e.g. `poligonos_FCUs/` for shapefiles)
3. Run transformation scripts to clip to Porto Alegre or join with other indicators
