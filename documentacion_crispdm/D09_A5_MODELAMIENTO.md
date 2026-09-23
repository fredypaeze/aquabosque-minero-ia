# D09.A5 - MODELAMIENTO DEL PROBLEMA

## Análisis del Modelado del Problema

### Objetivo del Modelado

El modelado del problema en AquaBosque Minero IA tiene como objetivo desarrollar un modelo de machine learning capaz de clasificar municipios Colombianos en niveles de riesgo ambiental asociado a presión minera, deforestación y afectación hídrica. El modelo debe ser explicativo y reproducible, utilizando técnicas de SHAP para interpretar las decisiones del sistema.

### Descripción del Problema de Machine Learning

#### Tipo de Problema
- **Clasificación multiclase**: Predicción de niveles de riesgo (Bajo, Medio, Alto, Crítico)
- **Problema supervisado**: Basado en datos etiquetados históricos
- **Problema de alto impacto**: Aplicación en gestión ambiental y toma de decisiones

#### Variables de Entrada
1. **Índices normalizados**:
   - Índice minero (0-1)
   - Índice de deforestación (0-1)
   - Índice de fuego (0-1)
   - Índice hídrico (0-1)
   - Índice de sensibilidad ambiental (0-1)

#### Variables de Salida
1. **Etiqueta de riesgo**:
   - Bajo (0)
   - Medio (1)
   - Alto (2)
   - Crítico (3)

### Selección del Modelo

#### Modelo Principal: XGBoost Multiclase

**Justificación**:
1. **Performance**: Excelente rendimiento en problemas de clasificación
2. **Robustez**: Alta capacidad de manejar datos complejos y no lineales
3. **Interpretabilidad**: Soporte nativo para métricas de importancia de características
4. **Eficiencia**: Rápido entrenamiento y predicción
5. **Flexibilidad**: Soporta múltiples objetivos de optimización

#### Alternativas Consideradas
1. **Random Forest**: Buen rendimiento pero menos interpretable
2. **SVM**: Buena para problemas de clasificación binaria
3. **Neural Networks**: Potencial alto pero mayor complejidad
4. **LightGBM**: Similar a XGBoost pero con ventajas en grandes datasets

### Arquitectura del Modelo

#### Estructura del Modelo XGBoost

```
Entrada (5 índices) → Modelo XGBoost (multiclase) → Salida (clase de riesgo)

Índice minero     → 
Índice deforestación → Modelo → Clase de riesgo (Bajo/Medio/Alto/Crítico)
Índice fuego      → 
Índice hídrico    → 
Índice sensibilidad →
```

#### Parámetros Clave del Modelo

1. **Objective**: multiclass:softprob (probabilidades de clase)
2. **Num_class**: 4 (Bajo, Medio, Alto, Crítico)
3. **Eval_metric**: mlogloss (log loss multiclase)
4. **Learning_rate**: 0.08 (tasa de aprendizaje)
5. **Max_depth**: 4 (profundidad máxima del árbol)
6. **Subsample**: 0.9 (proporción de datos para cada árbol)
7. **Colsample_bytree**: 0.9 (proporción de columnas para cada árbol)
8. **Random_state**: 42 (para reproducibilidad)

### Entrenamiento del Modelo

#### Proceso de Entrenamiento

1. **Preparación de datos**:
   - División en conjuntos de entrenamiento (70%), validación (15%) y prueba (15%)
   - Balanceo de clases (si es necesario)
   - Normalización de características

2. **Entrenamiento**:
   - Uso de 5-fold cross-validation para validación
   - Entrenamiento con conjunto de entrenamiento

3. **Validación**:
   - Evaluación en conjunto de validación
   - Métricas de rendimiento (accuracy, F1-score, precision, recall)
   - Análisis de curvas ROC para cada clase

4. **Prueba Final**:
   - Evaluación en conjunto de prueba
   - Cálculo de métricas finales
   - Generación de reportes de rendimiento

#### Métricas de Evaluación

1. **Accuracy**: 0.911 (superando línea base 0.598)
2. **F1-macro**: 0.784
3. **Precision**: 0.892
4. **Recall**: 0.911

### Explicabilidad del Modelo

#### Técnica de Explicabilidad: SHAP (SHapley Additive exPlanations)

**Justificación**:
1. **Teoría de juegos**: Basado en valores de Shapley para distribución justa de contribuciones
2. **Interpretabilidad local**: Explicación de predicciones individuales
3. **Interpretabilidad global**: Análisis de importancia de características
4. **Consistencia**: Propiedades matemáticas garantizadas

#### Aplicación de SHAP

1. **Importancia global de características**:
   - Análisis de qué índices son más importantes para la predicción
   - Visualización de contribuciones relativas

2. **Explicación local**:
   - Análisis de casos individuales
   - Visualización de contribuciones de cada índice a la predicción

3. **Análisis de dependencia**:
   - Relación entre variables y predicciones
   - Identificación de patrones en la influencia de cada índice

### Pipeline de Entrenamiento

#### Estructura del Pipeline

1. **Carga de datos** (`data/curated/dataset_maestro.csv`)
2. **Preparación de datos** (división y normalización)
3. **Entrenamiento del modelo** (`04_train_model.py`)
4. **Evaluación del modelo** (métricas y validación)
5. **Generación de SHAP** (importancia y explicaciones)
6. **Guardado del modelo** (`models/model.pkl`, `models/shap_values.npy`)

#### Componentes del Pipeline

1. **Script de entrenamiento** (`04_train_model.py`):
   - Carga de datos procesados
   - División de conjuntos
   - Entrenamiento XGBoost
   - Cálculo de métricas
   - Generación de SHAP
   - Guardado de artefactos

2. **Artefactos generados**:
   - Modelo entrenado (`models/model.pkl`)
   - Valores SHAP (`models/shap_values.npy`)
   - Métricas de rendimiento (`models/metrics.json`)
   - Importancia de características (`models/feature_importance.json`)

### Validación del Modelo

#### Validación Interna

1. **Cross-validation**: 5-fold cross-validation para estimación robusta
2. **Curvas ROC**: Evaluación de rendimiento por clase
3. **Matriz de confusión**: Análisis detallado de errores
4. **Análisis de errores**: Identificación de casos problemáticos

#### Validación Externa

1. **Benchmarking**: Comparación con modelo base (baseline)
2. **Pruebas de sensibilidad**: Análisis de impacto de variables
3. **Estabilidad**: Evaluación de consistencia en diferentes periodos

### Consideraciones de Reproducibilidad

#### Factor de Reproducibilidad

1. **Semilla aleatoria**: `random_state=42` para resultados reproducibles
2. **Versionado de dependencias**: `requirements.txt` específico
3. **Pipeline automatizado**: Scripts ejecutables desde cero
4. **Documentación**: Tarjeta de modelo (`MODEL_CARD.md`) completa

#### Procedimiento de Reproducción

1. **Instalación del entorno**:
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Ejecución del pipeline**:
   ```bash
   ./run_mvp.sh
   ```

3. **Verificación de resultados**:
   - Comparación de métricas con valores reportados
   - Verificación de igualdad en predicciones
   - Validación de SHAP

### Consideraciones Metodológicas Especiales

#### Honestidad en la Evaluación del Modelo

El modelo es honesto en que la etiqueta es una fórmula compuesta, por lo que el modelo re-aprende parcialmente la regla. Por esta razón:

1. **La exactitud no es un mérito predictivo**: El modelo supera la línea base porque re-aprende la regla de etiquetado
2. **El valor del modelo es la explicabilidad (SHAP)**: Qué factor pesa en cada clasificación para orientar revisión técnica
3. **No se vende la exactitud como mérito**: Se reporta y se contrasta con una línea base trivial

Esta honestidad metodológica es fundamental para evitar malentendidos sobre la capacidad predictiva del modelo.

## Referencias
- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Documentación del Concurso Datos al Ecosistema 2026
- Tarjeta de modelo (`MODEL_CARD.md`)