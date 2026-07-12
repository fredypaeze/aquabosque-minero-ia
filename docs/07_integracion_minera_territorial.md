# 07 — Integración espacial minera por unidad territorial DIVIPOLA (Fase 4A)

Intersecta los títulos mineros vigentes de la ANM (catastro minero `spatial_ready`,
Fase 3D.1) con las unidades territoriales subdepartamentales DIVIPOLA vigentes
(universo territorial reconciliado, Fase 3D.1), calcula la distribución territorial
real de cada título y agrega ANM Anotaciones RMN (Fase 3B) en indicadores
**descriptivos** de presión minera formal registrada por código DANE.

Generado por `scripts/06_build_mining_territorial.py`, que usa los nuevos módulos
`src/aquabosque/geo/intersection.py`, `src/aquabosque/utils/spatial_cache.py` y
`src/aquabosque/features/mining.py`.

**Esta fase integra únicamente:** universo territorial reconciliado, geometrías
territoriales, catastro minero ANM `spatial_ready` y ANM Anotaciones RMN limpias.
**No integra:** calidad hídrica, deforestación, bosque, RUNAP, áreas protegidas,
variables sociales, ni calcula riesgo, score, probabilidad de contaminación,
probabilidad de deforestación, minería ilegal, afectación causada por minería, índice
compuesto, modelo de IA ni dashboard — todo eso queda explícitamente fuera de alcance.

## Cómo regenerar

```powershell
.\venv\Scripts\Activate.ps1
python scripts\06_build_mining_territorial.py
```

Es completamente re-ejecutable e idempotente: si el caché espacial
(`data/interim/spatial_cache/territorial_units_epsg9377.pkl`) sigue siendo válido
(mismo CRS y misma huella SHA-256 de los archivos territoriales de origen), se
reutiliza (0 s de reproyección); si no, se regenera automáticamente.

Salidas versionables (git) vs. regenerables:

- `docs/07_...md` (este documento) y el código en `src/`/`scripts/` quedan en git.
- `data/processed/integrated/mineria_titulo_unidad_territorial.csv`,
  `data/processed/features/mineria_por_unidad_territorial.csv` y sus
  `.metadata.json` quedan ignorados por git (`data/processed/*`) — artefactos
  regenerables, igual que el resto de `data/processed/` desde la Fase 0.
- `data/interim/spatial_cache/territorial_units_epsg9377.pkl` (+ `.metadata.json`)
  queda ignorado por git (`data/interim/spatial_cache/*`, añadido en esta fase) —
  caché regenerable, nunca fuente de verdad.
- `outputs/reports/mining_integration/*.md` quedan ignorados por git
  (`outputs/reports/*`), mismo patrón desde la Fase 0.

## A. Universo territorial analítico

El universo analítico se define exactamente como
`presente_divipola_vigente == True AND tiene_geometria == True` sobre
`universo_territorial_divipola.csv` (Fase 3D.1) — **da 1.122 unidades**:

- **27493 (Nuevo Belén de Bajirá) incluido**: está vigente en DIVIPOLA y su
  geometría fue recuperada del DANE MGN2025 en la Fase 3D.1.
- **94663 (Mapiripaná) excluido del universo analítico**, aunque se conserva en
  `universo_territorial_divipola.csv` para trazabilidad: no está en DIVIPOLA
  vigente, así que no participa de la intersección ni de los indicadores.

Antes de continuar con la intersección, el script recalcula las tres métricas de
correspondencia (Fase 3D.1) sobre el universo ya filtrado, comparando los 1.122
códigos esperados contra los códigos efectivamente cargados desde los archivos de
geometría (11 partes de límites municipales + el archivo separado de Bajirá):

| Métrica | Resultado |
|---|---|
| `cobertura_divipola_por_geometria` | **100,0 %** |
| `precision_geometria_contra_divipola` | **100,0 %** |
| `similitud_jaccard` | **100,0 %** |

Las tres son 100 % por construcción; el script está diseñado para **detenerse con
error** si alguna no lo es (o si el universo analítico no tiene exactamente 1.122
filas, o si 27493/94663 no cumplen su condición esperada) — no se llegó a ese
escenario de fallo en esta corrida.

## B. Caché espacial regenerable

`data/interim/spatial_cache/territorial_units_epsg9377.pkl` guarda las 1.122
geometrías territoriales **ya reproyectadas** a EPSG:9377 (MAGNA-SIRGAS 2018 /
Origen-Nacional), junto a un `.metadata.json` con CRS, fecha de creación y la
huella (tamaño + SHA-256) de cada archivo de origen. Se invalida automáticamente
si cualquiera de esos archivos cambia. **No se serializa el índice `STRtree`**
(no hay garantía de estabilidad entre versiones de shapely); el índice se
reconstruye en cada corrida a partir de la lista de geometrías cacheada, lo cual
es rápido (0,0004 s) — lo costoso es la reproyección, que sí se cachea.

Verificado en dos corridas consecutivas:

- 1ª corrida (sin caché previo): caché generado, 5,4803 s de reproyección.
- 2ª corrida (caché válido): caché reutilizado, 0,0000 s de reproyección.

## C. Intersección espacial nacional

Se construyó el índice `STRtree` **una sola vez** sobre las 1.122 unidades
territoriales reproyectadas, y se consultó por bounding box para cada uno de los
6.294 títulos mineros antes de calcular la intersección geométrica real solo sobre
las candidatas — **no se ejecutó el producto cartesiano completo**
(6.294 × 1.122 = 7.061.868 pares posibles).

| Indicador | Valor |
|---|---|
| Pares candidatos por bounding box | 15.444 |
| Pares evitados frente al producto cartesiano completo | 7.046.424 |
| Intersecciones con área positiva | 8.263 |
| Contactos sin área (solo tocan el límite) | 0 |
| Títulos sin ninguna intersección con área positiva | 1 |

Instrumentación de tiempos (módulo `run_national_intersection`):

| Etapa | Tiempo |
|---|---|
| Reproyección de títulos (6.294, una vez cada uno) | 4,2679 s |
| Construcción del índice STRtree | 0,0004 s |
| Consulta por bounding box | 0,1421 s |
| Intersección geométrica real | 4,0787 s |
| **Total del módulo** | **8,6611 s** |
| Memoria pico (tracemalloc) | 3,53 MB |

Reglas geométricas aplicadas: solo un área de intersección positiva cuenta como
asignación territorial; un contacto de solo línea/punto se registra con
`solo_toca_limite=True` (0 % de estos en esta corrida, no descartado en silencio,
solo excluido de la tabla relacional y de los indicadores de área); si una
intersección produce una `GeometryCollection` mixta, se conservan solo los
componentes poligonales, documentando los descartados (no ocurrió en esta corrida:
0 componentes no poligonales descartados).

## D. Tabla relacional título–unidad territorial

`data/processed/integrated/mineria_titulo_unidad_territorial.csv` (3,1 MB, 8.263
filas — una por combinación real `codigo_expediente` + `cod_dane_mpio` con área de
intersección positiva; 6.293 códigos de expediente únicos, 856 unidades
territoriales únicas). Columnas: `codigo_expediente`, `cod_dane_mpio`,
`cod_dane_dpto`, `nombre_mpio`, `nombre_dpto`, `tipo_unidad_territorial`,
`area_interseccion_m2`, `area_interseccion_ha`, `area_geometria_titulo_ha`,
`area_reportada_anm_ha`, `pct_area_titulo_en_unidad`, `area_unidad_territorial_ha`,
`pct_area_unidad_titulada_por_este_titulo`, `es_fragmento_menor_0_01_ha`,
`modalidad_norm`, `etapa_norm`, `estado_norm`, `minerales_norm`,
`instrumento_ambiental`, `fecha_de_inscripcion`, `anio_inscripcion`,
`fecha_terminacion`, `anio_terminacion`, `diferencia_area_ha`,
`ratio_area_geometria_reportada`, `fuente_catastro`,
`fecha_actualizacion_fuente_catastro`.

`area_geometria_titulo_ha` (área real de la geometría del título, calculada en
EPSG:9377) y `area_reportada_anm_ha` (campo `area_ha` declarado por la ANM en el
catastro) se conservan **ambas, sin que una reemplace a la otra**;
`diferencia_area_ha` y `ratio_area_geometria_reportada` documentan la discrepancia
sin corregirla arbitrariamente. 36 filas tienen `es_fragmento_menor_0_01_ha=True`
(fragmentos menores a 0,01 ha) — se **mantienen**, no se descartan.

**Nota de vigencia de la fuente:** el catastro minero ANM WFS
(`geo.anm.gov.co`, capa `Titulo_Vigente`) declara como fecha de actualización el
**22/03/2023**. Ese dato queda en el campo `fecha_actualizacion_fuente_catastro`
de cada fila y **no debe presentarse como la fecha de este análisis**.

## E. Control de conservación de área por título

`tolerancia_area_m2 = 1,0` (0,0001 ha), documentada y aplicada consistentemente en
`build_area_conservation_table`. No oculta diferencias grandes: solo clasifica
`dentro_de_tolerancia` sí/no; toda diferencia queda en `diferencia_no_asignada_ha`.

| Indicador | Valor |
|---|---|
| Títulos evaluados | 6.294 |
| Dentro de tolerancia | 6.266 |
| Fuera de tolerancia | 28 |
| Con asignación superior a 100 % (más allá de tolerancia) | 5 |
| Sin ninguna intersección territorial | 1 |
| Diferencia no asignada (ha) — máx / mín | 3.564,89 / −3.196,54 |

Los casos con mayor discrepancia absoluta (p. ej. `ICQ-080212X`: geometría de
3.600 ha pero solo 35,6 ha asignadas a unidades territoriales — 0,99 % asignado; o
`HCA-144`/`HCA-146`/`HCA-145`/`GLL-15R`/`GLL-15T`: suma de intersecciones **mayor**
al área propia del título, hasta 200 % de asignación) están documentados en
`outputs/reports/mining_integration/mining_quality_checks.md` con su detalle
completo. No se corrigieron ni truncaron: son indicios de geometrías de entrada con
partes autointersectadas (multipolígonos con solapamiento interno tras la
reparación de validez de la Fase 3D.1) o de discrepancias entre la geometría real y
el `area_ha` declarado por la ANM — ambos escenarios quedan fuera del alcance de
esta fase, que solo los reporta.

## F. Anotaciones ANM agregadas

`aggregate_anm_annotations` agrupa por `codigo_expediente` **antes** de cualquier
unión con el catastro (para no duplicar área por la relación 1-a-muchos entre un
expediente y sus varias anotaciones). Resultado: 6.769 expedientes con anotaciones
agregadas.

| Indicador | Valor |
|---|---|
| Títulos en catastro | 6.294 |
| Títulos con anotaciones | 6.037 |
| Títulos sin anotaciones | 257 |
| Expedientes de anotaciones no encontrados en el catastro | 732 |
| Porcentaje de correspondencia | 95,92 % |

## G. Indicadores agregados por unidad territorial

`data/processed/features/mineria_por_unidad_territorial.csv` (447,0 KB, **1.122
filas — una por cada unidad del universo analítico**, incluidas las 266 sin ningún
título minero, con valores en cero, nunca filas ausentes). Columnas agrupadas por
identificación, área, presencia minera, etapa/modalidad, minerales, gestión
ambiental, anotaciones y calidad — ver el listado completo de 28 columnas en el
propio CSV o en `src/aquabosque/features/mining.py::build_territorial_indicators_table`.

- 856 unidades (76,3 %) tienen al menos un título minero; 266 no tienen ninguno.
- **`area_titulada_suma_ha`** (permite superposición entre títulos, suma simple) y
  **`area_titulada_union_ha`** (unión geométrica, sin doble conteo) se calculan
  **ambas**, junto a sus respectivos `pct_area_unidad_titulada_suma` y
  `pct_area_unidad_titulada_union`. Se recomienda usar la variante de **unión**
  para interpretar la proporción física real del territorio cubierto — la suma
  puede superar el 100 % del área de la unidad cuando hay títulos superpuestos
  entre sí (distintas modalidades o etapas sobre la misma área), lo cual **no es
  un error** y no se trunca.
- 262 unidades tienen `area_titulada_suma_ha > area_titulada_union_ha` (indicio de
  superposición interna entre títulos).
- 1 unidad supera el 100 % en `pct_area_unidad_titulada_suma`: **17442 — Marmato
  (Caldas)**, con 125 títulos, 102,41 % de suma vs. 70,87 % de unión (proporción
  física real).

**Advertencia explícita sobre `instrumento_ambiental`:** un valor `'N'` (o la
ausencia del campo) en `n_titulos_con_instrumento_ambiental` /
`pct_titulos_con_instrumento_ambiental` **no debe interpretarse como ausencia real
de licencia o instrumento ambiental** sin documentar esta limitación: es solo lo
que declara la fuente ANM en ese campo específico del catastro, que puede no
reflejar la totalidad de la gestión ambiental real de cada título.

### Unidades con mayor número de títulos mineros (top 5)

| cod_dane_mpio | Municipio | Departamento | Títulos | % área titulada (unión) |
|---|---|---|---|---|
| 05604 | Remedios | Antioquia | 140 | 22,80 % |
| 17442 | Marmato | Caldas | 125 | 70,87 % |
| 54001 | San José de Cúcuta | Norte de Santander | 106 | 11,18 % |
| 15759 | Sogamoso | Boyacá | 106 | 14,83 % |
| 15480 | Muzo | Boyacá | 78 | 44,68 % |

### Unidades con mayor % de área titulada — unión (top 5)

| cod_dane_mpio | Municipio | Departamento | % área titulada (unión) | Títulos |
|---|---|---|---|---|
| 05044 | Anzá | Antioquia | 72,17 % | 20 |
| 17442 | Marmato | Caldas | 70,87 % | 125 |
| 73270 | Falan | Tolima | 57,12 % | 16 |
| 23682 | San José de Uré | Córdoba | 55,75 % | 4 |
| 44078 | Barrancas | La Guajira | 53,91 % | 23 |

Rankings completos (top 15) en
`outputs/reports/mining_integration/mining_territorial_indicators.md`.

## H. Qué NO produce esta fase

Explícitamente, ninguna salida de esta fase contiene: `riesgo_minero`,
`score_minero`, `riesgo_ambiental`, probabilidad de contaminación, probabilidad de
deforestación, clasificación de minería ilegal, afectación causada por minería, ni
ningún índice compuesto. Los indicadores generados son **descriptivos de presión
minera formal registrada** (conteos, áreas, proporciones), no causales ni de
ilegalidad.

## Archivos creados o modificados

- `src/aquabosque/geo/intersection.py` (nuevo) — motor de intersección con
  `STRtree`, reglas de área positiva / contacto sin área / componentes no
  poligonales, instrumentación de tiempos y memoria.
- `src/aquabosque/utils/spatial_cache.py` (nuevo) — caché regenerable de
  geometrías reproyectadas, invalidado por huella SHA-256.
- `src/aquabosque/features/mining.py` (nuevo) — agregación de anotaciones ANM,
  tabla relacional título–unidad, control de conservación de área, indicadores
  territoriales.
- `scripts/06_build_mining_territorial.py` (nuevo) — orquesta toda esta fase.
- `data/processed/integrated/mineria_titulo_unidad_territorial.csv` (+ `.metadata.json`).
- `data/processed/features/mineria_por_unidad_territorial.csv` (+ `.metadata.json`).
- `data/interim/spatial_cache/territorial_units_epsg9377.pkl` (+ `.metadata.json`).
- `outputs/reports/mining_integration/mining_spatial_intersection.md`,
  `mining_territorial_indicators.md`, `mining_quality_checks.md` (nuevos).
- `.gitignore` — se añadió `data/interim/spatial_cache/*` (con excepción de
  `.gitkeep`) al patrón ya existente de `data/interim/*`.

## Riesgos y limitaciones pendientes

- El catastro minero ANM está declarado como actualizado al 22/03/2023 por el
  propio geoservicio; cualquier título registrado, modificado o extinguido después
  de esa fecha no está reflejado aquí.
- No se incluye minería informal o ilegal: todos los indicadores provienen
  exclusivamente de títulos formalmente registrados en el catastro ANM.
- `instrumento_ambiental` refleja solo lo declarado en ese campo específico de la
  fuente ANM, no una verificación independiente de licenciamiento ambiental.
- Algunos títulos (`HCA-144`, `HCA-146`, `HCA-145`, `GLL-15R`, `GLL-15T`,
  `ICQ-080212X`, entre otros) muestran discrepancias notables entre el área propia
  de su geometría y la suma de sus intersecciones territoriales, o entre su área
  geométrica real y el `area_ha` declarado por la ANM. Quedan documentados sin
  corregir; investigar su causa (geometría de entrada vs. dato tabular de la ANM)
  queda fuera de alcance de esta fase.
- No se determinó si conviene simplificar geometrías para futuras integraciones a
  mayor escala (p. ej. con deforestación o RUNAP en fases posteriores); esta fase
  preservó fidelidad geométrica total.

## Cierre de calidad Fase 4A.1

Antes de integrar calidad hídrica, la Fase 4A.1 auditó y cerró la trazabilidad
metodológica de la Fase 4A: explicó y clasificó las diferencias de asignación
espacial detectadas, validó las métricas de unión territorial y corrigió la
trazabilidad documental. **No recalculó ningún indicador, no integró calidad
hídrica, no descargó fuentes nuevas y no modificó datos crudos ni límites
administrativos.** Generada por `scripts/07_audit_mining_quality.py`, que usa el
nuevo `src/aquabosque/features/mining_audit.py`.

### Los 28 títulos fuera de tolerancia, explicados y clasificados

`data/processed/audit/mineria_area_conservation_audit.csv` (28 filas) reconstruye,
para cada título, el residual geométrico real (`geometría del título − unión de
sus intersecciones territoriales`, en EPSG:9377) y lo clasifica:

| Causa | N | Evidencia resumida |
|---|---|---|
| `hueco_entre_limites_territoriales` | 22 | el residual está a menos de 100 m de la unidad territorial (o 94663) más cercana — consistente con un *sliver* entre límites administrativos adyacentes, no con territorio sin cobertura. Incluye el único título sin ninguna intersección (`583`, a 24,0 m de `54001`). |
| `solape_entre_limites_territoriales` | 5 | `asignacion_superior_100=True` pero el residual real es prácticamente vacío: la aparente sobre-asignación es un artefacto de que dos unidades territoriales se solapan entre sí (ver más abajo). |
| `tolerancia_numerica` | 1 | diferencia absoluta < 0,01 ha: ruido numérico de reproyección. |
| `area_en_94663_excluida` | 0 | ningún título fuera de tolerancia se solapa con la geometría de 94663 (usada solo como capa de auditoría, verificado geométricamente, nunca reincorporada al universo analítico). |
| `fuera_universo_divipola_vigente`, `fuera_cobertura_geometrica_territorial`, `efecto_reparacion_geometrica`, `geometria_titulo_fuera_de_colombia` | 0 cada una | verificadas y descartadas con evidencia (ninguno de los 28 coincide con las 22 geometrías reparadas en la Fase 3D.1; todos los bbox caen dentro de la envolvente nacional). |

- **Área residual total no asignada:** 5.899,94 ha (suma de los 28 residuales reales).
- **Residual asociado a 94663:** 0 ha en todos los casos.
- 15 de los 28 casos quedan marcados `requiere_revision_manual=True` (diferencia
  ≥ 10 ha o causa no concluyente) — incluye títulos donde el residual real es
  grande (p. ej. `ICQ-080212X`: 3.564,89 ha, `LI9-10311`: 1.777,56 ha) y la
  cercanía de 0 m a una unidad territorial **no** implica que toda esa área sea
  una franja delgada; se documenta esa advertencia explícitamente en el CSV.
- **Autocorrección:** el resumen de la Fase 4A llamó "notables" a 6 casos sin
  incluir `LI9-10311`, que en realidad tiene la tercera mayor diferencia absoluta
  de los 28 — se documenta en `mining_area_conservation_audit.md`.

### Hallazgo principal: solape territorial de 27493 (Bajirá)

La auditoría de topología territorial (`territorial_topology_audit.md`) validó
espacialmente las 1.122 unidades analíticas: 0 geometrías inválidas, 0 áreas no
positivas, 0 códigos duplicados, 0 contenciones completas. Encontró **6 pares de
unidades que se solapan con área positiva, totalizando 128.926,00 ha** — casi en
su totalidad (>99,99 %) es **27493 (Nuevo Belén de Bajirá)**, cuya geometría se
recuperó del DANE MGN2025 en la Fase 3D.1, solapándose con el territorio que la
capa ArcGIS Divipola (usada para las otras 1.121 unidades) asigna a sus vecinos
(27615, 05480, 05837, 27150, 05234). El área propia de 27493 es prácticamente
idéntica al área total de solape, es decir, casi todo su polígono se superpone
con territorio ya reclamado por otra fuente geométrica. **Esta fase no asume ni
afirma ninguna causa administrativa o legal** para esa discrepancia de límites —
solo reporta el hallazgo geométrico, verificado con `shapely`. Se verificó además
que al menos 5 de los 28 títulos fuera de tolerancia (`HCA-144`, `HCA-145`,
`HCA-146`, `GLL-15R`, `GLL-15T`) están físicamente ubicados en esa zona y quedan
asociados a más de una unidad territorial en `mineria_titulo_unidad_territorial.csv`,
lo que explica directamente su `asignacion_superior_100`. Ningún indicador POR
UNIDAD queda inválido (cada unidad se validó contra su propia geometría), pero
cualquier suma NACIONAL de `n_titulos_mineros` entre unidades sobreestimaría estos
títulos.

El único hueco relevante (>1 ha) detectado en la unión nacional de las 1.122
unidades (470.232,17 ha) **coincide al 100 % con la geometría de 94663**: es el
resultado esperado de excluirla del universo analítico mientras sigue presente en
la capa geométrica, no un hueco de cobertura sin explicar.

### Validación de área titulada por unidad territorial

Las 6 reglas de la sección F (`area_titulada_union_ha ≤ area_unidad_territorial_ha`,
`pct_area_unidad_titulada_union ≤ 100 %`, `area_titulada_union_ha ≤ area_titulada_suma_ha`,
`n_titulos_mineros` = conteo distinto de `codigo_expediente`, sin pares
`codigo_expediente`+`cod_dane_mpio` duplicados, unidades sin títulos en cero) se
validaron sobre las 1.122 unidades y **las 1.122 pasaron sin ninguna excepción**
— no se generó tabla de excepciones porque no hubo nada que reportar.

### Auditoría de correspondencia de ANM Anotaciones RMN

`data/processed/audit/anm_annotation_correspondence_audit.csv` (7.026 filas)
clasifica los 6.294 títulos del catastro y los 732 expedientes de anotaciones sin
correspondencia (95,92 % de correspondencia = 6.037/6.294). Se probó normalización
determinista de espacios/mayúsculas sobre todos los códigos: **0 coincidencias
recuperadas** — la ausencia de correspondencia no es un problema de formato de
texto. Solo 4 de los 732 expedientes huérfanos tienen su última anotación antes de
2020; el resto (728) tiene actividad reciente (2023-2025) sin explicación
disponible en los datos de este proyecto. Se documenta como hipótesis no
confirmada que el catastro WFS solo incluye títulos `Titulo_Vigente`, mientras el
RMN registra trámites que pueden no haber llegado nunca a título vigente — no se
confirmó contra la fuente ANM original (fuera de alcance).

### Correcciones documentales

- `scripts/06_build_mining_territorial.py` atribuía
  `catastro_minero_anm_spatial_ready.geojson` a la **Fase 3C** en la metadata de
  salida; corregido para identificarlo como producto de la **Fase 3D.1**
  (preparado por `scripts/05_reconcile_and_prepare_spatial.py` a partir del
  catastro limpio de la Fase 3C, que sí es un producto de esa fase).
- Se revisó la consistencia de la fecha declarada del geoservicio ANM
  (22/03/2023) en todos los documentos y reportes del proyecto: en todos los
  casos ya se presenta explícitamente como "fecha declarada por el geoservicio",
  nunca como fecha del análisis. No se encontraron correcciones adicionales
  necesarias.

### Archivos de la Fase 4A.1

- `src/aquabosque/features/mining_audit.py` (nuevo).
- `scripts/07_audit_mining_quality.py` (nuevo).
- `data/processed/audit/mineria_area_conservation_audit.csv` (+ `.metadata.json`).
- `data/processed/audit/anm_annotation_correspondence_audit.csv` (+ `.metadata.json`).
- `outputs/reports/mining_integration/mining_area_conservation_audit.md`,
  `mining_annotation_correspondence_audit.md`, `territorial_topology_audit.md`,
  `phase4a_quality_closure.md` (nuevos).

### Riesgos que permanecen abiertos tras la Fase 4A.1

- El solape territorial de 27493 (128.926 ha) no se corrigió: mezclar la
  geometría DANE MGN2025 de Bajirá con la capa ArcGIS Divipola del resto del
  país seguirá produciendo doble conteo de títulos entre esas unidades en
  cualquier suma nacional futura.
- 22 de los 28 casos fuera de tolerancia se clasificaron como
  `hueco_entre_limites_territoriales` por proximidad geométrica, sin verificar si
  la causa de fondo es un artefacto de digitalización o una discrepancia real de
  límites administrativos.
- 728 expedientes de anotaciones sin correspondencia en el catastro quedan sin
  explicación confirmada.
- No se determinó si conviene, en una fase futura, resolver el solape de Bajirá
  sustituyendo parte de la capa ArcGIS Divipola por MGN2025 en la zona en
  disputa.
