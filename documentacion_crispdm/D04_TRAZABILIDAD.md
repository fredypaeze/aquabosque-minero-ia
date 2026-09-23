# D04 - TRAZABILIDAD

## Análisis de Trazabilidad del Sistema

La trazabilidad del sistema AquaBosque Minero IA permite seguir el flujo completo de datos desde las fuentes originales hasta los resultados finales. Esta trazabilidad es fundamental para garantizar la transparencia, reproducibilidad y verificabilidad del proceso de análisis.

## Flujo de Datos del Sistema

### 1. Fuentes Originales

Las fuentes de datos se dividen en cinco dimensiones principales:

| Dimensión | Fuente | Detalle |
|---|---|---|
| Minera | **ANM — RUCOM** (datos.gov.co) | 12.914 registros de comercialización + volumen de explotación + regalías → **actividad minera real** |
| Territorio | **DANE — DIVIPOLA** | 1.122 municipios, centroides |
| Deforestación | **Observatorio/IDEAM** (ArcGIS FeatureServer) | hectáreas por municipio |
| Hídrica | **IDEAM — DHIME** (ICA) | índice de calidad del agua por estación |
| Sensibilidad | **RUNAP** (áreas protegidas) + **PDET** | valor ambiental y social a proteger |

### 2. Pipeline de Procesamiento

El sistema sigue un pipeline estructurado de 6 fases:

1. **Descarga de datos** (`01_download_data.py`)
2. **Preparación de datos** (`02_prepare_data.py`)  
3. **Construcción de características** (`03_build_features.py`)
4. **Entrenamiento del modelo** (`04_train_model.py`)
5. **Generación de salidas** (`05_generate_outputs.py`)
6. **Ejecución de la aplicación** (`06_run_app.py`)

### 3. Flujo de Trazabilidad por Fase

#### Fase 1: Descarga de datos (`01_download_data.py`)
- **Origen**: Fuentes oficiales en datos.gov.co y ArcGIS
- **Destino**: `data/raw/`
- **Transformación**: Descarga directa de archivos
- **Identificadores**: Nombres de archivos y hashes de verificación

#### Fase 2: Preparación de datos (`02_prepare_data.py`)
- **Origen**: `data/raw/`
- **Destino**: `data/processed/`
- **Transformación**: Procesamiento geoespacial, cálculo de centroides, integración espacial
- **Identificadores**: Procesamiento por municipio con identificadores DANE

#### Fase 3: Construcción de características (`03_build_features.py`)
- **Origen**: `data/processed/`
- **Destino**: `data/curated/`
- **Transformación**: Cálculo de índices (minero, deforestación, hídrico, sensibilidad)
- **Identificadores**: Municipios con identificadores DANE, cálculo de cuantiles

#### Fase 4: Entrenamiento del modelo (`04_train_model.py`)
- **Origen**: `data/curated/`
- **Destino**: `models/`
- **Transformación**: Entrenamiento XGBoost multiclase con SHAP
- **Identificadores**: Modelo entrenado, métricas de performance, importancia SHAP

#### Fase 5: Generación de salidas (`05_generate_outputs.py`)
- **Origen**: `data/curated/`, `models/`
- **Destino**: `outputs/`
- **Transformación**: Generación de reportes, tablas, PDFs, archivos de salida
- **Identificadores**: Archivos de salida con nombres descriptivos

#### Fase 6: Ejecución de aplicación (`06_run_app.py`)
- **Origen**: `data/curated/`, `models/`
- **Destino**: Dashboard Streamlit
- **Transformación**: Visualización interactiva de resultados
- **Identificadores**: Acceso al dashboard en puerto 8510

### 4. Trazabilidad de Variables

#### Variables de Entrada
1. **Actividad minera**: ANM - RUCOM (comercialización, volumen, regalías)
2. **Territorio**: DANE - DIVIPOLA (centroids, identificadores)
3. **Deforestación**: Observatorio/IDEAM (hectáreas por municipio)
4. **Hídrica**: IDEAM - DHIME (índice de calidad del agua)
5. **Sensibilidad**: RUNAP + PDET (áreas protegidas, valor ambiental)

#### Variables de Salida
1. **Índices de riesgo**: Minero, deforestación, hídrico, sensibilidad (0-1)
2. **Etiqueta de riesgo**: Cuantiles (Bajo, Medio, Alto, Crítico)
3. **Predicciones del modelo**: Clases de riesgo (Bajo, Medio, Alto, Crítico)
4. **Importancia SHAP**: Características más relevantes para predicción

### 5. Identificadores de Trazabilidad

#### Identificadores de Municipios
- **DANE**: Código DIVIPOLA de 7 dígitos (ej. 1100101 para Bogotá)
- **Nombre**: Nombre del municipio
- **Centroides**: Coordenadas geográficas

#### Identificadores de Variables
- **Nombres de variables**: Descriptivos y consistentes
- **Unidades**: Consistentes con las fuentes originales
- **Dominios**: Valores válidos para cada tipo de variable

### 6. Trazabilidad de Métricas

#### Métricas del Modelo
1. **Accuracy**: 0.911 (superando línea base 0.598)
2. **F1-macro**: 0.784
3. **Importancia SHAP**: Características más relevantes
4. **Matriz de confusión**: Distribución de predicciones

#### Métricas de Datos
1. **Cobertura de municipios**: 1.122 municipios
2. **Cobertura de fuentes**: 5/5 fuentes oficiales
3. **Integridad de datos**: Verificación de consistencia

### 7. Componentes de Trazabilidad Específicos

#### Componente de Datos
- **Origen de datos**: Fuentes oficiales y abiertas
- **Procesamiento**: Pipeline automatizado
- **Almacenamiento**: Estructura de directorios clara
- **Versionado**: Control de versiones con Git

#### Componente de Modelo
- **Entrenamiento**: XGBoost multiclase
- **Explicabilidad**: SHAP
- **Validación**: Pruebas automatizadas (16/16)
- **Reproducibilidad**: `random_state=42`

#### Componente de Aplicación
- **Interfaz**: Streamlit dashboard
- **Visualización**: Mapa, ranking, ficha, explicabilidad
- **Acceso**: Puerto 8510
- **Documentación**: Metodología, datos abiertos, resultados

## Trazabilidad en la Auditoría

### Auditoría de Concurso 2026
- **Documento**: `docs/AUDITORIA_CONCURSO_2026.md`
- **Contenido**: Análisis de la implementación del proyecto para el concurso
- **Resultados**: Verificación de cumplimiento de requisitos

### Auditoría de Datos
- **Componentes**: `scripts/audit/`
- **Funcionalidades**: Perfilado de datos con ydata-profiling
- **Resultados**: Análisis de calidad y consistencia de datos

## Próximos Pasos

1. Verificación detallada de la trazabilidad entre componentes
2. Análisis de los scripts de auditoría adicionales
3. Documentación de la trazabilidad de componentes satelitales
4. Validación de la reproducibilidad del pipeline completo

## Referencias

- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Auditoría del concurso 2026