# PARTE 06 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Preguntas sobre priorizacion nacional
- **Propósito narrativo:** convertir el problema nacional en preguntas respondibles por el producto.
- **Contenido mínimo:** municipios con mayor riesgo combinado; factor dominante; distribucion territorial del ranking.
- **Afirmaciones que puede contener:** preguntas de ordenamiento y explicacion, no de causalidad.
- **Afirmaciones que NO debe contener:** preguntas que prometan medir dano ambiental real o ilegalidad.
- **Relación con partes anteriores y siguientes:** sigue del problema y delimita alcance.
- **Nivel de desarrollo esperado:** lista breve.

### 2. Preguntas sobre incendios como componente complementario
- **Propósito narrativo:** definir que se quiere leer con la capa de fuego/incendios.
- **Contenido mínimo:** presencia/magnitud reciente de focos o area quemada segun evidencia validada; municipios o AOI afectados.
- **Afirmaciones que puede contener:** si se usa FIRMS, pregunta por focos termicos recientes; si se usa dNBR, debe quedar como medicion por ventana validada.
- **Afirmaciones que NO debe contener:** vigilancia permanente o clasificacion de imagen cruda como ya productiva si no esta validada.
- **Relación con partes anteriores y siguientes:** enlaza con fuentes y alcance.
- **Nivel de desarrollo esperado:** una o dos preguntas.

### 3. Preguntas sobre Bogota
- **Propósito narrativo:** mantener el componente urbano separado del nacional.
- **Contenido mínimo:** si el producto vigente es descriptivo, preguntar por territorios con mayor densidad historica/susceptibilidad; no por probabilidad operativa si esta fallida.
- **Afirmaciones que puede contener:** evaluar si puede anticiparse es pregunta de investigacion, no resultado.
- **Afirmaciones que NO debe contener:** afirmar que el modelo anticipa operativamente emergencias.
- **Relación con partes anteriores y siguientes:** prepara alcance y resultados esperados.
- **Nivel de desarrollo esperado:** breve.

### 4. Pregunta de reproducibilidad
- **Propósito narrativo:** incluir auditabilidad como pregunta transversal.
- **Contenido mínimo:** reconstruccion desde datos abiertos, catalogo, tarjeta de modelo, pruebas.
- **Afirmaciones que puede contener:** pregunta si es replicable, no declarar adopcion.
- **Afirmaciones que NO debe contener:** certificacion externa si no existe.
- **Relación con partes anteriores y siguientes:** conecta con viabilidad y riesgos.
- **Nivel de desarrollo esperado:** breve.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Preguntas historicas del A1 | Documento historico, seccion 6 | Documento historico | Alta | No material | No |
| Pregunta nacional respondible por indice actual | master_con_etiqueta.csv; predicciones.csv; SHAP | Resultado tecnico | Alta | Distribucion antigua/actual difiere levemente | Si |
| Pregunta incendios | fuego_summary; firms_signal.py; runbook Sentinel-2 | Resultado/codigo/runbook | Media | Historico pregunta por incendios; tecnicamente hay FIRMS NRT y dNBR en construccion | Si |
| Pregunta Bogota predictiva | Historico y scripts vs PRODUCT_CONTRACT/VALIDATION_REPORT | Evidencia tecnica contradictoria | Alta | Estado vigente no permite vender prediccion como producto aprobado | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Preguntas sobre explicabilidad SHAP | Fuente metodologica | Media | Pendiente |
| Preguntas sobre FIRMS/dNBR | Documentacion oficial/metodologica satelital | Alta | Pendiente |
| Preguntas sobre alerta temprana urbana | Literatura/guia tecnica de alertas | Media | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Modulo formal del A1 | Preguntas alineadas con problema y alcance |
| Separacion Narrativa/Evidencia | APLICA | Preguntas no deben incluir auditoria | Evidencia queda fuera de la narrativa |
| PEDAT | APLICA | Requiere precision, no expansion larga | Preguntas claras con breve alcance |
| PBF | APLICA | Usa conceptos externos y tecnicos | Fuentes pendientes para metodos |
| PGV-ACG | NO_APLICA | No se planifica visual en esta parte | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | Aunque hay distribucion geografica, no se planifica mapa en la parte narrativa | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Enfoque de preguntas sobre municipios, factores, incendios, Bogota y reproducibilidad |
| Contenido a eliminar | Desarrollo metodologico largo, rutas y verificacion |
| Contenido a corregir | No usar preguntas genericas adicionales que amplien artificialmente el estudio |
| Afirmaciones no sustentadas | Validacion con feedback de audiencias; herramientas especificas no evidenciadas |
| Faltantes | Ajustar pregunta Bogota al estado real del producto |

## F. READINESS

PARTIAL
