# Model Card — Zoom Bogotá V1

Fuente de verdad: `outputs/rc_v1/rc_metrics.json`, `validation/validation_results.json`
(reproducible: `PYTHONHASHSEED=0 ./venv/bin/python scripts/rc/build_and_validate.py`).

## Resumen honesto
El producto V1 (Opción A) usa un **índice territorial DESCRIPTIVO** (densidad histórica de
emergencias, geocodificada por IDIGER). Además se **evaluó** un modelo predictivo por lluvia y se
**documenta que NO es apto** como producto predictivo. Se reportan ambos con transparencia.

## A) Índice territorial descriptivo (lo que usa el producto)
- Definición: eventos de remoción/inundación por localidad/UPZ, 2017–2025, geocodificados por IDIGER.
- Naturaleza: `OBSERVED_DESCRIPTIVE`. Georreferenciación: **sin transformación de CRS** (error 0).
- Trazabilidad: `outputs/rc_v1/territorial_index_validation.json` (hash del bronce).
- Sanidad física: remoción concentrada en cerros (Ciudad Bolívar 561, Usme 270, San Cristóbal 266…).
- Limitación: sesgo de reporte; refleja lo ocurrido/reportado, no susceptibilidad física ni pronóstico.

## B) Modelo predictivo evaluado (NO apto — documentado)
- Tarea evaluada: P(emergencia en `[t+1,t+3]`) por localidad-día. Algoritmo: XGBoost (sin monotonía).
- Partición temporal con embargo (train <2023-09 / calib 2023-09..12 / test 2024).
- **Métricas honestas (test 2024):** ROC-AUC 0.735 (IC95 0.67–0.78) · PR-AUC 0.163 (base 0.063) ·
  Brier Skill Score **0.035** · recall @naranja 17% (rojo inalcanzable).
- **Ablation:** no supera a territorio-solo (0.740) ni localidad-sola (0.741); lluvia sola 0.601.
- **Controles:** shuffle sin monotonía 0.458 (limpio); con monotonía 0.705 (prior espurio).
- **Veredicto:** `PREDICTIVE_VALUE = FAIL`, `OPERATIONAL_UTILITY = FAIL`. → No se usa como producto
  predictivo (Regla 21/72: métrica válida > número contaminado).

## Explicabilidad
SHAP explica comportamiento del modelo, **no causalidad**. Se recomputa tras cada reentrenamiento.
(Pendiente formalizar en la RC.)

## Uso previsto / no previsto
Ver `docs/PRODUCT_CONTRACT.md`. No interpretar el índice como probabilidad; no automatizar decisiones críticas.
