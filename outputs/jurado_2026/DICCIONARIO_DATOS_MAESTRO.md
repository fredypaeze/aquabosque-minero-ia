# Diccionario de Datos Maestro — AquaBosque Minero IA
_Cheat sheet de defensa ante jurado. Cada dato de la app, su origen, cálculo y significado. Basado en el código real del repositorio (`build_master.py`, `build_target.py`, `train.py`, `firms_signal.py`) y los datos vigentes._

**Convenciones de "Naturaleza":** `Fuente Cruda` (dato reportado tal cual por la entidad) · `Índice Normalizado` (calculado 0–1) · `Salida de Modelo (IA)` (inferencia XGBoost/SHAP) · `Metadato Territorial` (identidad/geografía).

> **Nota de honestidad (para el jurado):** la etiqueta de riesgo es una **fórmula técnica de priorización**, no una medición de daño. El modelo de IA la re-aprende y la explica; su valor es priorizar y explicar, no "acertar". Ningún dato prueba causalidad ni ilegalidad.

---

## 1) Inicio

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Inicio | Tarjeta KPI | **Municipios analizados** (1.122) | Cuántos municipios cubre el sistema: todo el país. | Metadato Territorial | DANE (DIVIPOLA) | Conteo de la base municipal oficial (1 fila por municipio con centroide). | Fijo: 1.122 | municipios (conteo) |
| Inicio | Tarjeta KPI | **Riesgo crítico** (57) | Municipios en la máxima prioridad de revisión. | Salida de Modelo (IA) | Cálculo propio sobre datos abiertos | Conteo de municipios con `riesgo_nivel = Crítico` (score ≥ percentil 95). | Conteo (≈5% superior) | municipios (conteo) |
| Inicio | Tarjeta KPI | **Riesgo alto** (112) | Municipios de atención prioritaria. | Salida de Modelo (IA) | Cálculo propio | Conteo con score entre p85 y p95. | Conteo (≈10%) | municipios (conteo) |
| Inicio | Tarjeta KPI | **Riesgo medio** (280) | Municipios en seguimiento. | Salida de Modelo (IA) | Cálculo propio | Conteo con score entre p60 y p85. | Conteo | municipios (conteo) |
| Inicio | Sección "Fuentes" | Listado de fuentes | Muestra que todo sale de datos abiertos oficiales. | Metadato | ANM, IDEAM, DANE, RUNAP, PDET | Enlaces a los datasets integrados. | — | — |

---

## 2) Mapa de riesgo

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Mapa de riesgo | Mapa de coropletas (polígonos) | **Nivel de riesgo por municipio** | Colorea cada municipio según su prioridad. | Salida de Modelo (IA) | Cálculo propio + geometría DANE | Polígonos DIVIPOLA (GeoJSON) coloreados por `riesgo_nivel`. | Verde=Bajo · Amarillo=Medio · Naranja=Alto · Rojo=Crítico | categórico (4 niveles) |
| Mapa de riesgo | Mapa (vista Puntos) | **Score de priorización** (tamaño) | El punto crece con la prioridad. | Índice/Salida | Cálculo propio | Tamaño del punto ∝ `riesgo_score` sobre el centroide del municipio. | 0–1 (mayor = más prioridad) | adimensional (0–1) |
| Mapa de riesgo | Filtro | **Departamento / Niveles / Vista** | Acota lo que se muestra. | Metadato Territorial | DANE | Filtros sobre el dataframe; no altera el cálculo. | Categórico | — |
| Mapa de riesgo | Tarjeta KPI | **Municipios en vista** | Cuántos municipios se ven con los filtros. | Metadato Territorial | — | Conteo de filas filtradas. | Conteo | municipios |
| Mapa de riesgo | Tarjeta KPI | **🔴 Crítico / 🟠 Alto (en vista)** | Cuántos críticos/altos hay en el filtro actual. | Salida de Modelo (IA) | Cálculo propio | Conteo por `riesgo_nivel` dentro del filtro. | Conteo | municipios |
| Mapa de riesgo | Tarjeta KPI | **Score máx.** | El puntaje más alto en la vista. | Índice/Salida | Cálculo propio | `max(riesgo_score)` de la vista. | 0–1 | adimensional (0–1) |
| Mapa de riesgo | Tabla superior | **Top 5** (Municipio, Departamento, Nivel, Score) | Los 5 más prioritarios de la vista. | Salida de Modelo (IA) | Cálculo propio | Orden descendente por `riesgo_score`. | 0–1 / categórico | adimensional / — |

---

## 3) Ranking

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Ranking | Gráfico de barras (Top N) | **Score de priorización** | Ordena los municipios de mayor a menor prioridad. | Índice/Salida | Cálculo propio | Barra horizontal = `riesgo_score`, color = `riesgo_nivel`. | 0–1 | adimensional (0–1) |
| Ranking | Deslizador | **Top N** | Cuántos municipios mostrar. | Metadato | — | Control de UI (10–200). | 10–200 | conteo |
| Ranking | Tabla | **Nivel / Score** | Nivel y puntaje por municipio. | Salida de Modelo (IA) | Cálculo propio | Ver definición de `riesgo_score` y `riesgo_nivel`. | 0–1 / 4 niveles | adimensional |
| Ranking | Tabla | **Minero / Deforest. / Hídrico / Sensib.** | Los 4 índices que componen el puntaje. | Índice Normalizado | ANM / IDEAM / IDEAM / RUNAP+PDET | Ver sección "Índices" abajo. | 0–1 | adimensional (0–1) |
| Ranking | Botón | **Descargar ranking (CSV)** | Exporta la tabla completa. | — | — | Descarga del dataframe a CSV. | — | archivo |

---

## 4) Ficha territorial

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Ficha territorial | Tarjeta KPI | **Nivel de riesgo** | La prioridad del municipio en palabras. | Salida de Modelo (IA) | Cálculo propio | Clasificación por cuantil del score (ver `riesgo_nivel`). | Bajo/Medio/Alto/Crítico | categórico |
| Ficha territorial | Tarjeta KPI | **Score de priorización** | El puntaje técnico exacto. | Índice/Salida | Cálculo propio | Suma ponderada de 5 índices (ver fórmula). | 0–1 (mayor = más prioridad) | adimensional (0–1) |
| Ficha territorial | Tarjeta KPI | **Predicción del modelo** | Nivel que asigna la IA (XGBoost). | Salida de Modelo (IA) | Cálculo propio | `argmax` de XGBoost multiclase sobre 15 variables. | Bajo/Medio/Alto/Crítico | categórico |
| Ficha territorial | Tarjeta KPI | **Confianza** | Qué tan seguro está el modelo de esa clasificación. | Salida de Modelo (IA) | Cálculo propio | `max(predict_proba)` de XGBoost. | 0–100% | % (0–1) |
| Ficha territorial | Gráfico de radar | **Perfil por dimensión** (Minero, Deforestación, Hídrico, Sensibilidad) | Muestra qué factor domina en ese municipio. | Índice Normalizado | ANM/IDEAM/IDEAM/RUNAP | Los 4 índices 0–1 en ejes de un radar. | 0–1 por eje | adimensional (0–1) |
| Ficha territorial | Tarjeta "Factor dominante" | **Mayor factor de priorización** | El índice más alto del municipio. | Índice Normalizado | (según dimensión) | `argmax` de los índices del municipio. | 0–1 | adimensional (0–1) |

---

## 5) Explicabilidad (SHAP) — _atención especial_

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Explicabilidad | Gráfico de barras SHAP | **Importancia SHAP (media \|valor\|)** por variable | Qué variables pesan más, en promedio, en las decisiones del modelo. | Salida de Modelo (IA) | Cálculo propio (TreeExplainer) | Media del valor absoluto de SHAP por variable sobre las 4 clases y todos los municipios. Variables tope: `idx_minero`, `idx_deforestacion`, `deforestacion_ha`, `idx_fuego`. | ≥ 0 (mayor = más influye) | adimensional (media \|SHAP\|) |
| Explicabilidad | Tarjeta KPI | **Accuracy** (89.0%) | Aciertos del modelo en la prueba. | Salida de Modelo (IA) | Cálculo propio | Exactitud en el 25% de test (split estratificado). **Es alta por construcción** (la etiqueta es una fórmula) → no se vende como mérito. | 0–100% | % |
| Explicabilidad | Tarjeta KPI | **Línea base (clase mayoritaria)** (60.1%) | Qué acertaría "adivinar siempre lo más común". | Salida de Modelo (IA) | Cálculo propio | Frecuencia de la clase mayoritaria en test; referencia honesta de comparación. | 0–100% | % |
| Explicabilidad | Tarjeta KPI | **F1-macro** (0.78) | Calidad equilibrada entre las 4 clases. | Salida de Modelo (IA) | Cálculo propio | Promedio no ponderado del F1 de las 4 clases. | 0–1 | adimensional |

---

## 6) Datos abiertos

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Datos abiertos | Tabla de fuentes | **Dimensión / Entidad / Fuente-URL / Registros / Clave territorial / Limitación** | Ficha de cada fuente: qué mide, quién la produce y cómo se conecta al municipio. | Metadato | ANM, IDEAM, DANE, RUNAP, PDET | Documenta el origen y el método de cruce (código DANE vs centroide). | — | según fila |

---

## 7) Monitoreo satelital (capa NRT)

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Monitoreo satelital | Tarjeta KPI | **🔥 Focos (7 días)** | Cuántos puntos de calor detectó el satélite en el país esta semana. | Fuente Cruda | NASA FIRMS (VIIRS SNPP+NOAA-20, MODIS C6.1) | Suma de detecciones asignadas a municipios en ventana de 7 días. | Conteo | focos (conteo) |
| Monitoreo satelital | Tarjeta KPI | **Municipios con fuego** | Cuántos municipios tienen al menos un foco activo. | Fuente Cruda | NASA FIRMS | Conteo de municipios con `focos_7d > 0`. | Conteo | municipios |
| Monitoreo satelital | Tarjeta KPI | **⚠️ Prioridad máxima** | Municipios que el modelo prioriza **y** con fuego hoy. | Salida IA + Cruda | Cálculo propio + FIRMS | Intersección: `riesgo_nivel ∈ {Alto,Crítico}` **y** `focos_7d > 0`. | Conteo | municipios |
| Monitoreo satelital | Tarjeta KPI | **🆕 Actividad nueva** | Fuego intenso donde el índice histórico no marcaba prioridad. | Salida IA + Cruda | Cálculo propio + FIRMS | `frp_total > 200` **y** `riesgo_nivel ∈ {Bajo,Medio}`. | Conteo | municipios |
| Monitoreo satelital | Mapa de coropletas | **Focos por municipio** | Mapa de intensidad de fuego reciente. | Fuente Cruda | NASA FIRMS | Coropleta por `focos_7d`. | 0 → alto | focos |
| Monitoreo satelital | Tabla | **Focos 7d** | Número de focos del municipio en 7 días. | Fuente Cruda | NASA FIRMS | Conteo de detecciones VIIRS/MODIS por polígono municipal. | ≥ 0 | focos (conteo) |
| Monitoreo satelital | Tabla | **FRP** (frp_total) | Intensidad acumulada del fuego (qué tan fuerte quema). | Fuente Cruda | NASA FIRMS | Suma de la Potencia Radiativa del Fuego (Fire Radiative Power) de los focos del municipio. | ≥ 0 (mayor = quema más intensa) | **MW (megavatios)** |

---

## 8) Asistente IA (capa generativa)

| Página | Componente Visual | Nombre del Dato | Definición Práctica | Naturaleza | Fuente Oficial | Metodología / Construcción | Interpretación (Rango) | Medida |
|---|---|---|---|---|---|---|---|---|
| Asistente IA | Respuesta del asistente | **Respuesta aterrizada + fuentes** | Explica en lenguaje natural, solo con la evidencia del sistema. | Salida de Modelo (IA) | LLM local (Ministerio) | Recuperación con embeddings `bge-m3` sobre el corpus del sistema + generación con LLM local; cita la fuente y no inventa. | Texto | — |

---

## Anexo A · Índices normalizados (el corazón del score) — _atención especial_

| Nombre | Definición Práctica | Fuente Oficial | Metodología / Fórmula | Rango | Medida |
|---|---|---|---|---|---|
| **idx_minero** | Presión minera formal del municipio. | ANM (RUCOM + volumen) · datos.gov.co | `minero_raw = mineria_titulos + mineria_volumen/1000`; luego **log1p + normalización MinMax** a [0,1]. Cruce por **código DANE** (exacto). | 0–1 (1 = mayor presión) | adimensional (0–1) |
| **idx_deforestacion** | Pérdida de bosque registrada. | IDEAM / SMByC | `deforestacion_ha` → **log1p + MinMax**. Cruce **por nombre de municipio**; sin registro = 0 (documentado). | 0–1 (1 = más deforestación) | adimensional (0–1) |
| **idx_fuego** | Señal satelital de quema reciente (dimensión dinámica). | NASA FIRMS | `log1p(frp_total) / log1p(max frp_total)`, acotado a [0,1]. Se refresca a diario. | 0–1 (1 = fuego más intenso) | adimensional (0–1) |
| **idx_hidrico** | Afectación de la calidad del agua. | IDEAM (DHIME · ICA) | `1 − ICA` donde hay estación a <50 km del centroide (haversine); **sin estación = 0** y se marca `hidrico_sin_dato`. | 0–1 (1 = agua más degradada) | adimensional (0–1) |
| **idx_sensibilidad** | Valor ambiental/social a proteger. | RUNAP + PDET (DANE) | `runap_hectareas` → log1p+MinMax; **+0.25 si el municipio es PDET** (posconflicto). Cruce RUNAP por centroide; PDET por código DANE. | 0–1 (1 = mayor sensibilidad) | adimensional (0–1) |

**Fórmula del score y de la etiqueta (documentada en `build_target.py`):**
```
riesgo_score = 0.30·idx_minero + 0.25·idx_deforestacion + 0.15·idx_fuego
             + 0.20·idx_hidrico + 0.10·idx_sensibilidad         (rango real ≈ 0–0.5)

riesgo_nivel (por CUANTILES del score):  Crítico ≥ p95 · Alto ≥ p85 · Medio ≥ p60 · Bajo < p60
```
_Se usan cuantiles (priorización relativa) porque las señales están dispersas y con umbrales absolutos las clases Alto/Crítico quedarían casi vacías._

**Modelo (`train.py`):** XGBoost multiclase · 15 variables (5 índices + 10 crudas, incl. `focos_7d`) · `n_estimators=300, max_depth=4, learning_rate=0.08` · split estratificado 75/25 · explicabilidad SHAP.

---

## Anexo B · Fuentes crudas y unidades

| Variable cruda | Definición | Fuente | Cruce | Medida |
|---|---|---|---|---|
| `mineria_titulos` | Nº de títulos/explotadores mineros formales | ANM RUCOM (datos.gov.co `42ha-fhvj`) | código DANE (exacto) | títulos (conteo) |
| `mineria_volumen` | Volumen de explotación (año más reciente) | ANM (`r85m-vv6c`) | código DANE | **heterogénea (t / m³ según mineral)** — no comparable directo entre minerales |
| `mineria_regalias` | Regalías pagadas | ANM | código DANE | **COP (pesos)** |
| `deforestacion_ha` | Hectáreas deforestadas (último año disp.) | IDEAM / SMByC | nombre de municipio | **ha (hectáreas)** |
| `agua_ica_medio` | ICA medio de estaciones cercanas | IDEAM DHIME (campo `ica5`) | centroide, haversine <50 km | adimensional (0–1; 1 = agua buena) |
| `agua_estaciones` | Nº de estaciones ICA asignadas | IDEAM DHIME | centroide | estaciones (conteo) |
| `runap_areas` | Nº de áreas protegidas cercanas | RUNAP | centroide | áreas (conteo) |
| `runap_hectareas` | Hectáreas protegidas cercanas | RUNAP | centroide | **ha (hectáreas)** |
| `es_pdet` | ¿Municipio PDET (posconflicto)? | DANE / PDET (datos.gov.co) | código DANE | binario (0/1) |
| `focos_7d` | Focos de calor activos (7 días) | NASA FIRMS | point-in-polygon | focos (conteo) |
| `frp_total` | Potencia radiativa acumulada del fuego | NASA FIRMS | point-in-polygon | **MW (megavatios)** |

---

## Anexo C · Incertidumbres declaradas (cero alucinaciones)

- **`mineria_volumen` — unidad heterogénea:** la fuente ANM mezcla minerales con distintas unidades (toneladas, m³…). Por eso en el índice se usa **transformada log + MinMax** (comparación relativa), no el valor absoluto. No debe leerse como una magnitud física única.
- **`idx_hidrico` — cobertura parcial:** solo ~71 municipios tienen estación ICA a <50 km; en el resto vale 0 y se marca `hidrico_sin_dato`. **0 significa "sin dato observado", no "agua sana".**
- **`deforestacion_ha` — cruce por nombre:** al no venir con código DANE, se asigna por nombre de municipio; puede haber omisiones por homónimos o tildes. Sin registro = 0 (no significativo, documentado).
- **`idx_fuego` (Sentinel-2 / U-Net):** la detección profunda por imagen es prueba de capacidad sobre AOIs; la señal operativa en la app es **FIRMS (focos térmicos)**, no clasificación de imagen cruda a nivel nacional.
- **Accuracy alta ≠ mérito predictivo:** la etiqueta es una fórmula; el modelo la re-aprende. Lo defendible es la **priorización interpretable (SHAP)**, no la exactitud.
