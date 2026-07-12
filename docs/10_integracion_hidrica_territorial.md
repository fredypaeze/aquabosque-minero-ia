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

## Cierre metodológico Fase 4B.1

Auditoría metodológica de sitios, parámetros censurados y cobertura hídrica, **sin
recalcular la asignación espacial ni construir indicadores de contaminación o riesgo**.
Generada por `scripts/15_audit_water_quality.py` (nuevo módulo
`src/aquabosque/features/water_audit.py`) y `scripts/16_write_water_audit_reports.py`.

### A. Sitios de monitoreo

Los 243 sitios se auditaron uno por uno (`calidad_agua_sitios_monitoreo_audit.csv`) y los
**243 clasificaron como `sitio_estable`**: por construcción, `sitio_monitoreo_id` ya
incorpora la coordenada, así que cada sitio tiene exactamente 1 coordenada, 1 municipio
espacial y 1 departamento espacial — confirmado con datos reales, no asumido. **0 códigos**
resultaron reutilizados en coordenadas distantes; el mecanismo de llave compuesta
(`codigo_origen + coordenadas_redondeadas`) quedó implementado pero no fue necesario
aplicarlo.

### B. Diccionario de normalización de parámetros

`diccionario_normalizacion_parametros_agua.csv` (96 filas) explica la reducción de 96
combinaciones propiedad+unidad originales (80 nombres de propiedad) a 85 combinaciones
normalizadas (77 parámetros): la mayor parte es normalización textual de unidad
(`Kg`→`kg`, `pH`), y **exactamente 2 fusiones de nombre de parámetro son técnicamente
dudosas** — `ENDOSULFAN EN AGUA` (fusiona α y β-endosulfán) y `HEXACLOROCICLOHEXANO HCH EN
AGUA` (fusiona α, β y ɣ-HCH) — causadas por la eliminación de prefijos griegos en
`normalize_text` (Fase 3B). Ambas quedan marcadas `requiere_revision_tecnica=True`. Se
verificó que las unidades originales de cada isómero SÍ difieren, así que el catálogo de la
Fase 4B (agrupado por propiedad+unidad) no mezcló ningún valor numérico entre isómeros — el
riesgo queda limitado a análisis futuros que agrupen solo por `propiedad_observada_norm`
sin considerar `unidad_norm`. No se encontraron fusiones por tilde, abreviatura, número,
estado disuelto/total o método analítico.

### C. Clasificación de idoneidad en 4 niveles

Reemplaza el aprobado/no aprobado binario de la Fase 4B
(`clasificacion_idoneidad_parametros_agua.csv`, 85 filas): **31 Nivel A** (indicador
numérico descriptivo), **33 Nivel B** (solo detección/censura, censura ≥80%), **21 Nivel
C** (cobertura insuficiente o unidades heterogéneas). **Plomo y cadmio se reclasifican de
"aprobado" a Nivel B** (94,8% y 99,1% de censura respectivamente): permiten
`pct_resultados_censurados`/`n_detecciones`/`límite de detección más frecuente`, pero NO
promedio, mediana, tendencia numérica predeterminada ni ranking territorial.

### D. Límites de detección

`calidad_agua_limites_deteccion_audit.csv` (71 combinaciones censuradas): **53/71 muestran
alta variabilidad** del límite de detección. Ejemplo documentado: el límite más frecuente
de plomo pasó de 0,01 mg/L (2005) a 0,5 mg/L (2009-2016) a 0,025 mg/L (2018-2024) — hasta
20x de diferencia, lo que impide comparar directamente resultados censurados entre esos
periodos.

### E. Tendencias

Las 2.896 tendencias calculables de la Fase 4B se auditaron una a una
(`calidad_agua_tendencias_audit.csv`): **2.896/2.896 confirmadas calculadas solo con
resultados numéricos** (recálculo independiente, coincide exactamente). 509 marcadas
`requiere_precaucion_por_censura` (20-80% de censura en el universo completo de esa
combinación) y 12 `no_recomendada_para_interpretacion_numerica` (>80%). Ninguna pendiente
se eliminó ni se interpretó como mejoría o deterioro.

### F. Cobertura territorial separada

| Categoría | N unidades |
|---|---|
| Sin monitoreo histórico | 950 |
| Con monitoreo histórico | 172 |
| — con monitoreo reciente (2020-2024) | 158 |
| — con monitoreo histórico pero desactualizado | 14 |

Partición verificada aritméticamente (950+172=1.122; 158+14=172).

### G. Discrepancias texto-geometría por causa

`calidad_agua_discrepancias_causa_audit.csv` clasifica los 45 sitios con evidencia
geométrica computada (distancia real al municipio nombrado en el texto, no una
suposición): **30 `coordenada_cerca_limite`** (≤2 km, casi siempre <100 m — el punto está
justo al otro lado de un límite administrativo), **8 `nombre_historico_o_variante`**
(p. ej. "GUICAN" en vez de "GÜICÁN DE LA SIERRA", "CÚCUTA" en vez de "SAN JOSÉ DE CÚCUTA" —
misma unidad, nombre antiguo/corto), **2 `municipio_textual_incorrecto`**, **2
`posible_error_coordenada`** (>50 km de distancia) y **3 `requiere_revision_manual`** (el
texto no corresponde a ningún nombre DIVIPOLA válido). **19.499 observaciones** (de
134.216) provienen de sitios con alguna discrepancia — se reporta por observaciones, no
solo por sitios. **No se sobrescribió ninguna asignación espacial.**

### Bug real encontrado y corregido durante esta fase

Al releer `calidad_agua_observaciones_georreferenciadas.csv` sin especificar
`dtype=str` para `cod_dane_mpio_asignado`, pandas infirió `int64` y perdió los ceros a la
izquierda (`"05390"` → `5390`), lo que hacía fallar el 100% de la verificación de
tendencias (comparaba contra códigos en formato `str` de otra tabla). Corregido antes de
generar ningún resultado final — mismo patrón de error de tipos que ya había aparecido en
fases anteriores del proyecto (DIVIPOLA, Fase 3A).

### Idempotencia

Verificada con dos corridas completas consecutivas de `scripts/15_audit_water_quality.py`:
resultados numéricos idénticos en las 6 salidas.

## Corrección canónica Fase 4B.2

Corrección canónica de normalización hídrica y validación independiente de códigos de sitio,
generada por `scripts/17_correct_water_normalization.py` (nuevo módulo
`src/aquabosque/features/water_normalization.py`, extensión de
`src/aquabosque/features/water_audit.py`) y `scripts/18_write_water_phase4b2_reports.py`.
**No recalculó la asignación espacial punto-territorio** (el georreferenciado nunca se abrió
en modo escritura; huella en bytes verificada sin cambios antes/después). No aplicó límites
legales. No integró minería ni deforestación. No construyó índice de riesgo.

### A. Auditoría independiente de códigos originales

`calidad_agua_codigos_sitio_origen_audit.csv` agrupa por `codigo_sitio_origen` — construido
con prioridad estación/punto (bracket en `nombre_del_punto_de_monitoreo`, 113.026
observaciones) > código de muestra (`codigo_muestra`, 21.190 observaciones; único usado como
respaldo real, ya que nunca está vacío) > proyecto > nombre completo — **sin coordenadas en
la llave de agrupación**, a diferencia de `sitio_monitoreo_id`. Los 194 códigos de
estación/punto reales clasificaron 100% `codigo_ubicacion_estable` (**0 reutilizados en
ubicaciones distantes**), confirmando de forma independiente el hallazgo de la Fase 4B.1. Los
824 grupos restantes derivados de `codigo_muestra` se etiquetaron `posible_codigo_de_muestra`
(no como reutilización, porque es un campo de otra granularidad, ya evaluado y descartado
como identificador de sitio). **49 sitios** siguen sin código de estación/punto real
disponible, reportados por separado.

### B/C. Corrección de normalización y tabla de correspondencia

`normalize_water_parameter_name` (nueva función especializada, separada de
`normalize_text` genérico) corrige la causa raíz encontrada en la Fase 4B.1: el filtro
`[^A-Z0-9 ]` de `normalize_text` trata las letras griegas de isómero (α/β/γ/ɣ/δ) como signos
de puntuación y las elimina. La función traduce cada letra griega a su nombre en español
(ALFA/BETA/GAMMA/DELTA) antes de la limpieza genérica, y unifica el único typo de deletreo
detectado (`HEXACLOROCICLOHEXA` → `HEXACLOROCICLOHEXANO`, solo en el nombre del isómero
delta). Resultado: **77 → 80 parámetros normalizados distintos**, **5 separaciones de
isómero** (`calidad_agua_normalizacion_parametros_comparison.csv`, 2.125 observaciones
afectadas), **0 fusiones técnicamente dudosas restantes** (antes: 5 filas / 2 grupos).

### D. Regeneración de productos derivados

Regenerados con la normalización corregida, sin recalcular asignación espacial: catálogo de
parámetros, tabla sitio+parámetro+año, tendencias territoriales, indicadores territoriales
(1.122 unidades, con conteos por parámetro/categoría/sitio recalculados), diccionario de
normalización, clasificación de idoneidad, auditoría de límites de detección y auditoría de
tendencias. El catálogo mantiene 85 combinaciones (las unidades de cada isómero ya diferían
entre sí, así que el catálogo agrupado por propiedad+unidad nunca mezcló valores numéricos
entre isómeros), pero 6 combinaciones cambiaron de identidad. Las 2.896 tendencias
calculables no cambiaron de universo.

### E. Reevaluación metodológica de tendencias

`calidad_agua_tendencias_audit.csv` reemplaza el booleano único de la Fase 4B.1 por cinco
señales no excluyentes: `pendiente_reproducida_correctamente` (2.896/2.896),
`apta_para_interpretacion_descriptiva` (2.267), `requiere_precaucion_por_censura` (509),
`requiere_precaucion_por_limite_deteccion_variable` (**371**, señal nueva, calculada por
combinación municipio+parámetro+unidad) y `no_recomendada_para_interpretacion_numerica` (12).
De las 371 con límite variable, 108 habrían sido "aptas" solo por censura — confirma que una
pendiente puede estar matemáticamente bien calculada y aun así no ser recomendable para
interpretación.

### F. Nivel D y candidatos ausentes

La clasificación de idoneidad A/B/C/D es por **combinación parámetro + unidad** (no por
parámetro aislado). `parametros_agua_candidatos_ausentes.csv` separa explícitamente los
candidatos evaluados pero ausentes de la fuente (**arsénico, confirmado, 0 observaciones en
todo el dataset**) del Nivel D (combinaciones observadas sin asignación espacial, 0 casos en
esta corrida) — nunca se mezclan. Niveles finales: A=31, B=33, C=21, D=0; suma=85=universo.

### G. Promoción canónica

Los 8 archivos derivados se promovieron como canónicos (mismos nombres de archivo);
la versión previa de cada uno se conserva como `<nombre>_legacy_normalizacion_previa.csv`.
Metadata de cada archivo promovido incluye `version_normalizacion_parametros =
"water_parameter_normalization_v2"`.

### Idempotencia (Fase 4B.2)

Verificada con dos corridas completas consecutivas de
`scripts/17_correct_water_normalization.py`: los 11 archivos generados/promovidos son
byte-idénticos entre ambas corridas (SHA-256), único cambio entre corridas: tiempo total.
