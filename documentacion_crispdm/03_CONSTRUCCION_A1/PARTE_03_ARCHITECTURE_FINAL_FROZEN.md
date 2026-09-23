# PARTE 03 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Objetivos especificos del componente nacional
- **Propósito narrativo:** desagregar el objetivo general sin mezclar componentes.
- **Contenido mínimo:** construir indice compuesto municipal; entrenar clasificador interpretable sobre la etiqueta tecnica; explicar factores dominantes; documentar reproducibilidad.
- **Afirmaciones que puede contener:** el modelo nacional clasifica niveles de priorizacion tecnica; la exactitud no prueba verdad ambiental externa.
- **Afirmaciones que NO debe contener:** afirmar prediccion causal o dano ambiental demostrado; presentar la accuracy como merito predictivo principal.
- **Relación con partes anteriores y siguientes:** operacionaliza el objetivo general y alimenta problema/preguntas.
- **Nivel de desarrollo esperado:** lista breve con precision tecnica.

### 2. Objetivos especificos de componentes complementarios
- **Propósito narrativo:** ubicar incendios y Bogota como capas auxiliares, no como nucleo del indice nacional.
- **Contenido mínimo:** incendios como senal/capa complementaria; Bogota como modulo urbano diferenciado; advertencia de no confundir prediccion validada con indice descriptivo si aplica.
- **Afirmaciones que puede contener:** FIRMS aporta focos termicos recientes; dNBR/Sentinel-2 aparece como capacidad satelital o componente pendiente si no esta validado nacionalmente.
- **Afirmaciones que NO debe contener:** afirmar area quemada por dNBR como producto nacional terminado si la evidencia vigente muestra FIRMS NRT y runbook de Sentinel-2 en construccion.
- **Relación con partes anteriores y siguientes:** prepara alcance y fuentes.
- **Nivel de desarrollo esperado:** lista corta con estado honesto.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Objetivos historicos: indice, clasificador SHAP, incendios, Bogota, reproducibilidad | Documento historico A1, seccion 3 | Documento historico | Alta | No material dentro del historico | No |
| Indice nacional ejecutado sobre 1122 municipios | master_con_etiqueta.csv; README | Resultado tecnico | Alta | Distribucion README 672/281/112/57 difiere de archivo actual 673/280/112/57 | Si |
| Formula del indice nacional | build_target.py | Codigo | Alta | MODEL_CARD historico usa pesos 0.35/0.30/0.25/0.10 y 4 indices; codigo actual usa 0.30/0.25/0.15/0.20/0.10 y fuego | Si |
| Capa de incendios | firms_signal.py; fuego_summary.json; runbook Sentinel-2 | Codigo/resultado/runbook | Alta para FIRMS; media para Sentinel-2 | Historico dice dNBR; evidencia actual consolidada muestra FIRMS NRT y Sentinel-2 como capacidad en construccion | Si |
| Bogota alerta temprana | MODEL_CARD_ZOOM_BOGOTA; PRODUCT_CONTRACT; VALIDATION_REPORT; rc_metrics | Evidencia tecnica | Alta | Script/metricas antiguas presentan modelo predictivo; contrato RC vigente dice producto descriptivo y modelo predictivo no apto | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Uso de SHAP como explicabilidad de modelos de arboles | Documentacion tecnica o articulo metodologico | Media | Pendiente |
| Uso de FIRMS como proxy de focos de calor/incendios | Documentacion oficial NASA FIRMS | Alta | Pendiente |
| Uso de dNBR/Sentinel-2 si se mantiene en objetivos | Fuente tecnica/teledeteccion | Alta | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Define modulos del documento | Separar objetivos nacional, incendios y Bogota |
| Separacion Narrativa/Evidencia | APLICA | No trasladar auditoria al texto final | Contradicciones solo en matriz/limitaciones |
| PEDAT | APLICA | Requiere precision conceptual | Expandir solo lo necesario para no sobreatribuir |
| PBF | APLICA | SHAP, FIRMS, dNBR y Sentinel son referencias externas | Registrar fuentes necesarias antes de redaccion final |
| PGV-ACG | NO_APLICA | No se exige visual en la narrativa de objetivos | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifica mapa aqui | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Lista base de cuatro objetivos especificos |
| Contenido a eliminar | Rutas, explicaciones de evidencia, medibilidad repetitiva, conclusiones |
| Contenido a corregir | Actualizar incendio dNBR/FIRMS y Bogota predictivo/descriptivo segun evidencia real |
| Afirmaciones no sustentadas | "validacion con datos historicos" del indice nacional como si hubiera ground truth |
| Faltantes | Diferenciar claramente intencion, resultado ejecutado y capacidad en construccion |

## F. READINESS

PARTIAL
