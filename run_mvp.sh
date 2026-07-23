#!/usr/bin/env bash
# Arranque de un paso: reconstruye features + modelo desde el raw y lanza el dashboard.
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d venv ] && PY=venv/bin/python
echo ">> Reconstruyendo features + etiqueta..."; $PY scripts/03_build_features.py
echo ">> Entrenando modelo + SHAP...";          $PY scripts/04_train_model.py
echo ">> Capas avanzadas (conformal + anomalias)...";     PYTHONPATH=src $PY -m aquabosque.models.conformal; PYTHONPATH=src $PY -m aquabosque.models.anomalias
echo ">> Verificando artefactos...";            $PY scripts/05_generate_outputs.py
echo ">> Lanzando dashboard en http://localhost:8510";  $PY scripts/06_run_app.py
