# -*- coding: utf-8 -*-
"""AUDITORÍA — baseline reproducible + ablation + controles.
Usa el GOLD ya generado (outputs/tables/bogota_alerta_dataset.csv) para aislar
DE DÓNDE viene la capacidad predictiva y verificar determinismo. No modifica el pipeline.
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "AUDIT_BASELINE"; OUT.mkdir(exist_ok=True)
g = pd.read_csv(ROOT / "outputs" / "tables" / "bogota_alerta_dataset.csv", parse_dates=["fecha"], dtype={"cod": str})

RAIN = ["p1", "p3", "p7", "p15", "pmax3", "wet7"]
SUSC = ["score_remocion", "score_agua"]
SEAS = ["mes_sin", "mes_cos"]
ALL = RAIN + SUSC + SEAS

core = g[g["fecha"] < "2023-09-01"]
test = g[g["fecha"] >= "2024-01-01"]

def train_eval(feats, seed=42, shuffle_y=False, add_locid=False):
    Xtr = core[feats].copy(); ytr = core["y"].values.copy()
    Xte = test[feats].copy(); yte = test["y"].values
    mono = [1 if f in RAIN + SUSC else 0 for f in feats]
    if add_locid:
        d = pd.get_dummies(pd.concat([core["cod"], test["cod"]]).astype("category")).astype(int)
        Xtr = pd.concat([Xtr.reset_index(drop=True), d.iloc[:len(core)].reset_index(drop=True)], axis=1)
        Xte = pd.concat([Xte.reset_index(drop=True), d.iloc[len(core):].reset_index(drop=True)], axis=1)
        mono = mono + [0] * d.shape[1]
    if shuffle_y:
        rng = np.random.default_rng(seed); ytr = rng.permutation(ytr)
    spw = (ytr == 0).sum() / max(1, (ytr == 1).sum())
    m = xgb.XGBClassifier(n_estimators=500, max_depth=4, learning_rate=0.04, subsample=0.85,
        colsample_bytree=0.85, min_child_weight=5, scale_pos_weight=spw, eval_metric="aucpr",
        random_state=seed, n_jobs=4, monotone_constraints=tuple(mono))
    m.fit(Xtr, ytr)
    p = m.predict_proba(Xte)[:, 1]
    return roc_auc_score(yte, p), average_precision_score(yte, p)

base_rate = float(test["y"].mean())
rows = []
for name, feats, kw in [
    ("M6_completo", ALL, {}),
    ("M2_susceptibilidad", SUSC, {}),
    ("M3_lluvia", RAIN, {}),
    ("M1_estacionalidad", SEAS, {}),
    ("M4_lluvia+estacion", RAIN + SEAS, {}),
    ("M5_lluvia+suscept", RAIN + SUSC, {}),
    ("LOCID_solo_localidad", [], {"add_locid": True}),
    ("CONTROL_target_shuffle", ALL, {"shuffle_y": True}),
]:
    auc, pr = train_eval(feats, **kw)
    rows.append({"modelo": name, "roc_auc": round(auc, 3), "pr_auc": round(pr, 3),
                 "pr_lift": round(pr / base_rate, 2)})
    print(f"{name:26s} ROC-AUC {auc:.3f}  PR-AUC {pr:.3f}  (lift x{pr/base_rate:.1f})")

# Determinismo
a1, _ = train_eval(ALL, seed=42); a2, _ = train_eval(ALL, seed=42)
det = abs(a1 - a2)
print(f"\nDeterminismo (mismo seed, 2 corridas): ROC-AUC {a1:.6f} vs {a2:.6f} | diff {det:.2e}")

pd.DataFrame(rows).to_csv(OUT / "ablation_results.csv", index=False)
(OUT / "baseline_metrics.json").write_text(json.dumps({
    "base_rate_test": round(base_rate, 4), "n_core": int(len(core)), "n_test": int(len(test)),
    "ablation": rows, "determinismo_diff_auc": det,
    "nota": "usa el gold actual (etiqueta [t,t+2] incluye día t). Ablation para localizar la señal."
}, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nEvidencia -> AUDIT_BASELINE/ablation_results.csv + baseline_metrics.json")
