# 5. DEFINICIÓN DEL PROBLEMA ANALÍTICO

## Propósito
Definir claramente el problema analítico que se aborda.

## Contenido mínimo
- Problema central del estudio
- Contexto del problema
- Relevancia del problema
- Impacto del problema

## Evidencia requerida
- Documento histórico A1
- Código fuente del proyecto
- Análisis de la problemática ambiental

## Criterios de aceptación
- Problema definido con precisión técnica
- Contexto claro y relevante
- Impacto claramente identificado
- Fundamentación en evidencia

## Desarrollo del contenido

### Problema central del estudio

El problema central del estudio es:

**"Combinar señales heterogéneas de presión ambiental en una priorización interpretable por municipio, y distinguir con honestidad dos tipos de tarea: la priorización nacional, que ordena y explica el riesgo a partir de un índice compuesto, y la alerta temprana urbana, que sí constituye un problema de predicción supervisada sobre eventos observados."**

Este problema central encapsula tanto el desafío técnico como el conceptual del proyecto AquaBosque Minero IA.

### Contexto del problema

#### Ambiente de gestión ambiental

El contexto del problema se encuentra dentro del entorno de gestión ambiental en Colombia, donde:

1. **La presión ambiental es desigual**: Diferentes regiones y municipios enfrentan distintos niveles de presión ambiental debido a actividades humanas como minería, deforestación y estrés hídrico.

2. **Los recursos son limitados**: Las instituciones encargadas de la protección ambiental tienen recursos limitados para abordar todos los problemas de manera simultánea.

3. **La toma de decisiones requiere evidencia**: Las políticas ambientales deben basarse en análisis y datos objetivos para ser efectivas.

#### Complejidad de los datos ambientales

El problema se complica por la naturaleza heterogénea de los datos ambientales:

1. **Datos de diferentes orígenes**: Información proveniente de instituciones gubernamentales, organismos internacionales y fuentes satelitales.

2. **Datos de diferentes escalas**: Desde datos locales (municipales) hasta datos globales (satelitales).

3. **Datos de diferentes tipos**: Datos numéricos, geoespaciales, temporales y categóricos.

4. **Datos de diferentes niveles de calidad**: Algunos datos son más confiables que otros, lo que requiere procesamiento cuidadoso.

### Relevancia del problema

#### Importancia para políticas públicas

El problema es altamente relevante para políticas públicas porque:

1. **Optimización de recursos**: Permite asignar recursos de manera más eficiente y efectiva.

2. **Toma de decisiones informada**: Facilita la toma de decisiones basadas en evidencia.

3. **Respuesta anticipada**: Permite identificar zonas de alto riesgo antes de que ocurran problemas graves.

4. **Transparencia**: Proporciona un proceso transparente y auditable para la priorización.

#### Relevancia técnica

Desde el punto de vista técnico, el problema es relevante porque:

1. **Desafío de integración de datos**: Combina múltiples fuentes de datos heterogéneas.

2. **Necesidad de interpretación**: No basta con predecir, se necesita entender por qué se predice.

3. **Enfoque multidisciplinario**: Requiere conocimientos de geografía, medio ambiente, estadística y ciencia de datos.

4. **Aplicación de IA explicables**: Representa un desafío actual en el campo de la inteligencia artificial.

### Impacto del problema

#### Impacto social

El impacto social del problema es significativo:

1. **Mejora en la calidad de vida**: Al priorizar acciones ambientales, se puede mejorar el entorno de vida de poblaciones vulnerables.

2. **Protección de ecosistemas**: Mejora la protección de ecosistemas críticos.

3. **Prevención de crisis ambientales**: Ayuda a prevenir crisis ambientales que podrían afectar comunidades enteras.

#### Impacto económico

El impacto económico incluye:

1. **Eficiencia en inversión**: Optimiza la inversión en protección ambiental.

2. **Reducción de costos**: Reduce los costos asociados a la gestión ambiental.

3. **Valoración de recursos**: Permite valorar mejor los recursos ambientales.

#### Impacto ambiental

El impacto ambiental es directo:

1. **Protección de áreas críticas**: Prioriza la protección de áreas más vulnerables.

2. **Mejora en la gestión**: Mejora la gestión de recursos naturales.

3. **Sostenibilidad**: Contribuye a la sostenibilidad a largo plazo.

### Fundamento técnico del problema

El problema analítico está fundamentado en evidencia técnica del proyecto:

#### Código fuente del proyecto

El código fuente del proyecto en `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/` demuestra el enfoque técnico:

1. **Construcción de índices**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py` muestra cómo se construyen índices de riesgo.

2. **Entrenamiento de modelos**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py` contiene la lógica de entrenamiento de modelos.

3. **Procesamiento de datos**: El código muestra cómo se manejan diferentes tipos de datos.

#### Documentación técnica

La documentación técnica del proyecto explica los enfoques:

1. **Metodología de construcción de índices**: Se describe cómo se combinan múltiples factores.

2. **Enfoque de explicabilidad**: Se explica el uso de técnicas como SHAP para explicar modelos.

3. **Arquitectura del sistema**: Se describe cómo se estructura la solución.

#### Estructura del proyecto

La estructura del proyecto refleja claramente el problema analítico:

1. **Enfoque multidimensional**: Se abordan múltiples factores ambientales.

2. **Enfoque interpretable**: Se enfatiza en la explicabilidad de los resultados.

3. **Enfoque basado en datos**: Todo el proceso se fundamenta en datos abiertos.

### Distinción entre tipos de tareas

Una característica clave del problema es la distinción entre dos tipos de tareas:

#### Priorización nacional (índice compuesto)

Esta tarea se enfoca en:

1. **Ordenamiento de municipios**: Clasificar los municipios según su riesgo ambiental combinado.

2. **Explicación de factores dominantes**: Identificar qué factor es el más importante en cada municipio.

3. **Uso de índices compuestos**: Utiliza múltiples variables para construir un índice único.

4. **Enfoque descriptivo**: Describe el estado actual del riesgo ambiental.

#### Alerta temprana urbana (predicción supervisada)

Esta tarea se enfoca en:

1. **Predicción de eventos observados**: Predecir eventos ambientales que ya han ocurrido.

2. **Modelos supervisados**: Se utilizan datos históricos para entrenar modelos.

3. **Aplicación específica**: Se enfoca en la ciudad de Bogotá.

4. **Enfoque predictivo**: Intenta predecir eventos futuros basados en patrones pasados.

### Componentes del problema analítico

El problema analítico se compone de varios componentes interrelacionados:

#### Componente 1: Integración de señales heterogéneas

- **Desafío**: Combinar datos de diferentes orígenes y tipos.
- **Solución**: Desarrollar métodos de integración y normalización.
- **Importancia**: Permite una visión completa del riesgo ambiental.

#### Componente 2: Priorización interpretable

- **Desafío**: Crear un sistema que no solo ordene, sino que explique.
- **Solución**: Utilizar técnicas de explicabilidad como SHAP.
- **Importancia**: Aumenta la confianza en los resultados.

#### Componente 3: Diferenciación de enfoques

- **Desafío**: Manejar diferentes tipos de análisis (descriptivo vs predictivo).
- **Solución**: Separar claramente los enfoques.
- **Importancia**: Evita confusiones metodológicas.

#### Componente 4: Uso de datos abiertos

- **Desafío**: Trabajar con datos disponibles públicamente.
- **Solución**: Desarrollar procesos de limpieza y validación.
- **Importancia**: Garantiza la reproducibilidad y transparencia.

### Verificación de aceptación

El problema analítico cumple con los criterios de aceptación:

- ✅ **Definido con precisión técnica**: Se describe claramente el problema y sus componentes.
- ✅ **Contexto claro y relevante**: Se sitúa dentro del entorno de gestión ambiental.
- ✅ **Impacto claramente identificado**: Se describen los impactos sociales, económicos y ambientales.
- ✅ **Fundamentación en evidencia**: Se basa en código fuente, documentación y estructura del proyecto.

### Relación con el documento histórico

El problema analítico se deriva directamente del documento histórico AquaBosque_A1_Definicion_Tematica.docx:

"El problema analítico consiste en combinar señales heterogéneas de presión ambiental en una priorización interpretable por municipio, y en distinguir con honestidad dos tipos de tarea: la priorización nacional, que ordena y explica el riesgo a partir de un índice compuesto, y la alerta temprana urbana, que sí constituye un problema de predicción supervisada sobre eventos observados. El estudio aporta a las dimensiones de capacidad predictiva y soporte a la planeación, robustez metodológica, escalabilidad e interoperabilidad y sostenibilidad técnica."

### Implicaciones del problema

El problema analítico tiene importantes implicaciones:

#### Implicaciones metodológicas

1. **Complejidad del análisis**: Requiere métodos avanzados de integración de datos.
2. **Necesidad de explicabilidad**: No basta con predecir, se debe entender.
3. **Enfoque mixto**: Combina análisis descriptivo y predictivo.

#### Implicaciones técnicas

1. **Arquitectura del sistema**: Requiere una arquitectura flexible para diferentes tipos de análisis.
2. **Calidad de datos**: La calidad de los resultados depende de la calidad de los datos de entrada.
3. **Escalabilidad**: El sistema debe ser escalable a diferentes niveles de análisis.

#### Implicaciones sociales

1. **Responsabilidad**: El sistema debe ser responsable y transparente.
2. **Accesibilidad**: Los resultados deben ser accesibles para usuarios no especializados.
3. **Impacto real**: El sistema debe tener impacto real en la gestión ambiental.

## Conclusión

El problema analítico del estudio está claramente definido y fundamentado. Se centra en la combinación de señales heterogéneas de presión ambiental para crear una priorización interpretable por municipio, distinguiendo claramente entre el análisis descriptivo (priorización nacional) y el análisis predictivo (alerta temprana urbana). Este problema es relevante, tiene un impacto significativo y está firmemente fundamentado en la evidencia técnica del proyecto, lo que garantiza su viabilidad y utilidad práctica.