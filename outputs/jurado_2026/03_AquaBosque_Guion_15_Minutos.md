# Guion de exposición de 15 minutos

## Diapositiva 1. AquaBosque Minero IA
- Objetivo: Abrir con una imagen real del producto y fijar que estamos mostrando un MVP existente.
- Duración máxima: 0:30
- Texto sugerido: AquaBosque Minero IA ya está desplegado y convierte datos ambientales dispersos en una priorización territorial interpretable. Lo que van a ver hoy no es un mockup: es un MVP funcional auditado sobre la app viva y el código real.
- Mensaje para el jurado: El producto existe y ya valida la cadena técnica principal.
- Transición: Después de mostrar que el producto existe, paso al problema que resuelve.
- Posibles preguntas:
  - ¿Está desplegado hoy? → Sí. Se auditó la URL pública y se tomaron capturas de la versión activa.

## Diapositiva 2. El Problema
- Objetivo: Explicar que el cuello no es la ausencia total de datos sino su dispersión.
- Duración máxima: 1:00
- Texto sugerido: El problema no es solamente tener datos; es convertirlos en señales territoriales comparables para actuar. Hoy la cobertura varía por fuente y eso dificulta priorizar recursos institucionales.
- Mensaje para el jurado: La propuesta nace de un problema de integración y priorización, no de falta absoluta de datos.
- Transición: Con el problema claro, muestro qué resuelve exactamente el MVP.
- Posibles preguntas:
  - ¿Por qué municipal y no otra unidad? → Porque el municipio permite integrar todas las fuentes abiertas actuales con una unidad comprensible para política pública.

## Diapositiva 3. La Propuesta
- Objetivo: Presentar AquaBosque como solución concreta y acotada al estado real del producto.
- Duración máxima: 1:00
- Texto sugerido: AquaBosque no reemplaza la validación ambiental. Lo que hace es integrar señales dispersas, priorizarlas y explicar por qué un territorio aparece arriba en la lista de revisión.
- Mensaje para el jurado: El MVP ya comprueba que la cadena técnica funciona de punta a punta.
- Transición: Ahora bajo a las fuentes reales que alimentan esa cadena.
- Posibles preguntas:
  - ¿Qué parte es IA y qué parte es integración? → La integración construye variables e índices; la IA clasifica y explica la priorización.

## Diapositiva 4. Datos Abiertos Integrados
- Objetivo: Mostrar qué fuentes son reales, qué cobertura tienen y cómo entran al sistema.
- Duración máxima: 1:00
- Texto sugerido: Aquí es importante ser precisos: la portada viva habla de cinco fuentes núcleo, pero el trabajo completo usa además DIVIPOLA y PDET como soportes territoriales. Por eso el deck distingue claramente entre dimensión ambiental y activo de integración.
- Mensaje para el jurado: La trazabilidad de fuentes es uno de los puntos fuertes del MVP.
- Transición: Con las fuentes claras, explico cómo se vuelven comparables a nivel municipal.
- Posibles preguntas:
  - ¿Por qué aparece a veces 5 y a veces 7 fuentes? → Cinco son dimensiones núcleo; DIVIPOLA y PDET son activos de soporte para integración y sensibilidad territorial.

## Diapositiva 5. Construcción De La Unidad Territorial
- Objetivo: Explicar la lógica territorial y el manejo de datos faltantes.
- Duración máxima: 1:00
- Texto sugerido: El MVP resuelve la comparabilidad territorial con una regla simple y auditable. La base es municipal, y las fuentes que no traen código DANE se asignan por proximidad al centroide, sin esconder esa simplificación.
- Mensaje para el jurado: La integración municipal es la pieza que hace posible comparar señales heterogéneas.
- Transición: Sobre esa base se monta la IA vigente y su forma correcta de narrarla.
- Posibles preguntas:
  - ¿Se hace intersección poligonal completa? → No en todas las fuentes. Para RUNAP e ICA el MVP usa centroide/proximidad como aproximación explícitamente documentada.

## Diapositiva 6. Cómo Funciona La IA
- Objetivo: Alinear el discurso con la implementación real y evitar sobredeclaraciones.
- Duración máxima: 1:30
- Texto sugerido: Aquí hay que ser transparentes: la versión actual no usa un detector de anomalías. Usa XGBoost para volver operativa una priorización técnica y SHAP para explicar cada caso. Esa honestidad fortalece, no debilita, la defensa.
- Mensaje para el jurado: La IA sí existe, pero su valor hoy está en interpretabilidad y operatividad, no en vender una accuracy descontextualizada.
- Transición: Con el modelo claro, muestro cómo se traduce en una lectura territorial entendible.
- Posibles preguntas:
  - ¿Por qué no hablan de anomalías? → Porque el producto vigente no las implementa. La auditoría obliga a defender la IA realmente activa.

## Diapositiva 7. Priorización E Interpretabilidad
- Objetivo: Bajar la IA a un caso concreto que una autoridad pueda entender.
- Duración máxima: 1:00
- Texto sugerido: Para la defensa conviene un municipio con varias señales a la vez. Barrancabermeja sirve porque no depende solo de deforestación o solo de minería: combina presión minera formal, una señal hídrica observada y alta sensibilidad territorial.
- Mensaje para el jurado: La salida del MVP es accionable porque combina ranking con explicación.
- Transición: Después del caso, enseño la aplicación real donde esto se consulta.
- Posibles preguntas:
  - ¿Por qué no usan Orito como caso? → Orito es muy fuerte en minería y bosque, pero Barrancabermeja muestra además señal hídrica y ayuda a explicar más dimensiones a la vez.

## Diapositiva 8. Capa Satelital · Monitoreo Near-Real-Time
- Objetivo: Mostrar que la solución ya incorpora imágenes satelitales y monitoreo near-real-time, no solo datos estáticos.
- Duración máxima: 1:30
- Texto sugerido: Aquí subimos de nivel: además del índice, integramos una capa satelital que se actualiza a diario. Los focos de calor son el proxy estándar de la frontera de deforestación y quema. Lo potente es la fusión: donde el modelo prioriza y el satélite confirma fuego hoy, la autoridad tiene su máxima prioridad de verificación. Y sobre imágenes crudas de Sentinel-2 corremos deep learning en la infraestructura GPU del Ministerio.
- Mensaje para el jurado: La solución ya no es estática: incorpora satélite y near-real-time, con soberanía de datos.
- Transición: Con la capacidad satelital demostrada, muestro la aplicación funcional donde todo se consulta.
- Posibles preguntas:
  - ¿Es tiempo real de verdad o promesa? → La capa de focos FIRMS es real y diaria, ya integrada. Sobre Sentinel-2 corremos detección de deforestación con deep learning en nuestras GPU L40S; lo presentamos según su estado de validación, sin sobredeclarar.

## Diapositiva 9. Capa Satelital · Deforestación con Sentinel-2 (GPU)
- Objetivo: Demostrar procesamiento real de imagen satelital cruda sobre GPU propia, con soberanía de datos.
- Duración máxima: 1:30
- Texto sugerido: Esta es la capa de imagen cruda: bajamos escenas Sentinel-2 de dos fechas y detectamos dónde el bosque cayó, midiendo hectáreas. Lo corrimos en la máquina de las L40S del Ministerio, así que la imagen y el resultado nunca salen del Estado. Es la base sobre la que el segmentador U-Net de deep learning eleva la precisión.
- Mensaje para el jurado: Ya procesamos imagen satelital de 10 m sobre GPU pública propia; no es teoría.
- Transición: Con las dos capas satelitales demostradas, muestro la aplicación funcional.
- Posibles preguntas:
  - ¿Ya usa deep learning o solo índices? → El resultado mostrado es detección de cambio NDVI sobre imagen real, corriendo en el host de las L40S. El segmentador U-Net (deep learning en GPU) es el siguiente paso de la misma capa, ya con el pipeline montado.

## Diapositiva 10. IA Generativa Soberana · Asistente
- Objetivo: Mostrar la capa de IA generativa soberana como diferenciador: frontera tecnológica sin exponer el dato del Estado.
- Duración máxima: 1:30
- Texto sugerido: Aquí está el diferenciador de frontera: un asistente de IA generativa que corre en NUESTRA infraestructura de GPU, no en una nube externa. Cualquier funcionario o ciudadano puede preguntarle al sistema y recibe una respuesta aterrizada en la evidencia, con soberanía total del dato. Es exactamente el tipo de IA que el concurso premia, hecha de forma responsable para lo público.
- Mensaje para el jurado: Tenemos IA generativa de frontera corriendo en infraestructura pública propia, con soberanía del dato.
- Transición: Con las tres capas de IA mostradas, paso a la aplicación funcional donde todo se consulta.
- Posibles preguntas:
  - ¿Usan ChatGPT / una nube externa? → No. Usamos modelos abiertos (Llama, Qwen) alojados en las L40S del Ministerio. El dato nunca sale de la infraestructura del Estado — un requisito clave en lo público.

## Diapositiva 11. La Aplicación Funcional
- Objetivo: Dejar evidencia visual de que la app existe y está navegable.
- Duración máxima: 1:00
- Texto sugerido: Esta diapositiva ayuda a cerrar cualquier duda de implementación: no estamos hablando de wireframes, sino de páginas activas que muestran resultados, explicación y fuente de datos.
- Mensaje para el jurado: El jurado debe ver que el MVP ya se usa como producto, no solo como notebook.
- Transición: Luego muestro cómo se haría la demo en menos de dos minutos.
- Posibles preguntas:
  - ¿Se puede mostrar en vivo? → Sí, pero además dejamos respaldo offline por si falla la conexión.

## Diapositiva 12. Demostración Del Producto
- Objetivo: Preparar una demo robusta y corta para la exposición.
- Duración máxima: 1:00
- Texto sugerido: La idea no es navegar todo el sistema, sino mostrar valor rápido: cobertura nacional, lectura territorial, explicación del modelo y salida exportable. Todo eso cabe en menos de dos minutos.
- Mensaje para el jurado: La demo debe vender utilidad institucional, no detalles de programación.
- Transición: Con la demo clara, paso a un caso institucional concreto.
- Posibles preguntas:
  - ¿Qué pasa si el mapa en vivo tarda? → Se usa el respaldo offline del paquete y se mantiene la secuencia narrativa.

## Diapositiva 13. Caso De Uso Institucional
- Objetivo: Conectar el MVP con una decisión pública concreta.
- Duración máxima: 1:30
- Texto sugerido: La pregunta institucional no es si el modelo sentencia algo, sino si ayuda a usar mejor el tiempo técnico. Un municipio crítico como Barrancabermeja sirve para ordenar revisión hídrica, cruce con actividad minera y sensibilidad territorial.
- Mensaje para el jurado: AquaBosque apoya decisiones de priorización; no suplanta la validación ambiental.
- Transición: Después del caso, cierro mostrando qué queda realmente validado por el MVP.
- Posibles preguntas:
  - ¿Qué haría una autoridad después de ver este caso? → Cruzar con inspección, seguimiento hídrico, expedientes y otras bases sectoriales antes de concluir.

## Diapositiva 14. Qué Valida El MVP
- Objetivo: Sintetizar la evidencia técnica sin convertirla en checklist de concurso.
- Duración máxima: 1:00
- Texto sugerido: Lo que el MVP ya valida es suficiente para una defensa seria: integración de fuentes reales, priorización interpretable, app funcional y capacidad de regenerar evidencias. Lo que no valida todavía se declara sin maquillaje.
- Mensaje para el jurado: El jurado debe concluir que hay sustancia técnica y honestidad metodológica.
- Transición: Con eso puesto, la ruta de escalamiento se vuelve creíble y no aspiracional.
- Posibles preguntas:
  - ¿Por qué esa honestidad importa? → Porque evita sobreprometer y hace más confiable el producto frente a un jurado técnico.

## Diapositiva 15. Escalamiento
- Objetivo: Mostrar una ruta de crecimiento sensata, no inflada.
- Duración máxima: 1:30
- Texto sugerido: Si el proyecto gana, el salto lógico no es rehacerlo todo, sino automatizar lo que ya funciona, ampliar cobertura y llevar la priorización a un uso operativo más estable con instituciones.
- Mensaje para el jurado: El escalamiento parte de una base validada, no de una idea en PowerPoint.
- Transición: Después del roadmap cierro con impacto potencial y mensaje final.
- Posibles preguntas:
  - ¿Por qué no prometen cobertura total inmediata? → Porque el producto todavía depende de coberturas y periodicidades reales de cada fuente, y eso es mejor decirlo explícitamente.

## Diapositiva 16. Impacto Potencial
- Objetivo: Traducir la solución en valor público sin inventar cifras de impacto.
- Duración máxima: 1:00
- Texto sugerido: El impacto potencial aquí es cualitativo pero concreto: ordenar mejor la revisión institucional, aprovechar datos públicos dispersos y crear una base escalable para ecosistemas estratégicos sin esperar a una plataforma perfecta desde el día uno.
- Mensaje para el jurado: El producto puede apoyar decisiones públicas porque transforma dispersión en señal territorial.
- Transición: Cierro con el mensaje síntesis y los accesos para revisar demo y repo.
- Posibles preguntas:
  - ¿Qué diferencia esto de un tablero tradicional? → Que no solo exhibe fuentes: las integra, prioriza y explica la lectura territorial resultante.

## Diapositiva 17. Cierre
- Objetivo: Cerrar con una tesis simple y con accesos directos a demo y repo.
- Duración máxima: 0:30
- Texto sugerido: AquaBosque Minero IA ya demuestra que datos ambientales dispersos pueden convertirse en señales territoriales interpretables. El siguiente paso no es inventar más narrativa, sino escalar esta capacidad validada hacia un uso operacional más robusto.
- Mensaje para el jurado: No es una maqueta; es un MVP serio con ruta clara de evolución.
- Transición: Fin de la presentación.
- Posibles preguntas:
  - ¿Dónde pueden revisar el producto? → En la URL pública y en el repositorio referenciado por los QR de cierre.
