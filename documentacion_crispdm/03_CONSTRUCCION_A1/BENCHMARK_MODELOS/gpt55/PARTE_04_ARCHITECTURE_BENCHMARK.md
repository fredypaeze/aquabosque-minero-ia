# PARTE 04 — JUSTIFICACIÓN: ARQUITECTURA DOCUMENTAL BENCHMARK

## 1. ARQUITECTURA NARRATIVA FINAL

### 4. Justificación

La Parte 04 debe justificar por qué el estudio AquaBosque Minero IA es pertinente, necesario y técnicamente defendible como definición temática. La narrativa debe sostenerse en cuatro ejes exigidos por el índice congelado: impacto ambiental significativo, necesidad de priorización de recursos, base científica del problema y aplicación práctica en políticas públicas.

La arquitectura final no debe incluir rutas de archivos, criterios de aceptación, verificaciones internas, listas de evidencia, estados de QA, trazabilidad de agente ni autoevaluación. Esos elementos pertenecen a matrices, anexos o controles, no al cuerpo que leería el destinatario del documento A1.

#### 4.1. Relevancia del problema ambiental territorial

Contenido mínimo esperado:

- Presentar que el estudio parte de una presión ambiental territorial asociada a minería, deforestación, estrés hídrico y sensibilidad del territorio.
- Explicar que dichas señales no se distribuyen homogéneamente entre municipios.
- Indicar que la unidad municipal permite organizar la lectura territorial del riesgo ambiental combinado.
- Evitar afirmar daño ambiental probado, causalidad directa, ilegalidad minera o contaminación específica si no existe evidencia validada para ello.

Función narrativa:

Abrir la justificación desde el problema público y ambiental, no desde la solución tecnológica. Esta sección debe responder por qué el tema importa antes de explicar por qué AquaBosque es un enfoque posible.

#### 4.2. Necesidad de focalización y priorización basada en evidencia

Contenido mínimo esperado:

- Desarrollar la necesidad de ordenar territorios para apoyar la focalización de la atención ambiental.
- Explicar que la priorización es útil cuando las señales ambientales son múltiples, heterogéneas y territorialmente dispersas.
- Presentar la priorización como un apoyo analítico para orientar revisión institucional más detallada.
- Mantener lenguaje prudente: el producto prioriza y orienta, no reemplaza evaluación ambiental, inspección, regulación ni decisión sancionatoria.

Función narrativa:

Conectar la existencia de presiones ambientales con la necesidad de un instrumento de ordenamiento analítico. Esta sección debe evitar beneficios genéricos no demostrados como ahorro económico, mejora automática de políticas públicas o eficiencia institucional no medida.

#### 4.3. Pertinencia de un enfoque transparente, explicable y reproducible

Contenido mínimo esperado:

- Justificar que la temática requiere no solo un ranking, sino una explicación del factor dominante por municipio.
- Introducir la explicabilidad como requisito de interpretación y revisión técnica, no como garantía de verdad causal.
- Explicar que el uso de datos abiertos y un proceso reproducible aumenta la auditabilidad del producto.
- Señalar que la replicabilidad es especialmente relevante cuando el resultado pretende apoyar decisiones públicas.

Función narrativa:

Sostener por qué la solución debe ser explicable y auditable. La sección debe derivarse del documento histórico y de la documentación técnica, pero sin redactarse como inventario de archivos.

#### 4.4. Base técnica y científica del planteamiento

Contenido mínimo esperado:

- Presentar el índice de riesgo ambiental combinado como una etiqueta técnica de priorización construida a partir de señales normalizadas.
- Explicar que el clasificador interpretable re-aprende parcialmente una regla definida y que su valor principal es la explicabilidad.
- Distinguir el índice compuesto de una medición oficial de daño ambiental.
- Identificar la necesidad de respaldo bibliográfico externo para conceptos como riesgo ambiental, priorización territorial, indicadores compuestos, explicabilidad de modelos y uso de datos abiertos en gestión ambiental.
- Evitar afirmar que la base científica ya está completa si la bibliografía no ha sido validada.

Función narrativa:

Dar soporte técnico prudente a la justificación. Esta sección debe convertir la evidencia técnica disponible en argumento comprensible, pero debe conservar las limitaciones metodológicas.

#### 4.5. Aplicación práctica esperada en planeación ambiental

Contenido mínimo esperado:

- Explicar que la salida esperada puede apoyar la identificación de municipios que ameritan revisión prioritaria.
- Indicar que el producto puede aportar a la planeación ambiental en tanto organiza señales abiertas y trazables.
- Presentar la utilidad como potencial analítico sujeto a validación institucional y humana.
- No afirmar impacto real en políticas públicas, adopción institucional, reducción de costos, mejora de eficiencia o resultados de intervención si no existe evidencia.

Función narrativa:

Cerrar la justificación mostrando la utilidad razonable del estudio sin sobreatribuir alcance. La aplicación práctica debe quedar formulada como apoyo a análisis y focalización, no como decisión pública automatizada.

#### 4.6. Condiciones de validez y límites de la justificación

Contenido mínimo esperado:

- Declarar que la priorización se basa en señales disponibles y no en una verdad oficial de riesgo ambiental.
- Señalar que la cobertura, actualización y calidad de las fuentes abiertas condicionan la interpretación.
- Explicar que la ausencia de señal en algunas fuentes no equivale necesariamente a ausencia de riesgo.
- Precisar que la herramienta no prueba causalidad, ilegalidad ni responsabilidad ambiental.

Función narrativa:

Incorporar las limitaciones que afectan materialmente la lectura del producto. Esta sección sí debe aparecer en la narrativa porque condiciona la validez de la justificación.

## 2. MATRIZ DE EVIDENCIA

| Afirmación o tema | Evidencia disponible | Tipo de evidencia | Nivel de certeza | Vacío detectado |
|---|---|---|---|---|
| La presión ambiental considerada incluye minería, deforestación y estrés hídrico. | Documento histórico A1, Parte 4, afirma esos tres componentes; título y objetivos mencionan priorización del riesgo ambiental territorial. | Evidencia histórica del proyecto. | Alta. | Requiere fuentes externas para sustentar relevancia ambiental de cada presión. |
| La presión ambiental se distribuye de forma desigual y requiere focalización basada en evidencia. | Documento histórico A1, Parte 4, lo formula explícitamente. | Evidencia histórica / definición temática. | Media. | Falta evidencia empírica o bibliográfica que demuestre la desigualdad territorial para Colombia. |
| El estudio trabaja a escala municipal nacional. | Documento histórico A1 indica 1.122 municipios; README y model card repiten unidad de análisis municipal; índice congelado exige ámbito municipal. | Evidencia histórica y técnica del proyecto. | Alta. | Validación externa de la cifra y corte DIVIPOLA debe permanecer trazada en fuentes de datos. |
| El producto busca ordenar municipios por riesgo ambiental combinado. | Documento histórico A1, objetivo general y resultados esperados; README describe priorización; build_target.py construye riesgo_score y riesgo_nivel. | Evidencia histórica y código fuente. | Alta. | Hay inconsistencias técnicas sobre componentes y pesos entre build_target.py y MODEL_CARD.md. |
| El índice usa señales normalizadas derivadas de minería, deforestación, fuego, agua y sensibilidad. | build_target.py documenta cinco índices, incluida señal de fuego, y pesos 0.30/0.25/0.15/0.20/0.10. | Código fuente del proyecto. | Alta para la existencia en código. | Inconsistencia con MODEL_CARD.md, que documenta cuatro índices y pesos 0.35/0.30/0.25/0.10. |
| El modelo explicable utiliza XGBoost y SHAP. | train.py y MODEL_CARD.md documentan XGBoost multiclase y SHAP; documento histórico menciona SHAP en objetivos específicos. | Código y documentación técnica. | Alta. | Falta bibliografía validada sobre XGBoost, SHAP e interpretabilidad si se desarrollan como fundamento científico. |
| La exactitud del modelo no debe presentarse como mérito predictivo central. | train.py, README, MODEL_CARD.md y docs/07_limitaciones.md declaran que el modelo re-aprende parcialmente la regla. | Documentación técnica y código. | Alta. | La narrativa final debe evitar vender desempeño predictivo como justificación principal. |
| La reproducibilidad y auditabilidad son criterios relevantes para decisiones públicas. | Documento histórico A1, Partes 4 y 9; README declara reconstrucción y pruebas. | Evidencia histórica y documentación técnica. | Media. | Falta respaldo normativo, institucional o bibliográfico externo sobre exigencias públicas de auditabilidad. |
| El uso de datos abiertos es un fundamento del estudio. | Documento histórico A1, objetivo general y justificación; README y config/data_sources.yaml listan fuentes abiertas. | Evidencia histórica y documentación técnica. | Alta. | Las fuentes oficiales deben validarse bibliográficamente y con URL directa cuando se citen en el documento final. |
| Las fuentes oficiales incluyen ANM, DANE, IDEAM y RUNAP. | README, diccionario_datos.md y config/data_sources.yaml las listan; el histórico incluye datos.gov.co, FIRMS/Sentinel-2, Datos Abiertos Bogotá y RUNAP. | Documentación técnica del proyecto. | Media. | config/data_sources.yaml marca varias fuentes como REQUIERE_VETTING; no todas están igualmente validadas. |
| La herramienta puede apoyar planeación ambiental y focalización. | Documento histórico A1, Parte 4; objetivo general habla de apoyar focalización de atención ambiental. | Definición temática / intención del proyecto. | Media. | Falta evidencia de uso institucional real, impacto en políticas públicas o adopción operacional. |
| La herramienta no prueba causalidad, ilegalidad ni daño ambiental. | README, MODEL_CARD.md, build_target.py y docs/07_limitaciones.md lo declaran. | Documentación técnica y limitaciones. | Alta. | Debe trasladarse a condiciones de validez de la narrativa final. |
| La priorización aporta sostenibilidad. | Documento histórico A1 lo afirma de forma general. | Narrativa histórica. | Baja-media. | Requiere bibliografía o evidencia institucional; no debe quedar como impacto demostrado. |
| La asignación eficiente de recursos es una motivación. | El borrador original lo desarrolla, pero el histórico habla de focalización y planeación, no de eficiencia medida. | Narrativa preliminar. | Baja. | Requiere bibliografía o evidencia institucional; evitar afirmaciones de eficiencia, ahorro o optimización demostrada. |
| Existen beneficios técnicos, sociales y económicos. | Solo aparecen en el borrador original. | Narrativa no sustentada. | Baja. | No hay evidencia localizada; debe eliminarse o reformularse como necesidad pendiente de respaldo. |

## 3. APLICABILIDAD DE PROTOCOLOS

### 00_APLICABILIDAD_PROTOCOLS.md

Estado: APLICA.

Justificación basada en el protocolo:

El protocolo establece que los protocolos ubicados en `PROTOCOLS/` son normas transversales obligatorias y que todo agente debe determinar cuáles aplican antes de producir un artefacto. También define que un documento técnico debe aplicar PEDAT, Separación Narrativa/Evidencia y PRD; PGV-ACG y PGV-MAPAS aplican si hay visuales o mapas; PBF aplica si se usan fuentes.

Exigencia concreta para esta parte:

- Determinar aplicabilidad protocolo por protocolo.
- No declarar cierre tipo PASS si existe incumplimiento material.
- Tratar la Parte 04 como documento técnico sustantivo en construcción, no como texto libre.

### 01_1_PEDAT_PROTOCOLO_EXPANSION_DOCUMENTAL.md

Estado: APLICA.

Justificación basada en el protocolo:

PEDAT aplica cuando se transforman notas, resultados, documentos históricos, código, cifras y evidencia dispersa en documentación técnica extensa, comprensible, rigurosa y trazable. Exige que cada elemento técnico relevante se convierta en unidad explicativa y prohíbe completar vacíos con información plausible presentada como real.

Exigencia concreta para esta parte:

- Expandir conceptos clave como priorización, índice compuesto, explicabilidad, auditabilidad, datos abiertos y limitaciones.
- Clasificar internamente cada afirmación como hecho documentado, inferencia sustentada, interpretación técnica o información no disponible.
- No convertir beneficios genéricos en hechos.
- Indicar cuando la documentación disponible no permite afirmar impacto, causalidad o adopción institucional.

### 01_2_REGLA_DE_SEPARACION_ENTRE_NARRATIVA_Y_EVIDENCIA.md

Estado: APLICA.

Justificación basada en el protocolo:

La regla aplica a todo documento, análisis, informe e interpretación de resultados. Exige separar evidencia, análisis, inferencia y narrativa, y evita que el cuerpo del documento explique archivos consultados, verificaciones o trazabilidad interna.

Exigencia concreta para esta parte:

- La arquitectura narrativa final debe contener solo texto de lector.
- Rutas, archivos, niveles de certeza y vacíos deben ir en matrices o anexos, no en la narrativa principal.
- El capítulo no debe decir "el repositorio indica", "durante la revisión se encontró" ni "el archivo demuestra".
- Solo deben entrar vacíos en el cuerpo si afectan materialmente la interpretación, como ausencia de causalidad o limitaciones de datos.

### 02_PGV_ACG_PROTOCOLO_GOBERNANZA_VISUAL.md

Estado: NO APLICA a la narrativa final prevista; APLICA si se incorporan tablas o figuras en la Parte 04.

Justificación basada en el protocolo:

PGV-ACG aplica a gráficos, tablas, mapas, diagramas, matrices, infografías e imágenes analíticas. La arquitectura narrativa final propuesta para la Parte 04 no requiere visuales en el cuerpo del lector.

Exigencia concreta para esta parte:

- No insertar visuales decorativos.
- Si se decide incluir una tabla de síntesis en el capítulo final, debe tener pregunta analítica, propósito, fuente, título claro y conexión con el texto.
- Las matrices de este benchmark no son narrativa final; si se incorporaran como anexo, deberían seguir reglas de fuente, legibilidad y propósito.

### 03_PGV-MAPAS.md

Estado: NO APLICA a la Parte 04 narrativa propuesta.

Justificación basada en el protocolo:

PGV-MAPAS aplica cuando exista mapa, capa geográfica, cartografía, representación territorial, análisis espacial, isócrona, geometría o visualización geoespacial. La Parte 04 justifica el estudio y no necesita mostrar cartografía para cumplir su función.

Exigencia concreta para esta parte:

- No incluir mapas en la justificación salvo que respondan una pregunta territorial concreta.
- Si se añadiera un mapa para ilustrar distribución territorial, debería documentar fuente, CRS, cobertura, método espacial, simbología, limitaciones e interpretación.
- No usar mapas como decoración o como sustituto de evidencia bibliográfica.

### 04_PRD_PIPELINE_REDACCION_DOCUMENTAL.md

Estado: APLICA.

Justificación basada en el protocolo:

PRD aplica a todo documento sustantivo y exige comprender, inventariar evidencia, diseñar arquitectura, validar cobertura, congelar estructura, planificar módulos, redactar por partes, controlar, integrar y auditar. También prohíbe redactar documentos sustantivos completos en una sola pasada cuando pueden modularizarse.

Exigencia concreta para esta parte:

- Esta entrega debe funcionar como arquitectura documental de la Parte 04, no como redacción final integrada de A1.
- La estructura debe ser jerárquica, lógica, sin repeticiones artificiales y con vacíos de evidencia identificados.
- Antes de redactar la Parte 04 final, debe existir cobertura completa de evidencia y bibliografía por sección.
- No declarar aptitud final del documento A1 solo por producir esta arquitectura.

### 05_PBF_PROTOCOLO_BIBLIOGRAFIA_Y_FUENTES.md

Estado: APLICA.

Justificación basada en el protocolo:

PBF aplica cuando se utilizan fuentes externas, bibliografía, literatura científica, documentación oficial, referencias técnicas, citas, URLs o normas. Exige identificar necesidades bibliográficas antes de buscar fuentes, validar cada fuente y no inventar referencias.

Exigencia concreta para esta parte:

- Construir necesidades bibliográficas por afirmación.
- No inventar literatura sobre riesgo ambiental, priorización, indicadores compuestos, SHAP, XGBoost, gestión pública ambiental ni datos abiertos.
- Separar fundamento bibliográfico de resultado propio.
- Marcar como pendiente cualquier afirmación que requiera fuente externa y aún no tenga fuente validada.

## 4. NECESIDADES BIBLIOGRÁFICAS

| Afirmación que necesita respaldo | Tipo de fuente | Prioridad | Estado actual |
|---|---|---|---|
| La minería, la deforestación y el estrés hídrico son presiones ambientales relevantes para priorización territorial. | Literatura científica, reportes oficiales ambientales, documentos técnicos institucionales. | Alta. | Pendiente; no existe fuente validada en las fuentes inspeccionadas. |
| La distribución desigual de presiones ambientales justifica enfoques territoriales de priorización. | Artículos científicos o reportes oficiales sobre distribución espacial de presión/riesgo ambiental en Colombia o América Latina. | Alta. | Pendiente. |
| La priorización basada en evidencia apoya la focalización de recursos o atención ambiental. | Literatura de política pública ambiental, planeación territorial o gestión de riesgo. | Alta. | Pendiente. |
| Los índices compuestos son una forma válida, con limitaciones, de sintetizar señales heterogéneas para priorización. | Literatura metodológica sobre indicadores compuestos y normalización. | Alta. | Pendiente. |
| La explicabilidad de modelos contribuye a la auditabilidad o interpretación en contextos de decisión pública. | Literatura científica sobre explicabilidad, transparencia algorítmica y ML responsable. | Alta. | Pendiente. |
| SHAP es un método de atribución utilizado para interpretar modelos de machine learning. | Artículo original o documentación técnica validada de SHAP. | Alta. | Pendiente. |
| XGBoost es un algoritmo apropiado para clasificación tabular bajo ciertos supuestos. | Artículo original o documentación técnica oficial; literatura metodológica. | Media. | Pendiente. |
| Los datos abiertos facilitan reproducibilidad y auditoría de productos analíticos públicos. | Documentos oficiales de gobierno abierto, organismos multilaterales o literatura académica. | Alta. | Pendiente. |
| ANM/RUCOM, DANE/DIVIPOLA, IDEAM, RUNAP, FIRMS/Sentinel-2 y Datos Abiertos Bogotá son fuentes oficiales o técnicas pertinentes para los insumos descritos. | Documentación oficial de cada entidad o portal, con URL directa y fecha/corte. | Alta. | Parcial: existen referencias internas en README, diccionario y config; falta validación bibliográfica formal. |
| La ausencia de señal o estación de monitoreo no equivale necesariamente a ausencia de riesgo. | Literatura de monitoreo ambiental, sesgos de cobertura o documentación metodológica de datos ambientales. | Alta. | Pendiente. |
| La salida de AquaBosque debe interpretarse como priorización técnica y no como prueba de causalidad, ilegalidad o daño. | Puede sustentarse con documentación interna; para marco externo, literatura o guías de uso responsable de IA/datos públicos. | Alta. | Internamente validado; externo pendiente si se formula como principio general. |
| La planeación ambiental puede beneficiarse de herramientas geoespaciales e indicadores territoriales. | Literatura de GIS ambiental, planeación ambiental o reportes institucionales. | Media. | Pendiente. |

## 5. EVALUACIÓN DEL BORRADOR ORIGINAL

### Contenido reutilizable

- La estructura inicial reconoce correctamente los cuatro mínimos del índice congelado: impacto ambiental significativo, priorización de recursos, base científica y aplicación práctica.
- La idea de presión ambiental desigual es coherente con el documento histórico.
- La necesidad de priorización basada en evidencia es compatible con el objetivo general histórico.
- La inclusión de explicabilidad, datos abiertos, reproducibilidad y auditabilidad es pertinente.
- La sección de coherencia con el documento histórico contiene una cita útil, aunque en la versión final debería integrarse narrativamente y no como bloque de trazabilidad.
- La mención de limitaciones públicas de replicabilidad y auditabilidad es valiosa, siempre que no se convierta en afirmación normativa sin fuente externa.

### Contenido incorrecto o excesivo

- "Verificación de aceptación" no debe aparecer en la narrativa de lector; corresponde a control interno.
- "Fundamento técnico del proyecto" redactado con rutas de código no debe ir en el cuerpo narrativo.
- "Fuentes oficiales de datos ambientales" está demasiado cerca de inventario de evidencia y debe ir principalmente en Parte 08 o en anexos/fuentes, salvo una mención sintética.
- "Estudios previos sobre impacto ambiental" enumera literatura inexistente o no validada; no debe redactarse como si ya existiera bibliografía.
- "Beneficios esperados" sobreatribuye impactos técnicos, sociales y económicos sin evidencia.
- "Contexto del problema ambiental" introduce desafíos globales y regionales que no están sustentados por las fuentes inspeccionadas.
- "Enfoque innovador" declara innovación sin comparación validada.
- El borrador mezcla justificación temática, evidencia técnica, fuentes de datos, validación, beneficios y contexto general sin jerarquía documental suficiente.

### Afirmaciones no sustentadas

- Que los recursos ambientales, financieros, humanos y tecnológicos son limitados en el contexto institucional concreto.
- Que sin priorización los recursos pueden ser malinvertidos.
- Que la priorización permite asignación equitativa de recursos.
- Que el proyecto mejora políticas públicas o respuestas ante emergencias ambientales.
- Que existen estudios previos específicos sobre distribución espacial de impactos que respaldan el caso.
- Que el proyecto reduce costos de intervención o mejora rendimiento de inversiones.
- Que el enfoque es innovador frente a alternativas comparables.
- Que existe aplicación directa en políticas públicas, más allá de potencial apoyo analítico.
- Que las fuentes ANM, IDEAM, NASA o IDIGER respaldan por sí mismas "impacto ambiental" sin validación específica de contenido.

### Elementos faltantes

- Separación explícita entre hechos del proyecto, inferencias técnicas y afirmaciones que requieren bibliografía.
- Condiciones de validez y límites dentro de la narrativa final.
- Reconocimiento de la inconsistencia detectada entre documentación técnica sobre número de índices y pesos del riesgo.
- Matriz bibliográfica previa a cualquier afirmación científica o de política pública.
- Evidencia externa validada para conceptos de riesgo ambiental, priorización, explicabilidad, datos abiertos y planeación ambiental.
- Tratamiento prudente de la utilidad práctica como apoyo a revisión humana, no como decisión automatizada.
- Relación más clara entre la Parte 04 y las demás partes: fuentes de datos detalladas deben quedar en Parte 08; resultados esperados en Parte 10; supuestos y riesgos en Partes 11 y 12.

## 6. READINESS

PARTIAL

Justificación:

La arquitectura narrativa de la Parte 04 puede definirse con base suficiente porque el índice congelado fija el propósito, contenidos mínimos, evidencia requerida y criterios de aceptación, y el documento histórico aporta el núcleo argumental de la justificación. También existe soporte técnico interno para priorización municipal, explicabilidad, reproducibilidad y límites de uso.

Sin embargo, la Parte 04 no está lista para redacción final completa ni para cierre documental porque faltan fuentes bibliográficas validadas para varias afirmaciones centrales, especialmente impacto ambiental, priorización territorial, base científica, utilidad en política pública, datos abiertos, indicadores compuestos y explicabilidad. Además, existe una inconsistencia técnica material entre build_target.py y MODEL_CARD.md sobre componentes y pesos del índice, que debe resolverse antes de congelar una versión final.

El estado no es BLOCKED porque la arquitectura puede entregarse y orientar la siguiente fase. El estado no es READY porque los protocolos PEDAT, Separación Narrativa/Evidencia, PRD y PBF impiden declarar suficiencia final mientras existan vacíos bibliográficos, afirmaciones no sustentadas y una contradicción técnica relevante.
