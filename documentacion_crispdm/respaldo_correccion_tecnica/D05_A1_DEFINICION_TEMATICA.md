# D05.A1 - DEFINICIÓN TEMÁTICA

## Definición del Problema Temático

### Contexto del Problema

Colombia carece de una vista integrada que cruce **actividad minera + deforestación + calidad del agua + sensibilidad ambiental** a nivel municipal. Esta falta de visión integral dificulta la toma de decisiones estratégicas sobre la gestión de recursos naturales y el monitoreo de riesgos ambientales asociados a actividades mineras.

### Problema Específico

La necesidad de priorizar territorios donde confluyen señales de presión minera, deforestación y afectación hídrica para facilitar el monitoreo estratégico y la toma de decisiones públicas basada en evidencia.

### Objetivo del Sistema

Desarrollar un sistema explicable de IA geoespacial que integre datos abiertos oficiales para priorizar municipios con riesgo ambiental asociado a presión minera, deforestación y afectación hídrica.

### Ámbito del Problema

#### Territorial
- **Alcance**: 1.122 municipios de Colombia (DIVIPOLA 2025)
- **Ubicación**: Todo el territorio nacional
- **Granularidad**: Municipios

#### Temático
- **Presión minera**: Actividad minera real registrada por ANM
- **Deforestación**: Cambios en cubierta vegetal por municipio
- **Afectación hídrica**: Calidad del agua en estaciones de monitoreo
- **Sensibilidad ambiental**: Áreas protegidas y valor social ambiental

## Justificación del Problema

### Importancia Ambiental
- Colombia posee una de las mayores biodiversidades del mundo
- La actividad minera puede tener impactos significativos en ecosistemas delicados
- La deforestación contribuye al cambio climático y pérdida de biodiversidad
- La calidad del agua afecta la salud humana y ecosistemas acuáticos

### Importancia Social y Económica
- Los municipios son los niveles de gobierno más cercanos a la población
- La gestión ambiental eficiente es clave para el desarrollo sostenible
- La priorización permite asignar recursos de manera más eficiente
- La transparencia en la toma de decisiones fortalece la democracia

### Importancia Institucional
- El proyecto apoya a instituciones del Ministerio de Minas y Energía
- Facilita el monitoreo de riesgos ambientales en áreas de interés
- Contribuye a políticas públicas basadas en evidencia
- Cumple con principios de datos abiertos y transparencia

## Problemas de Negocio Asociados

### Problemas de Recursos
- **Distribución desigual de recursos**: Necesidad de priorizar zonas con mayor riesgo
- **Limitaciones presupuestarias**: Asignación eficiente de fondos para monitoreo
- **Capacidades humanas**: Necesidad de herramientas que amplíen capacidades de análisis

### Problemas de Gestión
- **Monitoreo proactivo**: Detección temprana de riesgos ambientales
- **Toma de decisiones**: Soporte para políticas basadas en evidencia
- **Coordinación interinstitucional**: Compartir información entre entidades

### Problemas de Información
- **Fragmentación de datos**: Información dispersa en múltiples fuentes
- **Falta de visión integral**: Imposibilidad de cruzar múltiples variables
- **Baja disponibilidad de información**: Dificultades para acceder a datos relevantes

## Alcance del Sistema

### Alcance Funcional
1. **Integración de datos**: Unificación de fuentes oficiales y abiertas
2. **Cálculo de índices**: Desarrollo de indicadores de riesgo por municipio
3. **Priorización**: Asignación de niveles de riesgo (Bajo, Medio, Alto, Crítico)
4. **Explicabilidad**: Interpretación de resultados mediante SHAP
5. **Visualización**: Dashboard interactivo para análisis

### Alcance Geográfico
- **Territorio**: Todo el territorio colombiano (1.122 municipios)
- **Granularidad**: Municipios
- **Actualización**: Datos actualizados con frecuencia

### Alcance Temporal
- **Periodicidad**: Actualización de datos y modelos según disponibilidad
- **Cobertura**: Historial de datos disponible para análisis retroactivo
- **Proyección**: Capacidad de análisis de tendencias y escenarios futuros

## Variables Clave del Problema

### Variables de Entrada
1. **Actividad minera** (ANM - RUCOM): Volumen de explotación, regalías, comercialización
2. **Deforestación** (Observatorio/IDEAM): Cambios en cubierta vegetal por municipio
3. **Calidad del agua** (IDEAM - DHIME): Índice de calidad del agua por estación
4. **Sensibilidad ambiental** (RUNAP + PDET): Áreas protegidas y valor social ambiental

### Variables de Salida
1. **Índices de riesgo** (Minero, Deforestación, Hídrico, Sensibilidad): Escala 0-1
2. **Etiqueta de riesgo** (Bajo, Medio, Alto, Crítico): Clasificación por cuantiles
3. **Predicciones del modelo**: Clases de riesgo con probabilidades
4. **Importancia SHAP**: Características más relevantes para la predicción

## Hipótesis del Problema

### Hipótesis Fundamentales
1. **Hipótesis de relación**: Existe una relación significativa entre presión minera, deforestación y afectación hídrica en términos de riesgo ambiental
2. **Hipótesis de priorización**: Se pueden identificar zonas prioritarias basadas en la combinación de estas variables
3. **Hipótesis de explicabilidad**: La técnica SHAP permite entender la contribución de cada variable a las predicciones

### Hipótesis de Solución
1. **Hipótesis de integración**: La integración de múltiples fuentes de datos mejora la capacidad de detección de riesgos
2. **Hipótesis de modelado**: Un modelo de machine learning puede aprender patrones complejos en los datos ambientales
3. **Hipótesis de visualización**: Una interfaz interactiva facilita la comprensión y uso de los resultados

## Supuestos del Problema

### Supuestos de Datos
1. **Datos oficiales**: Las fuentes de datos oficiales son representativas y confiables
2. **Cobertura completa**: Las fuentes cubren el territorio nacional de manera uniforme
3. **Consistencia temporal**: Los datos mantienen consistencia en su definición y procedimiento de recolección

### Supuestos del Modelo
1. **Patrones estables**: Los patrones observados en los datos se mantienen en el futuro
2. **Independencia de variables**: Las variables contribuyen de manera independiente al riesgo ambiental
3. **Representatividad**: Los datos representan adecuadamente la realidad del riesgo ambiental

### Supuestos de Aplicación
1. **Uso responsable**: El sistema será utilizado de manera responsable y ética
2. **Acceso a información**: Los usuarios tendrán acceso a la información necesaria para interpretar los resultados
3. **Actualización de modelos**: El sistema podrá ser actualizado con nuevos datos y mejoras

## Próximos Pasos

1. Desarrollo de la comprensión del negocio (D06_A2)
2. Análisis detallado de los datos y sus fuentes (D07_A3)
3. Preparación y limpieza de datos (D08_A4)
4. Modelado del problema (D09_A5)
5. Evaluación del modelo (D10_A6)
6. Despliegue del sistema (D11_A7)

## Referencias

- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Documentación del Concurso Datos al Ecosistema 2026