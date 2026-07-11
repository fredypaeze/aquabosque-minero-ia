# 03 — Validación técnica de fuentes MVP (Fase 1.5)

Validación manual y técnica de las 7 fuentes MVP priorizadas en la Fase 1, mediante
pruebas livianas: peticiones `HEAD`, consultas de metadatos/capacidades (`GetCapabilities`,
`?f=json`, metadata Socrata) y primeras filas de API. **No se descargó ningún archivo
completo ni pesado.** Todas las pruebas se ejecutaron el 2026-07-11.

El detalle campo por campo de cada fuente está en `config/data_sources.yaml`, en los
campos nuevos `url_descarga_directa`, `formato_validado`, `llave_integracion_validada`,
`riesgo_tecnico` y `notas_validacion`.

## 1. Tabla de fuentes MVP validadas

| # | Fuente | Formato confirmado | Auth | Tamaño aprox. | Llave de integración validada | Riesgo técnico | Estado |
|---|---|---|---|---|---|---|---|
| 1 | DIVIPOLA - Municipios (DANE) | XLSX directo (293 KB) + API Socrata JSON | No | 299.758 bytes (XLSX) | `cod_dpto` + `cod_mpio` | **Bajo** | **Aprobada** |
| 2 | Marco Geoestadístico Nacional / DIVIPOLA cache (DANE) | ArcGIS REST Feature Layer (polígonos) | No | 1.122 features | `COD_MPIO` + `COD_DPTO` | **Medio** | Pendiente de validación |
| 3 | Catastro Minero Colombiano (ANM) | WFS 2.0.0 (GML, exportable) | No | ~6.294 features (Titulo_Vigente) | `CODIGO_EXPEDIENTE` + geometría (sin código DANE directo) | **Medio** | Pendiente de validación |
| 4 | ANM Títulos Mineros - Anotaciones RMN | API Socrata JSON/CSV | No | No confirmado (tabular, paginable) | `codigo_expediente` (cruza con #3) | **Bajo** | **Aprobada** |
| 5 | SMByC (IDEAM) | No confirmado técnicamente | Desconocido | Desconocido | No confirmada | **Alto** | Pendiente de validación |
| 6 | Calidad hídrica — Data Histórica de Calidad de Agua (IDEAM) | API Socrata JSON/CSV | No | 134.261 filas | `szh_c_digo_rea_zona_subzona` + coordenadas | **Bajo** | **Aprobada** |
| 7 | RUNAP (Parques Nacionales) | ZIP (geodatabase/shapefile) | No | 69,4 MB (66,2 MB) | No confirmada (requiere abrir el ZIP) | **Medio** | Pendiente de validación |

## 2. Fuentes aprobadas para descarga (MVP, riesgo bajo)

1. **DIVIPOLA - Códigos de municipios (DANE)** — XLSX directo de 293 KB o API Socrata.
   Es la llave maestra de integración territorial del proyecto.
2. **ANM Títulos Mineros - Anotaciones RMN** — API Socrata, cruza directo con el catastro
   minero por `codigo_expediente`.
3. **Data Histórica de Calidad de Agua (IDEAM, dataset `62gv-3857`)** — API Socrata con
   134.261 filas, coordenadas y código de subzona hidrográfica. Esta fuente reemplaza en
   la práctica a la entrada genérica "Redes de Monitoreo de Calidad del Agua" del catálogo
   de Fase 1: es un dataset real, estructurado y atribuido explícitamente a IDEAM.

Estas tres son de bajo riesgo técnico, sin autenticación, con formato estructurado
confirmado y tamaño manejable (nada pesado). Pueden pasar a la Fase 2 (descarga real)
sin más validación técnica previa.

## 3. Fuentes que siguen pendientes de validación

4. **Marco Geoestadístico Nacional (DANE)** — El portal oficial (`geoportal.dane.gov.co`)
   es una aplicación de una sola página (SPA) que no expone enlaces de descarga en HTML
   plano; no fue posible confirmar por HTTP simple cuál es el paquete oficial "MGN 2023"
   completo. Sí se encontró y validó un servicio ArcGIS REST funcional
   (`Cache_DivipolaEntidadesTerritorialesCP/MapServer/9`, capa "Municipios", 1.122
   polígonos, campos `COD_DPTO`/`COD_MPIO`/`NOM_DPTO`/`NOM_MPIO`) que es suficiente para el
   MVP, pero es una capa "cache" simplificada, no necesariamente la cartografía censal de
   mayor precisión. **Recomendación:** usar el servicio ArcGIS REST validado para el MVP,
   y dejar pendiente confirmar si se necesita la versión cartográfica completa del MGN en
   una fase posterior.

5. **Catastro Minero Colombiano (ANM)** — El servicio WFS funciona técnicamente sin
   problemas (WFS 2.0.0 estándar, ~6.294 títulos vigentes, 15 capas disponibles). El riesgo
   no es de acceso sino de **vigencia**: el `Abstract` del servicio indica "actualizado el
   22/03/2023", es decir, con más de 3 años de antigüedad respecto a hoy. Además,
   `DEPARTAMENTOS` y `MUNICIPIOS` vienen como texto libre, no como código DANE, por lo que
   el cruce con DIVIPOLA requiere normalización de nombres o unión espacial (spatial join)
   contra los polígonos municipales, no un join directo por código.
   **Recomendación:** confirmar con la ANM (o en su portal de datos abiertos) si existe una
   versión más reciente del catastro antes de aprobar para el MVP.

7. **RUNAP (Parques Nacionales)** — El enlace de descarga directa respondió correctamente
   (HTTP 200, `Content-Type: application/zip`, última modificación 2026-07-02, es decir,
   mantenimiento activo). El **tamaño es de 66,2 MB**, lo que lo clasifica como archivo
   pesado según las reglas del proyecto: su descarga real en la Fase 2 requiere aviso
   previo explícito. Tampoco se confirmaron los campos exactos ni la licencia de uso sin
   abrir el ZIP. **Recomendación:** aprobar la fuente en principio (el endpoint es estable
   y funcional), pero avisar antes de la descarga real por el peso del archivo, y validar
   licencia/campos al momento de abrirlo.

## 4. Fuentes descartadas

Ninguna de las 7 fuentes MVP fue descartada en esta fase. Ninguna presentó un bloqueo
definitivo (autenticación de pago, servicio inexistente sin alternativa, o acceso
restringido) — todas tienen al menos una vía de acceso técnico válida o una vía alternativa
identificada.

La única entrada que se dejó como referencia "hueca" fue `ideam_redes_calidad_agua` del
catálogo original de Fase 1: no se descartó, pero se documentó que la fuente real y
validada para cubrir esa necesidad es la nueva entrada `ideam_calidad_agua_historica`.

## 5. Campos clave confirmados (no inventados, verificados con respuesta real de API)

- **DIVIPOLA municipios:** `cod_dpto`, `dpto`, `cod_mpio`, `nom_mpio`, `tipo_municipio`,
  `longitud`, `latitud`.
- **MGN / capa Municipios (ArcGIS REST):** `OBJECTID`, `Shape`, `COD_DPTO`, `NOM_DPTO`,
  `COD_MPIO`, `NOM_MPIO`, `MPIO_CORRDEPTAL`.
- **Catastro Minero — capa Titulo_Vigente (WFS):** `CODIGO_EXPEDIENTE`, `AREA_HA`,
  `FECHA_DE_INSCRIPCION`, `ESTADO`, `MODALIDAD`, `ETAPA`, `MINERALES`,
  `NOMBRE_DE_TITULAR`, `NUMERO_IDENTIFICACION`, `TIPO_DE_IDENTIFICACION`,
  `IDENTIFICACION_TITULARES`, `PTO_PTI`, `INSTRUMENTO_AMBIENTAL`, `DEPARTAMENTOS`,
  `MUNICIPIOS`, `GRUPO_DE_TRABAJO`, `FECHA_TERMINACION`, `OBJECTID`, `SHAPE`.
- **ANM Anotaciones RMN:** `codigo_expediente`, `estado_juridico`, `modalidad`,
  `id_tipo_de_anotacion`, `tipo_de_anotacion`, `fecha_anotacion`, `fecha_ejecutoria`,
  `observacion`.
- **Calidad de agua histórica IDEAM:** `nombre_del_punto_de_monitoreo`, `latitud`,
  `longitud`, `elevaci_n_m_s_n_m`, `corriente`, `zona_hidrogr_fica_zh`,
  `szh_c_digo_rea_zona_subzona`, `nombre_subzona_hidrogr_fica`, `departamento`,
  `municipio`, `fecha`, `propiedad_observada`, `resultado`, `unidad_del_resultado`,
  `proyecto`, `codigo__muestra`.
- **SMByC:** sin campos confirmados técnicamente (ver riesgos).
- **RUNAP:** sin campos confirmados a nivel de atributo (requiere abrir el ZIP; se
  mantienen como esperados los del catálogo de Fase 1: nombre, categoría de manejo, acto
  administrativo, geometría).

## 6. Riesgos técnicos identificados

- **SMByC / IDEAM (riesgo alto):** el subdominio de geoserver esperado
  (`geoapps.ideam.gov.co`) **no resuelve por DNS** en este momento (`nslookup` devolvió
  "Non-existent domain"; `curl` falló con exit code 6 tanto en HTTP como HTTPS), a pesar de
  que resultados de búsqueda lo referencian como el geoserver de IDEAM. Esto puede deberse
  a que el servicio fue dado de baja, movido, o solo es accesible desde otra red — no se
  puede confirmar cuál sin acceso adicional. La propia página institucional del geovisor de
  bosque advierte "Mapa interactivo externo no accesible, consulte el geovisor de
  MinAmbiente", lo que confirma que la inestabilidad no es solo un artefacto de esta prueba.
  **Este es el hallazgo más importante de la Fase 1.5:** la fuente central de deforestación
  del proyecto no tiene, por ahora, un mecanismo de descarga automatizable confirmado.
- **Catastro Minero ANM (riesgo medio):** posible desactualización (~3 años) y ausencia de
  código DANE directo en los campos de ubicación (solo nombres de texto).
- **MGN / DANE (riesgo medio):** el portal oficial no es accesible por HTTP simple (SPA);
  el servicio ArcGIS REST alternativo encontrado es funcional pero podría ser una versión
  simplificada respecto al MGN cartográfico oficial completo.
- **RUNAP (riesgo medio):** archivo pesado (66,2 MB) — su descarga real requiere aviso
  previo; licencia y campos no confirmados sin abrir el archivo.
- **Nombres de municipio como llave (riesgo transversal):** varias fuentes (catastro
  minero, calidad de agua) usan nombres de texto de departamento/municipio en vez de
  código DANE. El pipeline de integración deberá incluir un paso de normalización de
  nombres o unión espacial (spatial join) contra los polígonos de DIVIPOLA/MGN, no solo
  joins directos por código.
- **Ningún hallazgo de servicio pago o de autenticación obligatoria** en las 7 fuentes
  probadas; todas respondieron sin token ni credenciales.

## 7. Archivos modificados

- **Actualizado:** `config/data_sources.yaml` — se agregaron los campos
  `url_descarga_directa`, `formato_validado`, `llave_integracion_validada`,
  `riesgo_tecnico` y `notas_validacion` a las 7 fuentes MVP, se actualizó su `estado`
  (3 pasaron a `aprobada`, 4 quedaron en `pendiente_de_validacion`), y se añadió una nueva
  fuente `ideam_calidad_agua_historica` (dataset real de calidad de agua de IDEAM
  encontrado durante esta validación, no presente en el catálogo de Fase 1).
- **Creado:** `docs/03_validacion_fuentes_mvp.md` — este documento.

No se modificó `requirements.txt` ni se agregaron librerías nuevas. No se descargó ningún
archivo pesado ni completo — solo peticiones `HEAD`, metadatos y muestras mínimas de filas.

## Endpoints técnicos probados (referencia)

- DIVIPOLA XLSX: `https://geoportal.dane.gov.co/descargas/divipola/DIVIPOLA_Municipios.xlsx`
- DIVIPOLA API: `https://www.datos.gov.co/resource/gdxc-w37w.json`
- MGN / Divipola ArcGIS REST: `https://geoportal.dane.gov.co/mparcgis/rest/services/Divipola/Cache_DivipolaEntidadesTerritorialesCP/MapServer/9`
- Catastro Minero WFS: `https://geo.anm.gov.co/webgis/services/ANM/ServiciosANM/MapServer/WFSServer`
- ANM Anotaciones RMN API: `https://www.datos.gov.co/resource/si2v-pbq5.json`
- Calidad de agua histórica API: `https://www.datos.gov.co/resource/62gv-3857.json`
- RUNAP ZIP: `https://storage.googleapis.com/pnn_geodatabase/runap/latest.zip`
- SMByC (no resuelto): `http://geoapps.ideam.gov.co/geoserver/ows` (DNS NXDOMAIN el 2026-07-11)
