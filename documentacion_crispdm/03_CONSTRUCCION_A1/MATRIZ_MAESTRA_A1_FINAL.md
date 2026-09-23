# MATRIZ MAESTRA A1 FINAL

| Numero | Parte | Subapartados narrativos | Vacios | Contradicciones | PBF pendiente | Readiness |
|---:|---|---|---|---|---|---|
| 1 | Titulo del estudio | Titulo del estudio; subtitulo o descriptor opcional | Sin vacio material para titulo | No material; solo precision entre "IA explicable" y componentes complementarios | No | READY |
| 2 | Objetivo general | Enunciado del objetivo general; alcance del objetivo | Falta sustento externo para "apoyar focalizacion" como valor publico | No demostrar impacto institucional; Bogota no debe mezclarse con componente nacional | Si: priorizacion basada en evidencia y datos abiertos | PARTIAL |
| 3 | Objetivos especificos | Objetivos del componente nacional; objetivos de componentes complementarios | Falta cerrar bibliografia SHAP/FIRMS/dNBR; falta reconciliar dNBR vs FIRMS | Codigo actual usa fuego e indices/pesos distintos a model card historica; Bogota predictivo reclasificado como descriptivo | Si: SHAP, FIRMS, dNBR/Sentinel | PARTIAL |
| 4 | Justificacion | Necesidad de lectura integrada; valor publico de explicabilidad/reproducibilidad; utilidad delimitada de complementarios | Falta bibliografia oficial/cientifica para presion desigual, valor publico e impacto | README declara fuentes verificadas; config conserva varias en vetting; beneficios del borrador no sustentados | Si: alta prioridad | BLOCKED |
| 5 | Problema analitico | Problema central; dos tareas que no deben confundirse; condiciones de interpretacion | Falta soporte externo de indice compuesto y limites de datos abiertos | Indice construido no es resultado observado independiente; Bogota predictivo no aprobado | Si: indice compuesto, SHAP/no causalidad | PARTIAL |
| 6 | Preguntas de investigacion | Preguntas nacional; incendios; Bogota; reproducibilidad | Preguntas de incendios y Bogota dependen de estado final de componentes | Historico pregunta por dNBR/alerta predictiva; evidencia actual valida FIRMS y reencuadra Bogota | Si: metodos satelitales y alerta temprana | PARTIAL |
| 7 | Alcance | Alcance nacional; incendios; Bogota; exclusiones y limites | Falta fuente oficial DANE y validacion externa de fuentes geoespaciales/satelitales | Historico dice dNBR; evidencia productiva muestra FIRMS y Sentinel en construccion; Bogota no generalizable | Si: DANE, NASA FIRMS, Sentinel/dNBR, IDIGER/SAB/IDECA | PARTIAL |
| 8 | Fuentes de datos | Fuentes nacionales; satelitales; Bogota; disponibilidad y limitaciones | Varias fuentes aun requieren validacion formal; estados internos no son homogeneos | README "5/5 verificadas" vs data_sources con REQUIERE_VETTING/GEOESPACIAL/PARCIAL_LOCAL | Si: todas las fuentes oficiales | PARTIAL |
| 9 | Viabilidad | Viabilidad nacional; satelital; Bogota; condiciones de viabilidad | No se verifico reconstruccion end-to-end ni disponibilidad GPU directa; bibliografia pendiente | Script/metricas antiguas de Bogota vs RC vigente FAIL predictivo; GPU historico/runbook no equivale a ejecucion validada | Si: viabilidad datos abiertos, satelital, IA responsable | PARTIAL |
| 10 | Resultados esperados | Nacional; incendios; Bogota; reproducibilidad/auditabilidad | Falta decidir redaccion final de dNBR/Sentinel; falta reconciliar conteos | Conteo README 672/281/112/57 vs archivo actual 673/280/112/57; Bogota predictivo esperado vs no aprobado | Si: SHAP, visualizacion, fuentes satelitales/urbanas | PARTIAL |
| 11 | Supuestos iniciales | Datos; indice nacional; complementarios; uso | Supuestos metodologicos requieren respaldo y validacion | Pesos/variables difieren entre documentacion y codigo; IDIGER valida etiqueta historica pero predictivo no aprobado | Si: cuantiles, datos administrativos, sesgo de reporte | PARTIAL |
| 12 | Riesgos y limitaciones | Interpretacion; datos; metodologia; componentes complementarios | Falta soporte bibliografico para no causalidad/limitaciones SHAP/FIRMS | Historico/metricas antiguas vs contrato Bogota; dNBR historico vs FIRMS actual | Si: alta prioridad para SHAP/no causalidad y satelital | PARTIAL |

## Conteo de readiness

| READY | PARTIAL | BLOCKED |
|---:|---:|---:|
| 1 | 10 | 1 |

## Contradicciones materiales detectadas

| ID | Contradiccion material | Partes afectadas |
|---|---|---|
| C01 | La documentacion/model card historica del componente nacional describe 4 indices y pesos 0.35/0.30/0.25/0.10; el codigo actual incorpora `idx_fuego` y pesos 0.30/0.25/0.15/0.20/0.10. | 2, 3, 5, 10, 11, 12 |
| C02 | El README reporta distribucion de niveles Bajo 672, Medio 281, Alto 112, Critico 57; los archivos tecnicos actuales reportan Bajo 673, Medio 280, Alto 112, Critico 57. | 3, 10 |
| C03 | El documento historico plantea incendios como area quemada por dNBR; la evidencia tecnica actual consolidada muestra FIRMS como senal NRT/proxy y Sentinel-2/dNBR como capacidad/runbook o componente condicionado, no como producto nacional cerrado. | 3, 6, 7, 10, 12 |
| C04 | El documento historico y scripts antiguos describen Bogota como alerta temprana predictiva; el PRODUCT_CONTRACT y VALIDATION_REPORT vigentes indican que el producto V1 es descriptivo y que el componente predictivo no esta aprobado para uso operativo. | 3, 5, 6, 7, 9, 10, 11, 12 |
| C05 | La documentacion general presenta fuentes integradas como verificadas; `config/data_sources.yaml` conserva estados REQUIERE_VETTING, GEOESPACIAL y PARCIAL_LOCAL para varias fuentes. | 4, 8, 9, 12 |
| C06 | El historico menciona capacidad de computo/GPU para capas satelitales; la evidencia localizada es un runbook/capacidad planificada, no una validacion directa de ejecucion GPU productiva en esta reconstruccion. | 9 |
