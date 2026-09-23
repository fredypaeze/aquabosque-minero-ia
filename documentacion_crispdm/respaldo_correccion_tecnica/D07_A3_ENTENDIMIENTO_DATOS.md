# D07.A3 - COMPRENSIÓN DE LOS DATOS

## Análisis de la Comprensión de los Datos

### Fuentes de Datos Principales

El sistema AquaBosque Minero IA integra cinco fuentes de datos principales, todas ellas oficiales y abiertas:

#### 1. Fuente Minera - ANM - RUCOM
- **Proveedor**: Agencia Nacional de Minería (ANM)
- **Fuente**: Base de datos RUCOM (Registro Único de Comercialización)
- **Contenido**: 
  - 12.914 registros de comercialización minera
  - Volumen de explotación
  - Regalías pagadas
- **Frecuencia de actualización**: Mensual
- **Cobertura**: Colombia entera
- **Unidad de medida**: Toneladas, millones de COP

#### 2. Fuente Territorial - DANE - DIVIPOLA
- **Proveedor**: Departamento Administrativo Nacional de Estadística (DANE)
- **Fuente**: DIVIPOLA 2025
- **Contenido**:
  - 1.122 municipios de Colombia
  - Coordenadas geográficas (centroides)
  - Códigos DIVIPOLA
- **Frecuencia de actualización**: Periódica (actualización cada 5 años)
- **Cobertura**: Todo el territorio nacional
- **Unidad de medida**: Códigos numéricos, coordenadas

#### 3. Fuente de Deforestación - Observatorio/IDEAM
- **Proveedor**: Observatorio de Cambio Climático del IDEAM
- **Fuente**: ArcGIS FeatureServer
- **Contenido**:
  - Cambios en cubierta vegetal por municipio
  - Área deforestada en hectáreas
- **Frecuencia de actualización**: Mensual
- **Cobertura**: Colombia entera
- **Unidad de medida**: Hectáreas

#### 4. Fuente Hídrica - IDEAM - DHIME
- **Proveedor**: Instituto de Hidrología, Meteorología y Estudios Ambientales (IDEAM)
- **Fuente**: DHIME (Datos Hidrometeorológicos)
- **Contenido**:
  - Índice de calidad del agua por estación
  - Parámetros de calidad (pH, turbidez, contaminantes)
- **Frecuencia de actualización**: Diaria
- **Cobertura**: Estaciones de monitoreo en todo el país
- **Unidad de medida**: Índice de calidad (0-100), parámetros específicos

#### 5. Fuente de Sensibilidad - RUNAP + PDET
- **Proveedor**: Registro Único de Áreas Protegidas (RUNAP) y Planes de Desarrollo Territorial (PDET)
- **Fuente**: Datos de áreas protegidas y valor social ambiental
- **Contenido**:
  - Áreas protegidas (parques nacionales, reservas naturales)
  - Valor ambiental y social a proteger
- **Frecuencia de actualización**: Periódica
- **Cobertura**: Colombia entera
- **Unidad de medida**: Área protegida, valor numérico de sensibilidad

### Variables de Datos

#### Variables de Entrada

| Variable | Fuente | Tipo | Unidad | Descripción |
|----------|--------|------|--------|-------------|
| Volumen_minero | ANM - RUCOM | Numérica | Toneladas | Volumen de producción minera |
| Regalias_minero | ANM - RUCOM | Numérica | Millones COP | Regalías pagadas por minería |
| Deforestacion_ha | Observatorio/IDEAM | Numérica | Hectáreas | Área deforestada |
| Calidad_agua | IDEAM - DHIME | Numérica | Índice 0-100 | Índice de calidad del agua |
| Sensibilidad_ambiental | RUNAP + PDET | Numérica | Valor 0-1 | Valor de sensibilidad ambiental |
| Municipio | DANE - DIVIPOLA | Categórica | Código DANE | Identificador único del municipio |

#### Variables de Salida

| Variable | Tipo | Unidad | Descripción |
|----------|------|--------|-------------|
| Indice_minero | Numérica | 0-1 | Índice de riesgo minero |
| Indice_deforestacion | Numérica | 0-1 | Índice de riesgo deforestación |
| Indice_hidrico | Numérica | 0-1 | Índice de riesgo hídrico |
| Indice_sensibilidad | Numérica | 0-1 | Índice de sensibilidad ambiental |
| Etiqueta_riesgo | Categórica | Bajo, Medio, Alto, Crítico | Clasificación de riesgo |
| Prediccion_modelo | Categórica | Bajo, Medio, Alto, Crítico | Predicción del modelo |

### Cobertura Temporal

#### Datos Históricos Disponibles
- **Actividad minera**: Histórico de 10+ años
- **Deforestación**: Histórico de 5+ años
- **Calidad del agua**: Histórico de 3+ años
- **Sensibilidad ambiental**: Datos estáticos (no temporal)
- **Municipios**: Datos estáticos (DIVIPOLA 2025)

#### Periodicidad de Actualización
- **Datos mensuales**: Deforestación, actividad minera
- **Datos diarios**: Calidad del agua
- **Datos estáticos**: Sensibilidad ambiental, municipios

### Calidad de los Datos

#### Calidad de las Fuentes
1. **ANM - RUCOM**: Alta calidad, datos oficialmente registrados
2. **DANE - DIVIPOLA**: Alta calidad, datos oficiales y estandarizados
3. **Observatorio/IDEAM**: Alta calidad, datos de monitoreo oficial
4. **IDEAM - DHIME**: Alta calidad, datos de monitoreo hidrometeorológico
5. **RUNAP + PDET**: Alta calidad, datos oficialmente catalogados

#### Validación de Datos
- **Consistencia**: Verificación de valores dentro de rangos lógicos
- **Compleción**: Verificación de cobertura de municipios
- **Integridad**: Verificación de duplicados y errores
- **Actualización**: Verificación de periodicidad de datos

### Estructura de Datos

#### Estructura de Directorios
```
data/
├── raw/           # Datos originales descargados
├── processed/     # Datos procesados y transformados
└── curated/       # Datos finalizados y listos para análisis
```

#### Estructura de Datos Procesados
1. **Datos de entrada**: Fuentes originales con identificadores
2. **Datos integrados**: Unificación de múltiples fuentes por municipio
3. **Datos de salida**: Índices calculados y etiquetas de riesgo

### Transformaciones de Datos

#### Transformaciones Principales
1. **Integración espacial**: Cálculo de centroides de municipios
2. **Cálculo de índices**: Normalización de variables a escala 0-1
3. **Categorización**: Asignación de etiquetas por cuantiles
4. **Agrupación**: Agrupamiento por municipio para análisis

#### Transformaciones de Variables
1. **Normalización**: Conversión a escala 0-1 para comparabilidad
2. **Categorización**: Conversión de valores continuos a categorías
3. **Aggregación**: Cálculo de totales y promedios por municipio
4. **Interpolación**: Estimación de valores faltantes

### Limpieza de Datos

#### Limpieza Realizada
1. **Eliminación de duplicados**: Verificación y eliminación de registros duplicados
2. **Manejo de valores nulos**: Identificación y tratamiento de datos faltantes
3. **Corrección de errores**: Verificación y corrección de inconsistencias
4. **Validación de rangos**: Verificación de valores dentro de rangos lógicos

#### Valores Atípicos
- **Detección**: Análisis de valores fuera de rangos esperados
- **Tratamiento**: Eliminación o corrección de valores atípicos
- **Justificación**: Documentación de decisiones de tratamiento

### Fuentes de Datos Secundarias

#### Fuentes de Apoyo
1. **Datos de sensores satelitales**: Para validación y análisis adicional
2. **Datos de investigación académica**: Para validación de modelos
3. **Datos de instituciones internacionales**: Para contexto global

### Consideraciones de Privacidad y Ética

#### Protección de Datos
- **Datos públicos**: Todas las fuentes son públicas y oficiales
- **No se identifican individuos**: Los datos son agregados a nivel municipal
- **Cumplimiento normativo**: Adecuado para uso público según normativas

#### Uso Responsable
- **No se acusa ni sanciona**: Solo se identifica riesgo potencial
- **No se determina causalidad**: Solo se observan correlaciones
- **Transparencia**: Todos los métodos y fuentes son públicos

## Próximos Pasos

1. Preparación y limpieza de datos (D08_A4)
2. Modelado del problema (D09_A5)
3. Evaluación del modelo (D10_A6)
4. Despliegue del sistema (D11_A7)

## Referencias

- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Documentación del Concurso Datos al Ecosistema 2026
- Especificaciones de las fuentes de datos oficiales