"""Detección de anomalías (Isolation Forest) — capa aditiva, no supervisada.

Rompe la circularidad del índice: en vez de re-aprender la fórmula, marca los
municipios con COMBINACIONES ATÍPICAS de presión ambiental (patrones que el
puntaje ponderado no destaca). Estándar en detección de fraude/riesgo; aquí es
totalmente aditivo (no toca el modelo del producto).

Salida: data/processed/anomalias_municipal.csv · models/metrics/anomalias_summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed" / "master_con_etiqueta.csv"
OUT_CSV = ROOT / "data" / "processed" / "anomalias_municipal.csv"
OUT_JSON = ROOT / "models" / "metrics" / "anomalias_summary.json"
FEATS = ["idx_minero", "idx_deforestacion", "idx_fuego", "idx_hidrico", "idx_sensibilidad"]
CONTAM = 0.05  # ~5% de municipios atípicos


def run() -> dict:
    df = pd.read_csv(DATA)
    X = df[FEATS].fillna(0).astype(float).to_numpy()
    iso = IsolationForest(n_estimators=300, contamination=CONTAM, random_state=42)
    iso.fit(X)
    # score de anomalía: mayor = más atípico (invertimos decision_function)
    raw = -iso.decision_function(X)
    df["score_anomalia"] = np.round((raw - raw.min()) / (raw.max() - raw.min() + 1e-9), 4)
    df["es_anomalia"] = (iso.predict(X) == -1).astype(int)

    an = df[df.es_anomalia == 1].copy()
    en_alto = an[an.riesgo_nivel.isin(["Alto", "Crítico"])]
    nuevas = an[an.riesgo_nivel.isin(["Bajo", "Medio"])]  # atípicas que el índice NO prioriza

    cols = ["cod_mpio", "municipio", "departamento", "riesgo_nivel", "score_anomalia",
            "idx_minero", "idx_deforestacion", "idx_fuego", "idx_hidrico", "idx_sensibilidad", "es_anomalia"]
    df[cols].sort_values("score_anomalia", ascending=False).to_csv(OUT_CSV, index=False)

    top = an.sort_values("score_anomalia", ascending=False).head(10)
    resumen = {
        "metodo": "Isolation Forest (no supervisado) sobre los 5 índices",
        "contaminacion": CONTAM,
        "n_anomalias": int(an.shape[0]),
        "anomalias_en_alto_critico": int(en_alto.shape[0]),
        "anomalias_no_priorizadas_por_indice": int(nuevas.shape[0]),
        "top10": [{"municipio": r.municipio, "departamento": r.departamento,
                   "nivel": r.riesgo_nivel, "score": float(r.score_anomalia)} for r in top.itertuples()],
        "valor": ("Las anomalías confirman parte de la priorización y, sobre todo, revelan combinaciones "
                  "atípicas de presión que el índice ponderado no destaca — un cruce independiente y sin etiquetas."),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Isolation Forest: {an.shape[0]} anomalías · {en_alto.shape[0]} coinciden con Alto/Crítico · "
          f"{nuevas.shape[0]} atípicas NO priorizadas por el índice")
    for r in top.head(5).itertuples():
        print(f"  {r.municipio} ({r.departamento}) [{r.riesgo_nivel}] score {r.score_anomalia:.2f}")
    print(f"OK: {OUT_CSV.name} · {OUT_JSON.name}")
    return resumen


if __name__ == "__main__":
    run()
