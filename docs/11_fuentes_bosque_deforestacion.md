# 11 — Fuentes de bosque y deforestación (Fase 2D)

Descubrimiento, inventario y validación técnica de fuentes geoespaciales oficiales para
construir, en fases posteriores, indicadores territoriales de superficie de bosque,
deforestación anual y detecciones tempranas. **Esta fase es exclusivamente de descubrimiento
y validación**: no descarga la serie histórica nacional completa, no procesa rásteres
nacionales, no calcula indicadores municipales, no cruza con minería ni calidad hídrica, no
construye índice de riesgo, no entrena modelos, no crea dashboard y no afirma monitoreo en
tiempo real.

## Cómo regenerar

```powershell
.\venv\Scripts\Activate.ps1
python scripts\19_discover_forest_deforestation_sources.py
```

Idempotencia verificada con dos corridas completas consecutivas: los dos archivos de
catálogo (`catalogo_fuentes_bosque_deforestacion.csv`, `actualidad_fuentes_deforestacion.csv`)
son byte-idénticos (SHA-256) entre ambas corridas, pese a tratarse de peticiones HTTP en
vivo contra servicios externos.

## A. Fuentes institucionales investigadas

Todas las fuentes principales encontradas son oficiales (IDEAM, a través de su Sistema de
Monitoreo de Bosques y Carbono — SMByC — y su Geoportal Ambiental Institucional). No se usó
ninguna fuente internacional: **el producto oficial colombiano existe y está vivo** para los
tres tipos de producto pedidos (B.1, B.2, B.3).

| # | Fuente investigada | Resultado |
|---|---|---|
| 1 | SMByC | Confirmado — administra los servicios ArcGIS y los boletines/informes |
| 2 | Portal/catálogo de datos abiertos geográficos IDEAM | Confirmado — `https://visualizador.ideam.gov.co/gisserver/rest/services` (ArcGIS Server institucional) |
| 3 | Geovisor Bosque y Deforestación en Cifras | Confirmado, disponible (HTTP 200), lanzado 2024-08-21; es una SPA que no expone enlaces directos a servicios en su HTML |
| 4 | Informes anuales de monitoreo de bosque y deforestación | Confirmado — última cifra: 2024, resumen ejecutivo publicado 2025-07-31 |
| 5 | Detecciones Tempranas de Deforestación (DTD) | Confirmado — microdato vectorial `DTD_Trimestral` (249.895 puntos) + boletines PDF trimestrales |
| 6 | Alertas Tempranas de Deforestación semanales | **No encontradas** como capa/microdato descargable independiente en esta fase — el sistema institucional vigente reporta con cadencia **trimestral** (DTD), no semanal; no se encontró un producto "alerta semanal" separado y oficial |
| 7 | Datos Abiertos Colombia (IDEAM/MinAmbiente) | Confirmado — 2 datasets Socrata (`39dh-rc72` Nacional, `env9-bhc9` Amazonía), pero **desactualizados** (último año 2022) frente al servicio ArcGIS institucional (2024) |

No se asumió que la página web, el boletín PDF y la capa geoespacial contuvieran el mismo
nivel de detalle: cada uno se validó por separado (ver catálogo, columna `tipo_servicio`).

## B. Productos distinguidos (terminología exigida por el encargo)

### B.1. `bosque_natural_observado`

`Superficie_Bosque/MapServer` — 17 capas ráster "Bosque No Bosque" (1990, 2000, 2005, 2010,
2012-2024 anual). Leyenda confirmada por petición real: **Bosque / No Bosque / Sin
Información**.

### B.2. `deforestacion_anual_confirmada`

Dos productos complementarios, ambos con **el mismo alcance temporal real: hasta el periodo
2023-2024** (cifra oficial 2024):

- `Dinamica_Cambio_Cobertura_Bosque/MapServer` — 16 capas ráster de cambio por periodo. Leyenda
  confirmada: **Bosque Estable / Deforestación / No Bosque Estable / Regeneración / Sin
  Información** — distingue explícitamente pérdida (deforestación) de ganancia
  (regeneración): es **pérdida bruta**, no cambio neto.
- `Hosted/zonas_deforestadas_2013_2024/FeatureServer` (Registro Nacional de Zonas
  Deforestadas) — **276.908 polígonos** individuales de zonas deforestadas, 2013-2024
  (12 años confirmados por consulta `returnDistinctValues` real), con hectáreas, código
  DANE de municipio/departamento, CAR y RUNAP ya vinculados por registro.

### B.3. `deteccion_temprana_posible_deforestacion`

`Hosted/DTD_Trimestral/FeatureServer` — **249.895 puntos**, 36 combinaciones año+trimestre
confirmadas (2017-I a 2025-IV), con núcleo trimestral (`nucleo_tri`), municipio, CAR y RUNAP
asociados. Complementado por los boletines PDF trimestrales narrativos (último localizado:
boletín 44, III trimestre 2025).

**Nunca se denomina esta señal "deforestación confirmada", "tala ilegal", "minería ilegal" ni
"daño ambiental probado"** — se mantiene siempre el término `detección temprana de posible
deforestación`, consistente con el resto del proyecto ("no afirmar causalidad").

## C. Tabla maestra de fuentes

`data/processed/reference/catalogo_fuentes_bosque_deforestacion.csv` — **14 filas**, una por
producto/capa/documento encontrado, con las 33 columnas pedidas por el encargo (id_fuente,
entidad, sistema, categoría, URLs, formato, CRS, periodo, validación, licencia, tamaño,
utilidad, limitaciones, observaciones). Todas las filas fueron validadas con al menos una
petición HTTP real (nunca solo por el código de estado): 9 servicios ArcGIS REST, 2 datasets
Socrata, 3 páginas/documentos.

## D. Validación de servicios geoespaciales

Todos los servicios se consultaron con `?f=json` real contra
`https://visualizador.ideam.gov.co/gisserver/rest/services` — el mismo ArcGIS Server
institucional de IDEAM ya usado en fases anteriores para calidad de agua (`Calidad_Agua`) y
entidades territoriales, confirmando que es la infraestructura de referencia de la entidad,
no una URL aislada.

| Servicio | Tipo | Capas/Tablas | CRS | maxRecordCount | Paginación |
|---|---|---|---|---|---|
| `Superficie_Bosque/MapServer` | Raster (MapServer) | 17 capas | EPSG:4686 | 2000 | N/A (raster) |
| `Dinamica_Cambio_Cobertura_Bosque/MapServer` | Raster (MapServer) | 16 capas | EPSG:4686 | 2000 | N/A (raster) |
| `Hosted/zonas_deforestadas_2013_2024/FeatureServer` | Vector polígono | 1 capa, 276.908 registros | EPSG:3857 | 2000 | Sí (`supportsPagination=True`) |
| `Hosted/DTD_Trimestral/FeatureServer` | Vector punto | 1 capa, 249.895 registros | EPSG:3857 | 2000 | Sí (`supportsPagination=True`) |
| `Hosted/Deforestacion_CAR_Deptos/FeatureServer` | Tabla (sin geometría) | 1 tabla, contenido no auditado | — | 2000 | — |
| `Hosted/Indicadores_SMByC_diferencia/FeatureServer` | Tabla (sin geometría) | 1 tabla ("Hoja1", baja confianza) | — | 2000 | — |
| `Uso_Recurso_Bosque/MapServer` | Vector polígono | 2 capas, 2000-2006 | EPSG:4686 | 2000 | — |
| `SNIF/SNIF/MapServer` | Vector mixto | 7 capas, 11 tablas | **EPSG:9377** | 2000 | — |

A diferencia de la fase de MGN2025 (Fase 3D.2), estos servicios **sí soportan paginación
estándar** (`supportsPagination=True`, confirmado por petición real a
`advancedQueryCapabilities`) — no se necesitaría el workaround de `objectIds` en chunks para
descargas futuras de `zonas_deforestadas_2013_2024` o `DTD_Trimestral`.

Se comprobó el contenido real (no solo el HTTP 200) mediante:
- Lectura de `layers`/`tables` y sus nombres.
- Lectura de campos (`fields`) de las capas vectoriales de interés.
- Conteo real de registros vía `returnCountOnly=true`.
- Lectura de leyenda real (`/legend`) para confirmar el diccionario de clases de las capas
  ráster, en vez de inferirlo por inspección visual.

## E. Validación de descargas

No se descargó la colección nacional completa. Se validó, sin descargar contenido pesado:
- **HEAD real** al adjunto ZIP de ambos datasets Socrata: `Cambio_2022.zip` (38.362.263 bytes,
  `application/x-zip-compressed`, HTTP 200) y `Cambio_2022_amazonia.zip` (10.138.443 bytes,
  HTTP 200) — tamaño confirmado por el propio campo `blobFileSize` de la API Socrata, no
  estimado.
- **HEAD real** a un PDF de informe anual y a un boletín DTD — ambos HTTP 200.
- Conteo de registros de las 2 capas vectoriales de interés (no se descargó ninguna fila).

No se descargó ninguna capa piloto ni recorte en esta fase: la metadata de servicio ya fue
suficiente para confirmar estructura técnica (campos, geometría, CRS, paginación).

## F. Serie anual oficial — confirmación documental y técnica

- **Primer año disponible (bosque/no bosque):** 1990.
- **Último año disponible (bosque/no bosque):** **2024**, confirmado por nombre de capa real
  (`Bosque No Bosque 2024 Raster Layer`) — no inferido de un informe.
- **Cadencia:** anual desde 2012-2013 en adelante; antes de eso, periodos multianuales
  (1990-2000, 2000-2005, 2005-2010, 2010-2012).
- **Significado de las clases**, confirmado por leyenda real (no inspección visual):
  bosque/no bosque = 3 clases (Bosque, No Bosque, Sin Información); cambio = 5 clases
  (Bosque Estable, Deforestación, No Bosque Estable, Regeneración, Sin Información) — **es
  pérdida bruta, no cambio neto**, porque deforestación y regeneración se reportan como
  clases separadas.
- **El último producto anual oficial geoespacial SÍ corresponde a 2024**: tanto la capa
  ráster (`Bosque No Bosque 2024`, `Cambio de Bosque 2023_2024`) como el registro vectorial
  de polígonos (`zonas_deforestadas_2013_2024`, año `2024` confirmado por consulta distinta
  real) están disponibles — la cifra de 113.608 ha publicada el 2025-07-31 en el resumen
  ejecutivo **sí tiene su capa geoespacial correspondiente descargable**, a diferencia de lo
  que advierte el encargo como riesgo genérico ("una cifra publicada en un informe no
  garantiza que la capa esté disponible").

## G. Detecciones tempranas — hallazgos

1. **No existen alertas semanales georreferenciadas descargables** encontradas en esta fase
   — el sistema vigente reporta trimestralmente (DTD), no semanalmente.
2. **Sí existen detecciones trimestrales georreferenciadas descargables**:
   `DTD_Trimestral` (FeatureServer, 249.895 puntos).
3. Los boletines trimestrales sí incluyen (según los títulos y estructura de archivo
   encontrados) anexos/análisis por núcleo, pero el microdato vectorial es un producto
   independiente ya descargable sin depender del PDF.
4. **Granularidad:** punto (no polígono, píxel, núcleo, municipio ni departamento
   directamente — aunque cada punto sí trae `cod_mpio`/`nom_mpio` y `nucleo_tri` como
   atributos).
5. **Fecha real del evento:** el campo `anio` + `periodo` (trimestre romano i-iv) identifica
   el periodo de observación; no se confirmó en esta fase si existe una fecha exacta por
   punto (los campos disponibles son `anio`, `periodo`, `id_bolet`, sin campo de fecha
   explícita tipo `fecha_deteccion`).
6. **Latencia:** no se pudo confirmar con precisión en esta fase (el microdato vectorial ya
   cubre 2025-IV, un trimestre más reciente que el boletín narrativo más reciente localizado,
   2025-III/boletín 44) — **queda como riesgo abierto**.
7. **Histórico disponible:** 2017-I a 2025-IV, 36 trimestres consecutivos sin vacíos
   confirmados por consulta real.
8. **Identificador estable:** existe el campo `cod_dtd`, pero esta fase no confirmó si es
   estable entre boletines sucesivos (no se comparó la misma detección entre dos versiones
   consecutivas del servicio) — **queda como riesgo abierto, requiere revisión manual**.
9. **Revisión/fusión/eliminación entre versiones:** no confirmado en esta fase — **riesgo
   abierto explícito**, documentado también en la sección K (leakage).
10. **Uso legal/metodológico como señal de monitoreo oportuno:** el propio IDEAM la
    denomina "detección temprana" (no "confirmada"), consistente con el término que este
    proyecto ya usa; es apta como **señal de monitoreo oportuno**, nunca como afirmación de
    deforestación confirmada, tala ilegal o minería ilegal.

## H. Revisión de actualidad

`data/processed/reference/actualidad_fuentes_deforestacion.csv` — 4 filas.

| Producto | Último periodo | Fecha publicación | Latencia aprox. | Clasificación |
|---|---|---|---|---|
| Informe anual + capas Bosque No Bosque / Cambio de Bosque | 2024 | 2025-07-31 | ~212 días | `historico_anual` |
| Registro Nacional de Zonas Deforestadas (polígonos) | 2024 | 2025-07-31 | ~212 días | `historico_anual` |
| DTD Trimestral (puntos) | 2025-IV | boletín narrativo más reciente: 2025-III | no determinada | `alerta_temprana` |
| Datos Abiertos Colombia (Socrata, nacional y Amazonía) | 2022 | 2024-01-30 | — (2 años de rezago) | `actualizacion_periodica` |

No se usa la expresión "tiempo real" en ningún caso — no se encontró evidencia de
transmisión continua; la señal más oportuna (DTD) tiene cadencia trimestral.

## I. Compatibilidad con MGN2025

- **CRS:** las capas ráster de bosque están en **EPSG:4686** (MAGNA-SIRGAS geográfico); las
  capas vectoriales (`zonas_deforestadas_2013_2024`, `DTD_Trimestral`) están en **EPSG:3857**
  (Web Mercator, proyección de servicio ArcGIS estándar). Ambas son reproyectables a
  EPSG:9377 (CRS de cálculo del proyecto) con `pyproj.Transformer`, el mismo patrón ya usado
  en las Fases 3D.2/4A.2/4B. Curiosamente, el servicio `SNIF/SNIF/MapServer` ya está
  publicado nativamente en **EPSG:9377** — confirma que IDEAM también usa ese CRS
  internamente para algunos productos.
- **Intersección con MGN2025:** viable en principio para los productos vectoriales
  (`zonas_deforestadas_2013_2024`, `DTD_Trimestral`) mediante el mismo patrón de
  `STRtree`/`covers()` ya usado en Fases 4A.2/4B — ambos productos ya traen `cod_mpio`
  textual, lo que permite además una auditoría de discrepancia texto-geometría análoga a la
  de la Fase 4B.1.
- **Rásteres (`Superficie_Bosque`, `Dinamica_Cambio_Cobertura_Bosque`):** la agregación por
  unidad territorial requerirá zonal statistics (recorte de ráster por polígono municipal),
  no una intersección vectorial simple — mayor costo computacional que los productos
  vectoriales.
- **Áreas costeras/insulares y píxeles limítrofes:** no evaluados en esta fase (requiere
  examinar el ráster real, que no se descargó); queda como riesgo técnico documentado en la
  sección L de `forest_source_selection.md`.
- **Librerías necesarias para una fase de procesamiento futura:** `rasterio` y/o
  `rioxarray`/`xarray` para leer los rásteres, `numpy` (ya en el proyecto); `rasterstats`
  solo si se necesita estadística zonal directa sin reinventar la lógica. **Ninguna se
  instaló en esta fase** — el entorno actual (`shapely`, `pyproj`, `pandas`) basta para
  validar y para procesar los productos vectoriales (`zonas_deforestadas`, `DTD_Trimestral`).

## J. Diseño preliminar del componente forestal (NO implementado)

Estas tres tablas son diseños preliminares únicamente — no se crearon con datos en esta fase.

### J.1. `data/processed/features/bosque_por_unidad_territorial_anio.csv`

`cod_dane_mpio, anio, area_unidad_ha, area_bosque_ha, pct_area_bosque, area_no_bosque_ha,
area_sin_informacion_ha, fuente, version`

### J.2. `data/processed/features/deforestacion_por_unidad_territorial_anio.csv`

`cod_dane_mpio, anio, area_deforestada_ha, pct_bosque_inicial_perdido, cambio_interanual_ha,
cambio_interanual_pct, deforestacion_acumulada_ha, fuente, version`

### J.3. `data/processed/integrated/detecciones_tempranas_deforestacion.csv`

`alerta_id, fecha_inicio, fecha_fin, periodo_reporte, geometry, area_alerta_ha,
cod_dane_mpio, metodo_asignacion, fuente, boletin, estado_confirmacion, fecha_descarga`

## K. Riesgo de leakage futuro

El modelo predictivo futuro deberá usar, para predecir una variable ambiental observada en un
periodo posterior:

- variables de presión minera en tiempo t (Fases 4A/4A.2);
- variables de monitoreo hídrico disponibles hasta tiempo t (Fases 4B/4B.1/4B.2);
- bosque remanente y deforestación histórica hasta tiempo t (esta fase);
- detecciones tempranas disponibles hasta tiempo t (esta fase).

**Nunca** una alerta o pérdida observada después del periodo objetivo. Riesgos concretos
identificados en esta fase que alimentan ese cuidado futuro:
- La latencia evento→publicación del DTD no está confirmada (sección G.6) — un uso ingenuo
  de "última fecha disponible en el servicio" como límite de corte podría filtrar
  información publicada después del periodo objetivo si la latencia real es mayor a la
  asumida.
- No se confirmó si versiones posteriores del DTD pueden confirmar/modificar/fusionar/
  eliminar detecciones previas (sección G.9) — si una detección de un trimestre puede
  cambiar retroactivamente en una descarga posterior, un modelo entrenado con una descarga
  antigua y validado con una descarga nueva estaría comparando dos "verdades" distintas para
  el mismo periodo.
- La variable objetivo **no se construyó** en esta fase.

## L. Priorización de fuentes

Ver `outputs/reports/forest_sources/forest_source_selection.md` para la tabla completa de
decisiones (`adoptar_fuente_principal` / `adoptar_fuente_complementaria` / `solo_validacion`
/ `solo_documental` / `rechazar` / `requiere_revision_manual`) con los criterios aplicados a
cada una de las 14 filas del catálogo.

## Archivos creados o modificados

- `scripts/19_discover_forest_deforestation_sources.py` (nuevo) — descubrimiento y
  validación con peticiones HTTP reales.
- `data/processed/reference/catalogo_fuentes_bosque_deforestacion.csv` (+ `.metadata.json`) —
  14 filas.
- `data/processed/reference/actualidad_fuentes_deforestacion.csv` (+ `.metadata.json`) —
  4 filas.
- `data/raw/metadata/forest_sources/` (nuevo, 22 archivos JSON livianos, ~282 KB total) —
  respuestas reales de servicio guardadas para trazabilidad.
- `outputs/reports/forest_sources/official_source_inventory.md`,
  `forest_annual_data_validation.md`, `early_deforestation_alerts_validation.md`,
  `geospatial_service_validation.md`, `forest_source_selection.md` (nuevos).
- `docs/11_fuentes_bosque_deforestacion.md` (este documento).

## Riesgos pendientes

- No se confirmó la latencia exacta evento→publicación del DTD ni la estabilidad del
  identificador `cod_dtd` entre boletines sucesivos.
- No se auditó el contenido de las tablas `Deforestacion_CAR_Deptos` ni
  `Indicadores_SMByC_diferencia` (nombres genéricos, baja confianza de estabilidad).
- No se descargó ninguna capa piloto para confirmar resolución real de píxel, tratamiento de
  costas/islas ni comportamiento en píxeles limítrofes — pendiente para la fase de
  procesamiento.
- El Geovisor (SPA) no pudo validarse más allá de su disponibilidad HTTP; probablemente
  consume los mismos servicios ya validados aquí, pero no se confirmó de forma programática.
- Las fuentes Socrata (Datos Abiertos Colombia) quedaron con 2 años de rezago frente al
  servicio ArcGIS institucional — no deben promoverse como fuente principal de actualidad.
