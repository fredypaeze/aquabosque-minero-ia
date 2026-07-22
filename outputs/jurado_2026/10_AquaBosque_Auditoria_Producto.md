# Auditoría del producto AquaBosque Minero IA

## Qué se verificó
- App desplegada en `https://streamlit.spartanit.pro/` con portada y páginas internas auditadas el 22-jul-2026.
- Repositorio local `/home/tuxilo/aquabosque-minero-ia` en commit `4f9989f`.
- Pipeline, artefactos, métricas y pruebas del estado actual del código.

## Hallazgos principales
- El producto vigente **sí está desplegado** y expone mapa, ranking, ficha territorial, explicabilidad, datos abiertos y metodología.
- La IA vigente es **XGBoost multiclase + SHAP**, no un detector de anomalías.
- La priorización usa una **etiqueta técnica compuesta por cuantiles**: `0.35·minero + 0.30·deforestación + 0.25·hídrico + 0.10·sensibilidad`.
- El repo pasa **16/16 pruebas**.
- Distribución verificada: **57 críticos, 112 altos, 281 medios, 672 bajos**.

## Cobertura real del dataset usado por el MVP
- Municipios base: `1.122`.
- Minería formal con señal: `667` municipios.
- Deforestación con señal: `75` municipios.
- Agua ICA con estación asociada: `71` municipios.
- RUNAP con señal: `505` municipios.
- PDET: `170` municipios.

## Contradicciones que había que corregir antes del deck
1. **Anomalías vs. clasificación**: el prompt de trabajo hablaba de detección de anomalías en tiempo real, pero el código, la app y la documentación vigente muestran XGBoost multiclase + SHAP sobre una etiqueta técnica.
2. **5 fuentes vs. 7 fuentes**: la portada viva y el README hablan de 5 fuentes oficiales integradas; algunos documentos (`docs/00_resumen_ejecutivo.md`, `docs/09_defensa_jurado.md`) dicen 7 al contar activos territoriales de soporte (`DIVIPOLA`, `PDET`) como fuentes separadas.
3. **Tiempo real**: la metodología viva niega tiempo real; agua usa observaciones con `fechamuestra` visible entre 2002 y 2018, y deforestación usa cortes 2017-2021.
4. **Cobertura satelital**: no existe un procesamiento satelital operacional nacional en la versión actual; la señal de bosque llega desde un FeatureServer municipal ya resumido.

## Documentos que conviene archivar o corregir
- `docs/00_resumen_ejecutivo.md`: unificar conteo de fuentes y evitar ambigüedad entre “5” y “7”.
- `docs/09_defensa_jurado.md`: mismo ajuste; además reemplazar cualquier lectura que el jurado pudiera interpretar como superioridad predictiva.
- Prompt o borradores externos que hablen de **anomalías**, **satélite en tiempo real** o **monitoreo nacional en vivo**.

## Posicionamiento defendible
- MVP funcional de inteligencia territorial ambiental.
- Integra datos abiertos reales a nivel municipal.
- Usa IA explicable para hacer operativa una priorización interpretable.
- No prueba causalidad, no sanciona y no detecta minería ilegal.
