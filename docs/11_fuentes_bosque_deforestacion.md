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
| 7 | Datos Abiertos Colombia (IDEAM/MinAmbiente) | Confirmado — 2 datasets Socrata (`39dh-rc72` Nacional, `env9-bhc9` Amazonía), pero **desactualizados** (último año 2022) frente al servicio ArcGIS institucional (2024) y **explícitamente no validados por IDEAM** según su propia metadata ("los datos... no han sido validados por el IDEAM") — corrección Fase 2D.1: `validado_oficialmente=False` |

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
asociados. Complementado por los boletines PDF trimestrales narrativos (último confirmado:
**boletín 45, IV trimestre 2025, publicado 2026-03-31** — corrección Fase 2D.1; la Fase 2D
había identificado erróneamente el boletín 44/III-2025 como el más reciente).

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
6. **Latencia:** no se pudo confirmar con precisión en esta fase — **corrección Fase 2D.1:**
   el boletín 45 (IV trimestre 2025) sí existe y cubre el mismo periodo que el microdato
   vectorial más reciente (2025-IV); ver la sección "Validación técnica piloto Fase 2D.1"
   más abajo para la comparación real entre ambos.
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
| DTD Trimestral (puntos) | 2025-IV | boletín 45 (IV trimestre 2025), publicado 2026-03-31 (corrección Fase 2D.1) | no determinada | `alerta_temprana` |
| Datos Abiertos Colombia (Socrata, nacional y Amazonía) | 2022 | 2024-01-30 | — (2 años de rezago; **no validado por IDEAM según su propia metadata — corrección Fase 2D.1**) | `actualizacion_periodica` |

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

## Validación técnica piloto Fase 2D.1

Piloto técnico de acceso, semántica y consistencia generado por
`scripts/20_validate_forest_data_pilot.py`. No descargó la colección nacional completa. No
calculó indicadores para los 1.122 territorios. No integró minería ni calidad hídrica. No
construyó índice de riesgo.

### Corrección de la Fase 2D (sección A)

Boletín DTD más reciente corregido a **45 (IV trimestre 2025, publicado 2026-03-31)**;
temporalidad de bosque aclarada como cortes 1990/2000/2005/2010/2012 + anual real 2013-2024
(no serie anual continua); los 2 datasets Socrata marcados `validado_oficialmente=False`
porque su propia metadata declara que no fueron validados por IDEAM.

### WCS (sección B)

Ambos servicios exponen WCS 2.0.1 real en la ruta `/gisserver/services/.../WCSServer` (no en
`/rest/`). **Hallazgo crítico**: WCS entrega la imagen RGB renderizada, no el grid de códigos
de clase — confirmado descargando un recorte real y comparando sus valores de píxel contra el
colormap oficial obtenido con la operación `identify`. Ver `forest_wcs_validation.md`.

### Municipios piloto (sección L), seleccionados con evidencia real

| Rol | Municipio | Criterio |
|---|---|---|
| Deforestación reciente | Puerto Rico, Meta (50590) | Mayor `total_ha` deforestada 2024 entre municipios ≤600.000 ha (consulta de estadísticas real) |
| Sin registros en vector de cobertura parcial *(corrección Fase 2D.3; antes descrito erróneamente como "bosque, baja/nula deforestación")* | Miritı́-Paraná, Amazonas (91460) | 0 registros en `zonas_deforestadas_2013_2024` entre municipios amazónicos, mayor área — la ausencia de registros refleja un vector con cobertura parcial (118/1.122 municipios), no evidencia de baja deforestación real |
| Geometría compleja | Bolívar, Santander (68101) | Mayor índice de compacidad (perímetro²/(4π·área)) entre municipios de una sola parte |

### Piloto ráster (secciones C-G)

Método adoptado: **WCS GetCoverage + decodificación inversa del colormap**, validada contra
`identify`. Códigos de clase confirmados: Bosque No Bosque {0=Sin Información, 1=Bosque,
2=No Bosque}; Cambio de Bosque {0=Sin Información, 1=Bosque Estable, 2=Deforestación,
5=No Bosque Estable}. Áreas piloto (Puerto Rico, EPSG:9377, `nearest`): Bosque 169.209,70 ha
(49,7%), Deforestación 2023-2024 2.972,71 ha. La reproyección no creó valores de clase nuevos
**después de corregir** un `dst_nodata` implícito de `rasterio.warp.reproject()` que
colisionaba con el código real 0 — hallazgo real documentado en `forest_raster_pilot.md`.

### Piloto vectorial y comparación (secciones H-I)

913 polígonos reales para Puerto Rico/2024 (5 geometrías inválidas, 0 duplicadas, 0 ha de
solape interno). Comparación ráster-vector: **correspondencia ALTA** (2.972,71 ha vs.
2.981,51 ha, diferencia 0,30%). Ver `deforestation_raster_vector_comparison.md`.

### Auditoría semántica DTD (secciones J-K)

Muestra de 2.000/21.044 registros reales del IV trimestre de 2025 (9,5% del periodo, límite
`maxRecordCount`). El esquema real NO tiene fecha exacta, fecha de publicación, área, nivel
de confianza ni fuente satelital por registro — no se convierte ningún punto en hectáreas.
Correspondencia cualitativa razonable con el Boletín 45 (mismos departamentos dominantes).
Estabilidad de `cod_dtd` entre descargas y posibilidad de revisión retroactiva: **no
confirmadas, riesgos abiertos**. Ver `dtd_semantic_validation.md`.

### Decisión de arquitectura (superada parcialmente por la Fase 2D.2 — ver más abajo)

- **Bosque**: `Superficie_Bosque` vía WCS + decodificación de colormap.
- **Deforestación anual**: `zonas_deforestadas_2013_2024` (vector) como fuente principal;
  `Dinamica_Cambio_Cobertura_Bosque` (ráster) como validación cruzada.
- **Monitoreo oportuno**: `DTD_Trimestral` aprobado solo para conteo y presencia/ausencia —
  **no aprobado para área** (la semántica real de los puntos no lo permite).

### Idempotencia

Verificada con dos corridas completas consecutivas: las 4 tablas de auditoría y los 2
recortes ráster descargados son byte-idénticos (SHA-256) entre ambas corridas.

## Cierre técnico Fase 2D.2

Generado por `scripts/21_forest_dtd_and_colormap_robustness.py`, reutilizando las funciones
de `scripts/20_validate_forest_data_pilot.py`. No descargó todavía la serie forestal
nacional. No calculó indicadores para los 1.122 territorios. No integró minería ni calidad
hídrica. No construyó índice de riesgo.

### A. Corrección del bug de conteo (sección A)

`dtd_semantic_audit` usaba `serie.value_counts().nunique()` — cuenta frecuencias distintas,
no categorías distintas. Corregido a `serie.nunique(dropna=True)`. Sobre la muestra de 2.000
registros de 2025-IV: municipios distintos corregido a **24** (antes 21, valor incorrecto);
departamentos distintos (nuevo): **5**. Prueba explícita:
`tests/test_dtd_distinct_counts.py`.

### B. Universo completo de 2025-IV (sección B)

**21.044 registros reales** (no la muestra de 2.000): 242 municipios, 26 departamentos
distintos. 7 de los 10 municipios reales con más detecciones no aparecían en el top-10 de la
muestra de la Fase 2D.1 — confirma que la muestra no era representativa para rankings
territoriales.

### C. Estabilidad de `cod_dtd` — histórico completo 2017-I a 2025-IV (sección C)

**249.895 registros** auditados vía paginación real completa. **Hallazgo crítico**:
32.062 registros (12,8%) comparten un `cod_dtd` placeholder no único DENTRO de su propio
trimestre (5 trimestres afectados: 2023-I con 13.593 registros bajo un solo código,
2023-III con 8.150, 2024-III con 6.769, 2023-II con 2.408, 2024-IV con 1.120). **0 casos**
de reaparición del mismo código entre trimestres distintos — estructuralmente imposible por
el formato `{año}_trim_{periodo}_{secuencial}` del identificador.

### D. Comparación correcta con el Boletín 45 (sección D)

Usando el universo completo (no la primera página): mismos 4 departamentos dominantes
(Meta, Caquetá, Guaviare, Putumayo) en ambas fuentes, pero **el orden relativo difiere**
(29,74% Meta vs. 26,63% Caquetá por conteo de puntos; 26% vs. 44% por área según el
boletín) — confirma que % de puntos y % de área no son la misma medida. Clasificación:
`parcialmente_consistente`.

### E. Auditoría exhaustiva del colormap (sección E)

**0% de píxeles no decodificados** en el 100% de los píxeles de ambos productos piloto
(no una muestra). 0 colores ambiguos. La única clase ausente en ambos productos fue "Sin
Información" — el municipio piloto está completamente clasificado.

### F. Estabilidad del WCS (sección F)

El servidor **remuestrea dinámicamente según la extensión solicitada** — resolución y tamaño
de salida varían levemente entre configuraciones de bbox distintas (mismos colores/códigos
de clase en ambas). Recomendación: fijar bbox e interpolación `nearest` para reproducibilidad.

### G. Comparación en 3 municipios y hallazgo crítico de cobertura del vector (sección G)

Puerto Rico: correspondencia alta (0,30%). Miritı́-Paraná: no comparable (WCS falló, HTTP
400, municipio de 1.681.437 ha excede el límite práctico del servidor). **Bolívar,
Santander: el ráster detecta 143,11 ha de deforestación real que el vector no registra en
absoluto** — evidencia directa de que `zonas_deforestadas_2013_2024` no tiene cobertura
nacional completa.

### H. Auditoría territorial del vector (sección H)

El vector es internamente limpio (118 municipios, todos con código DIVIPOLA válido, 0
nulos, 0 inconsistencias de nombre) pero **cubre solo 118 de los 1.122 municipios del
país**. En Puerto Rico, 8/913 polígonos (0,9%) tienen desajuste geométrico real con MGN2025.

### Decisiones actualizadas de arquitectura (históricas — corregidas en la Fase 2D.3, ver más abajo)

- **Bosque**: `aprobado_para_procesamiento_nacional` (0% de pérdida confirmado).
- **Deforestación vectorial**: `candidato_principal_pendiente_validacion_nacional` — el
  hallazgo de Bolívar impide su aprobación sin reservas como fuente principal nacional.
- **Ráster de cambio**: `fuente_de_validacion_cruzada` — con evidencia de que puede cubrir
  huecos geográficos reales del vector.
- **DTD**: `aprobado_para_conteo_y_presencia`; se mantiene `no_aprobado_para_area`.

> Corrección Fase 2D.3: el ráster de cambio pasa a ser la **fuente principal** de
> deforestación anual nacional; el vector pasa a **fuente complementaria de cobertura
> parcial**, nunca principal. Ver la sección "Cierre técnico Fase 2D.3" más abajo.

### Idempotencia

Verificada con dos corridas completas consecutivas de
`scripts/21_forest_dtd_and_colormap_robustness.py`: las 6 tablas de auditoría son
byte-idénticas (SHA-256) entre ambas corridas, incluida la paginación completa de 249.895
registros históricos.

## Cierre técnico Fase 2D.3

Generado por `scripts/22_design_forest_national_acquisition.py` y los módulos nuevos
`src/aquabosque/forest/{grid,colormap,tiles}.py` y `src/aquabosque/features/dtd.py`. No
descargó la serie forestal nacional. No calculó indicadores para las 1.122 unidades. No
integró minería ni agua. No construyó índice de riesgo. No entrenó modelos.

### A. Correcciones de arquitectura vigentes

El ráster `Dinamica_Cambio_Cobertura_Bosque` es la **fuente principal** de deforestación
anual nacional (`aprobado_para_adquisicion_nacional_raster`); `zonas_deforestadas_2013_2024`
es **fuente complementaria de cobertura parcial** (`fuente_complementaria_cobertura_parcial`,
118/1.122 municipios, no puede usarse para asignar cero deforestación a municipios sin
polígonos); Miritı́-Paraná se describe como
`sin_registros_en_vector_de_cobertura_parcial`, nunca como "baja o nula deforestación"; DTD
queda `aprobado_para_conteo_presencia_y_distribucion_espacial`, manteniendo
`no_aprobado_para_area`.

### B-D. Grilla nacional fija (896 tiles, 369 candidatos)

`DescribeCoverage` real reveló que `Superficie_Bosque` y `Dinamica_Cambio_Cobertura_Bosque`
**no comparten exactamente la misma grilla nativa** (resolución declarada difiere 0,02%,
orígenes difieren en la 6ª-7ª cifra decimal) — la grilla nacional canónica
(`config/forest_national_grid.json`) se alinea al origen de `Superficie_Bosque`; ambos
productos se descargarán siempre con los mismos bounds/tiles, no con su origen nativo. 896
tiles de 2.048×2.048 px generados por aritmética pura (nunca desde bbox municipal); 369
(41,2%) intersectan territorio nacional MGN2025 (marcado solo para filtrar, no para recortar
bounds).

### E/N. Continuidad y mosaico — aprobados

2 tiles contiguos reales se recomponen sin huecos ni superposición, misma resolución. Mosaico
2×2 real reconstruido con dimensiones correctas y área por clase idéntica antes/después.

### F/G/H. Colormap multitemporal — hallazgo crítico

El colormap confirmado en 2024 (0% de pérdida) **no decodifica con exactitud** las capas de
2012-2013 a 2018 (3,15%-3,66% de píxeles con RGB a 1-3 unidades de distancia de los valores
base) — evidencia de configuración de renderer posiblemente distinta por año
(`UniqueValueRenderer` vs. `RasterColormapRenderer`, confirmado con `identify()` real).
`decode_ideam_rgb_classes` (nueva función reutilizable,
`src/aquabosque/forest/colormap.py`) nunca asimiló un RGB desconocido a la clase 0 — los
marcó `clase_desconocida` (254) y el proceso se habría detenido con la tolerancia por
defecto (0,0%). `forest_layer_colormaps.csv` versiona cada colormap con hash de leyenda.

### I/J/K. Identificación DTD corregida

`dtd_registro_id` (hash SHA-256 determinístico, sin fecha de descarga) reemplaza a `cod_dtd`
como llave de fila. Sobre el histórico completo (249.895 registros): 5 códigos placeholder
(32.062 registros, ya conocido), 12 coordenadas repetidas bajo el mismo código, 2.080
coordenadas con múltiples `cod_dtd` (esperado, por diseño del identificador). Ningún registro
se eliminó. Metodología de asignación territorial (`covers()` sobre MGN2025) validada sobre
una muestra de 20 puntos: 19/20 (95%) de concordancia con el código de la fuente.

### L/M. Estimación y manifiesto

369 tiles candidatos, ~12,6 MB/tile observado. Alternativa recomendada: 5 cortes de bosque
clave (2013/2018/2020/2022/2024) + 16 cambios anuales completos (~97,5 GB, ~7.749
peticiones, ~1,8 h estimadas) — ninguna descarga nacional se ejecutó en esta fase. Esquema de
manifiesto diseñado en `data/raw/forest/manifest.json` (0 tiles reales registrados).

### Arquitectura definitiva

Bosque nacional y deforestación anual nacional: `WCS_RGB_FIXED_TILE_GRID`. Vector de zonas
deforestadas: `COMPLEMENTARY_PARTIAL_COVERAGE`. DTD: `POINT_COUNTS_PRESENCE_DISTRIBUTION`.

### Idempotencia

Verificada con múltiples corridas completas consecutivas de
`scripts/22_design_forest_national_acquisition.py`: las 8 tablas/archivos de referencia y
auditoría son byte-idénticos (SHA-256) entre corridas.
