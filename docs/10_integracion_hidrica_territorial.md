# 10 — Integración hídrica territorial (Fase 4B)

Asigna espacialmente las 134.216 observaciones históricas de calidad del agua del IDEAM
(2005-2024) a las 1.122 unidades territoriales DIVIPOLA vigentes, usando exclusivamente
`data/processed/territorio/base_geometrica_divipola_mgn2025/` (Fase 3D.2), y genera
indicadores **descriptivos** de cobertura, monitoreo y resultados observados por parámetro.

**Esta fase NO afirma que existe contaminación, NO atribuye resultados a minería, NO
construye un índice de riesgo, NO entrena ningún modelo, NO integra deforestación ni áreas
protegidas, NO crea dashboard, NO descargó fuentes nuevas y NO modificó datos crudos.**
`mineria_por_unidad_territorial_mgn2025.csv` (Fase 4A.2) se listó como entrada solo para
mantener compatibilidad futura — **no se unió** con nada de esta fase.

## Cómo regenerar

```powershell
.\venv\Scripts\Activate.ps1
python scripts\13_build_water_territorial.py
python scripts\14_write_water_reports.py
```

Idempotencia verificada con dos corridas completas consecutivas: resultados numéricos
idénticos (48,46 s y 48,52 s de tiempo total, mismo conteo en cada paso).

## Fuente y periodo

IDEAM — Data Histórica de Calidad de Agua (`datos.gov.co`, recurso `62gv-3857`), descargada
el 2026-07-11 (Fase 2A.1), limpiada en la Fase 3B
(`data/processed/agua/ideam_calidad_agua_clean.csv`, 134.216 filas). Periodo: **2005-2024**.
Los "últimos 5 años" de cualquier indicador de esta fase se calculan sobre 2020-2024 (los
últimos 5 años **disponibles en la fuente**, no respecto a la fecha de hoy) — documentado
explícitamente para no dar a entender que el dataset llega hasta el presente.

## Unidad de observación

Cada fila del CSV limpio es una **medición de un parámetro en una fecha en un punto**, no
un "sitio" ni una "estación" per se — un mismo sitio aporta muchas filas (una por
parámetro×fecha). Esta fase nunca asume que cada fila es un punto de monitoreo
independiente.

## Identificación de sitios de monitoreo

`nombre_del_punto_de_monitoreo` tiene 243 valores únicos, exactamente igual al número de
pares lat/lon únicos — es, de hecho, un identificador de sitio ya estable en la fuente.
`sitio_monitoreo_id` se construyó con la prioridad pedida:

1. **Código de estación** extraído del patrón `... [CODIGO]` al final del nombre del punto
   (194/243 sitios; verificado único por sitio antes de usarlo).
2. `codigo_muestra` y `proyecto` se **evaluaron y descartaron** como candidatos de prioridad
   2: `codigo_muestra` identifica una visita de muestreo (cambia con cada fecha en el mismo
   sitio, ~19,7 filas por código en promedio), no un sitio estable en el tiempo; `proyecto`
   tiene solo 8 valores para 243 sitios, demasiado agregado.
3. **Hash SHA-256 determinístico** (12 hex) de latitud/longitud redondeadas a 5 decimales
   (~1,1 m de precisión) + `municipio_norm` + nombre del punto, para los 49/243 sitios sin
   código entre corchetes.

## Asignación espacial

Se construyó un `STRtree` **una sola vez** sobre las 1.122 unidades MGN2025 (reutilizando el
caché espacial `territorial_units_mgn2025_epsg9377` de la Fase 3D.2/4A.2). La asignación se
calculó **por sitio único (243), no por fila (134.216)** — los resultados se unen de vuelta
por `sitio_monitoreo_id`, evitando repetir 134.216 veces una consulta cuyo resultado es el
mismo dentro de cada sitio.

Regla principal: `covers()` (no `contains()`, para que un punto sobre el borde de una unidad
sí pueda asignarse). Resultado real de esta corrida: **los 243 sitios (100 %) se asignaron
por `covers_directo`**, sin ambigüedad ni necesidad de proximidad — las coordenadas del IDEAM
en esta fuente son limpias (0 fuera del bbox de Colombia, 0 longitudes positivas, 0
coordenadas (0,0), 0 duplicadas, 0 indicios de intercambio lat/lon). El umbral de proximidad
(100 m, configurable vía `UMBRAL_PROXIMIDAD_M_DEFAULT`) y la lógica de desambiguación por
texto y de "sin asignación" quedan implementadas y probadas en
`src/aquabosque/geo/point_assignment.py`, listas para corridas futuras con fuentes de
coordenadas menos limpias.

## Tratamiento de censura

38.426 registros (28,6 %) están censurados por límite de detección inferior (`<X`) y 14 por
límite superior (`>X`, p. ej. conteos de coliformes que exceden el rango del método). Se
conserva siempre `resultado_texto_original`; `resultado_numerico_observado` queda `NaN` para
los censurados (**nunca se reemplaza por 0**). Se calculó aparte `resultado_imputado_ld_2`
(límite de detección / 2, solo para censura inferior, regla explícita del encargo),
**marcada como imputación y no usada por defecto en ningún indicador oficial** de esta fase.
Para censura superior no hay una regla de imputación documentada equivalente — esa columna
queda vacía en esos 14 casos en vez de inventar un factor.

## Catálogo de parámetros

`data/processed/reference/catalogo_parametros_calidad_agua.csv`: 85 combinaciones
`propiedad_observada_norm` + `unidad_norm` (77 parámetros distintos). La normalización de
unidad es **puramente textual** (espacios, "Kg"→"kg" al final de una fracción, "unidades de
pH"/"Unidades de pH" → una sola forma) — nunca una conversión numérica entre unidades
distintas (mg/L sigue siendo distinto de µg/L). Cada combinación se clasifica en una de 8
categorías (físico, químico, microbiológico, metal/metaloide, nutriente, hidrocarburo/compuesto
orgánico, indicador agregado, otro/no clasificado) — una **etiqueta de categoría**, nunca una
afirmación de equivalencia entre nombres distintos.

## Indicadores territoriales

`data/processed/features/calidad_agua_por_unidad_territorial.csv`: **1.122 filas**
(universo DIVIPOLA vigente completo), incluidas las 950 unidades sin ningún monitoreo. Son
indicadores de **disponibilidad e intensidad de monitoreo**, no de condición ambiental:
cobertura (sitios, observaciones, parámetros, años, últimos 5 años disponibles), calidad de
datos (% numérico, % censurado, % con asignación espacial de alta calidad), cobertura
temática (conteo de parámetros por categoría) e intensidad (observaciones por sitio, por
año, parámetros por sitio). Solo 172/1.122 unidades (15,3 %) tienen algún monitoreo.

### Parámetros aprobados para indicadores municipales específicos (sección K)

Se evaluaron 13 candidatos (pH, oxígeno disuelto, conductividad, turbidez, DBO5, DQO,
sólidos suspendidos, coliformes totales, *E. coli*, mercurio, arsénico, plomo, cadmio) contra
3 criterios documentados (unidad homogénea, ≥500 observaciones asignadas, ≥20 municipios con
dato). **9/13 aprobados.** Coliformes y *E. coli* no se aprobaron por estar repartidos entre
dos unidades de reporte (`NMP/100 mL` vs. `NMP/100 cm3`) que no se mezclaron sin una regla de
conversión explícita. Mercurio no alcanzó el mínimo de observaciones (262 < 500).
**Arsénico no está presente en esta fuente de datos en absoluto** — se documenta su ausencia,
no se evalúa como si existiera. Plomo y cadmio aprueban los 3 criterios pero tienen 94,8 % y
99,1 % de resultados censurados respectivamente — "aprobado" no implica que un estadístico
numérico basado en ellos vaya a ser informativo; se documenta esa limitación explícitamente.
Esta fase **no construyó** columnas de indicador municipal específicas para ningún
parámetro — solo dejó la evaluación lista para una fase posterior.

## Tendencias temporales

`data/processed/features/calidad_agua_tendencias_territoriales.csv`: pendiente de Theil-Sen
(mediana de las pendientes de todos los pares de observaciones, implementada en `numpy` puro
sin depender de `scipy`) calculada solo cuando hay evidencia suficiente (≥5 años distintos,
≥10 observaciones numéricas, periodo ≥4 años): **2.896/5.417 combinaciones** unidad
territorial + parámetro + unidad cumplen esos mínimos. **Ninguna pendiente se interpreta
como mejora o deterioro** — el significado depende del parámetro y esta fase no lo evalúa.

## Ausencia de monitoreo

Cuatro banderas de **disponibilidad de información, no de condición ambiental**:
`sin_monitoreo` (0 observaciones, 950/1.122), `monitoreo_escaso` (<5 observaciones, 950/1.122
— coincide con `sin_monitoreo` porque toda unidad sin monitoreo también tiene <5 por
definición), `monitoreo_desactualizado` (sin datos en 2020-2024, 964/1.122, incluidas 14 de
las 172 unidades CON monitoreo) y `cobertura_temporal_limitada` (<3 años distintos,
953/1.122).

## Limitaciones del catastro/fuente

- Cobertura geográfica muy desigual: 243 sitios para todo el país, concentrados en cuencas
  con monitoreo histórico del IDEAM (Alto Magdalena, Cauca, Catatumbo, entre otras) — la
  ausencia de datos en el resto del territorio no implica ausencia de presión ambiental.
- 45/243 sitios muestran alguna discrepancia entre el municipio/departamento textual
  declarado por la fuente y el municipio/departamento de la geometría MGN2025 que realmente
  cubre sus coordenadas (`calidad_agua_asignacion_territorial_audit.csv`) — no se corrigió
  ninguna con fuzzy matching, solo se documentó.
- Coliformes, *E. coli*, mercurio y arsénico quedan fuera de los indicadores específicos por
  razones documentadas (no por descarte arbitrario).

## Por qué todavía no se habla de contaminación ni de riesgo

Todo lo que produce esta fase son conteos, agregaciones descriptivas (mínimo, mediana,
máximo, pendiente de Theil-Sen) y banderas de disponibilidad de monitoreo. **No se aplicó
ningún límite legal o normativo** (p. ej. de la Resolución 2115 o el Decreto 1076) sobre
ningún resultado, **no se etiquetó ninguna observación como "contaminada" o "no
contaminada"**, y **no se cruzó ningún resultado hídrico con presencia minera** — eso queda
explícitamente fuera de alcance hasta una fase posterior que lo aborde con el mismo cuidado
metodológico (sin asumir causalidad) que las Fases 4A/4A.1/4A.2 aplicaron a la minería.

## Archivos creados o modificados

- `src/aquabosque/geo/point_assignment.py` (nuevo) — asignación punto-territorio con
  `covers()`, desambiguación por texto y proximidad configurable.
- `src/aquabosque/features/water.py` (nuevo) — censura, catálogo, sitios, agregaciones,
  indicadores, tendencias.
- `scripts/13_build_water_territorial.py` (nuevo) — orquesta toda esta fase.
- `scripts/14_write_water_reports.py` (nuevo) — genera los 6 reportes.
- `data/processed/reference/catalogo_parametros_calidad_agua.csv` (+ `.metadata.json`).
- `data/processed/integrated/calidad_agua_observaciones_georreferenciadas.csv` (+ `.metadata.json`).
- `data/processed/integrated/calidad_agua_sitio_parametro_anio.csv` (+ `.metadata.json`).
- `data/processed/features/calidad_agua_por_unidad_territorial.csv` (+ `.metadata.json`).
- `data/processed/features/calidad_agua_tendencias_territoriales.csv` (+ `.metadata.json`).
- `data/processed/audit/calidad_agua_asignacion_territorial_audit.csv` (+ `.metadata.json`).
- `outputs/reports/water_integration/water_parameter_catalog.md`,
  `water_spatial_assignment.md`, `water_data_quality.md`, `water_territorial_indicators.md`,
  `water_temporal_trends.md`, `water_phase4b_quality_closure.md` (nuevos).
- `docs/10_integracion_hidrica_territorial.md` (este documento).

## Riesgos pendientes

- Solo 172/1.122 unidades territoriales (15,3 %) tienen algún monitoreo IDEAM; el resto no
  puede caracterizarse en absoluto con esta fuente.
- 964 unidades (incluidas 14 de las 172 con monitoreo) no tienen datos en los últimos 5 años
  disponibles (2020-2024).
- La asignación espacial de esta corrida fue 100 % directa porque las coordenadas del IDEAM
  resultaron muy limpias; la lógica de proximidad/desambiguación/ambigüedad no se ejercitó
  con casos reales, solo queda disponible para fuentes futuras.
- Plomo y cadmio, aunque aprobados por los 3 criterios documentados, tienen >90 % de
  censura — cualquier indicador municipal específico futuro debe reportar la proporción
  censurada junto con cualquier valor numérico.
- No se investigó la causa de las 45 discrepancias texto/geometría más allá de auditarlas.
- Esta fase no cruza calidad hídrica con presión minera; ese cruce, si se hace, debe ser una
  fase explícita y separada, con el mismo cuidado de no asumir causalidad.
