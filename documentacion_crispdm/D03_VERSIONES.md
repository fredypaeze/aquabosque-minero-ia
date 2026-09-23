# D03.A3 - GESTIÓN DE VERSIONES

## Análisis de la Gestión de Versiones

### Estado Actual del Repositorio

#### Git Information
- **Git HEAD**: 945232a16faf7bf603ae87fc76abe4016d465db4
- **Rama**: feature/capa-incendios
- **Cambios locales no confirmados**: Presentes
- **Estado del repositorio**: En desarrollo

#### Estructura de Versiones
El proyecto utiliza una estructura de versiones basada en el flujo de trabajo CRISP-ML con las siguientes características:

1. **Versiones de datos**: Actualizadas mensualmente desde fuentes oficiales
2. **Versiones de modelos**: Versión 1.0.0 del modelo municipal principal
3. **Versiones de componentes**: Componentes especializados con versiones separadas

### Estructura del Proyecto

#### Pipeline Principal
1. `01_download_data.py` - Descarga de datos
2. `02_prepare_data.py` - Preparación de datos
3. `03_build_features.py` - Construcción de características
4. `04_train_model.py` - Entrenamiento del modelo
5. `05_generate_outputs.py` - Generación de salidas
6. `06_run_app.py` - Ejecución de aplicación

#### Componentes Adicionales
- `07_trio_insignia.py` - Componente de análisis especializado
- `08_bogota_upz.py` - Componente específico para Bogotá
- `09_bogota_alerta_ml.py` - Sistema de alerta para Bogotá
- `10_prepare_bogota_fire_sab.py` - Preparación de datos para incendios en Bogotá
- `11_prepare_bogota_remocion.py` - Preparación de datos para remoción de datos

### Fuentes de Datos y Versiones

#### Fuentes de Datos Oficiales
1. **ANM - RUCOM**: Datos mineros actualizados mensualmente
2. **DANE - DIVIPOLA**: Datos geoespaciales actualizados anualmente
3. **IDEAM - Observatorio**: Datos de deforestación actualizados mensualmente
4. **IDEAM - DHIME**: Datos hídricos actualizados mensualmente
5. **NASA FIRMS**: Datos satelitales actualizados diariamente

### Control de Cambios

#### Registro de Procesamiento
1. **Bitácora de transformaciones**:
   - Fecha de procesamiento
   - Descripción de transformaciones realizadas
   - Identificación de datos de entrada y salida

2. **Versionado de datos**:
   - Identificadores de versión de datasets
   - Historial de cambios en procesamiento
   - Control de calidad de cada versión

### Componentes de Desarrollo

#### Scripts de Procesamiento
1. **`01_download_data.py`**: Descarga de datos de fuentes oficiales
2. **`02_prepare_data.py`**: Procesamiento de datos geoespaciales
3. **`03_build_features.py`**: Construcción de características y cálculo de índices
4. **`04_train_model.py`**: Entrenamiento del modelo (incluye preparación)
5. **`05_generate_outputs.py`**: Generación de salidas y reportes
6. **`06_run_app.py`**: Ejecución de la aplicación completa

#### Componentes Especiales
1. **`07_trio_insignia.py`**: Componente de análisis especializado
2. **`08_bogota_upz.py`**: Componente específico para Bogotá
3. **`09_bogota_alerta_ml.py`**: Sistema de alerta para Bogotá
4. **`10_prepare_bogota_fire_sab.py`**: Preparación de datos para incendios en Bogotá
5. **`11_prepare_bogota_remocion.py`**: Preparación de datos para remoción de datos

### Métricas de Control de Calidad

#### Métricas de Cobertura
1. **Cobertura de municipios**: Porcentaje de municipios con datos completos
2. **Cobertura de variables**: Porcentaje de variables disponibles por municipio
3. **Cobertura temporal**: Periodicidad de datos disponibles

#### Métricas de Consistencia
1. **Consistencia de identificadores**: Porcentaje de códigos DANE válidos
2. **Consistencia de valores**: Porcentaje de valores dentro de rangos lógicos
3. **Consistencia temporal**: Coherencia en datos históricos

## Referencias
- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Documentación del Concurso Datos al Ecosistema 2026
- Especificaciones de las fuentes de datos oficiales