# Metodología del MVP — AquaBosque Minero IA

## Universo

1.122 unidades territoriales DIVIPOLA vigentes (`presente_divipola_vigente=True` en
`data/processed/territorio/universo_territorial_divipola.csv`), verificadas: cero códigos
duplicados, cero nulos, correspondencia completa con la geometría MGN2025 (1.122 features).

## Componentes

### Minería (`score_presion_minera`)

Fuente: `data/processed/features/mineria_por_unidad_territorial_mgn2025.csv` (canónico
MGN2025, Fase 09). Combinación de percentiles nacionales:

`0,5 × percentil(pct_area_unidad_titulada_UNIÓN) + 0,3 × percentil(n_titulos_mineros) + 0,2 × percentil(anotaciones_total)`

**Nunca** se usa área **suma** (que duplica área por títulos superpuestos) como sustituto del
área **unión** (área real ocupada). Un municipio sin títulos tiene score 0 real (ausencia real
de presión minera formal, no dato faltante).

### Señal hídrica estadística (`score_senal_hidrica`)

Fuente: clasificación de idoneidad de parámetros (`clasificacion_idoneidad_parametros_agua.csv`,
Fase 4B.2) filtrada a **Nivel A** (31 combinaciones parámetro+unidad con indicador numérico
aprobado) y valores sitio-parámetro-año (`calidad_agua_sitio_parametro_anio.csv`), usando
**solo resultados cuantificados** (nunca censurados).

1. Por municipio+parámetro+unidad: mediana de las medianas sitio-año (`valor_municipal`).
2. Para **PH**: anomalía = distancia absoluta a 7 (referencia descriptiva, no normativa).
3. Para los demás: anomalía = distancia absoluta a la mediana nacional del mismo
   parámetro+unidad, dividida por la desviación absoluta mediana (MAD) nacional (o desviación
   estándar si MAD=0).
4. Cada anomalía se convierte en un percentil nacional (0-100) dentro de su propio
   parámetro+unidad — nunca se compara directamente el valor crudo entre parámetros distintos.
5. `score_senal_hidrica` = promedio de los 3 percentiles de anomalía más altos disponibles por
   municipio.

**La ausencia de monitoreo NUNCA produce score = 0`** — queda `NaN` y `disponible_agua=False`.

### Detecciones tempranas de deforestación (`score_deteccion_temprana`)

Fuente: consulta acotada al servicio DTD de IDEAM (mismo usado en Fases 2D.1-2D.4), filtrada al
**último periodo completo disponible: 2025-IV**, agregada por `cod_mpio`:
`n_registros_dtd`, `n_coordenadas_dtd_unicas` (redondeo a 5 decimales), `n_nucleos_dtd`,
`n_registros_dtd_codigo_placeholder` (mismo criterio de placeholder de la Fase 2D.2/2D.3: >10
apariciones del mismo `cod_dtd` con más de una coordenada distinta).

`score_deteccion_temprana = 0,7 × percentil(log1p(n_registros_dtd)) + 0,3 × percentil(n_nucleos_dtd)`

No se usa `cod_dtd` como conteo principal (no es único, ver Fase 2D.2). No se convierten puntos
en hectáreas. Este componente **nunca** se presenta como "deforestación confirmada".

### Información forestal piloto

Único municipio con cobertura forestal confirmada: **Puerto Rico, Meta** (`cod_dane_mpio` =
`50590`), con los resultados reales validados en la Fase 2D.1/2D.2 (piloto WCS IDEAM):
bosque 2024 = 49,68 % del área piloto, deforestación 2023-2024 = 2.972,71 ha. Los demás 1.121
municipios quedan con `cobertura_forestal_confirmada_mvp=False` y valores `NaN` — **nunca** se
imputa deforestación igual a cero.

## Cobertura y brecha de información

`n_componentes_disponibles` (0-4: minería siempre disponible, DTD siempre disponible —ambos
producen un valor real incluso en cero—, agua y bosque confirmado pueden faltar).
`score_brecha_informacion = (4 − n_componentes_disponibles) / 4 × 100` — **nunca se mezcla**
con `score_prioridad_evidencia`.

## Score de prioridad por evidencia

Media ponderada con **renormalización de pesos sobre componentes disponibles** (minería 40 %,
agua 35 %, DTD 25 %) — un componente ausente nunca se sustituye por cero, se redistribuye el
peso entre los componentes presentes. Niveles por percentil nacional:

| Nivel | Percentil |
|---|---|
| Muy alta | ≥ P90 |
| Alta | P75-P90 |
| Media | P40-P75 |
| Baja | < P40 |

`principales_razones`, `advertencias_datos` y `resumen_explicativo` se generan
**determinísticamente** a partir de las variables reales de cada fila (no son texto fijo).

## Modelo IA: IsolationForest

`sklearn.ensemble.IsolationForest(random_state=42, contamination=0.10, n_estimators=200)`.
Variables: `log1p(n_titulos_mineros)`, `pct_area_unidad_titulada_union`, `score_senal_hidrica`,
`log1p(n_registros_dtd)`, `n_sitios_monitoreo`, `n_parametros_hidricos_evaluables`,
`disponible_agua`, `disponible_bosque_confirmado`. La imputación por mediana se aplica
**únicamente a la matriz que ve el modelo** — el dataset canónico conserva `NaN` y las
banderas de disponibilidad intactas.

`anomaly_score_raw = -score_samples` (mayor = más atípico). `es_perfil_atipico` =
`predict() == -1`. `explicacion_anomalia`: las 2 variables con mayor desviación estándar
absoluta (z-score) respecto a la población, calculadas de forma determinística (sin SHAP ni
aproximaciones no reproducibles).

Se presenta exclusivamente como **"modelo no supervisado de detección de patrones
territoriales atípicos"** — nunca como probabilidad de contaminación, predicción de
deforestación, riesgo de minería ilegal o cualquier afirmación causal.

## Municipios demo

1. **Puerto Rico, Meta** (obligatorio): único con cobertura forestal confirmada real.
2. Municipio de prioridad alta/muy alta con minería y agua disponibles simultáneamente.
3. Municipio con anomalía IA alta y perfil de datos distinto al anterior (típicamente sin
   monitoreo hídrico), para mostrar un caso contrastante.

La razón exacta de selección de cada uno queda registrada en
`data/processed/mvp/municipios_demo.csv`.
