"""Fase 6-7 — entrena XGBoost multiclase + explicabilidad SHAP; guarda modelo,
métricas, importancia SHAP y predicciones para el dashboard."""
import _bootstrap  # noqa: F401
from aquabosque.models.train import run

if __name__ == "__main__":
    run()
