# A1 - DEFINICIÓN TEMÁTICA

## 1. Introducción y Contexto del Problema

El proyecto AquaBosque Minero IA se centra en la necesidad de identificar y clasificar municipios Colombianos en niveles de riesgo ambiental asociado a presión minera, deforestación y afectación hídrica. Este problema es fundamental para la gestión ambiental y la toma de decisiones en políticas públicas.

## 2. Problema Temático

El problema temático del proyecto AquaBosque Minero IA se centra en la necesidad de identificar y clasificar municipios Colombianos en niveles de riesgo ambiental asociado a presión minera, deforestación y afectación hídrica. Este problema es fundamental para la gestión ambiental y la toma de decisiones en políticas públicas.

### Justificación del Problema

El problema se justifica por las siguientes razones:

1. **Impacto ambiental significativo**: La minería, deforestación y cambios en la calidad hídrica tienen efectos directos en el medio ambiente y la salud humana
2. **Necesidad de priorización**: Los recursos para monitoreo ambiental son limitados, requiriendo sistemas de priorización eficientes
3. **Evidencia científica**: Existe una base sólida de datos sobre estas presiones ambientales en Colombia
4. **Aplicación práctica**: La solución tiene aplicabilidad directa en políticas públicas y gestión ambiental

## 3. Alcance del Sistema

### Componentes Principales

1. **Modelo Municipal Principal**: Clasificación de riesgo ambiental por municipio
2. **Componentes Especiales**: 
   - Sistema de alerta para incendios
   - Componente específico para Bogotá
   - Análisis de anomalías

### Ámbito Geográfico

- **Cobertura**: Municipios Colombianos
- **Escala**: Territorial (municipal)
- **Actualización**: Mensual para datos estáticos, diaria para datos dinámicos

### Ámbito Temporal

- **Datos históricos**: Disponibles desde 2010
- **Actualización continua**: Datos dinámicos actualizados diariamente
- **Horizonte de análisis**: Corto plazo (1-3 meses)

## 4. Unidad de Análisis Territorial

La unidad de análisis territorial del sistema es el municipio colombiano. Esta elección se fundamenta en la disponibilidad de datos geoespaciales oficiales y la capacidad de análisis a nivel territorial para la gestión ambiental.

## 5. Dimensiones del Análisis

### Dimensión Minera
- **Fuente**: Agencia Nacional de Minería (ANM) - Base de datos RUCOM
- **Variables**: Volumen de producción minera, regalías promedio, títulos mineros
- **Características**: Presión directa sobre el medio ambiente

### Dimensión Forestal
- **Fuente**: Observatorio del IDEAM - Datos de cambio en cubierta vegetal
- **Variables**: Área deforestada por municipio
- **Características**: Impacto sobre la biodiversidad y el equilibrio ecológico

### Dimensión Hídrica
- **Fuente**: Instituto de Hidrología, Meteorología y Estudios Ambientales (IDEAM) - DHIME
- **Variables**: Calidad del agua y estaciones hidrometeorológicas
- **Características**: Impacto sobre la disponibilidad de recursos hídricos

### Dimensión Satelital
- **Fuente**: National Aeronautics and Space Administration (NASA) - FIRMS
- **Variables**: Focos de calor activos (NRT - Near Real-Time)
- **Características**: Monitoreo de eventos ambientales en tiempo real

### Dimensión de Sensibilidad Ambiental
- **Fuente**: Datos de áreas protegidas y valor ambiental
- **Variables**: Área protegida, valor de sensibilidad ambiental
- **Características**: Zonas de mayor vulnerabilidad ecológica

## 6. Usuarios y Decisiones que Apoya

### Usuarios Principales

1. **Autoridades ambientales**: Mejor asignación de recursos para monitoreo
2. **Gobiernos locales**: Identificación de áreas de alto riesgo
3. **Organismos de investigación**: Base de datos para estudios ambientales
4. **Sociedad civil**: Mayor transparencia en gestión ambiental

### Decisiones de Negocio Apoyadas

1. **Asignación de recursos**: Ayuda a asignar recursos de monitoreo y protección ambiental
2. **Políticas públicas**: Informa la formulación de políticas ambientales
3. **Intervención preventiva**: Facilita intervenciones preventivas en áreas de alto riesgo

## 7. Carácter de Priorización Técnica del Sistema

La solución tiene como propósito principal proporcionar un sistema de priorización técnica basado en evidencia para la gestión ambiental de municipios Colombianos.

### Características Clave

1. **Técnica de priorización**: No implica causalidad ni ilegalidad
2. **Base de datos**: Utiliza fuentes oficiales y verificables
3. **Transparencia**: Los cálculos son explícitos y reproducibles
4. **Actualización**: Datos se actualizan periódicamente

## 8. Limitaciones del Enfoque

1. **No causalidad**: El sistema no prueba causalidad entre variables
2. **No predicción de eventos**: No predice eventos específicos
3. **Dependencia de datos**: Rendimiento depende de calidad de datos
4. **Generalización**: Limitaciones en la generalización a nuevas condiciones

## 9. Diferenciación entre Riesgo Construido y Eventos Observados

El sistema AquaBosque Minero IA construye un riesgo ambiental basado en indicadores cuantificables, no predice eventos específicos. Esta diferencia es fundamental:

- **Riesgo construido mediante indicadores**: Sistema de priorización basado en evidencia
- **Eventos ambientales observados**: Monitoreo directo de fenómenos específicos

El sistema no busca predecir eventos futuros, sino priorizar áreas de interés para intervención basada en indicadores ambientales.

## Referencias

- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Documentación del Concurso Datos al Ecosistema 2026
- Especificaciones de las fuentes de datos oficiales