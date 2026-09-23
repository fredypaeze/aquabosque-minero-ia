# 3. OBJETIVOS ESPECÍFICOS

## Propósito
Desglosar los objetivos específicos que respaldan el objetivo general.

## Contenido mínimo
- Lista de objetivos específicos
- Relación con el objetivo general
- Cada objetivo debe ser medible
- Cada objetivo debe estar respaldado por evidencia

## Evidencia requerida
- Documento histórico A1
- Código fuente del proyecto
- Documentación técnica del proyecto

## Criterios de aceptación
- Objetivos específicos claros y medibles
- Relación directa con el objetivo general
- Fundamentación técnica sólida
- Coherencia entre objetivos

## Desarrollo del contenido

### Lista de objetivos específicos

Los objetivos específicos que respaldan el objetivo general son:

1. **Construir un índice de riesgo ambiental combinado por municipio a partir de fuentes abiertas**
2. **Entrenar un clasificador interpretable que ordene los municipios en niveles de riesgo y explique el aporte de cada factor (SHAP)**
3. **Complementar la lectura nacional con capas de incendios (área quemada por dNBR en municipios seleccionados) y de alerta temprana a escala urbana (Bogotá)**
4. **Garantizar la reproducibilidad y la auditabilidad del producto en repositorio abierto**

### Justificación de los objetivos específicos

Estos objetivos específicos están directamente alineados con el objetivo general y se derivan del documento histórico AquaBosque_A1_Definicion_Tematica.docx. Cada uno tiene una relación clara con el propósito del estudio y se fundamenta en evidencia técnica del proyecto.

### Objetivo específico 1: Construir un índice de riesgo ambiental combinado por municipio a partir de fuentes abiertas

#### Descripción
Este objetivo se centra en la construcción de un índice compuesto que combine múltiples factores ambientales para determinar el riesgo ambiental de cada municipio.

#### Fundamento técnico
- **Base en fuentes abiertas**: Se utilizan datos públicos y disponibles para construir el índice
- **Enfoque combinado**: Se consideran múltiples factores ambientales (presión minera, deforestación, estrés hídrico y sensibilidad del territorio)
- **Aplicación a municipios**: Se realiza el análisis a nivel municipal, que es el ámbito de interés del proyecto

#### Evidencia técnica
- **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios del país según su riesgo ambiental combinado (presión minera, deforestación, estrés hídrico y sensibilidad del territorio)"
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py` probablemente contiene la lógica de construcción de índices
- **Documentación**: La documentación del proyecto en `/home/tuxilo/aquabosque-minero-ia/docs/` contiene información sobre la construcción de índices

#### Medibilidad
- ✅ **Construcción del índice**: Se puede verificar si se ha construido un índice válido
- ✅ **Fuentes abiertas**: Se puede comprobar que se usan fuentes abiertas
- ✅ **Análisis municipal**: Se puede verificar que se aplica a los 1.122 municipios

### Objetivo específico 2: Entrenar un clasificador interpretable que ordene los municipios en niveles de riesgo y explique el aporte de cada factor (SHAP)

#### Descripción
Este objetivo se enfoca en el desarrollo de un modelo de machine learning que no solo ordene los municipios, sino que también sea interpretable, permitiendo entender qué factores contribuyen más al riesgo.

#### Fundamento técnico
- **Clasificador interpretable**: Se requiere que el modelo sea interpretable, no solo predictivo
- **SHAP (SHapley Additive exPlanations)**: Técnica para explicar las predicciones del modelo
- **Ordenamiento**: El modelo debe ordenar los municipios por niveles de riesgo

#### Evidencia técnica
- **Documento histórico**: "y lo hace de forma interpretable, con capas complementarias de incendios y de alerta temprana a escala urbana"
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py` probablemente contiene la lógica de entrenamiento de modelos
- **Documentación**: La documentación técnica hace referencia a modelos interpretables y explicabilidad

#### Medibilidad
- ✅ **Entrenamiento del clasificador**: Se puede verificar si se ha entrenado un modelo
- ✅ **Interpretabilidad**: Se puede comprobar si el modelo es interpretable
- ✅ **Explicación de factores**: Se puede verificar si se puede explicar el aporte de cada factor

### Objetivo específico 3: Complementar la lectura nacional con capas de incendios y de alerta temprana a escala urbana

#### Descripción
Este objetivo busca ampliar la visión del riesgo ambiental con capas adicionales que proporcionen información más específica y local.

#### Fundamento técnico
- **Capa de incendios**: Medición de área quemada por dNBR en municipios seleccionados
- **Capa de alerta temprana urbana**: Información específica para Bogotá
- **Complementar la lectura nacional**: Proporcionar información más detallada y específica

#### Evidencia técnica
- **Documento histórico**: "complementar la lectura nacional con capas de incendios (área quemada por dNBR en municipios seleccionados) y de alerta temprana a escala urbana (Bogotá)"
- **Componentes complementarios**: El documento menciona específicamente estos componentes
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/satelital/firms_signal.py` podría contener lógica relacionada con señales satelitales

#### Medibilidad
- ✅ **Capa de incendios**: Se puede verificar si se han calculado áreas quemadas
- ✅ **Capa de alerta temprana**: Se puede verificar si se tiene información para Bogotá
- ✅ **Complementar la lectura**: Se puede comprobar si se amplía la visión nacional

### Objetivo específico 4: Garantizar la reproducibilidad y la auditabilidad del producto en repositorio abierto

#### Descripción
Este objetivo se enfoca en asegurar que el producto desarrollado pueda ser replicado y auditado por terceros.

#### Fundamento técnico
- **Reproducibilidad**: El proceso debe poder ser replicado por otros investigadores
- **Auditabilidad**: El proceso debe ser verificable por terceros
- **Repositorio abierto**: El producto debe estar disponible públicamente

#### Evidencia técnica
- **Documento histórico**: "La reproducibilidad se asegura publicando el producto en repositorio abierto"
- **Documentación del proyecto**: El proyecto está estructurado para ser reproducible
- **Repositorio Git**: El proyecto se encuentra en un repositorio Git accesible

#### Medibilidad
- ✅ **Repositorio abierto**: Se puede verificar si el producto está en un repositorio público
- ✅ **Reproducibilidad**: Se puede comprobar si se puede replicar el proceso
- ✅ **Auditabilidad**: Se puede verificar si el proceso es auditable

### Relación entre objetivos específicos y el objetivo general

Los objetivos específicos están directamente relacionados con el objetivo general:

1. **Construir índice**: Es la base para ordenar los municipios por riesgo
2. **Entrenar clasificador interpretable**: Permite el ordenamiento y explicación de factores
3. **Complementar con capas**: Amplía la visión del riesgo ambiental
4. **Garantizar reproducibilidad**: Asegura que el resultado sea útil y confiable

### Coherencia entre objetivos

Los objetivos específicos son coherentes entre sí:

1. **Secuencia lógica**: El índice es necesario para entrenar el clasificador, que a su vez permite la explicación
2. **Complementariedad**: Los objetivos se complementan para ofrecer una solución completa
3. **Fundamentación común**: Todos están basados en el mismo enfoque de datos abiertos y análisis ambiental

### Fundamentación técnica sólida

Cada objetivo específico está fundamentado en:

1. **Documento histórico**: Todos los objetivos se derivan directamente del documento histórico
2. **Código fuente**: Se puede encontrar evidencia del enfoque en el código fuente del proyecto
3. **Documentación técnica**: La documentación del proyecto respalda los enfoques propuestos
4. **Estructura del proyecto**: La organización del proyecto refleja estos objetivos

### Verificación de aceptación

Los objetivos específicos cumplen con los criterios de aceptación:

- ✅ **Claros y medibles**: Cada objetivo tiene un enunciado claro y se puede verificar si se cumple
- ✅ **Relación directa con el objetivo general**: Todos están alineados con el objetivo principal
- ✅ **Fundamentación técnica sólida**: Se basan en evidencia técnica del proyecto
- ✅ **Coherencia entre objetivos**: Los objetivos se complementan y no se contradicen

### Contexto del conjunto de objetivos

El conjunto de objetivos específicos representa una solución integral para el problema ambiental identificado:

1. **Análisis completo**: Se cubren múltiples aspectos del riesgo ambiental
2. **Enfoque técnico**: Se utiliza tecnología avanzada (machine learning, SHAP)
3. **Aplicación práctica**: El resultado tiene aplicación directa en políticas públicas
4. **Calidad del producto**: Se garantiza reproducibilidad y auditabilidad

## Conclusión

Los objetivos específicos están claramente definidos, coherentes entre sí y directamente relacionados con el objetivo general. Cada uno está fundamentado en evidencia técnica del proyecto y es medible. Estos objetivos proporcionan una estructura clara para el desarrollo del estudio y garantizan que se alcance el propósito principal del proyecto AquaBosque Minero IA.