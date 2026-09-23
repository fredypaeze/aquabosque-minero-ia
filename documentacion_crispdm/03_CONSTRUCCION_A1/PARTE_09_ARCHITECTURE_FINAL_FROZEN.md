# PARTE 09 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Viabilidad tecnica del componente nacional
- **Propósito narrativo:** evaluar si el nucleo nacional puede sostenerse con evidencia disponible.
- **Contenido mínimo:** dataset municipal existe; formula y modelo existen; pruebas/documentacion soportan reproducibilidad; limitaciones de etiqueta tecnica.
- **Afirmaciones que puede contener:** el componente nacional es viable como priorizacion tecnica reproducible.
- **Afirmaciones que NO debe contener:** modelo predictivo externo validado o verdad oficial de riesgo.
- **Relación con partes anteriores y siguientes:** conecta fuentes con resultados esperados.
- **Nivel de desarrollo esperado:** medio.

### 2. Viabilidad de incendios y satelital
- **Propósito narrativo:** distinguir lo operativo de lo pendiente.
- **Contenido mínimo:** FIRMS disponible y ejecutado; Sentinel-2/dNBR/U-Net como capacidad en construccion si no hay validacion; GPU solo si esta evidenciada.
- **Afirmaciones que puede contener:** la capa FIRMS aporta proxy reciente; dNBR/Sentinel requiere validacion si se incluye.
- **Afirmaciones que NO debe contener:** cluster GPU disponible como hecho si no hay evidencia directa suficiente; produccion nacional dNBR.
- **Relación con partes anteriores y siguientes:** informa riesgos.
- **Nivel de desarrollo esperado:** medio.

### 3. Viabilidad del componente Bogota
- **Propósito narrativo:** presentar estado tecnico real.
- **Contenido mínimo:** fuentes Bogota registradas; indice descriptivo viable; producto predictivo no aprobado si gates fallan.
- **Afirmaciones que puede contener:** uso recomendado como priorizacion/escenario, no pronostico.
- **Afirmaciones que NO debe contener:** alerta predictiva operativa validada.
- **Relación con partes anteriores y siguientes:** informa resultados esperados.
- **Nivel de desarrollo esperado:** medio.

### 4. Condiciones de viabilidad
- **Propósito narrativo:** exponer dependencias criticas.
- **Contenido mínimo:** calidad/actualizacion de fuentes; consistencia entre documentacion y codigo; bibliografia validada; alcance honesto.
- **Afirmaciones que puede contener:** la viabilidad depende de gestionar limitaciones.
- **Afirmaciones que NO debe contener:** cronogramas inventados o recursos humanos no evidenciados.
- **Relación con partes anteriores y siguientes:** alimenta supuestos/riesgos.
- **Nivel de desarrollo esperado:** medio.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Nacional viable tecnicamente | master_con_etiqueta; metricas.json; README; tests mencionados | Resultado/documentacion | Alta | Metricas/documentacion anteriores no siempre coinciden con codigo actual | Si |
| Capacidad GPU para satelital | Historico; RUNBOOK_SATELITAL_L40S | Documento historico/runbook | Media | No hay evidencia directa de ejecucion GPU en esta revision | Si |
| Bogota producto predictivo | scripts/metricas antiguas vs VALIDATION_REPORT/PRODUCT_CONTRACT | Evidencia contradictoria | Alta | Gates vigentes fallan para producto predictivo | Si |
| Reproducibilidad | README; scripts pipeline; data/raw incluido | Documentacion/codigo | Media | No se ejecuto reconstruccion end-to-end aqui | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Viabilidad de datos abiertos para priorizacion ambiental | Guia/literatura | Media | Pendiente |
| Uso responsable de modelos explicables en decision publica | Guia/literatura | Media | Pendiente |
| Capacidad satelital FIRMS/Sentinel para incendios/deforestacion | Documentacion oficial/metodologica | Alta | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Seccion de evaluacion sustantiva | Separar componentes y condiciones |
| Separacion Narrativa/Evidencia | APLICA | Viabilidad debe distinguir hecho de condicion | No convertir deseos en hechos |
| PEDAT | APLICA | Requiere analisis proporcional | Desarrollar dependencias criticas |
| PBF | APLICA | Incluye metodos/fuentes externas | Fuentes pendientes impiden READY |
| PGV-ACG | NO_APLICA | No se planifican visuales narrativos obligatorios | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifican mapas en esta parte | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Datos abiertos, computo, reproducibilidad y calidad de fuentes como condiciones |
| Contenido a eliminar | Recursos humanos inventados, cronograma 10-15 semanas sin fuente, soporte institucional no evidenciado |
| Contenido a corregir | Viabilidad Bogota y satelital; GPU como condicion no verificada localmente |
| Afirmaciones no sustentadas | Experiencia del equipo, costos razonables, adopcion facil |
| Faltantes | Estado de gates tecnicos y contradicciones codigo-documentacion |

## F. READINESS

PARTIAL
