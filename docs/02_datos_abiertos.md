# 02 — Inventario de datos abiertos (Fase 1)

Este documento resume el catálogo estructurado en [`config/data_sources.yaml`](../config/data_sources.yaml).
Es un inventario de **fuentes candidatas**: ninguna ha sido descargada todavía.

Todas las fuentes fueron verificadas mediante búsqueda web el 2026-07-11 para confirmar que
las entidades y portales existen y son de acceso público. Los campos marcados como
**"por validar"** en el catálogo no fueron inventados: representan información que no pudo
confirmarse con certeza desde la búsqueda y requiere revisión manual directa en el portal
antes de construir cualquier pipeline de descarga.

## Cómo leer el catálogo

Cada fuente en `config/data_sources.yaml` tiene los siguientes campos: `nombre`,
`entidad_responsable`, `url`, `portal_origen`, `tipo_dato`, `cobertura_geografica`,
`cobertura_temporal`, `frecuencia_actualizacion`, `campos_clave_esperados`,
`llave_integracion_esperada`, `uso_en_modelo`, `prioridad` (alta/media/baja) y
`estado` (candidata/pendiente_de_validacion/aprobada/descartada).

## 1. Fuentes registradas por categoría

### Minería (5 fuentes)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| Catastro Minero Colombiano (CMC) | ANM | alta | candidata |
| ANM Títulos Mineros - Anotaciones RMN | ANM | media | candidata |
| Datos Abiertos ANLA (licencias ambientales, minería) | ANLA | media | candidata |
| SIMCO | UPME | media | pendiente_de_validacion |
| Portal de Datos Abiertos SGC | Servicio Geológico Colombiano | baja | candidata |

### Deforestación / bosque (3 fuentes)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| SMByC (Sistema de Monitoreo de Bosques y Carbono) | IDEAM | alta | candidata |
| Capas geográficas IDEAM (ecosistemas/bosque/agua) | IDEAM | media | candidata |
| Global Forest Watch - Colombia | WRI / GFW | media | candidata |

### Calidad hídrica (2 fuentes)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| Redes de Monitoreo de Calidad del Agua | IDEAM | alta | pendiente_de_validacion |
| REDCAM (aguas marinas y costeras) | IDEAM | baja | candidata |

### Territorio / DIVIPOLA (3 fuentes)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| DIVIPOLA - Códigos de municipios | DANE | alta | candidata |
| DIVIPOLA - Códigos geolocalizados | DANE | media | candidata |
| Marco Geoestadístico Nacional (límites municipales) | DANE | alta | pendiente_de_validacion |

### Cuencas / zonificación hidrográfica (1 fuente)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| Zonificación Hidrográfica de Colombia | IDEAM | alta | pendiente_de_validacion |

### Áreas protegidas / RUNAP (1 fuente)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| RUNAP - Registro Único Nacional de Áreas Protegidas | Parques Nacionales Naturales | alta | candidata |

### Sensibilidad social o territorial (2 fuentes)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| Resguardos Indígenas Formalizados | Agencia Nacional de Tierras | media | candidata |
| Mapa Digital de Tierras de Comunidades Negras | MADS / ICDE | media | pendiente_de_validacion |

### General / meta-portal (1 fuente)
| Fuente | Entidad | Prioridad | Estado |
|---|---|---|---|
| Datos Abiertos Colombia (datos.gov.co) | MinTIC / DNP (agregador) | media | candidata |

**Total: 18 fuentes candidatas en 7 dimensiones temáticas + 1 portal general.**

## 2. Archivos creados o modificados

- **Creado:** `config/data_sources.yaml` — catálogo estructurado de las 17 fuentes.
- **Creado:** `docs/02_datos_abiertos.md` — este documento.

No se modificó ningún otro archivo. No se descargó ningún dato.

## 3. Fuentes recomendadas para el MVP

Criterio: prioridad `alta`, con llave de integración territorial clara (código DANE o
geometría estable), y necesarias para responder la pregunta mínima del proyecto
(relación espacial entre minería, bosque, agua y áreas protegidas).

1. **DIVIPOLA - Códigos de municipios** (DANE) — llave maestra de integración territorial.
2. **Marco Geoestadístico Nacional** (DANE) — polígonos municipales oficiales.
3. **Catastro Minero Colombiano** (ANM) — ubicación y atributos de títulos mineros.
4. **SMByC** (IDEAM) — pérdida de cobertura boscosa oficial de Colombia.
5. **Zonificación Hidrográfica de Colombia** (IDEAM) — unidad de análisis por cuenca/subzona.
6. **Redes de Monitoreo de Calidad del Agua** (IDEAM) — variable hídrica central.
7. **RUNAP** (Parques Nacionales Naturales) — restricciones/traslapes con áreas protegidas.

Estas 7 fuentes cubren las 4 dimensiones núcleo del proyecto (territorio, minería, bosque,
agua) más el filtro legal de áreas protegidas. Tres de ellas (SIMCO, Marco Geoestadístico
Nacional, Zonificación Hidrográfica, Redes de Calidad del Agua) están en estado
`pendiente_de_validacion`: antes de construir el script de descarga real hace falta
confirmar manualmente el formato exacto de descarga y la vigencia de cada capa.

## 4. Fuentes opcionales para fase avanzada

- **ANM Títulos Mineros - Anotaciones RMN** (histórico tabular, complemento al catastro).
- **Datos Abiertos ANLA** (licenciamiento ambiental del sector minero, contexto regulatorio).
- **SIMCO** (contexto estadístico/económico del sector minero).
- **Portal de Datos Abiertos SGC** (contexto geológico de fondo).
- **Capas geográficas IDEAM adicionales** (ecosistemas más allá de bosque).
- **Global Forest Watch** (contraste con fuente satelital internacional, útil para
  validación cruzada, pero con metodología distinta a IDEAM).
- **REDCAM** (solo si el área de estudio final incluye zona costera).
- **DIVIPOLA geolocalizados** (atajo de coordenadas de cabecera municipal, no reemplaza el polígono).
- **Resguardos Indígenas Formalizados** y **Mapa Digital de Tierras de Comunidades Negras**
  (capas de sensibilidad territorial, relevantes para una fase de análisis más matizada,
  con tratamiento ético cuidadoso — ver riesgos abajo).
- **Datos Abiertos Colombia (datos.gov.co)** como API/respaldo general, no como fuente primaria.

## 5. Riesgos o vacíos de datos encontrados

- **Formato de descarga no confirmado en varias fuentes.** SIMCO, SMByC, Redes de Calidad
  del Agua y el Mapa Digital de Tierras de Comunidades Negras no dejaron claro en la
  búsqueda si exponen API/descarga estructurada directa o requieren navegación manual del
  portal. Esto puede implicar trabajo adicional de scraping o solicitud directa a la entidad.
- **Múltiples versiones de la misma capa.** La Zonificación Hidrográfica tiene al menos dos
  versiones documentadas (IDEAM 2013 y actualizaciones POMCA de MinAmbiente a escala
  1:100.000). Hay que fijar una sola versión de referencia antes de integrar.
- **Enlaces de descarga técnica potencialmente inestables.** El enlace directo de RUNAP
  (`storage.googleapis.com/pnn_geodatabase/...`) es un recurso técnico que puede cambiar;
  conviene siempre partir del portal oficial.
- **Cobertura desigual de estaciones de calidad de agua.** No se confirmó la densidad de
  estaciones IDEAM por región; puede haber zonas del área de estudio sin monitoreo directo.
- **Minería informal/ilegal fuera de alcance.** El catastro minero de la ANM solo cubre
  títulos formales. Conforme a las reglas del proyecto, este catálogo **no** incluye ni
  busca fuentes para inferir minería ilegal, y ningún análisis futuro debe afirmar
  causalidad ambiental ni actividad ilegal a partir de estos datos.
- **Datos de sensibilidad social/territorial requieren tratamiento ético reforzado.**
  Cualquier cruce espacial con resguardos indígenas o territorios de comunidades negras debe
  presentarse estrictamente como coexistencia espacial (traslape de polígonos), nunca como
  juicio, señalamiento o atribución de causalidad hacia esas comunidades.
- **No se confirmó autenticación/costos.** Todas las fuentes listadas parecen de acceso
  público sin costo según la búsqueda, pero esto debe confirmarse en la Fase 1.5/2 antes de
  automatizar cualquier descarga (regla del proyecto: no usar servicios pagos).

## 6. Preguntas a validar antes de pasar a descarga

1. ¿Cuál es el **área de estudio** exacta del proyecto (departamento, municipio, cuenca
   específica)? Esto determina si REDCAM y otras capas costeras aplican, y limita el
   volumen de datos a descargar.
2. ¿Qué **rango temporal** interesa priorizar (ej. últimos 5 años, últimos 10 años)? Afecta
   qué versiones de SMByC/GFW y qué cortes de catastro minero se deben usar.
3. Para las fuentes en estado `pendiente_de_validacion` (SIMCO, Marco Geoestadístico
   Nacional, Zonificación Hidrográfica, Redes de Calidad del Agua, Mapa de Tierras de
   Comunidades Negras): ¿se autoriza dedicar tiempo en la siguiente fase a probar
   manualmente el acceso y formato exacto de descarga antes de escribir el script?
4. ¿Se debe incluir la capa de **resguardos indígenas / comunidades negras** en el MVP, o se
   pospone a una fase posterior dado el tratamiento ético/legal adicional que requiere?
5. ¿Existe una **cuenta o API token** ya disponible para datos.gov.co (Socrata) o para GFW
   Data API, o hay que gestionarlos como parte de la Fase 1.5?
6. ¿El proyecto prioriza la fuente **oficial colombiana** (IDEAM/SMByC) o también quiere
   contrastar con **Global Forest Watch** desde el MVP, sabiendo que usan metodologías
   distintas y las cifras no son directamente comparables?
7. ¿Qué **licencia de uso** exige cada entidad (ANM, IDEAM, DANE, PNN, ANT) para
   republicar o transformar los datos en reportes o dashboards del proyecto?

## Fuentes consultadas para este inventario

- ANM — Datos Abiertos: https://www.anm.gov.co/Datos_Abiertos_ANM
- ANM — Catastro minero (WFS): https://geo.anm.gov.co/webgis/services/ANM/ServiciosANM/MapServer/WFSServer
- Datos Abiertos Colombia — ANM Títulos Mineros Anotaciones RMN: https://www.datos.gov.co/Minas-y-Energ-a/ANM-T-tulos-Mineros-Anotaciones-RMN/si2v-pbq5
- SIMCO (UPME): https://www1.upme.gov.co/simco/Paginas/home.aspx
- SGC — Portal de Datos Abiertos: https://datos.sgc.gov.co/
- IDEAM — SMByC: http://www.ideam.gov.co/en/web/siac/smbyc
- IDEAM — Capas geo: http://www.ideam.gov.co/capas-geo
- IDEAM — Redes de monitoreo de calidad de agua: http://www.ideam.gov.co/en/web/agua/redes-monitoreo-calidad-agua
- IDEAM — Agua: https://www.ideam.gov.co/agua
- IDEAM — Zonificación hidrográfica: http://www.ideam.gov.co/en/web/agua/zonificacion-hidrografica
- Datos Abiertos Colombia — Zonificación Hidrográfica: https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Zonificaci-n-Hidrogr-fica-Colombia/5kjg-nuda
- Geoportal DANE — Descarga DIVIPOLA: https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/descarga-divipola/
- Datos Abiertos Colombia — DIVIPOLA Códigos municipios: https://www.datos.gov.co/Mapas-Nacionales/DIVIPOLA-C-digos-municipios/gdxc-w37w
- Datos Abiertos Colombia — DIVIPOLA Códigos municipios geolocalizados: https://www.datos.gov.co/Mapas-Nacionales/DIVIPOLA-C-digos-municipios-geolocalizados/vafm-j2df
- RUNAP en cifras: https://runap.parquesnacionales.gov.co/cifras
- MADS — Portal de Datos Abiertos (RUNAP): https://siac-datosabiertos-mads.hub.arcgis.com/
- Agencia Nacional de Tierras — Portal de Datos Abiertos: https://data-agenciadetierras.opendata.arcgis.com/
- Datos Abiertos Colombia — Resguardo Indígena Formalizado: https://www.datos.gov.co/dataset/Resguardo-Indigena-Formalizado/f6du-dwd8
- ICDE — Mapa Digital de Tierras de Comunidades Negras (metadatos): https://metadatos.icde.gov.co/geonetwork/srv/api/records/fe0ca929-482b-41df-997a-a080b83030b9
- Global Forest Watch: https://www.globalforestwatch.org/map/country/COL/
- Global Forest Watch — Data API: https://data-api.globalforestwatch.org/
- Global Forest Watch — Portal de datos: https://data.globalforestwatch.org/
- ANLA — Datos Abiertos: https://datosabiertos-anla.hub.arcgis.com/
- Datos Abiertos Colombia (portal general): https://www.datos.gov.co/
