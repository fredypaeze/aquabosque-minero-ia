# PARTE 02 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Enunciado del objetivo general
- **Propósito narrativo:** declarar la finalidad principal del estudio en una frase controlada.
- **Contenido mínimo:** proveer una herramienta/capa de priorizacion; ordenar municipios de Colombia por riesgo ambiental combinado; explicar factor dominante; usar datos abiertos; apoyar focalizacion tecnica con transparencia y auditabilidad.
- **Afirmaciones que puede contener:** el objetivo es apoyar la priorizacion, no decidir automaticamente; la salida es tecnica y relativa.
- **Afirmaciones que NO debe contener:** impacto demostrado en politicas publicas, mejora institucional verificada, reduccion de dano, causalidad o sancion ambiental.
- **Relación con partes anteriores y siguientes:** deriva del titulo y gobierna los objetivos especificos.
- **Nivel de desarrollo esperado:** breve, con una aclaracion posterior sobre alcance si hace falta.

### 2. Alcance del objetivo
- **Propósito narrativo:** precisar que el objetivo central es nacional-municipal y que incendios/Bogota complementan la lectura.
- **Contenido mínimo:** componente nacional separado de componentes complementarios; distincion entre priorizacion descriptiva nacional y alerta/indice urbano Bogota.
- **Afirmaciones que puede contener:** la capa nacional usa indice compuesto; Bogota no debe confundirse con el ranking nacional.
- **Afirmaciones que NO debe contener:** presentar el modelo Bogota como producto predictivo validado si la evidencia tecnica vigente lo contradice.
- **Relación con partes anteriores y siguientes:** prepara objetivos especificos y problema analitico.
- **Nivel de desarrollo esperado:** parrafo corto.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Objetivo historico de proveer herramienta de priorizacion | Documento historico A1, seccion 2 | Documento historico | Alta | No material | No |
| Ordenamiento de 1122 municipios | README; master_con_etiqueta.csv; municipios.geojson | Evidencia tecnica | Alta | No material | No |
| Explicacion por factor dominante con SHAP | MODEL_CARD; train.py; modelos/shap | Codigo y documentacion | Alta | La documentacion antigua habla de 4 indices; codigo actual incluye idx_fuego | Si |
| Apoyo a focalizacion de atencion ambiental | Historico y README | Intencion/proposito | Media | No hay evidencia de adopcion institucional o efecto decisional | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Que la priorizacion basada en evidencia apoya focalizacion tecnica | Literatura o guia institucional sobre priorizacion ambiental basada en evidencia | Media | Pendiente |
| Datos abiertos como base de transparencia/auditabilidad | Norma o guia oficial sobre datos abiertos/reproducibilidad | Media | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Parte sustantiva modular | Objetivo unico y no mezclado con justificacion |
| Separacion Narrativa/Evidencia | APLICA | El objetivo debe redactarse para el lector | Evidencia y rutas solo en matriz |
| PEDAT | APLICA | Documento tecnico | Desarrollo proporcional: enunciado + delimitacion |
| PBF | APLICA | Usa conceptos externos de datos abiertos y priorizacion publica | Registrar necesidades, no inventar fuentes |
| PGV-ACG | NO_APLICA | No se planifican visuales narrativos | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifican mapas | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Enunciado del objetivo historico |
| Contenido a eliminar | Justificacion larga, medibilidad generica, verificacion de aceptacion, rutas |
| Contenido a corregir | No presentar "apoyo a focalizacion" como impacto ya demostrado |
| Afirmaciones no sustentadas | "mejorar asignacion de recursos" si se formula como resultado |
| Faltantes | Delimitar componente nacional y componente Bogota |

## F. READINESS

PARTIAL
