# ZOOM BOGOTÁ V1 — ESTADO RELEASE CANDIDATE (bloqueo estructural)

RELEASE_ID: zoom-bogota-v1-rc-wip · COMMIT: rama `feature/zoom-bogota-rc-v1`
Evidencia machine-readable: `config/release_zoom_bogota_v1.yaml`, `outputs/rc_v1/rc_metrics.json`,
`outputs/rc_v1/baselines_ablation_controls.csv`, `outputs/rc_v1/geospatial_crs_error.json`,
`outputs/rc_v1/gold_localidad_dia.csv`. Reproducible: `PYTHONHASHSEED=0 ./venv/bin/python scripts/rc/build_and_validate.py`.

> Se entrega este informe intermedio porque, conforme a la Regla 3/80, se encontró un
> **bloqueo estructural** (dato fuente inválido + producto predictivo sin sustento).

## CONTRATO (congelado — config/release_zoom_bogota_v1.yaml)
- Target: evento remoción/inundación en **[t+1, t+3]** (estrictamente futuro; el día t NO cuenta).
- Momento de predicción: cierre del día t. Features con fecha ≤ t.
- Resolución estadística: **localidad-día**. UPZ = solo priorización, no probabilidad.
- Producto (decisión Opción A): índice de susceptibilidad territorial + escenario de lluvia etiquetado; **no** probabilidad predictiva calibrada.

## CAPA 1 — DATA
| Control | Estado | Evidencia |
|---|---|---|
| TEMPORAL_INTEGRITY | **PASS** | target [t+1,t+3] + embargo 3d; control shuffle sin monotonía = 0.458 (≈azar) |
| DATA_LEAKAGE (temporal) | **PASS** | mismo control |
| TARGET_VALIDITY | **PASS** | regex tipos, dedup día-localidad, ventana futura explícita |
| SUFFICIENCY | Cuantificado | pos: train 853 / calib 190 / test 455; prevalencia 0.059 / 0.080 / 0.063 |
| REPRESENTATIVENESS | WARNING | calib (sep–dic 2023) más húmedo → prevalencia 0.080 > test 0.063 (label shift estacional) |
| **GEOSPATIAL_INTEGRITY** | **FAIL (crítico)** | método afín de bbox para POT→localidad: **error mediana 57 km, máx 75 km** (geospatial_crs_error.json) |
| DATA_TRACEABILITY | PARCIAL | contrato+config+bronze con hash; falta source_registry/field_lineage formal |

**DATA_APPROVED = FAIL** — la feature territorial dominante (`score_remocion`) está asignada a
localidades con ~57 km de error. Es espacialmente inválida. Por la Regla 21 **no se optimiza el
modelo para compensar el dato**.

## CAPA 2 — MODEL (revalidación honesta, test 2024)
| Métrica | Valor |
|---|---|
| ROC-AUC | **0.735** (IC95 0.67–0.78) |
| PR-AUC | **0.163** (base 0.063) |
| Brier (calibrado) | 0.057 · trivial(prev train) 0.059 → **Brier Skill Score 0.035** |
| Recall @naranja (umbral desde calib) | **17%** · rojo inalcanzable |

Ablation: M6 completo 0.735 **≤** territorio-solo 0.740 ≈ localidad-solo 0.741. Lluvia sola 0.601.
Controles: shuffle sin monotonía 0.458 (limpio); con monotonía 0.705 (prior espurio → el 0.793 del
modelo monótono NO es habilidad).

| Control Capa 2 | Estado |
|---|---|
| BASELINES / NEGATIVE_CONTROLS / UNCERTAINTY | PASS (ejecutados, IC por bootstrap de bloque) |
| CALIBRATION | PASS (isotónica en calib) pero BSS 0.035 (marginal) |
| **PREDICTIVE_VALUE** | **FAIL** (no supera al baseline territorial) |
| **OPERATIONAL_UTILITY** | **FAIL** (recall 17%, rojo inalcanzable) |

**MODEL_APPROVED = FAIL.**

## CAPA 3 / CAPA 4
**NO INICIADAS** — por el gating de la Regla 4 (no se declara PRODUCT/TRACEABILITY si MODEL≠PASS).
Trabajo preparado: contrato+config (Sec 5/23), bronze con hash (Sec 7), pipeline reproducible.

## LIMITACIONES REALES (materiales)
1. La feature territorial (`score_remocion`) es espacialmente inválida (CRS afín, ~57 km).
2. `score_agua` y demás capas de `bogota_zoom.csv` provienen del mismo tipo de proceso → sospechosas de igual defecto.
3. Sin la señal territorial válida, la lluvia sola no tiene habilidad predictiva útil (ROC 0.601).
4. Calibración marginal (BSS 0.035): no procede mostrar porcentajes como probabilidad interpretable.
5. Muestra escasa de positivos por localidad/mes → validación por territorio limitada.
6. CRS local de Bogotá no etiquetado en la fuente; se identificó (~96% in-bbox) pero falta la definición autoritativa IDECA para asignación fina.

## VEREDICTO: **NOT READY FOR FINAL REVIEW**
OVERALL RELEASE = FAIL (DATA FAIL + MODEL FAIL).

## Camino para una RC válida (Opción A, honesta)
1. **Reconstruir la capa territorial con georreferenciación correcta:** (a) refinar el CRS local de Bogotá a los parámetros autoritativos de IDECA y reasignar polígonos POT con pyproj (transformación geodésica), o (b) usar la **geocodificación por localidad de la Bitácora IDIGER** (autoritativa, sin CRS) para un índice **descriptivo** de densidad histórica de emergencias. Regenerar `score_remocion`/`score_agua` con test de puntos conocidos y error en metros.
2. Rehacer `bogota_zoom.csv` bajo el mismo estándar (todas las capas con CRS validado).
3. Reejecutar Capa 1+2 completas sobre el dato corregido.
4. Solo si DATA_APPROVED=PASS y (bajo Opción A) el índice territorial queda validado espacialmente, continuar a Capa 3 (producto: índice + escenario de lluvia etiquetado, UPZ = priorización) y Capa 4 (source registry, lineage, run manifest, tests de regresión de los hallazgos, clean-room).
