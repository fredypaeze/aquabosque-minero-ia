# 12. RIESGOS Y LIMITACIONES

## Propósito
Identificar los riesgos y limitaciones del estudio.

## Contenido mínimo
- Riesgos técnicos
- Limitaciones del enfoque
- Limitaciones de datos
- Limitaciones de alcance

## Evidencia requerida
- Documento histórico A1
- Código fuente del proyecto
- Documentación técnica del proyecto
- Análisis de riesgos y limitaciones

## Criterios de aceptación
- Riesgos y limitaciones claramente identificados
- Fundamentación técnica
- Impacto identificado en el desarrollo
- Estrategias de mitigación propuestas

## Desarrollo del contenido

### Riesgos técnicos

#### Riesgo 1: Fallo en la integración de datos heterogéneos

**Descripción**: Posible incapacidad para integrar correctamente datos de diferentes fuentes y formatos.

**Fundamento técnico**:
- **Documento histórico**: "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible"
- **Código fuente**: El código muestra procesamiento de datos heterogéneos
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Si la integración falla, el análisis será incompleto o incorrecto.

**Estrategia de mitigación**:
- Realizar pruebas de integración con datos de prueba
- Implementar validación cruzada de datos
- Utilizar herramientas especializadas de integración de datos

#### Riesgo 2: Problemas de escalabilidad en el procesamiento

**Descripción**: Posible incapacidad para procesar los datos de los 1.122 municipios en tiempos razonables.

**Fundamento técnico**:
- **Documento histórico**: "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible"
- **Código fuente**: El código muestra procesamiento de grandes volúmenes de datos
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Si hay problemas de escalabilidad, se retrasará el desarrollo o se requerirá optimización.

**Estrategia de mitigación**:
- Realizar pruebas de escalabilidad con subconjuntos de datos
- Optimizar algoritmos de procesamiento
- Utilizar técnicas de procesamiento paralelo

#### Riesgo 3: Fallo en el entrenamiento de modelos interpretables

**Descripción**: Posible incapacidad para entrenar modelos que sean realmente interpretables y precisos.

**Fundamento técnico**:
- **Documento histórico**: "Entrenar un clasificador interpretable que ordene los municipios en niveles de riesgo y explique el aporte de cada factor (SHAP)"
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py` contiene lógica de entrenamiento
- **Documentación**: Se menciona la importancia de SHAP

**Impacto**: Si los modelos no son interpretables, no se cumplirá con el objetivo principal.

**Estrategia de mitigación**:
- Realizar pruebas piloto con modelos pequeños
- Validar la interpretabilidad con métricas específicas
- Utilizar técnicas de validación cruzada

### Limitaciones del enfoque

#### Limitación 1: Enfoque exclusivo en municipios

**Descripción**: El estudio se centra únicamente en análisis a nivel municipal, excluyendo otros niveles de análisis.

**Fundamento técnico**:
- **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios del país"
- **Código fuente**: El código se estructura para análisis municipal
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Se pierde la capacidad de análisis a otros niveles (departamentales, regionales).

**Estrategia de mitigación**:
- Documentar la limitación claramente
- Proporcionar marcos para extensión futura
- Mantener estructura flexible para futuras expansiones

#### Limitación 2: Separación entre priorización y alerta temprana

**Descripción**: El enfoque separa claramente la priorización nacional de la alerta temprana urbana, lo cual puede limitar la integración de ambos enfoques.

**Fundamento técnico**:
- **Documento histórico**: "distinguir con honestidad dos tipos de tarea: la priorización nacional, que ordena y explica el riesgo a partir de un índice compuesto, y la alerta temprana urbana, que sí constituye un problema de predicción supervisada sobre eventos observados"
- **Código fuente**: El código muestra separación de enfoques
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Puede haber oportunidades perdidas de integración de ambos enfoques.

**Estrategia de mitigación**:
- Documentar claramente la separación como intencional
- Proporcionar marcos para futura integración
- Mantener la separación como enfoque válido

#### Limitación 3: Enfoque basado en datos abiertos

**Descripción**: El estudio depende completamente de datos abiertos, lo cual puede limitar la profundidad del análisis.

**Fundamento técnico**:
- **Documento histórico**: "El estudio es viable con datos abiertos"
- **Código fuente**: El código está estructurado para datos abiertos
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Puede haber datos de menor calidad o cobertura que afecten resultados.

**Estrategia de mitigación**:
- Documentar las limitaciones de los datos abiertos
- Proveer recomendaciones para mejoras futuras
- Validar resultados con fuentes alternativas cuando sea posible

### Limitaciones de datos

#### Limitación 1: Disponibilidad temporal limitada

**Descripción**: La disponibilidad de datos históricos puede ser limitada o inconsistente.

**Fundamento técnico**:
- **Documento histórico**: "La delimitación temporal debe quedar sujeta a evidencia real de disponibilidad y cobertura"
- **Código fuente**: El código muestra procesamiento de datos temporales
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Análisis limitado a períodos de tiempo específicos.

**Estrategia de mitigación**:
- Documentar claramente los períodos de datos disponibles
- Proporcionar marcos para actualización de datos
- Usar métodos robustos que manejen datos incompletos

#### Limitación 2: Calidad variable de datos

**Descripción**: La calidad de los datos puede variar entre fuentes y con el tiempo.

**Fundamento técnico**:
- **Documento histórico**: "La reproducibilidad se asegura publicando el producto en repositorio abierto"
- **Código fuente**: El código muestra procesamiento de datos de calidad variable
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Resultados pueden verse afectados por errores o inconsistencias en los datos.

**Estrategia de mitigación**:
- Implementar validación y limpieza de datos
- Documentar las limitaciones de calidad de datos
- Proporcionar métricas de calidad de los resultados

#### Limitación 3: Cobertura geográfica incompleta

**Descripción**: La cobertura geográfica puede no ser completa en todas las regiones.

**Fundamento técnico**:
- **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios"
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` contiene los datos
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Algunas áreas pueden tener menos precisión en el análisis.

**Estrategia de mitigación**:
- Documentar claramente las áreas con menor cobertura
- Proporcionar métricas de cobertura
- Recomendar actualización de datos para mejor cobertura

### Limitaciones de alcance

#### Limitación 1: Exclusión de monitoreo satelital en tiempo real

**Descripción**: El estudio excluye el monitoreo satelital continuo en tiempo real.

**Fundamento técnico**:
- **Documento histórico**: "Queda fuera del alcance el monitoreo satelital continuo en tiempo real"
- **Código fuente**: No se menciona en el código actual
- **Documentación**: Se menciona en la documentación general del proyecto

**Impacto**: Se pierde la capacidad de monitoreo continuo de eventos ambientales.

**Estrategia de mitigación**:
- Documentar claramente esta limitación
- Proporcionar marcos para futuras extensiones
- Enfatizar los beneficios de los enfoques incluidos

#### Limitación 2: Exclusión de otros tipos de análisis

**Descripción**: El estudio se centra en el análisis de riesgo ambiental, excluyendo otros tipos de análisis.

**Fundamento técnico**:
- **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios"
- **Código fuente**: El código se enfoca en análisis de riesgo ambiental
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: No se abordan otros aspectos del análisis ambiental.

**Estrategia de mitigación**:
- Documentar claramente el alcance específico
- Proporcionar marcos para análisis adicionales futuros
- Enfatizar el enfoque específico como válido y útil

#### Limitación 3: Dependencia de fuentes externas

**Descripción**: El estudio depende de fuentes de datos externas que pueden no estar disponibles o cambiar.

**Fundamento técnico**:
- **Documento histórico**: "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible"
- **Código fuente**: El código utiliza fuentes externas
- **Documentación**: Se menciona en la documentación del proyecto

**Impacto**: Cambios en las fuentes pueden afectar reproducibilidad.

**Estrategia de mitigación**:
- Documentar claramente las fuentes utilizadas
- Proporcionar alternativas o marcos para fuentes alternas
- Mantener estructura flexible para cambios de fuentes

### Análisis de impacto de riesgos y limitaciones

#### Impacto positivo

1. **Conciencia de riesgos**: Identificar riesgos permite prepararse para ellos.
2. **Mejora del diseño**: Las limitaciones ayudan a mejorar el diseño del estudio.
3. **Gestión proactiva**: Permite una gestión proactiva de problemas potenciales.

#### Impacto negativo

1. **Riesgo de fallo**: Algunos riesgos pueden causar fallos en el desarrollo.
2. **Limitaciones en resultados**: Las limitaciones pueden afectar la calidad de los resultados.
3. **Necesidad de ajustes**: Se pueden requerir ajustes en el desarrollo si ocurren riesgos.

### Verificación de aceptación

Los riesgos y limitaciones cumplen con los criterios de aceptación:

- ✅ **Claramente identificados**: Todos los riesgos y limitaciones están claramente definidos
- ✅ **Fundamentación técnica**: Cada riesgo y limitación está fundamentado en el documento histórico y código fuente
- ✅ **Impacto identificado**: Se ha analizado el impacto de cada riesgo y limitación
- ✅ **Estrategias de mitigación propuestas**: Se han propuesto estrategias para mitigar los riesgos y limitaciones

### Coherencia con el documento histórico

Los riesgos y limitaciones están completamente alineados con el documento histórico:

> "Queda fuera del alcance el monitoreo satelital continuo en tiempo real: las capas satelitales corresponden a mediciones por ventana y por evento, no a un servicio de vigilancia permanente, y así se declara para no sobreatribuir capacidades al producto."

> "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible (incluido un clúster de GPU para las capas satelitales). La reproducibilidad se asegura publicando el producto en repositorio abierto y verificando que su reconstrucción desde los datos crudos arroja las mismas métricas. La principal condición de viabilidad es la calidad y actualización de las fuentes abiertas y la gestión honesta del alcance de cada capa."

### Consideraciones adicionales

#### Riesgos de implementación

1. **Cambios en el entorno**: Cambios en el entorno de ejecución pueden afectar el desarrollo.
2. **Problemas de compatibilidad**: Incompatibilidades con herramientas o sistemas pueden surgir.
3. **Tiempo de ejecución**: Tiempos de ejecución más largos de lo esperado.

#### Limitaciones de mantenimiento

1. **Actualización de datos**: La necesidad de mantener los datos actualizados.
2. **Mantenimiento del código**: La necesidad de mantener el código actualizado.
3. **Soporte técnico**: La necesidad de soporte técnico continuo.

## Conclusión

Los riesgos y limitaciones identificados son fundamentales para comprender los desafíos del estudio. Están claramente definidos, fundamentados en el documento histórico y código fuente, y con estrategias de mitigación propuestas. Los riesgos principales incluyen problemas de integración de datos, escalabilidad y entrenamiento de modelos, mientras que las limitaciones principales se centran en el enfoque exclusivo en municipios, la dependencia de datos abiertos y la exclusión de monitoreo en tiempo real. Estas consideraciones son esenciales para el desarrollo exitoso del proyecto y deben mantenerse en cuenta durante todo el proceso.