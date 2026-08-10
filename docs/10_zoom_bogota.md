# Zoom Bogotá para AquaBosque

## Objetivo

Extender AquaBosque con un módulo territorial específico para Bogotá que complemente el enfoque nacional municipal. En Bogotá el valor no está en "minería municipal", sino en un índice de presión eco-territorial que combine riesgo de incendio forestal, presión hídrica, susceptibilidad a remoción en masa y señales operativas de corto plazo.

## Unidad de análisis recomendada

- MVP: `localidad`
- Fase 2: `UPZ`
- Fase 3: grilla fina o unidad ecológica en borde urbano-rural

La recomendación para arrancar es `localidad`, porque simplifica el cruce de fuentes, la comunicación ejecutiva y la visualización.

## Propuesta de producto

### Nombre sugerido

`Zoom Bogotá · presión eco-territorial`

### Ejes analíticos

1. `Cerros y fuego`
   - Riesgo de incendio forestal
   - Interfaz urbano-rural
   - Cobertura vegetal susceptible
   - Estacionalidad seca

2. `Agua y anegamiento`
   - Cercanía a ríos, quebradas y humedales
   - Puntos críticos de inundación
   - Condición hidrometeorológica reciente

3. `Ladera y remoción`
   - Pendiente / ladera
   - Susceptibilidad a remoción en masa
   - Puntos críticos o eventos recurrentes

4. `Señal operativa`
   - Lluvia reciente
   - Radar / estaciones
   - Reportes diarios y boletines del SAB

## Variables sugeridas

### 1. Variables estructurales

Estas cambian lento y sirven para un score base.

| Grupo | Variable candidata | Tipo |
|---|---|---|
| Incendio forestal | zonificación de amenaza/susceptibilidad | score |
| Incendio forestal | proximidad a Cerros Orientales | distancia o dummy |
| Incendio forestal | cobertura vegetal o proporción de suelo de borde | porcentaje |
| Hidrología | proximidad a ríos Bogotá, Fucha, Tunjuelo, Salitre | distancia |
| Hidrología | proximidad/intersección con humedales y rondas | porcentaje |
| Inundación | puntos críticos históricos por localidad/UPZ | conteo |
| Remoción | susceptibilidad a movimientos en masa | score |
| Territorio | proporción de suelo urbano-rural de transición | porcentaje |
| Clima futuro | estrés climático esperado | score |

### 2. Variables dinámicas

Estas cambian rápido y sirven para priorización operativa.

| Grupo | Variable candidata | Ventana |
|---|---|---|
| Lluvia | precipitación acumulada | 24h / 72h / 7d |
| Lluvia | intensidad máxima reciente | 24h |
| Radar | señal de precipitación o tormenta | nowcast |
| SAB | alertas o reportes operativos | diario |
| Fuego | eventos/incidentes reportados | diario o semanal |
| Hidrología | condición o nivel en puntos de monitoreo si aplica | diario |

## Fuentes oficiales candidatas

### SIRE / IDIGER / SAB Bogotá

- Portal principal: `https://www.sire.gov.co/web/sab`
- Reportes y boletines: `https://www.sire.gov.co/web/sab/reportes-boletines`
- Biblioteca digital SIRE/IDIGER: repositorio documental y estudios técnicos

### Capas o documentos prioritarios para vetting

1. `Zonificación de riesgo de incendio forestal en Bogotá / Cerros Orientales`
   - Uso: score estructural de fuego en borde urbano-rural

2. `Puntos críticos por inundación`
   - Uso: recurrencia operativa y priorización territorial

3. `Puntos críticos por remoción en masa`
   - Uso: score de ladera y sensibilidad

4. `Información hidrológica e hidrometeorológica del SAB`
   - Uso: capa dinámica de lluvia y condición hídrica

5. `Escenarios de cambio climático Bogotá 2021-2100`
   - Uso: capa estructural de presión futura

6. `Cartografía de cerros, quebradas, humedales y rondas`
   - Uso: exposición eco-hidrológica

## Cómo meterlo en la app

### Opción A: nueva página dedicada

Crear una página nueva tipo:

- `app/pages/10_🏙️_Zoom_Bogotá.py`

Contenido mínimo:

1. selector de escala: `Localidad` / `UPZ`
2. mapa coroplético de Bogotá
3. ranking de territorios más expuestos
4. tablero por eje: fuego, agua, ladera, señal operativa
5. ficha territorial de la unidad seleccionada

Esta es la mejor opción para una demo clara.

### Opción B: integrar como vista dentro de mapa actual

Agregar una vista Bogotá dentro de [01_🗺️_Mapa_de_riesgo.py](/home/tuxilo/aquabosque-minero-ia/app/pages/01_🗺️_Mapa_de_riesgo.py).

No la recomiendo para el MVP, porque mezcla dos lógicas:

- nacional por municipio
- Bogotá por localidad/UPZ

### Opción C: acoplarla al monitoreo satelital

Extender [07_🛰️_Monitoreo_satelital.py](/home/tuxilo/aquabosque-minero-ia/app/pages/07_🛰️_Monitoreo_satelital.py) con una pestaña Bogotá para lluvia/fuego/eventos.

Sí suma, pero mejor como segunda fase después de la página dedicada.

## Modelo analítico propuesto

### Índice base

`indice_bogota_base`

Combinación ponderada de:

- incendio estructural
- exposición hídrica
- susceptibilidad de ladera
- presión territorial de borde

### Índice dinámico

`indice_bogota_dinamico`

Combinación de:

- lluvia reciente
- radar / tormenta
- reportes/boletines operativos
- incidentes recientes

### Índice final

`indice_presion_ecoterritorial_bogota`

Fórmula sugerida para MVP:

- `0.65 * indice_bogota_base + 0.35 * indice_bogota_dinamico`

La ponderación exacta debe calibrarse cuando se validen las fuentes.

## Estructura de datos sugerida

### Archivo maestro

- `data/processed/bogota_zoom.csv`

Columnas sugeridas:

- `unidad`
- `tipo_unidad`
- `codigo`
- `score_fuego_estructural`
- `score_agua`
- `score_remocion`
- `score_borde`
- `score_lluvia_24h`
- `score_lluvia_72h`
- `score_operativo`
- `indice_bogota_base`
- `indice_bogota_dinamico`
- `indice_presion_ecoterritorial_bogota`
- `nivel`

### Geometría

- `data/processed/bogota_localidades.geojson`
- luego `data/processed/bogota_upz.geojson`

## Roadmap recomendado

### Fase 1. Descubrimiento y vetting

- confirmar qué datasets/capas de SIRE tienen acceso estable
- verificar granularidad: localidad, UPZ o punto
- inventariar campos, fecha, cobertura y formato

### Fase 2. MVP Bogotá

- consolidar localidades
- construir `bogota_zoom.csv`
- crear página `Zoom Bogotá`
- mostrar score total y subíndices

### Fase 3. Señal operativa

- incorporar lluvia reciente y boletines/reportes
- habilitar capa de "hoy / últimos 3 días / última semana"

### Fase 4. UPZ y ficha avanzada

- bajar a UPZ
- enriquecer fichas con explicación por drivers

## Priorización territorial inicial

Para una primera iteración, vale la pena arrancar por territorios donde la señal sea más fuerte:

- `Usme`
- `Ciudad Bolívar`
- `San Cristóbal`
- `Santa Fe`
- `Usaquén rural / borde norte`
- corredores asociados a `Cerros Orientales`, `Tunjuelo`, `Fucha`, `río Bogotá` y humedales

## Encaje narrativo con AquaBosque

Esto no debe venderse como un módulo de minería para Bogotá. Debe presentarse como:

`capacidad de adaptación territorial del motor AquaBosque`

Mensaje sugerido:

- a nivel nacional prioriza municipios por presión ambiental
- en Bogotá se adapta a escala intraurbana con foco eco-hidrológico y de borde
- el valor está en combinar capas estructurales y señales operativas recientes

## Siguiente paso concreto

1. armar inventario verificable de capas/datasets SIRE-IDIGER
2. definir unidad del MVP: localidad
3. construir primer dataset `bogota_zoom.csv`
4. montar nueva página Streamlit para demo
