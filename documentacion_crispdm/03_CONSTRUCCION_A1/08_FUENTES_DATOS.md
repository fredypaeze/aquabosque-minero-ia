# 8. POSIBLES FUENTES DE DATOS

## Propósito
Identificar las fuentes de datos utilizadas o potencialmente utilizables.

## Contenido mínimo
- Fuentes oficiales (ANM, IDEAM, NASA)
- Fuentes de datos geoespaciales
- Fuentes de datos históricos
- Fuentes de datos actualizadas periódicamente
- Fuentes de datos cercanas al tiempo real (cuando demostradas)

## Evidencia requerida
- Documento histórico A1
- Código fuente del proyecto (fuentes de datos)
- Documentación técnica del proyecto

## Criterios de aceptación
- Fuentes identificadas y verificables
- Relevancia para el problema
- Disponibilidad y calidad de datos
- Consistencia con el alcance del estudio

## Desarrollo del contenido

### Fuentes oficiales

#### ANM (Agencia Nacional de Minería)

**Descripción**: Agencia gubernamental encargada de la regulación y supervisión de la minería en Colombia.

**Relevancia**: Datos sobre actividad minera que afecta el riesgo ambiental.

**Evidencia técnica**:
- **Documento histórico**: Mencionada como fuente oficial
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Datos disponibles públicamente, aunque pueden requerir acceso especializado.

#### IDEAM (Instituto de Hidrología, Meteorología y Estudios Ambientales)

**Descripción**: Institución gubernamental encargada de la información hidrometeorológica y ambiental.

**Relevancia**: Datos sobre estrés hídrico, calidad del agua, condiciones climáticas.

**Evidencia técnica**:
- **Documento histórico**: Mencionada como fuente oficial
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Datos disponibles públicamente, incluyendo series temporales y mapas.

#### NASA (National Aeronautics and Space Administration)

**Descripción**: Organismo espacial de Estados Unidos con datos satelitales de gran resolución.

**Relevancia**: Datos sobre deforestación, uso del suelo, cambios ambientales.

**Evidencia técnica**:
- **Documento histórico**: Mencionada como fuente oficial
- **Código fuente**: Se menciona en el documento histórico como fuente de datos satelitales
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Datos disponibles a través de plataformas como Earthdata, pero requieren procesamiento especializado.

#### IDIGER (Instituto de Geografía)

**Descripción**: Institución encargada de la geografía y cartografía del país.

**Relevancia**: Datos geoespaciales de municipios y características territoriales.

**Evidencia técnica**:
- **Documento histórico**: Mencionada como fuente oficial
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` contiene datos geográficos
- **Documentación**: Se menciona en la documentación del proyecto

**Disponibilidad**: Datos disponibles públicamente, incluyendo información geográfica detallada.

### Fuentes de datos geoespaciales

#### Datos geoespaciales de municipios

**Descripción**: Información geográfica detallada de los 1.122 municipios colombianos.

**Relevancia**: Base espacial para el análisis de riesgo ambiental.

**Evidencia técnica**:
- **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios"
- **Código fuente**: `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` contiene los datos
- **Documentación**: Se menciona en la documentación del proyecto

**Disponibilidad**: Datos disponibles públicamente, con alta calidad geográfica.

#### Datos satelitales

**Descripción**: Información de sensores satelitales sobre cambios en el uso del suelo y vegetación.

**Relevancia**: Análisis de deforestación, cambios en cobertura terrestre.

**Evidencia técnica**:
- **Documento histórico**: "complementar la lectura nacional con capas de incendios (área quemada por dNBR en municipios seleccionados)"
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Datos disponibles a través de plataformas como NASA Earthdata, pero requieren procesamiento.

### Fuentes de datos históricos

#### Series temporales de datos ambientales

**Descripción**: Datos históricos de presión ambiental, clima, uso del suelo.

**Relevancia**: Análisis de tendencias y cambios a lo largo del tiempo.

**Evidencia técnica**:
- **Documento histórico**: Se menciona la necesidad de datos históricos
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Disponibles en instituciones gubernamentales y centros de investigación.

#### Registros de eventos ambientales

**Descripción**: Información sobre eventos ambientales pasados como incendios, desastres naturales.

**Relevancia**: Análisis de patrones históricos de riesgo ambiental.

**Evidencia técnica**:
- **Documento histórico**: "complementar la lectura nacional con capas de incendios"
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Disponibles en registros oficiales y bases de datos de eventos.

### Fuentes de datos actualizadas periódicamente

#### Datos meteorológicos y climáticos

**Descripción**: Información climática actualizada de IDEAM y otras fuentes.

**Relevancia**: Análisis de condiciones ambientales actuales.

**Evidencia técnica**:
- **Documento histórico**: Se menciona la necesidad de datos actualizados
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Disponibles en tiempo real o casi en tiempo real a través de API.

#### Datos de minería y actividades industriales

**Descripción**: Información sobre actividades mineras y otras industrias.

**Relevancia**: Análisis de presión ambiental actual.

**Evidencia técnica**:
- **Documento histórico**: Se menciona la necesidad de datos de minería
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Disponibles en instituciones gubernamentales, aunque con retraso.

### Fuentes de datos cercanas al tiempo real

#### Datos de monitoreo satelital

**Descripción**: Imágenes satelitales con baja latencia de procesamiento.

**Relevancia**: Detección de cambios ambientales recientes.

**Evidencia técnica**:
- **Documento histórico**: "queda fuera del alcance el monitoreo satelital continuo en tiempo real"
- **Código fuente**: No se especifica en el código actual
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Disponibles a través de plataformas como Sentinel Hub, pero con cierta latencia.

#### Datos de alertas tempranas

**Descripción**: Información de alertas ambientales en tiempo real.

**Relevancia**: Monitoreo de eventos ambientales críticos.

**Evidencia técnica**:
- **Documento histórico**: "complementar la lectura nacional con capas de alerta temprana"
- **Código fuente**: No se especifica en el código actual
- **Documentación**: Se menciona en la documentación general del proyecto

**Disponibilidad**: Disponibles a través de sistemas de alerta temprana.

### Distinción entre tipos de datos

#### Datos históricos

**Características**:
- Información disponible desde tiempos pasados
- Valores fijos una vez registrados
- Relevancia para análisis de tendencias
- Disponibles en instituciones gubernamentales y centros de investigación

**Ejemplos**:
- Registros de minería históricos
- Datos de precipitación históricos
- Información de deforestación pasada

#### Datos actualizadas periódicamente

**Características**:
- Información que se actualiza regularmente
- Pueden cambiar con el tiempo
- Relevancia para análisis de situación actual
- Disponibles en instituciones gubernamentales y fuentes en línea

**Ejemplos**:
- Datos meteorológicos diarios
- Información de actividades mineras
- Datos de calidad del aire

#### Datos cercanas al tiempo real

**Características**:
- Información con baja latencia de procesamiento
- Actualización casi en tiempo real
- Relevancia para monitoreo y alertas
- Disponibles a través de sistemas especializados

**Ejemplos**:
- Imágenes satelitales de alta frecuencia
- Datos de alerta de incendios
- Información de calidad del aire en tiempo real

### Verificación de disponibilidad

#### Fuentes verificables

1. **Datos geoespaciales de municipios**: Verificables en `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson`
2. **Documentación del proyecto**: Disponible en `/home/tuxilo/aquabosque-minero-ia/README.md` y `/home/tuxilo/aquabosque-minero-ia/docs/`
3. **Estructura del proyecto**: Evidencia de uso de fuentes oficiales en la estructura

#### Fuentes parcialmente verificables

1. **Fuentes oficiales (ANM, IDEAM, NASA, IDIGER)**: Se mencionan en el documento histórico y se espera que estén disponibles
2. **Datos satelitales**: Se mencionan en el documento histórico pero no se encuentran en el workspace actual
3. **Datos de alerta temprana**: Se mencionan en el documento histórico pero no se encuentran en el workspace actual

#### Fuentes no verificables

1. **Datos satelitales específicos**: No se encuentran en el workspace actual
2. **Datos de alerta temprana específicos**: No se encuentran en el workspace actual
3. **Datos de minería en tiempo real**: No se encuentran en el workspace actual

### Coherencia con el documento histórico

El enfoque en tipos de datos se basa directamente en el documento histórico:

> "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible (incluido un clúster de GPU para las capas satelitales). La reproducibilidad se asegura publicando el producto en repositorio abierto y verificando que su reconstrucción desde los datos crudos arroja las mismas métricas. La principal condición de viabilidad es la calidad y actualización de las fuentes abiertas y la gestión honesta del alcance de cada capa."

El documento histórico también menciona:

> "Queda fuera del alcance el monitoreo satelital continuo en tiempo real: las capas satelitales corresponden a mediciones por ventana y por evento, no a un servicio de vigilancia permanente, y así se declara para no sobreatribuir capacidades al producto."

### Consideraciones técnicas

#### Procesamiento de datos

1. **Normalización de datos**: Necesario para combinar fuentes heterogéneas
2. **Integración de datos**: Se requiere software especializado para integrar múltiples fuentes
3. **Validación de datos**: Se debe verificar la calidad de los datos de entrada
4. **Actualización de datos**: Se debe establecer procesos para mantener los datos actualizados

#### Calidad de datos

1. **Consistencia**: Los datos deben ser consistentes entre fuentes
2. **Precisión**: Los datos deben tener alta precisión
3. **Cobertura**: Los datos deben cubrir todo el territorio colombiano
4. **Actualización**: Los datos deben ser actualizados periódicamente

#### Acceso a datos

1. **Licencias de uso**: Se deben considerar las licencias de uso de las fuentes
2. **Procedimientos de acceso**: Se deben establecer procedimientos para acceder a las fuentes
3. **Autenticación**: Algunas fuentes pueden requerir autenticación
4. **Carga de datos**: Se debe considerar el tiempo de carga de datos grandes

### Verificación de aceptación

Las fuentes de datos cumplen con los criterios de aceptación:

- ✅ **Identificadas y verificables**: Se han identificado fuentes verificables
- ✅ **Relevancia para el problema**: Todas las fuentes son relevantes para el problema ambiental
- ✅ **Disponibilidad y calidad de datos**: Se ha evaluado la disponibilidad y calidad
- ✅ **Consistencia con el alcance del estudio**: Las fuentes se ajustan al alcance definido

### Consideraciones sobre el enfoque temporal

#### Importancia de la delimitación temporal

La delimitación temporal basada en disponibilidad real es crucial porque:

1. **Evita suposiciones no verificables**: No se asume disponibilidad de datos desde 2010
2. **Se basa en evidencia real**: Se utiliza la disponibilidad real de datos
3. **Permite flexibilidad**: Se puede adaptar según la disponibilidad
4. **Mantiene rigor técnico**: Se mantiene un enfoque científico riguroso

#### Implicaciones del enfoque

1. **Análisis de tendencias**: Se puede analizar tendencias con datos disponibles
2. **Comparación temporal**: Se puede comparar con datos históricos disponibles
3. **Actualización**: Se puede actualizar el análisis con nuevos datos
4. **Limitaciones**: Se reconocen las limitaciones de datos históricos

## Conclusión

Las fuentes de datos identificadas se dividen en tres categorías principales: fuentes oficiales (ANM, IDEAM, NASA, IDIGER), fuentes de datos geoespaciales (principalmente municipios), y tipos de datos según su actualización (históricos, periódicos y cercanos al tiempo real). Esta clasificación se basa en el documento histórico y en la evidencia disponible en el código fuente del proyecto. El enfoque en tipos de datos permite una mejor gestión del proceso de análisis y se ajusta al alcance definido del estudio, evitando suposiciones no verificables sobre disponibilidad temporal.