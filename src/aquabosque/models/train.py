"""Fase 6-7: clasificador XGBoost + explicabilidad SHAP.

Entrena un XGBoost multi-clase para clasificar el nivel de riesgo ambiental de
priorización (Bajo/Medio/Alto/Crítico) de cada municipio.

HONESTIDAD (declarada): la etiqueta es una fórmula compuesta, por lo que el
modelo en parte RE-APRENDE la regla. Por eso NO se vende la exactitud como
mérito: se reporta y se contrasta con una línea base trivial (predecir la clase
mayoritaria). El valor del modelo es la EXPLICABILIDAD (SHAP): qué factor pesa
en cada clasificación, para orientar revisión técnica — no probar causalidad.

Salidas: models/trained/xgb_riesgo.joblib · models/metrics/metricas.json
         models/shap/importancia_global.csv · outputs/tables/predicciones.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import train_test_split
import joblib
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed" / "master_con_etiqueta.csv"
FEATURES = ["idx_minero", "idx_deforestacion", "idx_hidrico", "idx_sensibilidad",
            "mineria_titulos", "mineria_minerales", "deforestacion_ha",
            "runap_areas", "runap_hectareas", "agua_estaciones",
            "mineria_volumen", "mineria_regalias", "es_pdet"]
NIVELES = ["Bajo", "Medio", "Alto", "Crítico"]


def run() -> dict:
    df = pd.read_csv(DATA)
    X = df[FEATURES].fillna(0).astype(float)
    y = df["riesgo_nivel"].map({n: i for i, n in enumerate(NIVELES)})

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    modelo = xgb.XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.08,
                               subsample=0.9, colsample_bytree=0.9, random_state=42,
                               objective="multi:softprob", num_class=4, eval_metric="mlogloss")
    modelo.fit(Xtr, ytr)

    pred = modelo.predict(Xte)
    acc = accuracy_score(yte, pred)
    # línea base: predecir siempre la clase mayoritaria (honestidad)
    base_acc = (yte == yte.mode()[0]).mean()
    rep = classification_report(yte, pred, target_names=NIVELES, output_dict=True, zero_division=0)
    cm = confusion_matrix(yte, pred).tolist()

    (ROOT / "models" / "trained").mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "features": FEATURES, "niveles": NIVELES},
                ROOT / "models" / "trained" / "xgb_riesgo.joblib")

    metricas = {
        "n_train": len(Xtr), "n_test": len(Xte),
        "accuracy": round(acc, 4), "baseline_clase_mayoritaria": round(float(base_acc), 4),
        "f1_macro": round(rep["macro avg"]["f1-score"], 4),
        "por_clase": {n: {"precision": round(rep[n]["precision"], 3), "recall": round(rep[n]["recall"], 3),
                          "f1": round(rep[n]["f1-score"], 3), "n": int(rep[n]["support"])} for n in NIVELES},
        "matriz_confusion": cm,
        "nota_honestidad": ("La etiqueta es una fórmula compuesta; el modelo re-aprende parcialmente la regla, "
                            "por eso la accuracy es alta por construcción y NO se presenta como mérito predictivo. "
                            "Se reporta la línea base (clase mayoritaria) para contexto. El valor del modelo es la "
                            "EXPLICABILIDAD (SHAP) y su capacidad de generalizar la priorización, no la exactitud."),
    }
    (ROOT / "models" / "metrics").mkdir(parents=True, exist_ok=True)
    (ROOT / "models" / "metrics" / "metricas.json").write_text(
        json.dumps(metricas, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- SHAP (importancia global) ---
    import shap
    expl = shap.TreeExplainer(modelo)
    sv = expl.shap_values(X)
    # importancia global: media |SHAP| agregada por feature sobre todas las clases
    arr = np.array(sv)
    imp = np.abs(arr).reshape(-1, len(FEATURES)).mean(axis=0) if arr.ndim == 3 else np.abs(arr).mean(axis=0)
    imp_df = pd.DataFrame({"feature": FEATURES, "importancia_shap": np.round(imp, 5)}).sort_values(
        "importancia_shap", ascending=False)
    (ROOT / "models" / "shap").mkdir(parents=True, exist_ok=True)
    imp_df.to_csv(ROOT / "models" / "shap" / "importancia_global.csv", index=False)

    # --- predicciones completas (para el dashboard) ---
    df["riesgo_pred"] = [NIVELES[i] for i in modelo.predict(X)]
    proba = modelo.predict_proba(X)
    df["confianza"] = proba.max(axis=1).round(3)
    (ROOT / "outputs" / "tables").mkdir(parents=True, exist_ok=True)
    cols_out = ["cod_mpio", "municipio", "departamento", "lat", "lon", "riesgo_score",
                "riesgo_nivel", "riesgo_pred", "confianza"] + FEATURES
    df[cols_out].to_csv(ROOT / "outputs" / "tables" / "predicciones.csv", index=False)

    print(f"XGBoost entrenado · accuracy {acc:.3f} (línea base clase mayoritaria {base_acc:.3f}) · f1-macro {metricas['f1_macro']:.3f}")
    print("SHAP importancia global:")
    for _, r in imp_df.iterrows():
        print(f"  {r['feature']:22s} {r['importancia_shap']:.4f}")
    return metricas


if __name__ == "__main__":
    run()
