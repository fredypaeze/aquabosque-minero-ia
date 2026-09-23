# PARTE 11 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Supuestos sobre datos
- **Propósito narrativo:** declarar condiciones iniciales necesarias para interpretar el estudio.
- **Contenido mínimo:** fuentes abiertas reflejan senales observables, no verdad completa; cobertura y calidad varian; ausencia de dato no equivale a ausencia de riesgo.
- **Afirmaciones que puede contener:** RUCOM capta mineria formal; agua depende de estaciones; deforestacion/fuego tienen cobertura y temporalidad propias.
- **Afirmaciones que NO debe contener:** cobertura perfecta, calidad suficiente universal, disponibilidad garantizada.
- **Relación con partes anteriores y siguientes:** sigue de fuentes y anticipa riesgos.
- **Nivel de desarrollo esperado:** medio.

### 2. Supuestos sobre el indice nacional
- **Propósito narrativo:** explicar que el ranking depende de decisiones metodologicas.
- **Contenido mínimo:** pesos definidos; cuantiles; priorizacion relativa; etiqueta tecnica.
- **Afirmaciones que puede contener:** los pesos son auditables y ajustables.
- **Afirmaciones que NO debe contener:** el nivel de riesgo como verdad oficial independiente.
- **Relación con partes anteriores y siguientes:** conecta con resultados y limitaciones.
- **Nivel de desarrollo esperado:** medio.

### 3. Supuestos sobre componentes complementarios
- **Propósito narrativo:** delimitar incendios y Bogota.
- **Contenido mínimo:** FIRMS como proxy; Sentinel/dNBR condicionado; Bogota sujeto a sesgo de reporte y estado de aprobacion del modelo.
- **Afirmaciones que puede contener:** cada componente tiene supuestos distintos.
- **Afirmaciones que NO debe contener:** generalizacion de Bogota al pais.
- **Relación con partes anteriores y siguientes:** alimenta riesgos.
- **Nivel de desarrollo esperado:** medio.

### 4. Supuestos sobre uso
- **Propósito narrativo:** evitar interpretaciones indebidas.
- **Contenido mínimo:** apoyo a monitoreo/revision tecnica; no decision automatica; no sancion.
- **Afirmaciones que puede contener:** uso con revision humana.
- **Afirmaciones que NO debe contener:** reemplazo de autoridad ambiental.
- **Relación con partes anteriores y siguientes:** prepara riesgos y limitaciones.
- **Nivel de desarrollo esperado:** breve.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Fuentes abiertas reflejan razonablemente presion | Historico; README | Supuesto/intencion | Media | Falta validacion externa por fuente | Si |
| Indice por cuantiles ordena territorio | Historico; build_target.py | Metodo/codigo | Alta como metodo | No valida riesgo real independiente | Si |
| IDIGER como etiqueta valida | Historico; source_registry; VALIDATION_REPORT | Registro/evaluacion | Media | Producto predictivo no aprobado; sesgo de reporte declarado | Si |
| Pesos del indice | MODEL_CARD vs build_target.py | Documentacion/codigo | Alta para contradiccion | Pesos y variables difieren | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Validez/limitaciones de datos administrativos para riesgo | Literatura o guia oficial | Media | Pendiente |
| Uso de cuantiles en priorizacion relativa | Fuente metodologica | Media | Pendiente |
| Sesgo de reporte en bitacoras de emergencias | Literatura/guia tecnica | Media | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Supuestos son modulo formal | Agrupar por datos, metodo, componentes y uso |
| Separacion Narrativa/Evidencia | APLICA | Deben distinguirse supuestos de hechos | No redactar supuestos como resultados |
| PEDAT | APLICA | Supuestos requieren interpretacion | Explicar impacto sin alargar |
| PBF | APLICA | Requiere soporte metodologico externo | Pendiente |
| PGV-ACG | NO_APLICA | No se planifican visuales narrativos obligatorios | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifican mapas en esta parte | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Supuestos de fuentes abiertas, indice por cuantiles e IDIGER |
| Contenido a eliminar | Supuestos redundantes, rutas, verificacion |
| Contenido a corregir | Datos geoespaciales completos no basta; fuente oficial y cobertura deben validarse |
| Afirmaciones no sustentadas | Capacidad computacional suficiente, datos de alerta disponibles, consistencia entre fuentes |
| Faltantes | Supuesto de formula/pesos y diferencia entre etiqueta tecnica y verdad oficial |

## F. READINESS

PARTIAL
