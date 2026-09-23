# PARTE 07 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Alcance principal: priorizacion nacional municipal
- **Propósito narrativo:** delimitar el nucleo del estudio.
- **Contenido mínimo:** 1122 municipios de Colombia; indice compuesto; variables ambientales abiertas; salida de niveles y explicacion.
- **Afirmaciones que puede contener:** el estudio trabaja a escala municipal nacional; el ranking es relativo.
- **Afirmaciones que NO debe contener:** analisis departamental/regional como alcance principal; dano observado independiente; causalidad.
- **Relación con partes anteriores y siguientes:** concreta preguntas y orienta fuentes.
- **Nivel de desarrollo esperado:** medio.

### 2. Componente complementario de incendios
- **Propósito narrativo:** definir el lugar de incendios sin sobreatribuirlo.
- **Contenido mínimo:** componente complementario por ventana/evento; distinguir FIRMS, dNBR o Sentinel-2 segun evidencia validada.
- **Afirmaciones que puede contener:** FIRMS aporta senal reciente de focos termicos; dNBR/Sentinel-2 puede aparecer como medicion/capacidad si esta validada.
- **Afirmaciones que NO debe contener:** monitoreo satelital continuo permanente; cobertura nacional dNBR si no esta demostrada.
- **Relación con partes anteriores y siguientes:** conecta con fuentes y riesgos.
- **Nivel de desarrollo esperado:** breve-medio.

### 3. Componente complementario Bogota
- **Propósito narrativo:** separar escala urbana de la lectura nacional.
- **Contenido mínimo:** Bogota como modulo urbano; localidad/UPZ segun evidencia; producto descriptivo si ese es el contrato vigente; prediccion solo como evaluacion si no esta aprobada.
- **Afirmaciones que puede contener:** usa fuentes IDIGER/SAB/IDECA cuando verificadas.
- **Afirmaciones que NO debe contener:** aplicar resultados Bogota al resto del pais; usar el indice como probabilidad.
- **Relación con partes anteriores y siguientes:** prepara fuentes, resultados y limitaciones.
- **Nivel de desarrollo esperado:** medio.

### 4. Exclusiones y limites
- **Propósito narrativo:** evitar promesas fuera del alcance.
- **Contenido mínimo:** no sanciona, no determina ilegalidad, no prueba causalidad; no monitoreo en tiempo real salvo senales declaradas como NRT/proxy; no decisiones automaticas.
- **Afirmaciones que puede contener:** las limitaciones hacen parte del uso responsable.
- **Afirmaciones que NO debe contener:** lenguaje defensivo de auditoria interna.
- **Relación con partes anteriores y siguientes:** alimenta riesgos y supuestos.
- **Nivel de desarrollo esperado:** medio.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Alcance nacional de 1122 municipios | Historico; README; municipios.geojson; master_con_etiqueta.csv | Historico y tecnico | Alta | No material | No |
| Incendios fuera de monitoreo continuo en tiempo real | Historico; docs/07_limitaciones.md | Historico/documentacion | Alta | firms_signal usa NRT 7 dias; debe redactarse como senal NRT/proxy, no vigilancia permanente | Si |
| dNBR area quemada | Historico; runbook Sentinel-2 | Historico/runbook | Media-baja | Evidencia productiva actual localizada es FIRMS; Sentinel-2/dNBR aparece como capacidad o demo, no como alcance nacional cerrado | Si |
| Bogota alerta urbana | PRODUCT_CONTRACT; MODEL_CARD_ZOOM_BOGOTA; VALIDATION_REPORT | Documentacion tecnica | Alta | Historico habla de alerta temprana predictiva; contrato vigente la reencuadra como indice descriptivo | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Numero oficial de municipios/DIVIPOLA 2025 | Fuente oficial DANE | Alta | Pendiente |
| FIRMS como fuente de focos de calor | Documentacion oficial NASA FIRMS | Alta | Pendiente |
| Sentinel-2/dNBR para area quemada si se mantiene | Fuente tecnica satelital | Alta | Pendiente |
| Fuentes IDIGER/SAB/IDECA y licencias | Fuentes oficiales Bogota | Alta | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Delimita modulos del documento | Congelar inclusiones y exclusiones |
| Separacion Narrativa/Evidencia | APLICA | Alcance no debe narrar verificaciones | Rutas solo en matriz |
| PEDAT | APLICA | Alcance necesita precision | Desarrollo suficiente sin convertirlo en metodologia completa |
| PBF | APLICA | Depende de fuentes oficiales externas | No READY sin fuentes validadas |
| PGV-ACG | NO_APLICA | No se planifica visual en esta parte | Sin exigencia visual |
| PGV-MAPAS | APLICA | El alcance planifica mapa/representacion territorial en el producto A1 futuro | Exigir CRS, cobertura, escala y limites cuando se redacten mapas |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Alcance nacional, incendios, Bogota y exclusion de tiempo real |
| Contenido a eliminar | Rutas, conclusiones, verificacion de aceptacion |
| Contenido a corregir | Temporalidad "disponibilidad real" sin inventar periodos; dNBR/FIRMS; Bogota predictivo/descriptivo |
| Afirmaciones no sustentadas | Escalabilidad futura y actualizaciones periodicas si no se evidencian |
| Faltantes | Separacion estricta entre componente nacional y urbano |

## F. READINESS

PARTIAL
