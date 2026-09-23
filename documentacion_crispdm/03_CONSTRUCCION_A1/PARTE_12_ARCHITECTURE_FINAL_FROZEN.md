# PARTE 12 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Riesgos de interpretacion
- **Propósito narrativo:** prevenir lecturas indebidas del producto.
- **Contenido mínimo:** no causalidad, no ilegalidad, no sancion, no dano probado; accuracy nacional no es merito predictivo.
- **Afirmaciones que puede contener:** el uso correcto es priorizacion tecnica y explicable.
- **Afirmaciones que NO debe contener:** lenguaje de descargo legal excesivo o metadocumentacion.
- **Relación con partes anteriores y siguientes:** cierra el A1 con uso responsable.
- **Nivel de desarrollo esperado:** medio.

### 2. Limitaciones de datos
- **Propósito narrativo:** explicar restricciones que afectan cobertura e interpretacion.
- **Contenido mínimo:** mineria formal/RUCOM; agua por estaciones; deforestacion/fuego con cobertura temporal y espacial; sesgo de reporte Bogota.
- **Afirmaciones que puede contener:** ausencia de senal no equivale a riesgo cero.
- **Afirmaciones que NO debe contener:** cobertura completa sin evidencia.
- **Relación con partes anteriores y siguientes:** recoge fuentes y supuestos.
- **Nivel de desarrollo esperado:** medio.

### 3. Riesgos metodologicos
- **Propósito narrativo:** declarar dependencia de formula, pesos, cuantiles y re-aprendizaje.
- **Contenido mínimo:** etiqueta construida; pesos auditables; clase critica minoritaria; cambios de codigo/documentacion deben reconciliarse.
- **Afirmaciones que puede contener:** la explicabilidad ayuda a revisar factores dominantes.
- **Afirmaciones que NO debe contener:** modelo como prueba externa del riesgo.
- **Relación con partes anteriores y siguientes:** cierra problema y resultados.
- **Nivel de desarrollo esperado:** medio.

### 4. Limitaciones de componentes complementarios
- **Propósito narrativo:** ubicar incendios y Bogota con honestidad.
- **Contenido mínimo:** FIRMS proxy; Sentinel/dNBR condicionado; Bogota descriptivo si predictivo no aprobado; no tiempo real permanente.
- **Afirmaciones que puede contener:** componentes requieren validacion continua.
- **Afirmaciones que NO debe contener:** alerta operativa aprobada sin evidencia.
- **Relación con partes anteriores y siguientes:** cierre de alcance.
- **Nivel de desarrollo esperado:** medio.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| No causalidad/no ilegalidad/no sancion | README; MODEL_CARD; docs/07_limitaciones.md | Documentacion tecnica | Alta | No material | No |
| Accuracy no es merito predictivo nacional | MODEL_CARD; metricas.json | Documentacion/resultado | Alta | No material | No |
| Datos con cobertura limitada | docs/07_limitaciones.md; diccionario; config | Documentacion | Alta | config vs README difieren en grado de verificacion | Si |
| Bogota predictivo no aprobado | VALIDATION_REPORT; PRODUCT_CONTRACT | Evidencia tecnica | Alta | Contradice historico y metricas antiguas que lo presentan como predictivo | Si |
| Incendios satelitales | firms_signal; runbook | Codigo/runbook | Media | dNBR historico no esta cerrado como producto nacional | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Limitaciones de inferencia causal con datos observacionales | Literatura metodologica | Media | Pendiente |
| Limitaciones de SHAP/no causalidad | Fuente metodologica | Alta | Pendiente |
| Sesgo de reporte en emergencias urbanas | Literatura o guia oficial | Media | Pendiente |
| Limitaciones FIRMS/Sentinel por nubes/proxy | Documentacion oficial/metodologica | Alta | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Cierre modular del A1 | Riesgos agrupados y no dispersos |
| Separacion Narrativa/Evidencia | APLICA | Riesgos deben fundarse sin narrar auditoria | Contradicciones en matriz, no como seccion del lector |
| PEDAT | APLICA | Requiere explicar limites tecnicos | Desarrollo suficiente, no defensivo |
| PBF | APLICA | Riesgos metodologicos requieren soporte externo | Pendiente |
| PGV-ACG | NO_APLICA | No se planifican visuales narrativos obligatorios | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifican mapas en esta parte | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Riesgos de integracion, datos, escalabilidad, no tiempo real |
| Contenido a eliminar | Estrategias genericas no sustentadas, impactos no demostrados, rutas, verificacion |
| Contenido a corregir | Riesgos deben incluir contradiccion codigo-documentacion y Bogota no predictivo |
| Afirmaciones no sustentadas | Mitigaciones como si estuvieran implementadas |
| Faltantes | Riesgo de confundir indice construido con resultado observado independiente |

## F. READINESS

PARTIAL
