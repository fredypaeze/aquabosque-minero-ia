# 7. ALCANCE DEL ESTUDIO

## Propósito
Definir los límites y extensión del estudio.

## Contenido mínimo
- Ámbito geográfico (municipios Colombianos)
- Componentes principales (modelo municipal principal)
- Componentes complementarios (incendios, Bogotá)
- Delimitación temporal basada en disponibilidad de datos

## Evidencia requerida
- Documento histórico A1
- Código fuente del proyecto (municipios.geojson)
- Documentación técnica del proyecto

## Criterios de aceptación
- Ámbito claro y definido
- Límites bien establecidos
- Coherencia con el problema identificado
- Fundamentación técnica

## Desarrollo del contenido

### Ámbito geográfico

El ámbito geográfico del estudio es:

**"Priorización nacional de los 1.122 municipios de Colombia"**

Este alcance se basa en el documento histórico y en la estructura del proyecto:

#### Fundamento técnico

1. **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios del país según su riesgo ambiental combinado"

2. **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` contiene datos geoespaciales de todos los municipios colombianos

3. **Documentación técnica**: La documentación del proyecto hace referencia a análisis a nivel nacional

#### Justificación del alcance

El alcance de 1.122 municipios es justificado porque:

- **Cobertura completa**: Cubre todos los municipios del país
- **Relevancia política**: Los municipios son unidades administrativas clave
- **Disponibilidad de datos**: Se tienen datos geoespaciales completos
- **Aplicación práctica**: Permite priorización a nivel territorial

### Componentes principales

#### Modelo municipal principal

El componente principal del estudio es:

**"Modelo de priorización ambiental municipal"**

Este componente incluye:

1. **Construcción de índice compuesto**: Combinación de múltiples factores ambientales
2. **Ordenamiento de municipios**: Clasificación por niveles de riesgo
3. **Explicación de factores dominantes**: Identificación de qué factor predomina en cada municipio
4. **Análisis geoespacial**: Visualización del riesgo por región

#### Fundamento técnico

1. **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios del país según su riesgo ambiental combinado"

2. **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py` muestra cómo se construyen los índices

3. **Documentación técnica**: Se enfatiza en el análisis de municipios como unidad de análisis

### Componentes complementarios

#### Capa de incendios

**"Medición de área quemada por dNBR en municipios seleccionados"**

Este componente complementario se basa en:

1. **Documento histórico**: "complementar la lectura nacional con capas de incendios (área quemada por dNBR en municipios seleccionados)"

2. **Fundamento**: Análisis específico de incendios forestales que afectan el riesgo ambiental

3. **Enfoque**: Área quemada medida por dNBR (Difference Normalized Burn Ratio)

#### Capa de alerta temprana urbana

**"Alerta temprana a escala urbana para Bogotá"**

Este componente complementario se basa en:

1. **Documento histórico**: "complementar la lectura nacional con capas de alerta temprana a escala urbana (Bogotá)"

2. **Fundamento**: Sistema de alerta para la ciudad capital

3. **Enfoque**: Monitoreo de eventos observados en la ciudad

#### Justificación de componentes complementarios

Los componentes complementarios son justificados porque:

- **Amplían la visión**: Proporcionan información más específica
- **No extienden el alcance principal**: Se mantienen dentro del enfoque del proyecto
- **Son relevantes**: Aportan información valiosa para decisiones locales
- **Se mencionan explícitamente**: Están definidos en el documento histórico

### Delimitación temporal

#### Enfoque temporal actualizado

**"Delimitación temporal basada en disponibilidad de datos"**

Esta delimitación se diferencia del supuesto original de 2010 porque:

1. **Fundamento técnico**: "La delimitación temporal debe quedar sujeta a evidencia real de disponibilidad y cobertura"

2. **Justificación**: Evita suposiciones no verificables y se basa en evidencia real

3. **Flexibilidad**: Se adapta a la disponibilidad real de datos

#### Evidencia de disponibilidad

La delimitación temporal se basa en:

1. **Fuentes oficiales**: Datos disponibles de ANM, IDEAM, NASA, IDIGER
2. **Historial de datos**: Disponibilidad real de datos históricos
3. **Actualizaciones periódicas**: Datos que se actualizan regularmente
4. **Señales cercanas al tiempo real**: Cuando están demostradas

#### Consideraciones temporales

1. **Datos históricos**: Se pueden utilizar datos históricos disponibles
2. **Actualizaciones periódicas**: Se consideran datos que se actualizan regularmente
3. **Señales cercanas al tiempo real**: Se consideran cuando están demostradas
4. **Limitaciones**: Se reconocen las limitaciones de disponibilidad temporal

### Coherencia con el problema identificado

El alcance del estudio está completamente coherente con el problema analítico:

1. **Priorización nacional**: Responde al desafío de ordenar municipios por riesgo ambiental
2. **Componentes complementarios**: Proporciona información adicional sin extender el alcance
3. **Delimitación temporal**: Se basa en evidencia real en lugar de suposiciones
4. **Enfoque técnico**: Se centra en el análisis de datos geoespaciales y ambientales

### Fundamento técnico del alcance

#### Código fuente del proyecto

El código fuente del proyecto respalda el alcance:

1. **Archivo de municipios**: `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` contiene todos los municipios
2. **Funciones de construcción**: `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py` construye índices por municipio
3. **Estructura de modelos**: `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py` entrena modelos para municipios

#### Documentación técnica

La documentación del proyecto apoya el alcance:

1. **README**: Describe el alcance del proyecto
2. **Documentación de features**: Explica cómo se construyen los índices
3. **Documentación de modelos**: Muestra cómo se entrenan modelos por municipio

#### Estructura del proyecto

La estructura del proyecto refleja el alcance:

1. **Directorio de datos**: `/home/tuxilo/aquabosque-minero-ia/data/` contiene datos de municipios
2. **Directorio de código**: `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/` está organizado para análisis municipal
3. **Documentación**: Se enfatiza en el análisis territorial

### Límites del estudio

#### Límites establecidos

1. **Ámbito geográfico**: Solo municipios colombianos (no departamentos ni regiones)
2. **Componentes principales**: Solo el modelo municipal principal y componentes complementarios mencionados
3. **Temporal**: Basado en disponibilidad real de datos
4. **No incluye**: Monitoreo satelital continuo en tiempo real (como se menciona en el documento histórico)

#### Justificación de límites

Los límites están justificados porque:

1. **Relevancia del alcance**: Se centra en la unidad de análisis más adecuada para políticas locales
2. **Recursos disponibles**: Se enfoca en lo que es técnicamente manejable
3. **Claridad del enfoque**: Evita extender el alcance más allá de lo definido
4. **Consistencia con documento histórico**: Se mantiene el enfoque del documento original

### Comparación con documento histórico

El alcance actual mantiene coherencia con el documento histórico:

#### Coincidencias

1. **Ámbito principal**: Priorización nacional de municipios (1.122)
2. **Componentes complementarios**: Incendios y alerta urbana de Bogotá
3. **Enfoque técnico**: Análisis de datos ambientales

#### Diferencias técnicas

1. **Delimitación temporal**: Cambio de supuesto de 2010 a disponibilidad real
2. **Enfoque de datos**: Cambio de exigencia de tiempo real a distinción de tipos de datos

### Impacto del alcance

#### Impacto técnico

1. **Complejidad del análisis**: Se requiere análisis de 1.122 unidades
2. **Escalabilidad**: El sistema debe ser escalable a este número
3. **Calidad de resultados**: Mayor cobertura implica mejores resultados

#### Impacto metodológico

1. **Enfoque sistemático**: Análisis sistemático de todos los municipios
2. **Comparabilidad**: Se pueden comparar resultados entre municipios
3. **Generalización**: Resultados aplicables a toda la nación

#### Impacto práctico

1. **Aplicación política**: Resultados aplicables a políticas locales
2. **Asignación de recursos**: Permite priorizar recursos por municipio
3. **Monitoreo**: Facilita el seguimiento del riesgo ambiental

### Verificación de aceptación

El alcance del estudio cumple con los criterios de aceptación:

- ✅ **Ámbito claro y definido**: Se especifica claramente el alcance geográfico
- ✅ **Límites bien establecidos**: Se definen claramente los límites del estudio
- ✅ **Coherencia con el problema identificado**: Se relaciona directamente con el problema analítico
- ✅ **Fundamentación técnica**: Se basa en evidencia del código fuente y documentación

### Consideraciones adicionales

#### Actualización de datos

El estudio considera:

1. **Fuentes de datos actualizadas**: Se pueden incorporar datos actualizados periódicamente
2. **Procesos de actualización**: Se deben establecer procesos para mantener los datos actualizados
3. **Versionado de datos**: Se debe controlar la versión de los datos utilizados

#### Escalabilidad futura

El alcance permite:

1. **Extensión**: Puede ampliarse a otros niveles de análisis (departamentos, regiones)
2. **Refinamiento**: Puede refinarse con más datos o técnicas
3. **Adaptación**: Puede adaptarse a otros contextos similares

#### Integración con otros estudios

El alcance permite:

1. **Integración**: Se puede integrar con otros estudios ambientales
2. **Complementariedad**: Se complementa con estudios de otros temas
3. **Coherencia**: Se mantiene coherente con otros estudios del ministerio

## Conclusión

El alcance del estudio está claramente definido y fundamentado. Se centra en la priorización nacional de los 1.122 municipios de Colombia, con componentes principales y complementarios que amplían la visión sin extender el alcance principal. La delimitación temporal se basa en disponibilidad real de datos, evitando suposiciones no verificables. Este alcance es coherente con el problema analítico, fundamentado en evidencia técnica del proyecto y permite una aplicación práctica efectiva en políticas públicas ambientales.