"""Fase 8 — verifica que los artefactos para el dashboard estén generados.
Las predicciones (outputs/tables/predicciones.csv) las produce 04_train_model."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = [
    "data/processed/master_con_etiqueta.csv",
    "models/trained/xgb_riesgo.joblib",
    "models/metrics/metricas.json",
    "models/shap/importancia_global.csv",
    "outputs/tables/predicciones.csv",
]
if __name__ == "__main__":
    faltan = [a for a in ART if not (ROOT / a).exists()]
    if faltan:
        raise SystemExit("Faltan artefactos (corre las fases 1-4): " + ", ".join(faltan))
    print("Artefactos completos — el dashboard puede arrancar:")
    for a in ART:
        print(f"  ✓ {a}")
