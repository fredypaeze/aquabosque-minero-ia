# D02.A2 - AUDITORÍA DEL ESTADO ACTUAL

## Análisis de la Auditoría del Estado Actual

### Estado Actual del Proyecto

El sistema AquaBosque Minero IA es un sistema de machine learning modular que integra cinco fuentes de datos principales para clasificar municipios Colombianos en niveles de riesgo ambiental asociado a presión minera, deforestación y afectación hídrica. El proyecto está basado en la metodología CRISP-ML y utiliza un pipeline de procesamiento estructurado.

### Componentes del Sistema

#### Modelo Municipal Principal
- **Tipo de modelo**: XGBoost multiclase para clasificación (Bajo/Medio/Alto/Crítico)
- **Objetivo**: Priorización de municipios según riesgo ambiental
- **Enfoque**: Honestidad metodológica - la etiqueta es una fórmula compuesta, por lo que el modelo re-aprende parcialmente la regla

#### Modelos y Componentes Secundarios
1. **Modelo de Anomalías**: Detecta patrones inusuales en los datos
2. **Modelo Conformal**: Calibración de predicciones probabilísticas
3. **Componente de Bogotá**: Específico para la región capitalina
4. **Sistema de Alerta**: Componente de monitoreo en tiempo real

### Resultados Obtenidos

#### Pipeline Principal
1. `01_download_data.py` - Descarga de datos
2. `02_prepare_data.py` - Preparación de datos
3. `03_build_features.py` - Construcción de características
4. `04_train_model.py` - Entrenamiento del modelo
5. `05_generate_outputs.py` - Generación de salidas
6. `06_run_app.py` - Ejecución de aplicación

#### Componentes Adicionales
- Capa satelital NRT (FIRMS) para monitoreo de incendios
- Componente específico para Bogotá
- Sistema de validación y pruebas automatizadas

### Pruebas Automatizadas
El proyecto incluye una batería completa de pruebas automatizadas que validan:
1. Integridad del dataset
2. Reproducción de la fórmula de la etiqueta
3. Superación del modelo de línea base
4. Completitud de SHAP
5. Artefactos del dashboard
6. Procesamiento de datos
7. Entrenamiento del modelo
8. Generación de salidas
9. Funcionalidad del dashboard
10. Cálculo de índices
11. Normalización de variables
12. Agrupación por municipio
13. Cálculo de métricas
14. Generación de SHAP
15. Funcionalidad de exportación
16. Ejecución completa

## Referencias
- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Documentación del Concurso Datos al Ecosistema 2026
- Tarjeta de modelo (`MODEL_CARD.md`)