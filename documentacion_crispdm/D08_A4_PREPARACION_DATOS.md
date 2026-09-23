# D08.A4 - PREPARACIÓN DE LOS DATOS

## Análisis de la Preparación de los Datos

### Objetivo de la Preparación de Datos

La preparación de datos es una fase crítica en el pipeline del proyecto AquaBosque Minero IA, donde se transforman los datos brutos obtenidos de las diversas fuentes en un formato adecuado para el modelado. Este proceso asegura la calidad, consistencia y compatibilidad de los datos que alimentarán el modelo de machine learning.

### Procesamiento de Datos

#### 1. Procesamiento de Datos Mineros (ANM - RUCOM)

**Fuente**: Base de datos RUCOM de la Agencia Nacional de Minería

**Transformaciones realizadas**:
- **Limpieza de datos**: Eliminación de registros duplicados y valores atípicos
- **Normalización de volumen**: Conversión de diferentes unidades a toneladas estándar
- **Cálculo de regalías promedio**: Promedio de regalías por municipio
- **Agrupación temporal**: Agregación por año y municipio

**Salida esperada**:
- Archivo `data/processed/mineria_municipal.csv`
- Columnas: municipio (DANE), volumen_minero, regalias_promedio, periodo

#### 2. Procesamiento de Datos Territoriales (DANE - DIVIPOLA)

**Fuente**: DIVIPOLA 2025 del Departamento Administrativo Nacional de Estadística

**Transformaciones realizadas**:
- **Extracción de coordenadas**: Obtención de centroides de municipios
- **Normalización de códigos**: Formato consistente de códigos DANE
- **Creación de identificadores**: Generación de identificadores únicos
- **Validación de cobertura**: Verificación de cobertura completa de municipios

**Salida esperada**:
- Archivo `data/processed/municipios_geolocalizados.csv`
- Columnas: codigo_dane, nombre_municipio, latitud, longitud

#### 3. Procesamiento de Datos de Deforestación (Observatorio/IDEAM)

**Fuente**: Datos de cambio en cubierta vegetal del Observatorio del IDEAM

**Transformaciones realizadas**:
- **Integración temporal**: Sincronización de datos mensuales
- **Cálculo de tendencias**: Análisis de cambios en cubierta vegetal
- **Normalización de área**: Conversión a hectáreas consistentes
- **Agrupación por municipio**: Agregación por código DANE

**Salida esperada**:
- Archivo `data/processed/deforestacion_municipal.csv`
- Columnas: municipio (DANE), deforestacion_ha, periodo, tendencia

#### 4. Procesamiento de Datos Hídricos (IDEAM - DHIME)

**Fuente**: Datos hidrometeorológicos del IDEAM

**Transformaciones realizadas**:
- **Normalización de calidad**: Conversión a escala 0-100
- **Cálculo de promedios**: Promedio mensual por estación
- **Agrupación por municipio**: Asociación con municipios mediante coordenadas
- **Identificación de tendencias**: Análisis de cambios en calidad del agua

**Salida esperada**:
- Archivo `data/processed/calidad_agua_municipal.csv`
- Columnas: municipio (DANE), calidad_agua, periodo, tendencia

#### 5. Procesamiento de Datos de Sensibilidad (RUNAP + PDET)

**Fuente**: Datos de áreas protegidas y valor ambiental

**Transformaciones realizadas**:
- **Identificación de áreas protegidas**: Extracción de datos de RUNAP
- **Cálculo de valor de sensibilidad**: Agregación de múltiples indicadores
- **Asociación con municipios**: Mapeo de áreas a municipios
- **Normalización de valores**: Conversión a escala 0-1

**Salida esperada**:
- Archivo `data/processed/sensibilidad_ambiental_municipal.csv`
- Columnas: municipio (DANE), sensibilidad_ambiental, areas_protegidas, valor_sensibilidad

### Integración de Datos

#### Proceso de Integración

1. **Unificación de identificadores**: Uso del código DANE como identificador único
2. **Alineamiento temporal**: Sincronización de datos por período
3. **Agrupación por municipio**: Consolidación de datos por entidad territorial
4. **Validación de cobertura**: Verificación de municipios con datos completos

#### Estructura de Datos Integrados

```
data/curated/dataset_maestro.csv
┌─────────────────┬────────────────────┬─────────────────────┬────────────────────┬────────────────────┬────────────────────┐
│ municipio       │ volumen_minero     │ regalias_promedio   │ deforestacion_ha   │ calidad_agua       │ sensibilidad_ambiental│
├─────────────────┼────────────────────┼─────────────────────┼────────────────────┼────────────────────┼────────────────────┤
│ 1100101         │ 15000              │ 2500                │ 1200               │ 75                 │ 0.85               │
│ 1100102         │ 8000               │ 1200                │ 800                │ 68                 │ 0.72               │
│ ...             │ ...                │ ...                 │ ...                │ ...                │ ...                │
└─────────────────┴────────────────────┴─────────────────────┴────────────────────┴────────────────────┴────────────────────┘
```

### Limpieza de Datos

#### Procesos de Limpieza

1. **Manejo de valores nulos**:
   - Identificación de municipios con datos incompletos
   - Imputación de valores faltantes mediante promedios históricos
   - Eliminación de registros con múltiples valores faltantes

2. **Detección de valores atípicos**:
   - Análisis estadístico de distribuciones
   - Identificación de outliers mediante percentiles
   - Corrección o eliminación de valores extremos

3. **Validación de consistencia**:
   - Verificación de rangos lógicos para cada variable
   - Validación de coherencia entre variables
   - Chequeo de integridad de identificadores

#### Estrategias de Imputación

1. **Imputación por promedio**: Para variables continuas con datos parciales
2. **Imputación por mediana**: Para variables con distribuciones sesgadas
3. **Imputación por valor constante**: Para variables categóricas
4. **Eliminación de registros**: Cuando los datos faltantes son excesivos

### Transformaciones de Variables

#### Normalización de Variables

1. **Variables numéricas continuas**:
   - **Minería**: Normalización a escala 0-1 usando min-max
   - **Deforestación**: Normalización a escala 0-1
   - **Calidad del agua**: Conversión a escala 0-1 (inversa, cuanto menor el valor, mayor el riesgo)
   - **Sensibilidad ambiental**: Escala 0-1

2. **Variables categóricas**:
   - **Etiquetas de riesgo**: Conversión a valores numéricos (Bajo=0, Medio=1, Alto=2, Crítico=3)

#### Cálculo de Índices

1. **Índice Minero**:
   ```
   indice_minero = (volumen_minero + regalias_promedio) / (max_volumen + max_regalias)
   ```

2. **Índice de Deforestación**:
   ```
   indice_deforestacion = deforestacion_ha / max_deforestacion
   ```

3. **Índice Hídrico**:
   ```
   indice_hidrico = 1 - (calidad_agua / 100)
   ```

4. **Índice de Sensibilidad Ambiental**:
   ```
   indice_sensibilidad = sensibilidad_ambiental
   ```

### Validación de Datos

#### Validación de Calidad

1. **Integridad de datos**:
   - Verificación de cobertura completa de municipios
   - Validación de consistencia en formatos de datos
   - Chequeo de identificadores únicos

2. **Consistencia semántica**:
   - Verificación de valores dentro de rangos lógicos
   - Validación de relaciones entre variables
   - Chequeo de coherencia temporal

3. **Validación de fuentes**:
   - Comparación con fuentes de datos alternativas
   - Verificación de consistencia histórica
   - Validación de actualizaciones

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

### Componentes de Preparación

#### Scripts de Procesamiento

1. **`02_prepare_data.py`**: Procesamiento de datos geoespaciales
2. **`03_build_features.py`**: Construcción de características y cálculo de índices
3. **`04_train_model.py`**: Entrenamiento del modelo (incluye preparación)

#### Archivos de Salida

1. **`data/curated/dataset_maestro.csv`**: Dataset final integrado
2. **`data/curated/indices_municipales.csv`**: Índices calculados por municipio
3. **`data/curated/etiquetas_riesgo.csv`**: Etiquetas de riesgo por municipio

### Métricas de Calidad de Datos

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