# PARTE 01 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Título del estudio
- **Propósito narrativo:** presentar en una sola formulación el nombre técnico del estudio y su unidad de análisis principal.
- **Contenido mínimo:** nombre AquaBosque; carácter de sistema o herramienta de IA explicable; priorización del riesgo ambiental territorial; ámbito nacional municipal de Colombia.
- **Afirmaciones que puede contener:** el estudio se orienta a ordenar municipios por riesgo ambiental combinado; la explicabilidad es parte del enfoque; incendios y Bogotá son componentes complementarios, no el núcleo del título.
- **Afirmaciones que NO debe contener:** resultados del modelo, métricas, rutas, verificación de archivos, cumplimiento de protocolos, promesas de impacto institucional, causalidad ambiental o capacidad sancionatoria.
- **Relación con partes anteriores y siguientes:** abre el documento; debe anticipar el objetivo general sin desarrollar justificación, alcance ni fuentes.
- **Nivel de desarrollo esperado:** breve; no requiere expansión artificial.

### 2. Subtítulo o descriptor opcional
- **Propósito narrativo:** aclarar, si el título principal queda corto, que la priorización usa datos abiertos y explicación de factores dominantes.
- **Contenido mínimo:** mención sobria a datos abiertos y unidad municipal.
- **Afirmaciones que puede contener:** el producto apoya lectura técnica y priorización; no declara resultados demostrados.
- **Afirmaciones que NO debe contener:** porcentajes de desempeño, conteos de clases, beneficios sociales no demostrados.
- **Relación con partes anteriores y siguientes:** conecta con el objetivo general.
- **Nivel de desarrollo esperado:** una frase, solo si aporta precisión.

## B. MATRIZ DE EVIDENCIA

| Afirmación o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacío |
|---|---|---|---|---|---|
| Título base: "AquaBosque - sistema de inteligencia artificial explicable para la priorización del riesgo ambiental territorial de Colombia" | Documento histórico A1, sección 1; borrador 01_TITULO.md | Documento histórico y borrador original | Alta | No material | No |
| Ambito municipal colombiano | A1 historico; A1-INDEX-V1.1; README; master_con_etiqueta y municipios.geojson con 1122 filas/features | Documento historico, indice, evidencia tecnica | Alta | No material | No |
| Enfoque de IA explicable | README; MODEL_CARD; train.py con XGBoost y SHAP | Documentacion y codigo | Alta | README/model card antiguo describe 4 indices; codigo actual usa 5 indices incluyendo fuego | Si, para precision tecnica posterior |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| No aplica bibliografia externa para fijar el titulo | No aplica | Baja | No requiere |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Es parte de arquitectura documental sustantiva | Mantener estructura modular congelada |
| Separacion Narrativa/Evidencia | APLICA | El titulo no debe mezclar evidencia o QA | Narrativa sin rutas, verificaciones ni trazabilidad |
| PEDAT | APLICA | A1 es documento tecnico | Intensidad minima; explicar solo terminos del titulo que lo requieran |
| PBF | NO_APLICA | No se requieren fuentes externas para formular el titulo | No inventar bibliografia |
| PGV-ACG | NO_APLICA | No se planifican tablas o figuras en esta parte narrativa | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifican mapas en esta parte narrativa | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Titulo propuesto y justificacion conceptual basica |
| Contenido a eliminar | "Evidencia requerida", "criterios de aceptacion", "verificacion de aceptacion", rutas y metadocumentacion |
| Contenido a corregir | "inteligencia artificial explicables" debe quedar en singular/plural correcto; no debe citar el historico como contenido del lector |
| Afirmaciones no sustentadas | "solucion integral" y profundidad tecnica del titulo si se presenta como hecho fuerte |
| Faltantes | Separar titulo principal de descriptor opcional |

## F. READINESS

READY
