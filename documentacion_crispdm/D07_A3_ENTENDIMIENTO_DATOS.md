# D07.A3 - COMPRENSIÓN DE LOS DATOS

## Análisis de la Comprensión de los Datos

### Fuentes de Datos Principales

El sistema AquaBosque Minero IA integra cinco fuentes de datos principales, todas ellas oficiales y abiertas:

#### 1. Fuente Minera - ANM - RUCOM
- **Proveedor**: Agencia Nacional de Minería (ANM)
- **Fuente**: Base de datos RUCOM
- **Datos**: Información sobre títulos mineros, volumen de producción y regalías
- **Frecuencia de actualización**: Mensual
- **Cobertura**: Todos los municipios con actividad minera

#### 2. Fuente Territorial - DANE - DIVIPOLA
- **Proveedor**: Departamento Administrativo Nacional de Estadística (DANE)
- **Fuente**: DIVIPOLA 2025
- **Datos**: Coordenadas geográficas y códigos DANE de municipios
- **Frecuencia de actualización**: Anual
- **Cobertura**: Todos los municipios Colombianos

#### 3. Fuente de Deforestación - Observatorio/IDEAM
- **Proveedor**: Observatorio del IDEAM
- **Fuente**: Datos de cambio en cubierta vegetal
- **Datos**: Área deforestada por municipio
- **Frecuencia de actualización**: Mensual
- **Cobertura**: Municipios con datos de deforestación disponibles

#### 4. Fuente Hídrica - IDEAM - DHIME
- **Proveedor**: Instituto de Hidrología, Meteorología y Estudios Ambientales (IDEAM)
- **Fuente**: DHIME
- **Datos**: Calidad del agua y estaciones hidrometeorológicas
- **Frecuencia de actualización**: Mensual
- **Cobertura**: Municipios con estaciones hidrometeorológicas

#### 5. Fuente Satelital - NASA FIRMS
- **Proveedor**: National Aeronautics and Space Administration (NASA)
- **Fuente**: FIRMS (Fire Information for Resource Management System)
- **Datos**: Focos de calor activos (NRT - Near Real-Time)
- **Frecuencia de actualización**: Diaria
- **Cobertura**: Colombia continental y regional

### Variables de Datos

#### Variables Numéricas Continuas
1. **Índice Minero**: Normalización a escala 0-1 usando min-max
2. **Índice de Deforestación**: Normalización a escala 0-1
3. **Índice de Fuego**: Escala 0-1 basada en FRP (Fire Radiative Power)
4. **Índice Hídrico**: Conversión a escala 0-1 (inversa, cuanto menor el valor, mayor el riesgo)
5. **Índice de Sensibilidad Ambiental**: Escala 0-1

#### Variables Categóricas
1. **Etiquetas de Riesgo**: Bajo (0), Medio (1), Alto (2), Crítico (3)
2. **Áreas Protegidas**: Identificación de áreas protegidas
3. **Valor Ambiental**: Categorías de sensibilidad ambiental

### Estructura de Datos

#### Dataset Maestro
```
data/curated/dataset_maestro.csv
┌─────────────────┬────────────────────┬─────────────────────┬────────────────────┬────────────────────┬────────────────────┐
│ municipio       │ volumen_minero     │ regalias_promedio   │ deforestacion_ha   │ calidad_agua       │ sensibilidad_ambiental│
├─────────────────┼────────────────────┼─────────────────────┼────────────────────┼────────────────────┼────────────────────┤
│ 1100101         │ 15000              │ 2500                │ 1200               │ 75                 │ 0.85               │
│ 1100102         │ 8000               │ 1200                │ 800                │ 68                 │ 0.72               │
│ ...             │ ...                │ ...                 │ ...                │ ...                │ ...                │
└─────────────────┴────────────────────┴─────────────────────┴────────────────────┴────────────────────┴────────────────────┘
```

### Manejo de Datos Incompletos

#### Identificación de Valores Nulos
1. **Municipios sin datos**: Se identifican mediante verificación de cobertura
2. **Variables faltantes**: Se registran y documentan
3. **Cobertura temporal**: Se verifica periodicidad de datos

#### Estrategias de Imputación
1. **Imputación por promedio**: Para variables continuas con datos parciales
2. **Imputación por mediana**: Para variables con distribuciones sesgadas
3. **Imputación por valor constante**: Para variables categóricas
4. **Eliminación de registros**: Cuando los datos faltantes son excesivos

#### Validación de Consistencia
1. **Integridad de datos**: Verificación de cobertura completa de municipios
2. **Consistencia semántica**: Validación de valores dentro de rangos lógicos
3. **Validación de fuentes**: Comparación con fuentes de datos alternativas

## Referencias
- Metodología CRISP-ML: Cross Industry Standard Process for Machine Learning
- Metodología de Estudios Estratégicos - Tuxilo
- Documentación técnica del proyecto AquaBosque Minero IA
- Documentación del Concurso Datos al Ecosistema 2026
- Especificaciones de las fuentes de datos oficiales