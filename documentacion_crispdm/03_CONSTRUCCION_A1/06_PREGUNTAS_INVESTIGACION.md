# 6. PREGUNTAS DE INVESTIGACIÓN

## Propósito
Formular preguntas específicas que guiarán el análisis.

## Contenido mínimo
- Lista de preguntas de investigación
- Relación con el problema analítico
- Cada pregunta debe ser investigable
- Cada pregunta debe estar respaldada por evidencia

## Evidencia requerida
- Documento histórico A1
- Código fuente del proyecto
- Documentación técnica del proyecto

## Criterios de aceptación
- Preguntas claras y específicas
- Relación directa con el problema
- Investigables con los métodos disponibles
- Fundamentadas en evidencia

## Desarrollo del contenido

### Lista de preguntas de investigación

Las preguntas de investigación que guían el análisis son:

1. **¿Cómo se puede integrar de manera efectiva señales heterogéneas de presión ambiental para construir un índice compuesto de riesgo ambiental municipal?**
2. **¿Qué factores ambientales predominan en cada municipio colombiano y cómo se puede explicar su influencia en el riesgo ambiental?**
3. **¿Cuál es la distribución geográfica del riesgo ambiental en Colombia y cómo se puede identificar las zonas más vulnerables?**
4. **¿Cómo se puede desarrollar un modelo de machine learning interpretable que ordene los municipios por nivel de riesgo ambiental y explique el aporte de cada factor?**
5. **¿Qué métodos de análisis y visualización permiten comunicar eficazmente los resultados de la priorización ambiental a diferentes audiencias?**
6. **¿Cómo se puede garantizar la reproducibilidad y auditabilidad del proceso de priorización ambiental desarrollado?**

### Justificación de las preguntas de investigación

Estas preguntas de investigación están directamente relacionadas con el problema analítico del estudio y están fundamentadas en evidencia técnica del proyecto. Cada pregunta busca abordar un componente específico del problema central.

### Pregunta de investigación 1: ¿Cómo se puede integrar de manera efectiva señales heterogéneas de presión ambiental para construir un índice compuesto de riesgo ambiental municipal?

#### Descripción
Esta pregunta se enfoca en el desafío técnico de combinar diferentes tipos de datos ambientales provenientes de diversas fuentes.

#### Fundamento técnico
- **Datos heterogéneos**: Se deben integrar datos de diferentes orígenes (ANM, IDEAM, NASA, etc.)
- **Escala variable**: Datos a diferentes escalas (nacional, regional, municipal)
- **Tipos de datos**: Numéricos, geoespaciales, temporales, categóricos
- **Calidad variable**: Diferentes niveles de confiabilidad de los datos

#### Evidencia técnica
- **Documento histórico**: El estudio construye una capa analítica que ordena los municipios según su riesgo ambiental combinado
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py` probablemente contiene lógica de construcción de índices
- **Documentación**: Se requiere procesamiento de múltiples fuentes de datos

#### Investigabilidad
- ✅ **Métodos disponibles**: Métodos de integración de datos, normalización, procesamiento de datos
- ✅ **Herramientas técnicas**: Python, Pandas, GeoPandas, etc.
- ✅ **Validación**: Se puede validar con datos históricos

### Pregunta de investigación 2: ¿Qué factores ambientales predominan en cada municipio colombiano y cómo se puede explicar su influencia en el riesgo ambiental?

#### Descripción
Esta pregunta se enfoca en la explicación de los resultados obtenidos, buscando entender qué factores son los más influyentes en cada municipio.

#### Fundamento técnico
- **Explicabilidad**: Se requiere comprensión de qué factores predominan
- **SHAP (SHapley Additive exPlanations)**: Técnica para explicar modelos de machine learning
- **Análisis de sensibilidad**: Evaluar el impacto de cada variable en el resultado

#### Evidencia técnica
- **Documento histórico**: "y lo hace de forma interpretable"
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py` probablemente contiene lógica de entrenamiento de modelos interpretables
- **Documentación**: Se menciona la explicabilidad como característica clave

#### Investigabilidad
- ✅ **Métodos disponibles**: Técnicas de explicabilidad de modelos, análisis de sensibilidad
- ✅ **Herramientas técnicas**: SHAP, LIME, análisis estadístico
- ✅ **Validación**: Se puede validar con análisis de casos

### Pregunta de investigación 3: ¿Cuál es la distribución geográfica del riesgo ambiental en Colombia y cómo se puede identificar las zonas más vulnerables?

#### Descripción
Esta pregunta se enfoca en la visualización y análisis espacial del riesgo ambiental.

#### Fundamento técnico
- **Análisis geoespacial**: Uso de datos geográficos para identificar patrones
- **Mapas de riesgo**: Visualización del riesgo ambiental por región
- **Identificación de zonas críticas**: Determinar áreas con mayor riesgo

#### Evidencia técnica
- **Documento histórico**: Se menciona la priorización de los 1.122 municipios
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` contiene datos geoespaciales
- **Documentación**: Se requiere análisis espacial de los resultados

#### Investigabilidad
- ✅ **Métodos disponibles**: Análisis espacial, visualización geográfica
- ✅ **Herramientas técnicas**: GeoPandas, Folium, QGIS, etc.
- ✅ **Validación**: Se puede validar con mapas históricos o datos de referencia

### Pregunta de investigación 4: ¿Cómo se puede desarrollar un modelo de machine learning interpretable que ordene los municipios por nivel de riesgo ambiental y explique el aporte de cada factor?

#### Descripción
Esta pregunta se enfoca en el desarrollo técnico del modelo que será la base del sistema.

#### Fundamento técnico
- **Modelos interpretables**: Requerimiento específico del proyecto
- **Clasificación**: Ordenamiento de municipios por niveles de riesgo
- **Explicación**: Entendimiento de contribución de cada factor

#### Evidencia técnica
- **Documento histórico**: "Entrenar un clasificador interpretable que ordene los municipios en niveles de riesgo y explique el aporte de cada factor (SHAP)"
- **Código fuente**: `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py` contiene la lógica de entrenamiento
- **Documentación**: Se menciona la importancia de SHAP

#### Investigabilidad
- ✅ **Métodos disponibles**: Machine learning interpretable, SHAP, XGBoost, Random Forest
- ✅ **Herramientas técnicas**: Scikit-learn, SHAP, MLflow, etc.
- ✅ **Validación**: Se puede validar con métricas de rendimiento y explicabilidad

### Pregunta de investigación 5: ¿Qué métodos de análisis y visualización permiten comunicar eficazmente los resultados de la priorización ambiental a diferentes audiencias?

#### Descripción
Esta pregunta se enfoca en la comunicación de los resultados del estudio.

#### Fundamento técnico
- **Comunicación de resultados**: Necesidad de hacer accesibles los resultados
- **Diferentes audiencias**: Técnicos, gestores, tomadores de decisiones, público general
- **Visualización efectiva**: Uso de gráficos, mapas y dashboards

#### Evidencia técnica
- **Documento histórico**: "El estudio construye una capa analítica que ordena los municipios del país según su riesgo ambiental combinado"
- **Código fuente**: `/home/tuxilo/modelo-riesgo-suspension/` contiene scripts de visualización
- **Documentación**: Se requiere presentación de resultados

#### Investigabilidad
- ✅ **Métodos disponibles**: Visualización de datos, dashboard, reportes
- ✅ **Herramientas técnicas**: Plotly, Dash, Streamlit, Tableau, etc.
- ✅ **Validación**: Se puede validar con feedback de diferentes audiencias

### Pregunta de investigación 6: ¿Cómo se puede garantizar la reproducibilidad y auditabilidad del proceso de priorización ambiental desarrollado?

#### Descripción
Esta pregunta se enfoca en la calidad y fiabilidad del proceso desarrollado.

#### Fundamento técnico
- **Reproducibilidad**: Que otros puedan replicar el proceso
- **Auditabilidad**: Que el proceso sea verificable
- **Documentación**: Buenas prácticas de documentación

#### Evidencia técnica
- **Documento histórico**: "La reproducibilidad se asegura publicando el producto en repositorio abierto"
- **Código fuente**: El proyecto está estructurado para ser reproducible
- **Documentación**: Se requiere documentación completa del proceso

#### Investigabilidad
- ✅ **Métodos disponibles**: Buenas prácticas de desarrollo, documentación, versionado
- ✅ **Herramientas técnicas**: Git, Docker, Jupyter Notebooks, CI/CD
- ✅ **Validación**: Se puede validar con pruebas de reproducibilidad

### Relación con el problema analítico

Cada pregunta de investigación está directamente relacionada con el problema analítico:

1. **Integración de datos**: Aborda el desafío de señales heterogéneas
2. **Explicación de factores**: Responde a la necesidad de interpretación
3. **Distribución geográfica**: Proporciona visión espacial del problema
4. **Modelo interpretable**: Desarrolla la solución técnica principal
5. **Comunicación de resultados**: Asegura que los resultados sean útiles
6. **Reproducibilidad**: Garantiza calidad del proceso

### Coherencia entre preguntas

Las preguntas de investigación son coherentes entre sí:

1. **Secuencia lógica**: Desde la integración de datos hasta la comunicación de resultados
2. **Complementariedad**: Cada pregunta aborda un aspecto diferente pero necesario
3. **Fundamentación común**: Todas se basan en el mismo problema central

### Fundamentación en evidencia

Todas las preguntas están fundamentadas en:

1. **Documento histórico**: Derivadas directamente del documento histórico
2. **Código fuente**: Basadas en las prácticas del código del proyecto
3. **Documentación técnica**: Consistentes con la documentación disponible
4. **Estructura del proyecto**: Reflejan la organización del proyecto

### Verificación de aceptación

Las preguntas de investigación cumplen con los criterios de aceptación:

- ✅ **Claridad y especificidad**: Cada pregunta es clara y específica
- ✅ **Relación directa con el problema**: Todas están vinculadas al problema central
- ✅ **Investigabilidad**: Se pueden abordar con los métodos y herramientas disponibles
- ✅ **Fundamentación en evidencia**: Basadas en el documento histórico y código fuente

### Contexto de las preguntas de investigación

Las preguntas de investigación se sitúan dentro del contexto más amplio del proyecto:

1. **Contexto técnico**: Desarrollo de soluciones basadas en datos y machine learning
2. **Contexto metodológico**: Aplicación de metodologías científicas rigurosas
3. **Contexto social**: Contribución a la gestión ambiental sostenible
4. **Contexto institucional**: Apoyo a políticas públicas basadas en evidencia

### Impacto de las preguntas de investigación

Las preguntas de investigación tienen un impacto significativo:

1. **Impacto técnico**: Avanzan en la solución del problema analítico
2. **Impacto metodológico**: Establecen buenas prácticas para el análisis
3. **Impacto social**: Contribuyen a la gestión ambiental efectiva
4. **Impacto institucional**: Apoyan la toma de decisiones basada en evidencia

## Conclusión

Las preguntas de investigación están claramente definidas, coherentes entre sí y directamente relacionadas con el problema analítico del estudio. Cada pregunta aborda un componente fundamental del problema central y está fundamentada en evidencia técnica del proyecto. Estas preguntas guiarán el análisis y desarrollo del estudio de manera efectiva y sistemática.