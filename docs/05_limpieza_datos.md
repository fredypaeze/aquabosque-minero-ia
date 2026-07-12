# 05 — Limpieza y estandarización de datos (Fase 3B / 3C / 3D)

Limpieza de las fuentes descargadas (Fase 2A/2A.1/2B/2C) y perfiladas (Fase 3A/3C/3D),
cada una por separado. Generado por `scripts/03_clean_raw_data.py`, que usa
`src/aquabosque/data/clean.py`. La Fase 3C amplió esta limpieza al Catastro Minero
geoespacial de la ANM; la Fase 3D la amplió a los Límites municipales DANE, con
reparación trazable de geometrías inválidas y validación de reproyección a un CRS
métrico.

**Esta fase NO cruza fuentes ni construye dataset maestro.** Cada fuente se limpia de
forma independiente y se guarda en `data/processed/`.

## Cómo regenerar la limpieza

```powershell
.\venv\Scripts\Activate.ps1
python scripts\03_clean_raw_data.py
```

Salidas (todas ignoradas por git, igual que el resto de `data/processed/` y
`outputs/reports/` desde la Fase 0 — son artefactos regenerables):

- `data/processed/territorio/divipola_municipios_clean.csv` (+ `.metadata.json`)
- `data/processed/mineria/anm_anotaciones_rmn_clean.csv` (+ `.metadata.json`)
- `data/processed/agua/ideam_calidad_agua_clean.csv` (+ `.metadata.json`)
- `data/processed/mineria/catastro_minero_anm_clean.geojson` (+ `.metadata.json`)
- `data/processed/territorio/limites_municipales_dane/*.geojson` (11 partes, + `.metadata.json` por parte, + `manifest.json`)
- `outputs/reports/cleaning/cleaning_summary.md`
- `outputs/reports/cleaning/catastro_minero_anm_cleaning.md`
- `outputs/reports/cleaning/limites_municipales_dane_cleaning.md`

## Librerías geoespaciales: shapely y pyproj en vez de geopandas

Para limpiar el catastro minero (Fase 3C) y los límites municipales (Fase 3D) hacía
falta validar geometrías GeoJSON (nulas, tipo, validez topológica, reparación) y, en la
Fase 3D, verificar que fuera posible transformar coordenadas a un CRS métrico. Se evaluó
`geopandas`, pero se optó por **`shapely` + `pyproj`** por separado (ambos declarados en
`requirements.txt`, justificados ahí mismo):

- El GeoJSON de entrada y de salida ya se lee/escribe con `json` estándar de Python — no
  se necesita la capa de I/O de geopandas (que internamente depende de `fiona`/`pyogrio`).
- `geopandas` exige además `GDAL`, mucho más pesado de instalar (especialmente en Windows
  sin conda) que lo que esta fase necesita.
- Lo que se requería era: construir una geometría desde GeoJSON y consultar
  `.is_valid`/`.geom_type` (shapely), repararla con `shapely.make_valid`, y transformar
  puntos de un CRS a otro (`pyproj.Transformer`) — exactamente lo que ofrecen estas dos
  librerías livianas por separado, sin la capa de abstracción adicional de geopandas.

Si una fase futura necesita operaciones espaciales más complejas (`sjoin`, lectura de
Shapefile/GPKG, manejo integrado de CRS por capa), ahí sí se justificaría agregar
`geopandas` — no antes.

## Función de normalización de texto reutilizable

`normalize_text()` en `src/aquabosque/data/clean.py`: mayúsculas, sin tildes (vía
`unicodedata`), sin signos de puntuación, sin espacios dobles, y colapsa variantes
conocidas de "Bogotá D.C." (`BOGOTÁ, D.C.`, `Bogota D.C.`, `BOGOTA D C`, `Bogotá Distrito
Capital`, etc.) a una única forma canónica `BOGOTA DC`. Se probó explícitamente con esas
4 variantes y las 4 colapsan correctamente a `BOGOTA DC`.

Esta función **nunca reemplaza el campo original**: cada columna de texto relevante
(nombre de municipio, departamento, modalidad, tipo de anotación, propiedad observada)
queda con su valor original intacto más una columna `*_norm` adicional, para mantener
trazabilidad.

## Filas / features antes / después por fuente

| Fuente | Entrada | Salida | Diferencia | Tamaño |
|---|---|---|---|---|
| DIVIPOLA - Códigos de municipios (DANE) | 1.135 | 1.122 | -13 | 86,9 KB |
| ANM Títulos Mineros - Anotaciones RMN | 37.763 | 37.555 | -208 | 14,3 MB |
| IDEAM - Data Histórica de Calidad de Agua | 134.261 | 134.216 | -45 | 32,4 MB |
| Catastro Minero ANM - Títulos Vigentes (WFS) | 6.294 | 6.294 | 0 | 9,1 MB |
| Límites municipales DANE (ArcGIS REST) | 1.122 | 1.122 | 0 | 158,9 MB (11 partes) |

## Columnas finales por fuente

- **DIVIPOLA:** `cod_dpto`, `nombre_dpto`, `nombre_dpto_norm`, `cod_dane_mpio`,
  `nombre_mpio`, `nombre_mpio_norm`, `tipo`, `longitud`, `latitud`
- **ANM Anotaciones RMN:** `codigo_expediente`, `estado_juridico`, `modalidad`,
  `modalidad_norm`, `id_tipo_de_anotacion`, `tipo_de_anotacion`, `tipo_anotacion_norm`,
  `fecha_anotacion`, `anio_anotacion`, `fecha_ejecutoria`, `anio_ejecutoria`, `observacion`
- **Calidad de agua IDEAM:** `nombre_del_punto_de_monitoreo`, `latitud`, `longitud`,
  `elevacion_msnm`, `corriente`, `zona_hidrografica`, `codigo_subzona_hidrografica`,
  `nombre_subzona_hidrografica`, `departamento`, `departamento_norm`, `municipio`,
  `municipio_norm`, `fecha`, `anio`, `propiedad_observada`, `propiedad_observada_norm`,
  `resultado`, `resultado_numerico`, `unidad_del_resultado`, `proyecto`, `codigo_muestra`
- **Catastro Minero ANM (properties del GeoJSON):** `codigo_expediente`, `estado`,
  `estado_norm`, `modalidad`, `modalidad_norm`, `etapa`, `etapa_norm`, `area_ha`,
  `minerales`, `minerales_norm`, `nombre_de_titular`, `numero_identificacion`,
  `tipo_de_identificacion`, `identificacion_titulares`, `pto_pti`,
  `instrumento_ambiental`, `departamentos`, `departamentos_norm`, `municipios`,
  `municipios_norm`, `grupo_de_trabajo`, `fecha_de_inscripcion`, `anio_inscripcion`,
  `fecha_terminacion`, `anio_terminacion`, `objectid` — más el campo `geometry`
  (`MultiPolygon`) estándar de cada Feature, fuera de `properties`.
- **Límites municipales DANE (properties del GeoJSON):** `objectid`, `cod_dane_dpto`,
  `nom_dpto`, `nombre_dpto_norm`, `cod_dane_mpio`, `nom_mpio`, `nombre_mpio_norm`,
  `mpio_corrdeptal` — más el campo `geometry` (`MultiPolygon` homogéneo) y un miembro
  `crs` a nivel de `FeatureCollection` (`urn:ogc:def:crs:EPSG::4326`).

## Registros eliminados y motivo

### DIVIPOLA
- **13 filas** descartadas por no ser registros territoriales válidos (título del
  reporte DANE y notas al pie que el XLSX arrastraba dentro del rango de datos leído).
- **0 duplicados completos** tras la limpieza (los duplicados de la Fase 3A eran, en su
  mayoría, esas mismas 13 filas basura, ya descartadas por el filtro anterior).
- Se eliminó la columna `nota` (99,6% nula, texto de nota al pie sin valor analítico).

### ANM Anotaciones RMN
- **208 filas** completamente duplicadas eliminadas.

### Calidad de agua IDEAM
- **45 filas** completamente duplicadas eliminadas.

### Catastro Minero ANM
- **0 features eliminadas** (0 duplicados completos no geométricos; `CODIGO_EXPEDIENTE`
  ya era único en el origen).

### Límites municipales DANE
- **0 features eliminadas.** Por diseño explícito: ninguna fila se descarta por
  invalidez de geometría (esta fuente no tuvo geometrías inválidas, pero el código está
  preparado para conservar el registro de propiedades incluso si la geometría queda
  vacía tras intentar repararla).

## Calidad de fechas / coordenadas / resultados / geometrías

- **DIVIPOLA:** `cod_dane_mpio` tiene longitud 5 en el 100% de las 1.122 filas finales
  (0 con longitud distinta), 0 códigos DANE duplicados.
- **ANM:** `fecha_anotacion` parseó al 100% (0 no parseables); `fecha_ejecutoria` tuvo
  **1.724 valores no parseables** (p. ej. `"N/E"`), que quedaron nulos en el CSV final —
  no se inventó ninguna fecha.
- **Calidad de agua:** `fecha` parseó al 100% (0 no parseables). `latitud`/`longitud` son
  100% numéricas y no nulas (134.216 de 134.216 filas con coordenadas completas).
  `resultado_numerico` tiene **38.440 valores nulos** de 134.216 (≈28,6%): corresponden en
  buena parte a notación de censura de límite de detección (`"<0.4"`, `"<10"`, etc.), que
  se conserva intacta en el campo original `resultado` (texto) para no perder esa
  información.
- **Catastro Minero ANM:**
  - `codigo_expediente`: 0 vacíos, 0 duplicados, **es único** en las 6.294 features.
  - Geometría: 0 nulas; **22 topológicamente inválidas** (verificado con shapely), no
    corregidas ni descartadas en esta fase.
  - `area_ha`: 100% numérica (0 no numéricas).
  - `fecha_de_inscripcion`: 0 no parseables. `fecha_terminacion`: **91 no parseables**
    (todas por el valor de texto literal `'null'` en el origen, correctamente convertido
    a nulo real — no es un problema del parser).
  - 3 features tienen `fecha_terminacion` en el año 9999 (valor centinela probable de
    "sin vencimiento"); con la versión de pandas usada (3.x, resolución `datetime64[us]`)
    estas fechas sí se representan sin overflow, así que `anio_terminacion=9999` aparece
    tal cual en la salida y debe tratarse como caso especial, no como fecha real lejana.
  - 138 features tenían `ETAPA = 'null'` (texto literal), corregido a nulo real antes de
    normalizar.
- **Límites municipales DANE:**
  - `cod_dane_mpio`: 0 vacíos, 0 duplicados, **único** en las 1.122 features, longitud 5
    en el 100%.
  - Geometría: 0 nulas, **0 inválidas** (antes y después de limpiar, verificado con
    shapely) — no hubo geometrías que reparar en esta corrida.
  - 100% de las geometrías finales son `MultiPolygon` (los 1.114 `Polygon` originales se
    convirtieron de forma consistente).
  - Correspondencia con DIVIPOLA limpia (por código DANE): **1.121/1.122 (99,82%)**.
    Único código sin correspondencia real (no de formato): `94663` (Mapiripana, Guainía)
    solo en límites; `27493` (Nuevo Belén de Bajirá, Chocó) solo en DIVIPOLA.
  - CRS validado: transformación de muestra de 15 centroides de EPSG:4326 a EPSG:9377
    (MAGNA-SIRGAS 2018 / Origen-Nacional) con `pyproj`, 0 errores. La geometría
    almacenada sigue en EPSG:4326; no se reemplazó por la versión reproyectada.

## Riesgos pendientes para integración (Fase 4+)

- De las 5 fuentes, **Límites municipales DANE es la única con código DANE de municipio
  limpio y único, listo para join directo** con DIVIPOLA. DIVIPOLA tiene `cod_dane_mpio`
  (código DANE), pero ANM Anotaciones RMN no tiene territorio en absoluto, calidad de
  agua solo tiene `departamento_norm`/`municipio_norm` de texto (sin código DANE), y el
  catastro minero tiene geometría pero también `departamentos_norm`/`municipios_norm` de
  texto (a veces con varias unidades territoriales en una sola cadena).
- El código `94663` (Mapiripana) solo existe en Límites municipales; el código `27493`
  (Nuevo Belén de Bajirá) solo existe en DIVIPOLA. Cualquier join por código DANE entre
  ambas fuentes debe decidir explícitamente cómo tratar estos dos casos — no se afirma
  aquí cuál código es "correcto" ni se infiere ninguna causa administrativa o legal.
- El cruce territorial de calidad de agua/catastro minero con DIVIPOLA requerirá
  emparejar texto normalizado (no código), con riesgo de nombres compuestos o variantes
  de escritura no cubiertas por las equivalencias conocidas hoy (solo se resolvió
  explícitamente el caso Bogotá D.C.).
- `codigo_expediente` de ANM Anotaciones RMN sigue siendo una llave 1-a-muchos (6.769
  expedientes únicos sobre 37.555 filas): cualquier integración futura debe decidir si se
  agrega a nivel de expediente antes de cruzar con otras fuentes. En cambio,
  `codigo_expediente` del catastro minero geoespacial **sí es único por feature**, y
  podría usarse para enlazar ambas fuentes de ANM entre sí.
- `resultado_numerico` de calidad de agua tiene ~28,6% de nulos por censura de límite de
  detección; un análisis agregado ingenuo (promedios simples, etc.) debe decidir
  explícitamente cómo tratar esos casos en vez de ignorarlos silenciosamente.
- Las 22 geometrías inválidas del catastro minero deben corregirse (p. ej. `buffer(0)`) o
  descartarse explícitamente antes de cualquier operación espacial (intersección, área
  exacta, unión con otras capas).
- `FECHA_TERMINACION = 9999-12-31` (y similares) del catastro minero no debe usarse en
  cálculos de vigencia/antigüedad sin tratarse como caso especial.
- `DEPARTAMENTOS`/`MUNICIPIOS` del catastro minero pueden traer varias unidades
  territoriales en una sola cadena separada por coma: un cruce por municipio individual
  requerirá "explotar" (split) estos campos primero.
- El geoservicio WFS de la ANM sigue declarando última actualización "22/03/2023"
  (Fase 1.5/2B/3C); conviene confirmar vigencia con la entidad antes de un uso analítico
  o público del catastro.
- La reproyección real a EPSG:9377 y el cálculo de áreas municipales quedan pendientes
  para la Fase 4A; en esta fase solo se validó que la transformación es técnicamente
  posible (0 errores en una muestra de 15 centroides).
- Los límites municipales son un dataset pesado (158,9 MB en 11 partes, geometrías sin
  simplificar); cualquier intersección futura con el catastro minero deberá considerar el
  costo computacional de operar sobre polígonos de hasta 126.304 vértices.

## Próximos pasos (Fase 4+, no ejecutados aquí)

1. Diseñar la estrategia de emparejamiento de nombres de municipio/departamento
   (más allá del caso Bogotá D.C. ya resuelto) antes de cualquier cruce real.
2. Decidir el nivel de agregación de ANM Anotaciones RMN (por expediente vs. detalle de
   anotación) antes de integrarlo con otras fuentes.
3. Decidir el tratamiento de las 22 geometrías inválidas y del valor centinela
   `FECHA_TERMINACION = 9999-12-31` del catastro minero.
4. Decidir cómo tratar los códigos `94663`/`27493` (discrepancia real entre Límites
   municipales y DIVIPOLA) antes de usar Límites municipales como base territorial.
5. En Fase 4A: reproyectar a EPSG:9377 (ya validado) para calcular áreas municipales y
   ejecutar la intersección espacial entre Límites municipales y Catastro Minero.
6. Solo entonces, avanzar a la construcción de un dataset maestro — todavía sin tocar
   RUNAP, SMByC, el MGN completo por otras vías, Global Forest Watch, MapBiomas, Sentinel
   ni Landsat.
