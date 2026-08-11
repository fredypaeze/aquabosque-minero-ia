# Validation Report — Zoom Bogotá V1

Fuente de verdad (machine-readable): `validation/validation_results.json`
(regenerar: `./venv/bin/python validation/run_validation.py`). Este documento es una vista.

## Veredicto: **NOT READY FOR FINAL REVIEW** — OVERALL RELEASE = FAIL

## Estado de gates (resumen)
| Capa | Gate crítico | Estado |
|---|---|---|
| 1 Data | TEMPORAL / TARGET / LEAKAGE | **PASS** |
| 1 Data | GEOSPATIAL | PARTIAL (índice territorial IDIGER CRS-safe; falta `score_agua`/POT reproyectado) |
| 1 Data | TRACEABILITY / QUALITY | PARTIAL (source registry OK; falta field lineage / data contracts) |
| 1 Data | **DATA_APPROVED** | **FAIL** |
| 2 Model | NEGATIVE_CONTROLS / BASELINES / UNCERTAINTY | PASS |
| 2 Model | PREDICTIVE_VALUE / OPERATIONAL_UTILITY | **FAIL** |
| 2 Model | **MODEL_APPROVED** | **FAIL** (Opción A: producto no es predictivo) |
| 3 Product | end-to-end / frontend / semantics / fail-safe / freshness | NOT_STARTED |
| 3 Product | **PRODUCT_APPROVED** | **FAIL** |
| 4 Trace | SOURCE_REGISTRY / REGRESSION_TESTS | PASS |
| 4 Trace | lineage / prediction-trace / clean-room / rollback | PENDING |
| 4 Trace | **TRACEABILITY_APPROVED** | **FAIL** |

## Métricas honestas (test 2024)
ROC-AUC 0.735 (IC95 0.67–0.78) · PR-AUC 0.163 (base 0.063) · Brier Skill Score 0.035 · error CRS afín (evidencia F3) mediana **57.496 m**.

## Tests de regresión
`tests/bogota/` — 11/11 PASS (blindan F1, F2, F3, F4, F9, resolución UPZ). Ejecutar: `pytest tests/bogota`.

## Pendiente para una RC válida
Cerrar `score_agua`/capas restantes CRS-safe · Capa 3 producto (encuadre honesto, sin claim predictivo) ·
Capa 4 (field lineage, prediction trace, run manifest, clean-room, rollback, observability) ·
docs restantes (ARCHITECTURE/DAG, DATA_DICTIONARY, README RC) · reejecución final + release manifest.
