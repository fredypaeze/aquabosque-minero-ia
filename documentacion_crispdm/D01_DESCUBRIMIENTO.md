# D01 - DESCUBRIMIENTO

## Descripción del Proyecto

**Nombre del proyecto:** AquaBosque Minero IA  
**Objetivo principal:** Sistema explicable de IA geoespacial para priorizar municipios colombianos con riesgo ambiental asociado a presión minera, deforestación y afectación hídrica, usando datos abiertos.

## Alcance del Análisis

El proyecto desarrolla una solución de inteligencia artificial que integra datos abiertos oficiales para priorizar territorios con riesgo ambiental, facilitando el monitoreo estratégico y la toma de decisiones públicas basada en evidencia.

## Componentes Clave del Sistema

### 1. Arquitectura del Proyecto

```
Fuentes abiertas oficiales → ingesta → integración municipal (centroides + haversine, sin GDAL)
  → dataset maestro (1.122 municipios) → 4 índices 0-1 (minero, deforestación, hídrico, sensibilidad)
  → etiqueta técnica por cuantiles → XGBoost multiclase + SHAP
  → dashboard Streamlit (mapa, ranking, ficha, explicabilidad, datos abiertos, metodología)
```

### 2. Fases del Pipeline

1. **Descarga de datos** (`01_download_data.py`)
2. **Preparación de datos** (`02_prepare_data.py`)  
3. **Construcción de características** (`03_build_features.py`)
4. **Entrenamiento del modelo** (`04_train_model.py`)
5. **Generación de salidas** (`05_generate_outputs.py`)
6. **Ejecución de la aplicación** (`06_run_app.py`)

### 3. Fuentes de Datos

| Dimensión | Fuente | Detalle |
|---|---|---|
| Minera | **ANM — RUCOM** (datos.gov.co) | 12.914 registros de comercialización + volumen de explotación + regalías → **actividad minera real** |
| Territorio | **DANE — DIVIPOLA** | 1.122 municipios, centroides |
| Deforestación | **Observatorio/IDEAM** (ArcGIS FeatureServer) | hectáreas por municipio |
| Hídrica | **IDEAM — DHIME** (ICA) | índice de calidad del agua por estación |
| Sensibilidad | **RUNAP** (áreas protegidas) + **PDET** | valor ambiental y social a proteger |

### 4. Componentes Técnicos

- **Modelo de machine learning:** XGBoost multiclase
- **Explicabilidad:** SHAP (SHapley Additive exPlanations)
- **Interfaz de usuario:** Streamlit dashboard
- **Metodología:** CRISP-ML aplicado al contexto de estudios estratégicos

## Estructura del Repositorio

```
aquabosque-minero-ia/
├── app/                  # dashboard Streamlit (6 páginas)
├── src/                  # código fuente organizado por capas
│   ├── aquabosque/data/     # fuentes tabulares (Socrata)
│   ├── aquabosque/features/ # dataset maestro + 4 índices + etiqueta
│   └── aquabosque/models/   # entrenamiento + SHAP + métricas
├── scripts/              # pipeline ejecutable por fases (01-06) + arranque de un paso
├── data/                 # datos descargados y procesados
│   ├── raw/              # fuentes descargadas (incluidas para reconstrucción offline)
│   └── curated/          # datos procesados
├── models/               # modelo entrenado · métricas · importancia SHAP
├── docs/                 # documentación técnica
├── tests/                # batería pytest (16)
├── outputs/              # PDF técnico · pitch PPTX · tablas
└── requirements*.txt     # dependencias del proyecto
```

## Resultados Clave Verificados

- **Municipios analizados:** 1.122 (DIVIPOLA 2025)
- **Fuentes reales integradas:** 5/5 — sin datos sintéticos
- **Priorización:** Bajo 672 · Medio 281 · Alto 112 · **Crítico 57**
- **Modelo:** XGBoost · accuracy **0.911** (línea base 0.598) · F1-macro **0.784**
- **Explicabilidad:** SHAP global + por municipio

## Pruebas y Validación

El proyecto incluye una batería de 16 pruebas automatizadas que validan:
- Integridad del dataset
- Reproducibilidad de la fórmula de la etiqueta
- Superación del modelo de línea base
- Completitud de SHAP
- Artefactos del dashboard

## Documentación Existente

- **Metodología CRISP-ML:** [`docs/CRISP_ML.md`](docs/CRISP_ML.md)
- **Model Card:** [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md)
- **Diccionario de datos:** [`docs/diccionario_datos.md`](docs/diccionario_datos.md)
- **Auditoría del concurso:** [`docs/AUDITORIA_CONCURSO_2026.md`](docs/AUDITORIA_CONCURSO_2026.md)

## Análisis Inicial

El proyecto está completamente estructurado siguiendo buenas prácticas de ciencia de datos, con:
- Pipeline automatizado de 6 fases
- Integración de fuentes oficiales y abiertas
- Modelo de machine learning explicado con SHAP
- Dashboard interactivo
- Pruebas automatizadas
- Documentación técnica completa

## Próximos Pasos

1. Auditoría detallada del estado actual del proyecto
2. Exploración de los componentes del sistema y sus interacciones
3. Verificación de trazabilidad de datos y procesos
4. Documentación de la comprensión del negocio
5. Análisis de los datos y sus fuentes

## Referencias

- Framework CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA