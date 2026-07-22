# Metodología CRISP-ML(Q) — AquaBosque Minero IA

Documentación del proceso de desarrollo bajo **CRISP-ML(Q)** (Cross-Industry Standard Process for Machine Learning with Quality assurance), requerida por los Términos de Referencia del Concurso Datos al Ecosistema 2026. Cada fase se mapea a artefactos **reales y reproducibles** del repositorio; no se documenta nada que no exista en el código.

| Fase | Artefacto en el repo |
|---|---|
| 1. Comprensión del negocio y los datos | `README.md`, `docs/00_resumen_ejecutivo.md`, `docs/diccionario_datos.md` |
| 2. Preparación de datos | `src/aquabosque/data/`, `src/aquabosque/features/build_master.py` |
| 3. Modelado | `src/aquabosque/features/build_target.py`, `src/aquabosque/models/train.py` |
| 4. Evaluación (con QA) | `models/metrics/metricas.json`, `tests/` (16 pruebas) |
| 5. Despliegue | `app/` (Streamlit) → https://streamlit.spartanit.pro/ |
| 6. Monitoreo y mantenimiento | §6 (ruta de escalamiento) |

---

## Fase 1 — Comprensión del negocio y de los datos

**Problema público.** Colombia no tiene una vista integrada que cruce, a nivel municipal, **presión minera + deforestación + afectación hídrica + sensibilidad ambiental**. La autoridad revisa esas señales por separado, lo que dificulta **priorizar dónde mirar primero** con recursos limitados.

**Objetivo de negocio.** Entregar una **priorización territorial transparente y explicable** que oriente la focalización (no la sanción) de la revisión ambiental.

**Criterio de éxito (negocio).** Que una autoridad pueda responder *qué municipios priorizar* y *por qué*, con evidencia auditable de datos abiertos.

**Datos disponibles (7 fuentes, unidad = municipio DIVIPOLA, 1.122 municipios):**

| Dimensión | Fuente | ¿datos.gov.co? |
|---|---|---|
| Minería formal (títulos, minerales) | ANM · RUCOM `42ha-fhvj` | ✅ |
| Producción y regalías | ANM `r85m-vv6c` | ✅ |
| Base territorial (código + centroide) | DANE · DIVIPOLA `gdxc-w37w` | ✅ |
| Sensibilidad social | Municipios PDET | ✅ |
| Deforestación (ha) | IDEAM / SMByC (ArcGIS) | portal oficial |
| Calidad hídrica (ICA) | IDEAM · DHIME | portal oficial |
| Áreas protegidas (RUNAP) | RUNAP (ArcGIS) | portal oficial |

**Riesgos/límites detectados desde el inicio** (ver `docs/07_limitaciones.md`): cobertura heterogénea por fuente, ICA con solo 71 municipios con estación, deforestación focalizada (no nacional homogénea), y RUNAP por proximidad de centroide (no intersección poligonal).

---

## Fase 2 — Preparación de datos

**Ingesta** (`src/aquabosque/data/download.py`, `download_arcgis.py`): descarga de cada fuente a `data/raw/` con registro de estado (`_estado_fuentes.json`, `_download_log.json`).

**Integración municipal** (`src/aquabosque/features/build_master.py`):
- Unidad común = municipio (código DANE + centroide).
- Cruces directos por código DANE (RUCOM, ANM volumen, PDET).
- Cruces por **proximidad al centroide** (haversine, sin GDAL) para ICA y RUNAP.
- **Ausencias explícitas:** cuando no hay estación ICA se marca `hidrico_sin_dato` y se usa 0 como señal observada — **no se imputa contaminación**.
- Salida: `data/processed/master_con_etiqueta.csv` (1.122 filas × 22 columnas).

**Variables (15 features del modelo):** 5 índices normalizados (`idx_minero`, `idx_deforestacion`, **`idx_fuego`** [satelital NRT], `idx_hidrico`, `idx_sensibilidad`) + 10 variables crudas trazables (`mineria_titulos`, `mineria_minerales`, `mineria_volumen`, `mineria_regalias`, `es_pdet`, `deforestacion_ha`, `agua_estaciones`, `runap_areas`, `runap_hectareas`, **`focos_7d`** [satelital]).

**Aseguramiento de calidad (Q):** 16 pruebas automáticas en `tests/` validan integridad de datos, coherencia de la etiqueta y consistencia modelo/SHAP en cada corrida (CI).

---

## Fase 3 — Modelado

**Índice técnico (fórmula documentada, pesos ajustables):**
```
riesgo = 0.30·idx_minero + 0.25·idx_deforestacion + 0.15·idx_fuego
         + 0.20·idx_hidrico + 0.10·idx_sensibilidad
```
Cada índice se normaliza min-max a [0,1]. **`idx_fuego`** es la **dimensión dinámica
satelital** (focos de calor activos FIRMS, log1p FRP + min-max): se refresca a diario
y aporta la evidencia reciente que el dato histórico no captura. Ver la capa satelital
en `src/aquabosque/satelital/` y `docs/RUNBOOK_SATELITAL_L40S.md`.

**Etiqueta por cuantiles (priorización RELATIVA).** Como ninguna dimensión supera ~0.45 en absoluto, umbrales absolutos dejarían Alto/Crítico vacíos. Se usan cuantiles del score:
- **Crítico** ≥ p95 · **Alto** ≥ p85 · **Medio** ≥ p60 · **Bajo** < p60.

**Clasificador** (`src/aquabosque/models/train.py`): **XGBoost multiclase** sobre **15 features** — `n_estimators=300`, `max_depth=4`, `learning_rate=0.08`. Split estratificado 75/25 (`random_state=42`): 841 train / 281 test. Explicabilidad con **SHAP** (importancia global + por caso). SHAP confirma que `idx_fuego` (satelital) es una de las variables más influyentes (4ª), evidenciando que el modelo usa la señal satelital de forma material.

---

## Fase 4 — Evaluación (con aseguramiento de calidad)

**Métricas en test (`models/metrics/metricas.json`):**

| Métrica | Valor |
|---|---|
| Accuracy | **0.890** |
| Línea base (clase mayoritaria) | 0.601 |
| F1 macro | **0.778** |

**Por clase (precision / recall / f1 / n):**

| Clase | P | R | F1 | n |
|---|---|---|---|---|
| Bajo | 0.95 | 0.99 | 0.97 | 169 |
| Medio | 0.82 | 0.83 | 0.82 | 70 |
| Alto | 0.71 | 0.61 | 0.65 | 28 |
| Crítico | 0.80 | **0.57** | 0.67 | 14 |

**Matriz de confusión** `[[167,2,0,0],[9,58,3,0],[0,9,17,2],[0,2,4,8]]`.

_Nota: al incorporar la dimensión satelital `idx_fuego`, la accuracy baja levemente (0.911→0.890) porque la etiqueta deja de ser perfectamente reconstruible desde 4 índices — señal de **menor circularidad**, no de peor modelo. El recall de Crítico mejora (0.43→0.57)._

**Nota de honestidad metodológica (declarada en el artefacto):** la etiqueta es una **fórmula compuesta**; el modelo re-aprende parcialmente la regla, por lo que la accuracy es **alta por construcción y NO se presenta como mérito predictivo**. El valor del modelo está en la **explicabilidad (SHAP)** y en generalizar la priorización. El recall bajo en *Crítico* (clase minoritaria, n=14) se reporta abiertamente.

**Validación externa (trabajo declarado):** contrastar el ranking contra una señal independiente (sanciones ANLA, alertas de deforestación, municipios ya intervenidos) para evidenciar que la priorización correlaciona con fenómenos reales y no solo con su propia fórmula.

---

## Fase 5 — Despliegue

Aplicación **Streamlit** desplegada y navegable en **https://streamlit.spartanit.pro/** con 6 vistas: mapa de riesgo, ranking, ficha territorial, explicabilidad (SHAP), datos abiertos y metodología. La app **lee los artefactos reales** del pipeline (no es maqueta) y expone **descarga CSV**. Repo público con CI: cada cambio corre las 16 pruebas antes de integrar.

---

## Fase 6 — Monitoreo y mantenimiento

Ruta de sostenibilidad (ver `docs/AUDITORIA_CONCURSO_2026.md`): automatizar el refresco de fuentes, versionar modelo y datos, monitorear deriva, y reentrenar periódicamente. Escalable/replicable a otras regiones y retos por ser código abierto, datos abiertos trazables y arquitectura sin dependencias propietarias (sin GDAL).

---

_Reproducibilidad: todo el flujo (`download → build_master → build_target → train`) se regenera desde el repositorio; los datos, el modelo y la documentación quedan disponibles para validación del jurado._
