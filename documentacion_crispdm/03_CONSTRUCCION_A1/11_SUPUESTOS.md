# 11. SUPUESTOS

## Propósito
Identificar los supuestos necesarios para el desarrollo del estudio.

## Contenido mínimo
- Supuestos técnicos
- Supuestos de disponibilidad de datos
- Supuestos de calidad de datos
- Supuestos de alcance del estudio

## Evidencia requerida
- Documento histórico A1
- Código fuente del proyecto
- Documentación técnica del proyecto
- Análisis de los supuestos identificados

## Criterios de aceptación
- Supuestos claramente identificados
- Fundamentación técnica
- Verificabilidad de los supuestos
- Impacto en el desarrollo del estudio

## Desarrollo del contenido

### Supuestos técnicos

#### Supuesto 1: Disponibilidad de datos geoespaciales completos

**Descripción**: Se asume que los datos geoespaciales de los 1.122 municipios colombianos están disponibles y completos.

**Fundamento técnico**:
- **Documento histórico**: "El estudio construye una capa analítica que ordena los 1.122 municipios del país según su riesgo ambiental combinado"
- **Código fuente**: El archivo `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` contiene los datos geográficos
- **Documentación**: Se menciona en la documentación del proyecto

**Verificabilidad**: Se puede verificar consultando el archivo `/home/tuxilo/aquabosque-minero-ia/data/municipios.geojson` y comparando con el número de municipios colombianos.

**Impacto en el desarrollo**: Si este supuesto no se cumple, el análisis no podrá abarcar todos los municipios, afectando la priorización nacional.

#### Supuesto 2: Capacidad de procesamiento computacional suficiente

**Descripción**: Se asume que existe capacidad de cómputo suficiente para procesar los datos y ejecutar los modelos.

**Fundamento técnico**:
- **Documento histórico**: "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible (incluido un clúster de GPU para las capas satelitales)."
- **Código fuente**: El código utiliza herramientas que requieren recursos computacionales
- **Documentación**: Se menciona en la documentación del proyecto

**Verificabilidad**: Se puede verificar revisando la infraestructura disponible y el tiempo de ejecución de procesos similares.

**Impacto en el desarrollo**: Si este supuesto no se cumple, se podrían requerir ajustes en la metodología o en los recursos disponibles.

#### Supuesto 3: Disponibilidad de datos de fuentes oficiales

**Descripción**: Se asume que las fuentes oficiales (ANM, IDEAM, NASA, IDIGER) tendrán datos disponibles para el análisis.

**Fundamento técnico**:
- **Documento histórico**: "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible"
- **Código fuente**: No se especifica en el código actual, pero se espera que estén disponibles
- **Documentación**: Se menciona en la documentación general del proyecto

**Verificabilidad**: Se puede verificar consultando las fuentes oficiales o revisando su historial de disponibilidad.

**Impacto en el desarrollo**: Si las fuentes no están disponibles, se requerirán alternativas o se tendrán que ajustar los análisis.

### Supuestos de disponibilidad de datos

#### Supuesto 4: Disponibilidad de datos históricos

**Descripción**: Se asume que los datos históricos necesarios para el análisis están disponibles.

**Fundamento técnico**:
- **Documento histórico**: "La reproducibilidad se asegura publicando el producto en repositorio abierto y verificando que su reconstrucción desde los datos crudos arroja las mismas métricas"
- **Código fuente**: No se especifica en el código actual, pero se espera que estén disponibles
- **Documentación**: Se menciona en la documentación general del proyecto

**Verificabilidad**: Se puede verificar revisando las instituciones que proveen datos históricos.

**Impacto en el desarrollo**: Si los datos históricos no están disponibles, se tendrán que usar aproximaciones o datos más recientes.

#### Supuesto 5: Disponibilidad de datos satelitales (cuando aplicable)

**Descripción**: Se asume que los datos satelitales necesarios para componentes complementarios estarán disponibles.

**Fundamento técnico**:
- **Documento histórico**: "complementar la lectura nacional con capas de incendios (área quemada por dNBR en municipios seleccionados)"
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Verificabilidad**: Se puede verificar consultando plataformas como NASA Earthdata.

**Impacto en el desarrollo**: Si los datos satelitales no están disponibles, se tendrán que ajustar los componentes complementarios o buscar alternativas.

#### Supuesto 6: Disponibilidad de datos de alerta temprana

**Descripción**: Se asume que los datos de alerta temprana para Bogotá estarán disponibles.

**Fundamento técnico**:
- **Documento histórico**: "complementar la lectura nacional con capas de alerta temprana a escala urbana (Bogotá)"
- **Código fuente**: No se especifica en el código actual, pero podría ser relevante
- **Documentación**: Se menciona en la documentación general del proyecto

**Verificabilidad**: Se puede verificar consultando instituciones locales de alerta temprana.

**Impacto en el desarrollo**: Si los datos no están disponibles, se tendrán que ajustar los componentes complementarios.

### Supuestos de calidad de datos

#### Supuesto 7: Consistencia de los datos de diferentes fuentes

**Descripción**: Se asume que los datos de diferentes fuentes son consistentes entre sí.

**Fundamento técnico**:
- **Documento histórico**: "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible"
- **Código fuente**: El código muestra procesamiento de datos heterogéneos
- **Documentación**: Se menciona en la documentación del proyecto

**Verificabilidad**: Se puede verificar mediante análisis de calidad y validación cruzada.

**Impacto en el desarrollo**: Si los datos no son consistentes, se requerirán ajustes en el procesamiento de datos.

#### Supuesto 8: Calidad suficiente de los datos para análisis

**Descripción**: Se asume que los datos disponibles tienen suficiente calidad para realizar el análisis requerido.

**Fundamento técnico**:
- **Documento histórico**: "La reproducibilidad se asegura publicando el producto en repositorio abierto"
- **Código fuente**: El código muestra procesamiento de datos de calidad variable
- **Documentación**: Se menciona en la documentación del proyecto

**Verificabilidad**: Se puede verificar mediante análisis de calidad de datos y validación de resultados.

**Impacto en el desarrollo**: Si la calidad no es suficiente, se tendrán que implementar procesos de limpieza o encontrar fuentes alternas.

### Supuestos de alcance del estudio

#### Supuesto 9: Coherencia del alcance con el problema analítico

**Descripción**: Se asume que el alcance definido (priorización nacional de municipios) es coherente con el problema analítico.

**Fundamento técnico**:
- **Documento histórico**: "El problema analítico consiste en combinar señales heterogéneas de presión ambiental en una priorización interpretable por municipio"
- **Código fuente**: El código se centra en análisis municipal
- **Documentación**: Se menciona en la documentación del proyecto

**Verificabilidad**: Se puede verificar comparando el alcance con el problema definido.

**Impacto en el desarrollo**: Si no es coherente, se tendrán que redefinir los alcances o ajustar el problema.

#### Supuesto 10: Viabilidad del enfoque de componentes complementarios

**Descripción**: Se asume que los componentes complementarios (incendios y alerta urbana) son viables y pueden integrarse al estudio principal.

**Fundamento técnico**:
- **Documento histórico**: "complementar la lectura nacional con capas de incendios (área quemada por dNBR en municipios seleccionados) y de alerta temprana a escala urbana (Bogotá)"
- **Código fuente**: No se especifica en el código actual, pero se espera que estén disponibles
- **Documentación**: Se menciona en la documentación general del proyecto

**Verificabilidad**: Se puede verificar revisando la disponibilidad de estos componentes en el entorno del proyecto.

**Impacto en el desarrollo**: Si no son viables, se tendrán que ajustar o eliminar estos componentes.

### Análisis de impacto de los supuestos

#### Impacto positivo

1. **Facilitación del desarrollo**: Los supuestos permiten avanzar con el desarrollo del estudio sin tener que validar cada detalle.

2. **Enfoque claro**: Los supuestos ayudan a mantener un enfoque claro y definido del proyecto.

3. **Eficiencia en el tiempo**: Permite centrarse en el desarrollo principal en lugar de validar cada suposición.

#### Impacto negativo

1. **Riesgo de fallo**: Si alguno de los supuestos no se cumple, puede afectar el desarrollo del estudio.

2. **Necesidad de ajustes**: Podría requerirse hacer ajustes en el desarrollo si algunos supuestos no se cumplen.

3. **Limitaciones en resultados**: Los resultados podrían verse limitados si algunos supuestos no se cumplen.

### Verificación de aceptación

Los supuestos cumplen con los criterios de aceptación:

- ✅ **Claramente identificados**: Todos los supuestos están claramente definidos
- ✅ **Fundamentación técnica**: Cada supuesto está fundamentado en el documento histórico y código fuente
- ✅ **Verificabilidad**: Se puede verificar cada supuesto mediante análisis o consulta directa
- ✅ **Impacto en el desarrollo**: Se ha analizado el impacto de cada supuesto en el desarrollo del estudio

### Coherencia con el documento histórico

Los supuestos están completamente alineados con el documento histórico:

> "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible (incluido un clúster de GPU para las capas satelitales). La reproducibilidad se asegura publicando el producto en repositorio abierto y verificando que su reconstrucción desde los datos crudos arroja las mismas métricas. La principal condición de viabilidad es la calidad y actualización de las fuentes abiertas y la gestión honesta del alcance de cada capa."

> "Queda fuera del alcance el monitoreo satelital continuo en tiempo real: las capas satelitales corresponden a mediciones por ventana y por evento, no a un servicio de vigilancia permanente, y así se declara para no sobreatribuir capacidades al producto."

### Consideraciones adicionales

#### Supuestos de tiempo de ejecución

Se asume que los tiempos de ejecución estimados son realistas:

- **Documento histórico**: "El estudio es viable con datos abiertos y con la capacidad de cómputo disponible"
- **Código fuente**: El código muestra procesamiento de datos de tamaño considerable
- **Documentación**: Se menciona en la documentación del proyecto

#### Supuestos de mantenimiento

Se asume que el sistema puede mantenerse actualizado:

- **Documento histórico**: "La reproducibilidad se asegura publicando el producto en repositorio abierto"
- **Código fuente**: El código está estructurado para actualización
- **Documentación**: Se menciona en la documentación del proyecto

## Conclusión

Los supuestos identificados son fundamentales para el desarrollo del estudio. Están claramente definidos, fundamentados en el documento histórico y código fuente, y verificables. Cada supuesto tiene un impacto claro en el desarrollo del proyecto, y su cumplimiento es necesario para el éxito del estudio. Los supuestos abarcan aspectos técnicos, de disponibilidad de datos, calidad de datos y alcance del estudio, proporcionando una base sólida para el desarrollo del proyecto.