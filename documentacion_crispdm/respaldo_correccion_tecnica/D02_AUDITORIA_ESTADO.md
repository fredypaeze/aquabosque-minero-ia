# D02 - AUDITORÍA DEL ESTADO ACTUAL

## Estado General del Proyecto

El proyecto AquaBosque Minero IA se encuentra en un estado avanzado de desarrollo con una estructura sólida y documentación completa. El sistema está completamente implementado con un pipeline automatizado de 6 fases, integración de fuentes oficiales, modelo de machine learning explicado con SHAP y dashboard interactivo.

## Componentes del Sistema

### 1. Pipeline de Procesamiento

El proyecto sigue un pipeline estructurado de 6 fases:

1. **Descarga de datos** (`01_download_data.py`)
2. **Preparación de datos** (`02_prepare_data.py`)  
3. **Construcción de características** (`03_build_features.py`)
4. **Entrenamiento del modelo** (`04_train_model.py`)
5. **Generación de salidas** (`05_generate_outputs.py`)
6. **Ejecución de la aplicación** (`06_run_app.py`)

### 2. Estructura de Directorios

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

### 3. Resultados Obtenidos

- **Municipios analizados:** 1.122 (DIVIPOLA 2025)
- **Fuentes reales integradas:** 5/5 — sin datos sintéticos
- **Priorización:** Bajo 672 · Medio 281 · Alto 112 · **Crítico 57**
- **Modelo:** XGBoost · accuracy **0.911** (línea base 0.598) · F1-macro **0.784**
- **Explicabilidad:** SHAP global + por municipio

### 4. Pruebas Automatizadas

El proyecto incluye una batería de 16 pruebas automatizadas que validan:
- Integridad del dataset
- Reproducibilidad de la fórmula de la etiqueta
- Superación del modelo de línea base
- Completitud de SHAP
- Artefactos del dashboard

## Documentación Técnica

### Documentos Oficiales

- **Metodología CRISP-ML:** [`docs/CRISP_ML.md`](docs/CRISP_ML.md) - Documentación de la metodología aplicada
- **Model Card:** [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md) - Tarjeta de modelo con métricas y detalles
- **Diccionario de datos:** [`docs/diccionario_datos.md`](docs/diccionario_datos.md) - Descripción de variables y fuentes
- **Auditoría del concurso:** [`docs/AUDITORIA_CONCURSO_2026.md`](docs/AUDITORIA_CONCURSO_2026.md) - Auditoría del proceso de concurso

### Documentación Adicional

- **Resumen ejecutivo:** [`docs/00_resumen_ejecutivo.md`](docs/00_resumen_ejecutivo.md)
- **Resultados:** [`docs/06_resultados.md`](docs/06_resultados.md)
- **Limitaciones:** [`docs/07_limitaciones.md`](docs/07_limitaciones.md)
- **Defensa jurado:** [`docs/09_defensa_jurado.md`](docs/09_defensa_jurado.md)

## Fuentes de Datos

### 5 Dimensiones de Datos

| Dimensión | Fuente | Detalle |
|---|---|---|
| Minera | **ANM — RUCOM** (datos.gov.co) | 12.914 registros de comercialización + volumen de explotación + regalías → **actividad minera real** |
| Territorio | **DANE — DIVIPOLA** | 1.122 municipios, centroides |
| Deforestación | **Observatorio/IDEAM** (ArcGIS FeatureServer) | hectáreas por municipio |
| Hídrica | **IDEAM — DHIME** (ICA) | índice de calidad del agua por estación |
| Sensibilidad | **RUNAP** (áreas protegidas) + **PDET** | valor ambiental y social a proteger |

## Tecnologías y Herramientas

- **Lenguaje:** Python 3.12
- **Machine Learning:** XGBoost
- **Explicabilidad:** SHAP
- **Visualización:** Streamlit
- **Testing:** Pytest
- **Dependencias:** requirements.txt

## Estado de Implementación

### Completo
- Pipeline de 6 fases implementado
- Dashboard Streamlit funcional
- Modelo entrenado y validado
- Pruebas automatizadas (16/16)
- Documentación técnica completa

### Parcial
- Documentación de auditoría específica del concurso
- Documentación de zoom de Bogotá (opcional)

### Pendiente
- Revisión exhaustiva de todos los scripts de auditoría
- Validación de la trazabilidad completa de datos
- Análisis de componentes adicionales (scripts 07-12)

## Próximos Pasos

1. Verificación detallada de la trazabilidad de datos
2. Análisis de los componentes del sistema y sus interacciones
3. Documentación de la comprensión del negocio
4. Análisis de los datos y sus fuentes
5. Preparación de datos y modelado

## Referencias

- Framework CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA