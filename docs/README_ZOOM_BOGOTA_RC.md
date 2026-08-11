# Zoom Bogotá V1 — README (Release Candidate)

Producto (Opción A): **índice territorial descriptivo** de emergencias por lluvia + escenario
etiquetado. **No** es un pronóstico ni una probabilidad calibrada. Contrato: `docs/PRODUCT_CONTRACT.md`.

## REBUILD FROM SCRATCH (Sec 56)
Entorno: Python 3.12, `./venv` (numpy/pandas/sklearn/xgboost/shap/pyproj/pyyaml). Seed 42.
```bash
# 1) BRONZE (descarga desde fuente oficial si falta; hashes en metadata/source_registry.json)
./venv/bin/python scripts/_bogota_sources.py
# 2) GOLD + modelo + validación honesta (temporal, sin fuga)
PYTHONHASHSEED=0 ./venv/bin/python scripts/rc/build_and_validate.py
# 3) NÚCLEO territorial descriptivo (CRS-safe, geocodificación IDIGER)
./venv/bin/python scripts/rc/build_territorial_index.py
# 4) metadata (source registry, lineage, run manifest, artifact registry)
./venv/bin/python scripts/rc/build_source_registry.py
./venv/bin/python scripts/rc/build_metadata.py
# 5) VALIDACIÓN GLOBAL (gates → machine-readable)
./venv/bin/python validation/run_validation.py
# 6) TESTS de regresión
./venv/bin/python -m pytest tests/bogota -q
```
Comparar `outputs/rc_v1/rc_metrics.json` (ROC-AUC 0.735, seed 42) y hashes en `metadata/run_manifest.json`.

## Trazabilidad puntual (Sec 41)
```bash
./venv/bin/python audit/trace_observation.py --territorial "Ciudad Bolívar"
./venv/bin/python audit/trace_observation.py --feature --cod 19 --fecha 2024-05-10
```

## ROLLBACK (Sec 60)
Cada estado está en git + tags. Para volver a un estado válido previo:
```bash
git checkout <tag_o_commit_previo> -- app/ scripts/rc/ config/ data/processed/bogota_territorial_v1.csv
./venv/bin/python validation/run_validation.py   # confirmar gates del estado restaurado
```
Punto de recuperación de la auditoría: tag `audit/pre-merge-b61a910` + rama `audit-backup/trio-insignia`.
El tablero degrada con fail-safe (`st.stop`) si falta el dato, en vez de mostrar valores no verificados.

## Estado
Ver `docs/VALIDATION_REPORT.md` y `validation/validation_results.json`. **NOT READY** (en construcción).

## Docs
PRODUCT_CONTRACT · MODEL_CARD_ZOOM_BOGOTA · DECISION_LOG · VALIDATION_REPORT · ARCHITECTURE ·
DATA_DICTIONARY_BOGOTA (existente) · metadata/*.
