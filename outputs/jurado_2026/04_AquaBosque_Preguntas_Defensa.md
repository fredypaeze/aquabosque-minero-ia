# Preguntas y respuestas para la defensa

## 1. ¿Dónde está realmente la inteligencia artificial?
En el clasificador XGBoost multiclase que toma 13 variables municipales y asigna uno de cuatro niveles de priorización. SHAP explica qué factores pesan en cada clasificación.

## 2. ¿Por qué se utilizó ese modelo?
Porque el producto actual no tiene etiquetas oficiales de “riesgo ambiental” por municipio. XGBoost permite convertir una priorización técnica en un modelo reproducible e interpretable, y SHAP hace visible el peso de cada variable.

## 3. ¿Qué diferencia existe entre el ranking y la anomalía?
En la versión vigente no hay un módulo activo de anomalías. Lo que existe es un score técnico de priorización y una clasificación XGBoost que lo hace operativo y explicable.

## 4. ¿Cómo se valida una alerta?
No se presenta como alerta automática confirmada. La salida sirve para decidir dónde revisar primero con análisis experto y validación ambiental adicional.

## 5. ¿Una anomalía significa contaminación?
No aplica al producto actual. Incluso en la dimensión hídrica, una señal estadística o un ICA bajo no prueba contaminación causal; solo prioriza revisión.

## 6. ¿El producto detecta minería ilegal?
No. Usa minería formal observada en RUCOM y señales ambientales/territoriales. Sirve para focalizar revisión, no para declarar ilegalidad.

## 7. ¿El sistema funciona actualmente en tiempo real?
No. La metodología viva y la auditoría muestran actualización periódica según la frecuencia real de publicación de cada fuente.

## 8. ¿Qué parte ya está construida?
Descarga o consumo de fuentes, integración municipal, construcción de variables, entrenamiento del modelo, métricas, SHAP y aplicación desplegada.

## 9. ¿Qué parte se escalaría si el proyecto gana?
Automatización de cortes, históricos temporales, reentrenamiento, validación con expertos, mejoras de demo y alertas/reportes operacionales.

## 10. ¿Cómo se actualizarían las fuentes?
Reejecutando los scripts de descarga y preparación o sustituyéndolos por tareas automatizadas según la periodicidad de cada fuente.

## 11. ¿Qué pasa cuando un municipio no tiene datos?
Se mantiene la fila municipal y se documenta la ausencia. En agua, por ejemplo, sin estación asociada el índice hídrico observado se deja en 0 y se marca la ausencia de dato.

## 12. ¿Cómo se evita generar falsas conclusiones?
Separando explícitamente priorización de causalidad, mostrando limitaciones por fuente y manteniendo trazabilidad de cada variable.

## 13. ¿Cómo puede utilizarlo una entidad pública?
Como tablero de focalización territorial para ordenar revisión técnica, cruces interinstitucionales y priorización de recursos de monitoreo.

## 14. ¿Por qué se considera un producto avanzado?
Porque no es una idea: integra múltiples fuentes reales, produce resultados reproducibles, tiene explicabilidad y está desplegado.

## 15. ¿Cómo puede ampliarse hacia Amazonía y Pacífico?
Automatizando cortes, ampliando coberturas geográficas y sumando nuevas fuentes con la misma lógica territorial municipal o submunicipal.

## 16. ¿Cómo se garantiza trazabilidad?
Cada afirmación del deck quedó vinculada a archivos, scripts, capturas o artefactos de salida en las tablas de evidencias.

## 17. ¿Cómo se asegura la interpretabilidad?
Con SHAP global y por caso, además de variables crudas visibles en ranking y ficha.

## 18. ¿Qué diferencia a AquaBosque de un tablero tradicional?
No solo visualiza datos: los integra, normaliza, prioriza y explica el peso relativo de cada señal.

## 19. ¿Qué decisiones puede apoyar?
Dónde revisar primero, dónde cruzar análisis de agua y minería, y qué municipios requieren seguimiento reforzado.

## 20. ¿Qué evidencia demuestra que no es solo una idea?
App desplegada, repo reproducible, métricas guardadas, capturas auditadas, archivos de salida y 16 pruebas pasando.
