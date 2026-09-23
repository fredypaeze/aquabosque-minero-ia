# A1: Definición de la Temática - AquaBosque Minero IA

## 1. Título

**"Priorización ambiental nacional mediante índice compuesto de riesgo para municipios colombianos"**

## 2. Objetivo General

**Construir un índice de riesgo ambiental combinado por municipio a partir de fuentes abiertas, entrenar un clasificador interpretable que ordene los municipios en niveles de riesgo y explique el aporte de cada factor, complementar la lectura nacional con capas de incendios y de alerta temprana a escala urbana, y garantizar la reproducibilidad y la auditabilidad del producto en repositorio abierto.**

## 3. Objetivos Específicos

1. **Construir un índice de riesgo ambiental combinado por municipio a partir de fuentes abiertas**
2. **Entrenar un clasificador interpretable que ordene los municipios en niveles de riesgo y explique el aporte de cada factor (SHAP)**
3. **Complementar la lectura nacional con capas de incendios (área quemada por dNBR en municipios seleccionados) y de alerta temprana a escala urbana (Bogotá)**
4. **Garantizar la reproducibilidad y la auditabilidad del producto en repositorio abierto**

## 4. Justificación

El proyecto AquaBosque Minero IA tiene un impacto ambiental significativo porque aborda uno de los grandes desafíos de gestión ambiental en Colombia: la distribución desigual de la presión ambiental sobre el territorio. La presión ambiental sobre el territorio —minería, deforestación y estrés hídrico— se distribuye de forma desigual, y requiere una focalización basada en evidencia. Disponer de una priorización transparente y explicable, construida sobre datos abiertos y replicable por terceros, aporta a la sostenibilidad y a la planeación ambiental. El estudio se inscribe además en la exigencia de replicabilidad y auditabilidad propia de lo público: si un resultado no puede replicarse o auditarse, no es viable como instrumento de decisión.

## 5. Problema Analítico

**"Combinar señales heterogéneas de presión ambiental en una priorización interpretable por municipio, y distinguir con honestidad dos tipos de tarea: la priorización nacional, que ordena y explica el riesgo a partir de un índice compuesto, y la alerta temprana urbana, que sí constituye un problema de predicción supervisada sobre eventos observados."**

## 6. Preguntas de Investigación

1. **¿Cómo se puede integrar de manera efectiva señales heterogéneas de presión ambiental para construir un índice compuesto de riesgo ambiental municipal?**
2. **¿Qué factores ambientales predominan en cada municipio colombiano y cómo se puede explicar su influencia en el riesgo ambiental?**
3. **¿Cuál es la distribución geográfica del riesgo ambiental en Colombia y cómo se puede identificar las zonas más vulnerables?**
4. **¿Cómo se puede desarrollar un modelo de machine learning interpretable que ordene los municipios por nivel de riesgo ambiental y explique el aporte de cada factor?**
5. **¿Qué métodos de análisis y visualización permiten comunicar eficazmente los resultados de la priorización ambiental a diferentes audiencias?**
6. **¿Cómo se puede garantizar la reproducibilidad y auditabilidad del proceso de priorización ambiental desarrollado?**

## 7. Alcance del Estudio

**"Priorización nacional de los 1.122 municipios de Colombia"**

El alcance del estudio se centra en la priorización nacional de los 1.122 municipios colombianos, con componentes principales y complementarios que amplían la visión sin extender el alcance principal. La delimitación temporal se basa en disponibilidad real de datos, evitando suposiciones no verificables.

## 8. Posibles Fuentes de Datos

- **Fuentes oficiales**: ANM (Agencia Nacional de Minería), IDEAM (Instituto de Hidrología, Meteorología y Estudios Ambientales), NASA (National Aeronautics and Space Administration), IDIGER (Instituto de Geografía)
- **Fuentes de datos geoespaciales**: Datos geoespaciales de municipios
- **Fuentes de datos históricos**: Series temporales de datos ambientales, registros de eventos ambientales
- **Fuentes de datos actualizadas periódicamente**: Datos meteorológicos y climáticos, datos de minería y actividades industriales
- **Fuentes de datos cercanas al tiempo real**: Datos de monitoreo satelital, datos de alertas tempranas

## 9. Viabilidad del Estudio

El enfoque del estudio es técnicamente viable por varias razones:

- **Método de construcción de índices**: El proyecto utiliza técnicas probadas para construir índices compuestos de múltiples variables ambientales.
- **Enfoque de machine learning interpretable**: Se emplean técnicas modernas de aprendizaje automático que permiten no solo predicción, sino también explicabilidad.
- **Análisis geoespacial**: El enfoque de análisis territorial está bien establecido y respaldado por herramientas especializadas.
- **Integración de datos heterogéneos**: El proyecto tiene experiencia previa en integración de datos de diferentes fuentes.

## 10. Resultados Esperados

1. **Índice de riesgo ambiental compuesto por municipio**: Un índice compuesto que combine múltiples factores ambientales para determinar el riesgo ambiental de cada municipio.
2. **Modelo de machine learning interpretable**: Un modelo de clasificación que ordene los municipios por niveles de riesgo ambiental y explique el aporte de cada factor.
3. **Visualización geoespacial del riesgo ambiental**: Representación visual del riesgo ambiental por municipio a través de mapas y dashboards.
4. **Priorización de municipios por nivel de riesgo**: Ordenamiento de los 1.122 municipios colombianos según su riesgo ambiental combinado.
5. **Identificación de factores dominantes**: Determinación de qué factor ambiental es el más importante en cada municipio.
6. **Análisis geoespacial del riesgo ambiental**: Representación visual del riesgo ambiental por región.

## 11. Supuestos

1. **Disponibilidad de datos geoespaciales completos**: Los datos geoespaciales de los 1.122 municipios colombianos están disponibles y completos.
2. **Capacidad de procesamiento computacional suficiente**: Existe capacidad de cómputo suficiente para procesar los datos y ejecutar los modelos.
3. **Disponibilidad de datos de fuentes oficiales**: Las fuentes oficiales (ANM, IDEAM, NASA, IDIGER) tendrán datos disponibles para el análisis.
4. **Disponibilidad de datos históricos**: Los datos históricos necesarios para el análisis están disponibles.
5. **Disponibilidad de datos satelitales**: Los datos satelitales necesarios para componentes complementarios estarán disponibles.
6. **Disponibilidad de datos de alerta temprana**: Los datos de alerta temprana para Bogotá estarán disponibles.
7. **Consistencia de los datos de diferentes fuentes**: Los datos de diferentes fuentes son consistentes entre sí.
8. **Calidad suficiente de los datos para análisis**: Los datos disponibles tienen suficiente calidad para realizar el análisis requerido.
9. **Coherencia del alcance con el problema analítico**: El alcance definido (priorización nacional de municipios) es coherente con el problema analítico.
10. **Viabilidad del enfoque de componentes complementarios**: Los componentes complementarios (incendios y alerta urbana) son viables y pueden integrarse al estudio principal.

## 12. Riesgos y Limitaciones

### Riesgos Técnicos

1. **Fallo en la integración de datos heterogéneos**: Posible incapacidad para integrar correctamente datos de diferentes fuentes y formatos.
2. **Problemas de escalabilidad en el procesamiento**: Posible incapacidad para procesar los datos de los 1.122 municipios en tiempos razonables.
3. **Fallo en el entrenamiento de modelos interpretables**: Posible incapacidad para entrenar modelos que sean realmente interpretables y precisos.

### Limitaciones del Enfoque

1. **Enfoque exclusivo en municipios**: El estudio se centra únicamente en análisis a nivel municipal, excluyendo otros niveles de análisis.
2. **Separación entre priorización y alerta temprana**: El enfoque separa claramente la priorización nacional de la alerta temprana urbana, lo cual puede limitar la integración de ambos enfoques.
3. **Enfoque basado en datos abiertos**: El estudio depende completamente de datos abiertos, lo cual puede limitar la profundidad del análisis.

### Limitaciones de Datos

1. **Disponibilidad temporal limitada**: La disponibilidad de datos históricos puede ser limitada o inconsistente.
2. **Calidad variable de datos**: La calidad de los datos puede variar entre fuentes y con el tiempo.
3. **Cobertura geográfica incompleta**: La cobertura geográfica puede no ser completa en todas las regiones.

### Limitaciones de Alcance

1. **Exclusión de monitoreo satelital en tiempo real**: El estudio excluye el monitoreo satelital continuo en tiempo real.
2. **Exclusión de otros tipos de análisis**: El estudio se centra en el análisis de riesgo ambiental, excluyendo otros tipos de análisis.
3. **Dependencia de fuentes externas**: El estudio depende de fuentes de datos externas que pueden no estar disponibles o cambiar.

## Bibliografía

1. AquaBosque_A1_Definicion_Tematica.docx - Documento histórico de definición de temática
2. /home/tuxilo/aquabosque-minero-ia/README.md - Documentación general del proyecto
3. /home/tuxilo/aquabosque-minero-ia/docs/ - Documentación técnica del proyecto
4. /home/tuxilo/aquabosque-minero-ia/data/municipios.geojson - Datos geoespaciales de municipios
5. /home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py - Código de construcción de índices
6. /home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py - Código de entrenamiento de modelos
7. /home/tuxilo/modelo-riesgo-suspension/ - Repositorio del modelo de riesgo de apagón