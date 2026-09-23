# PARTE 10 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Resultados esperados del componente nacional
- **Propósito narrativo:** declarar productos esperados sin confundirlos con impactos.
- **Contenido mínimo:** ranking municipal; niveles de riesgo tecnico; factor dominante/SHAP; dashboard o tablero interpretativo; catalogo/model card.
- **Afirmaciones que puede contener:** resultados como salidas tecnicas esperadas o disponibles segun evidencia.
- **Afirmaciones que NO debe contener:** prediccion de dano, causalidad, politica publica implementada, mejora ambiental.
- **Relación con partes anteriores y siguientes:** responde a objetivos y prepara supuestos/riesgos.
- **Nivel de desarrollo esperado:** medio.

### 2. Resultados esperados de incendios
- **Propósito narrativo:** delimitar la salida satelital complementaria.
- **Contenido mínimo:** senal de focos/incendios por ventana; mapas o tablas solo si se validan; dNBR/Sentinel como resultado esperado condicionado si no esta final.
- **Afirmaciones que puede contener:** proxy reciente de fuego; municipios con senal en ventana.
- **Afirmaciones que NO debe contener:** deforestacion confirmada por foco termico; monitoreo permanente.
- **Relación con partes anteriores y siguientes:** conecta con riesgos.
- **Nivel de desarrollo esperado:** breve-medio.

### 3. Resultados esperados de Bogota
- **Propósito narrativo:** presentar outputs urbanos segun estado vigente.
- **Contenido mínimo:** indice territorial descriptivo, ranking de localidades/UPZ, escenarios de lluvia etiquetados, limitaciones; modelo predictivo solo como evaluacion no apta si corresponde.
- **Afirmaciones que puede contener:** producto de priorizacion espacial.
- **Afirmaciones que NO debe contener:** probabilidad calibrada operativa si el contrato vigente lo niega.
- **Relación con partes anteriores y siguientes:** conecta con limitaciones.
- **Nivel de desarrollo esperado:** medio.

### 4. Resultados de reproducibilidad y auditabilidad
- **Propósito narrativo:** fijar productos documentales/tecnicos de transparencia.
- **Contenido mínimo:** catalogo de datos, diccionario, tarjeta de modelo, pruebas, repositorio.
- **Afirmaciones que puede contener:** artefactos existen o se esperan, segun evidencia.
- **Afirmaciones que NO debe contener:** auditoria externa final si no existe.
- **Relación con partes anteriores y siguientes:** prepara supuestos y riesgos.
- **Nivel de desarrollo esperado:** breve.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Ranking nacional y niveles | predicciones.csv; master_con_etiqueta.csv | Resultado tecnico | Alta | Conteo actual 673/280/112/57 difiere del README 672/281/112/57 | Si |
| Modelo nacional SHAP | train.py; metricas.json; shap output | Codigo/resultado | Alta | Modelo re-aprende regla; no es merito predictivo | No |
| Incendios | fuego_summary; firms_signal.py | Resultado/codigo | Alta para FIRMS | Historico esperaba dNBR; evidencia actual no valida dNBR nacional como terminado | Si |
| Bogota predictivo | VALIDATION_REPORT; PRODUCT_CONTRACT | Evidencia tecnica | Alta | Historico dice modelo de alerta validado; RC vigente dice no usar como predictivo | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Interpretacion de SHAP | Fuente metodologica | Media | Pendiente |
| Uso de mapas/tableros para comunicar riesgo territorial | Literatura/guia tecnica | Baja | Pendiente |
| Fuentes satelitales y urbanas | Documentacion oficial | Alta | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Define salidas esperadas | Separar salida tecnica e impacto |
| Separacion Narrativa/Evidencia | APLICA | No confundir resultados observados con esperados | Matriz para evidencia real |
| PEDAT | APLICA | Requiere explicar outputs y limites | Desarrollo proporcional |
| PBF | APLICA | SHAP, fuentes y visualizacion requieren soporte | Pendiente validacion |
| PGV-ACG | APLICA | Se planifican tablero/tablas/graficos potenciales | Cada visual debe tener pregunta y fuente |
| PGV-MAPAS | APLICA | Se planifican mapas territoriales | CRS, cobertura, escala y limitaciones obligatorias |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Ranking, factor dominante, tablero, reproducibilidad |
| Contenido a eliminar | Recomendaciones automaticas, impactos en politicas, facilidad de uso no evaluada |
| Contenido a corregir | Bogota como predictivo validado; dNBR vs FIRMS; accuracy como resultado principal |
| Afirmaciones no sustentadas | Calidad de visualizaciones, recomendaciones por municipio, impacto publico |
| Faltantes | Estado condicionado de resultados satelitales y urbanos |

## F. READINESS

PARTIAL
