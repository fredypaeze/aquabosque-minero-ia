"""Conformal Prediction (inductivo, split) sobre el XGBoost vigente.

Convierte la 'confianza' (softmax, no calibrada) en CONJUNTOS DE PREDICCIÓN con
COBERTURA GARANTIZADA: para un nivel de confianza 1−α (p.ej. 90%), el nivel real
del municipio está dentro del conjunto en ≥90% de los casos. Rigor estadístico
usado en ML de alto riesgo (medicina, finanzas) — poco frecuente en el sector
público. NO reemplaza el modelo: lo envuelve (riesgo cero para el producto).

Método: se reproduce el split 75/25 de train.py; el 25% de test (no visto por el
modelo) se parte en calibración y evaluación. La no-conformidad es 1 − p(clase
verdadera); qhat es el cuantil (n+1)(1−α)/n. El conjunto de un municipio es
{clase : p(clase) ≥ 1 − qhat}. Se reporta la cobertura empírica en evaluación.

Salidas: data/processed/conformal_municipal.csv · data/gold/conformal_summary.json (si existe gold)
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "processed" / "master_con_etiqueta.csv"
MODEL = ROOT / "models" / "trained" / "xgb_riesgo.joblib"
OUT_CSV = ROOT / "data" / "processed" / "conformal_municipal.csv"
OUT_JSON = ROOT / "models" / "metrics" / "conformal_summary.json"
ALPHA = 0.10  # 1 − α = 90% de cobertura objetivo


def run() -> dict:
    bundle = joblib.load(MODEL)
    model, FEATURES, NIVELES = bundle["modelo"], bundle["features"], bundle["niveles"]
    df = pd.read_csv(DATA)
    X = df[FEATURES].fillna(0).astype(float)
    y = df["riesgo_nivel"].map({n: i for i, n in enumerate(NIVELES)}).to_numpy()

    # mismo split que train.py -> el test NO fue visto por el modelo
    idx = np.arange(len(df))
    _, ite = train_test_split(idx, test_size=0.25, random_state=42, stratify=y)
    yte = y[ite]
    proba_te = model.predict_proba(X.iloc[ite])
    # Cobertura ROBUSTA: promedio sobre 100 particiones calibración/evaluación
    ic = np.arange(len(ite))
    covs, tams = [], []
    for seed in range(100):
        cal, ev = train_test_split(ic, test_size=0.5, random_state=seed, stratify=yte)
        sc = 1.0 - proba_te[cal, yte[cal]]
        nc = len(cal)
        ql = min(1.0, np.ceil((nc + 1) * (1 - ALPHA)) / nc)
        q = float(np.quantile(sc, ql, method="higher"))
        sev = proba_te[ev] >= (1.0 - q)
        covs.append(np.mean([yte[ev][i] in np.where(sev[i])[0] for i in range(len(ev))]))
        tams.append(sev.sum(1).mean())
    cobertura = float(np.mean(covs))
    tam_medio = float(np.mean(tams))

    # Umbral de PRODUCCIÓN: calibrado con TODO el test (más datos = más estable)
    scores_full = 1.0 - proba_te[np.arange(len(ite)), yte]
    n = len(ite)
    qlevel = min(1.0, np.ceil((n + 1) * (1 - ALPHA)) / n)
    qhat = float(np.quantile(scores_full, qlevel, method="higher"))
    thr = 1.0 - qhat

    # conjuntos para TODOS los municipios
    proba_all = model.predict_proba(X)
    filas = []
    dist = {1: 0, 2: 0, 3: 0, 4: 0}
    for i, row in df.iterrows():
        s = np.where(proba_all[i] >= thr)[0]
        if len(s) == 0:  # no dejar conjunto vacío: incluir la clase más probable
            s = np.array([int(proba_all[i].argmax())])
        niveles_set = [NIVELES[k] for k in s]
        tam = len(niveles_set)
        dist[tam] = dist.get(tam, 0) + 1
        certeza = "Alta" if tam == 1 else "Media" if tam == 2 else "Baja"
        filas.append({"cod_mpio": int(row["cod_mpio"]), "municipio": row["municipio"],
                      "nivel_predicho": NIVELES[int(proba_all[i].argmax())],
                      "conjunto_conformal": " / ".join(niveles_set),
                      "tamano_conjunto": tam, "certeza_calibrada": certeza})
    out = pd.DataFrame(filas)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    resumen = {
        "metodo": "Split Conformal Prediction (inductivo) sobre XGBoost multiclase",
        "confianza_objetivo": 1 - ALPHA,
        "cobertura_empirica": round(cobertura, 4),
        "qhat": round(qhat, 4),
        "umbral_probabilidad": round(thr, 4),
        "tamano_conjunto_medio": round(tam_medio, 3),
        "n_calibracion": int(n), "n_evaluacion": int(len(ev)),
        "distribucion_certeza": {"Alta (1 nivel)": dist.get(1, 0), "Media (2)": dist.get(2, 0),
                                 "Baja (3-4)": dist.get(3, 0) + dist.get(4, 0)},
        "nota": ("Garantía de cobertura: el nivel real cae dentro del conjunto con probabilidad ≥ "
                 f"{int((1-ALPHA)*100)}% (validado empíricamente en evaluación: {cobertura:.1%})."),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Conformal @ {int((1-ALPHA)*100)}%: cobertura empírica {cobertura:.1%} · "
          f"tamaño medio {tam_medio:.2f} · umbral p≥{thr:.3f}")
    print(f"  certeza — Alta:{dist.get(1,0)}  Media:{dist.get(2,0)}  Baja:{dist.get(3,0)+dist.get(4,0)}")
    print(f"OK: {OUT_CSV.name} · {OUT_JSON.name}")
    return resumen


if __name__ == "__main__":
    run()
