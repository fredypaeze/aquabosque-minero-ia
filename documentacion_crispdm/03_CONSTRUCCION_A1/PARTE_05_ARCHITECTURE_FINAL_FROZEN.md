# PARTE 05 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Problema analitico central
- **Propósito narrativo:** formular el reto tecnico que resuelve A1.
- **Contenido mínimo:** combinar senales heterogeneas de presion ambiental en una priorizacion interpretable por municipio.
- **Afirmaciones que puede contener:** el indice es construido; la clasificacion nacional deriva de formula/variables; no existe ground truth oficial de riesgo ambiental municipal.
- **Afirmaciones que NO debe contener:** que el modelo descubre dano real, causalidad o ilegalidad.
- **Relación con partes anteriores y siguientes:** traduce objetivos en problema investigable.
- **Nivel de desarrollo esperado:** medio.

### 2. Dos tareas que no deben confundirse
- **Propósito narrativo:** separar priorizacion nacional y componente urbano Bogota.
- **Contenido mínimo:** nacional = indice/priorizacion tecnica; Bogota = modulo urbano con evidencia historica y estado de validacion propio.
- **Afirmaciones que puede contener:** el componente predictivo Bogota fue evaluado; su uso final debe respetar el contrato vigente.
- **Afirmaciones que NO debe contener:** presentar Bogota como prediccion operativa validada si la evidencia RC dice lo contrario.
- **Relación con partes anteriores y siguientes:** alimenta preguntas y alcance.
- **Nivel de desarrollo esperado:** medio.

### 3. Condiciones de interpretacion
- **Propósito narrativo:** fijar limites conceptuales del problema.
- **Contenido mínimo:** priorizacion relativa; ausencia de senal no equivale a ausencia de riesgo; revision humana; limitaciones de datos abiertos.
- **Afirmaciones que puede contener:** el resultado es instrumento de lectura tecnica.
- **Afirmaciones que NO debe contener:** automatizacion decisional.
- **Relación con partes anteriores y siguientes:** conecta con riesgos y supuestos.
- **Nivel de desarrollo esperado:** breve-medio.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Problema historico de combinar senales heterogeneas | Documento historico A1, seccion 5 | Documento historico | Alta | No material | No |
| Priorizacion nacional por indice compuesto | build_target.py; MODEL_CARD; master_con_etiqueta.csv | Codigo/resultado | Alta | Pesos y variables difieren entre MODEL_CARD y codigo actual | Si |
| No ground truth oficial de riesgo | MODEL_CARD | Documentacion tecnica | Alta | No material | No |
| Alerta Bogota como prediccion supervisada | Historico; scripts/09_bogota_alerta_ml.py | Historico/codigo | Media | PRODUCT_CONTRACT y VALIDATION_REPORT vigentes reclasifican producto como descriptivo y predictivo no apto | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Concepto de indice compuesto para priorizacion territorial | Literatura metodologica | Media | Pendiente |
| Explicabilidad SHAP como lectura de contribuciones, no causalidad | Fuente metodologica | Alta | Pendiente |
| Limitaciones de usar datos abiertos/administrativos para inferencia ambiental | Literatura o guia oficial | Media | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Define problema del documento | No mezclar problema, justificacion y resultados |
| Separacion Narrativa/Evidencia | APLICA | Requiere distinguir hechos e inferencias | Matriz separada para contradicciones |
| PEDAT | APLICA | Conceptos comprimidos requieren explicacion | Desarrollo proporcional de indice, tarea y limites |
| PBF | APLICA | Usa conceptos metodologicos externos | Fuentes pendientes antes de READY |
| PGV-ACG | NO_APLICA | No se planifican tablas/figuras narrativas | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifican mapas aqui | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Formulacion historica del problema y distincion nacional/Bogota |
| Contenido a eliminar | Impactos sociales/economicos no sustentados, rutas, verificacion de aceptacion |
| Contenido a corregir | Bogota debe reflejar estado tecnico vigente; no sobreatribuir prediccion |
| Afirmaciones no sustentadas | Prevencion de crisis, mejora de calidad de vida, eficiencia economica |
| Faltantes | Declarar que indice construido no es resultado observado independiente |

## F. READINESS

PARTIAL
