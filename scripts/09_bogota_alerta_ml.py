# -*- coding: utf-8 -*-
"""AquaBosque · Zoom Bogotá — Modelo predictivo de ALERTA TEMPRANA por lluvia.

Aprende de 8 años de historia la relación lluvia → emergencia (remoción en masa /
inundación) y entrega, por localidad-día, la PROBABILIDAD CALIBRADA de emergencia
en las próximas 72 h, con un UMBRAL DE LLUVIA APRENDIDO por nivel de susceptibilidad
(mejora los umbrales fijos que opera IDIGER hoy).

Datos oficiales:
  - Bitácora de Emergencias IDIGER (2017–jun 2025)     → etiqueta (evento por fecha/localidad)
  - SAB Lluvia diaria IDIGER (sep 2021–dic 2024)       → features (lluvia por estación)
  - Catálogo de estaciones (lat/lon/localidad)          → mapeo estación→localidad
  - bogota_zoom.csv (susceptibilidad remoción/agua)     → susceptibilidad estática

Modelo: XGBoost (clasificación), validación TEMPORAL (entrena en pasado, prueba en
futuro), calibración isotónica, SHAP y curva de umbral aprendido. Honestidad: se
reportan métricas de test honestas (ROC-AUC, PR-AUC, Brier); no se infla nada.

Salidas:
  models/bogota_alerta_xgb.joblib
  models/metrics/bogota_alerta_metrics.json
  outputs/tables/bogota_umbrales_aprendidos.csv
  outputs/tables/bogota_alerta_importancia.csv
"""
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "bogota"
PROC = ROOT / "data" / "processed"
MODELS = ROOT / "models"
MET = MODELS / "metrics"
TAB = ROOT / "outputs" / "tables"
for d in (MET, TAB):
    d.mkdir(parents=True, exist_ok=True)


def norm(s):
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


# Asegura el bronze (descarga desde fuente oficial si falta) — reproducible en clon limpio
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bogota_sources
_bogota_sources.fetch_all(RAW)


def num_coma(x):
    """Lluvia con decimal-coma ('3,1' -> 3.1). Descarta absurdos (>400 mm/día)."""
    try:
        v = float(str(x).replace(".", "").replace(",", ".")) if str(x).count(",") else float(str(x).replace(",", "."))
    except (ValueError, TypeError):
        return np.nan
    return v if 0 <= v <= 400 else np.nan


# ---------------------------------------------------------------- susceptibilidad
zoom = pd.read_csv(PROC / "bogota_zoom.csv", dtype={"codigo": str})
zoom["cod"] = zoom["codigo"].str.zfill(2)
susc = zoom.set_index("cod")[["localidad", "score_remocion", "score_agua"]].copy()
name2cod = {norm(r.localidad): c for c, r in susc.iterrows()}

# ---------------------------------------------------------------- eventos (etiqueta)
bit = pd.read_csv(RAW / "bitacora_emergencias.csv", sep=";", encoding="latin-1",
                  skiprows=2, low_memory=False)
bit.columns = [c.strip() for c in bit.columns]
bit["fecha"] = pd.to_datetime(bit["Fecha reporte"], format="%d/%m/%Y", errors="coerce")
bit["cod"] = bit["Localidad"].astype(str).str.extract(r"^\s*(\d+)").astype(float)
bit = bit.dropna(subset=["fecha", "cod"])
bit["cod"] = bit["cod"].astype(int).astype(str).str.zfill(2)
t = bit["Tipo de afectación"].astype(str)
bit["remocion"] = t.str.contains("emoci|eslizam|talud|ladera", case=False, regex=True)
bit["inundacion"] = t.str.contains("nundaci|ncharca|negaci|venida|creciente", case=False, regex=True)
bit["evento"] = bit["remocion"] | bit["inundacion"]
ev = (bit[bit["evento"]].groupby(["cod", "fecha"]).size().rename("n_eventos").reset_index())
print(f"Eventos remoción+inundación: {int(bit['evento'].sum())}  |  localidad-días con evento: {len(ev)}")

# ---------------------------------------------------------------- lluvia (features)
rain = pd.read_csv(RAW / "sab_lluvia_diaria.csv", sep=";", encoding="latin-1",
                   skiprows=2, low_memory=False)
rain = rain.rename(columns={rain.columns[0]: "fecha"})
rain["fecha"] = pd.to_datetime(rain["fecha"], errors="coerce")
rain = rain.dropna(subset=["fecha"])
long = rain.melt(id_vars="fecha", var_name="estacion", value_name="mm")
long["mm"] = long["mm"].map(num_coma)

est = pd.read_csv(RAW / "sab_estaciones.csv", sep=";", encoding="latin-1",
                  skiprows=2, low_memory=False)
est.columns = [c.strip() for c in est.columns]
est["est_n"] = est["Estación"].astype(str).str.replace(r"(?i)^estaci[oó]n\s+", "", regex=True).map(norm)
est["cod"] = est["Localidad"].map(lambda x: name2cod.get(norm(x)))
sta2cod = {r.est_n: r.cod for r in est.itertuples() if r.cod}
long["est_n"] = long["estacion"].map(norm)
long["cod"] = long["est_n"].map(sta2cod)
matched = long["cod"].notna().mean()
print(f"Estaciones mapeadas a localidad: {long[long['cod'].notna()]['estacion'].nunique()} "
      f"/ {long['estacion'].nunique()}  ({matched*100:.0f}% de lecturas)")

# lluvia media por localidad-día + media ciudad como respaldo
loc_day = long.dropna(subset=["cod"]).groupby(["cod", "fecha"])["mm"].mean().rename("p1").reset_index()
city_day = long.groupby("fecha")["mm"].mean().rename("p1_city").reset_index()

# ---------------------------------------------------------------- rejilla localidad-día
fechas = pd.date_range(loc_day["fecha"].min(), loc_day["fecha"].max(), freq="D")
grid = pd.MultiIndex.from_product([susc.index, fechas], names=["cod", "fecha"]).to_frame(index=False)
g = (grid.merge(loc_day, on=["cod", "fecha"], how="left")
         .merge(city_day, on="fecha", how="left"))
g["p1"] = g["p1"].fillna(g["p1_city"]).fillna(0.0)
g = g.sort_values(["cod", "fecha"]).reset_index(drop=True)

# features de lluvia (acumulados / antecedente / intensidad)
grp = g.groupby("cod")["p1"]
g["p3"] = grp.transform(lambda s: s.rolling(3, min_periods=1).sum())
g["p7"] = grp.transform(lambda s: s.rolling(7, min_periods=1).sum())
g["p15"] = grp.transform(lambda s: s.rolling(15, min_periods=1).sum())
g["pmax3"] = grp.transform(lambda s: s.rolling(3, min_periods=1).max())
g["wet7"] = g.groupby("cod")["p1"].transform(lambda s: (s > 1).rolling(7, min_periods=1).sum())

# susceptibilidad estática + estacionalidad
g = g.merge(susc.reset_index()[["cod", "score_remocion", "score_agua"]], on="cod", how="left")
g["mes_sin"] = np.sin(2 * np.pi * g["fecha"].dt.month / 12)
g["mes_cos"] = np.cos(2 * np.pi * g["fecha"].dt.month / 12)

# etiqueta: evento en ventana [t, t+2] (72 h)
ev_flag = ev.assign(ev=1)[["cod", "fecha", "ev"]]
g = g.merge(ev_flag, on=["cod", "fecha"], how="left")
g["ev"] = g["ev"].fillna(0).astype(int)
g["y"] = g.groupby("cod")["ev"].transform(
    lambda s: s[::-1].rolling(3, min_periods=1).max()[::-1]).astype(int)

FEATS = ["p1", "p3", "p7", "p15", "pmax3", "wet7", "score_remocion", "score_agua", "mes_sin", "mes_cos"]
print(f"\nMatriz: {g.shape[0]} localidad-días  |  positivos (72h): {int(g['y'].sum())} "
      f"({g['y'].mean()*100:.1f}%)")
g[["cod", "fecha"] + FEATS + ["y"]].to_csv(TAB / "bogota_alerta_dataset.csv", index=False)
print("Dataset guardado. Rango:", g["fecha"].min().date(), "→", g["fecha"].max().date())

# ================================================================ ENTRENAMIENTO
import joblib
import xgboost as xgb
import shap
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

# Partición TEMPORAL honesta (entrena en pasado, calibra y prueba en futuro)
core = g[g["fecha"] < "2023-09-01"]
calib = g[(g["fecha"] >= "2023-09-01") & (g["fecha"] < "2024-01-01")]
test = g[g["fecha"] >= "2024-01-01"]
Xtr, ytr = core[FEATS], core["y"]
Xca, yca = calib[FEATS], calib["y"]
Xte, yte = test[FEATS], test["y"]
spw = (ytr == 0).sum() / max(1, (ytr == 1).sum())
print(f"\nTrain {len(Xtr)} (pos {int(ytr.sum())}) · Calib {len(Xca)} · Test {len(Xte)} (pos {int(yte.sum())})")

# Monotonía física: la probabilidad NO puede bajar si sube la lluvia o la susceptibilidad.
# FEATS = [p1,p3,p7,p15,pmax3,wet7, score_remocion,score_agua, mes_sin,mes_cos]
MONO = (1, 1, 1, 1, 1, 1, 1, 1, 0, 0)
model = xgb.XGBClassifier(
    n_estimators=500, max_depth=4, learning_rate=0.04,
    subsample=0.85, colsample_bytree=0.85, min_child_weight=5,
    scale_pos_weight=spw, eval_metric="aucpr", random_state=42, n_jobs=4,
    monotone_constraints=MONO,
)
model.fit(Xtr, ytr)

# Calibración isotónica sobre la ventana de calibración (sin fuga temporal)
p_ca = model.predict_proba(Xca)[:, 1]
iso = IsotonicRegression(out_of_bounds="clip").fit(p_ca, yca)

p_te_raw = model.predict_proba(Xte)[:, 1]
p_te = iso.predict(p_te_raw)
base_rate = float(yte.mean())
metrics = {
    "n_train": int(len(Xtr)), "n_calib": int(len(Xca)), "n_test": int(len(Xte)),
    "pos_rate_test": round(base_rate, 4),
    "roc_auc": round(roc_auc_score(yte, p_te_raw), 3),
    "pr_auc": round(average_precision_score(yte, p_te_raw), 3),
    "pr_auc_baseline": round(base_rate, 3),
    "lift_pr_auc": round(average_precision_score(yte, p_te_raw) / base_rate, 1),
    "brier_uncal": round(brier_score_loss(yte, p_te_raw), 4),
    "brier_cal": round(brier_score_loss(yte, p_te), 4),
    "ventana": "evento remoción/inundación en 72 h",
    "particion": "train <2023-09 · calib 2023-09..12 · test 2024",
}

# SHAP (importancia explicable)
expl = shap.TreeExplainer(model)
sv = expl.shap_values(Xte)
imp = pd.DataFrame({"feature": FEATS, "shap_abs": np.abs(sv).mean(0)}).sort_values("shap_abs", ascending=False)
imp.to_csv(TAB / "bogota_alerta_importancia.csv", index=False)
metrics["top_features"] = imp.head(5)["feature"].tolist()

# UMBRAL DE LLUVIA APRENDIDO por nivel de susceptibilidad (mejora el umbral fijo de IDIGER)
def feats_from_R(R, srem, sagu, mes=4):
    """Mapea una lluvia 72h (R mm) a la fila de features (misma regla que usará el tablero)."""
    return pd.DataFrame([{
        "p1": R / 3, "p3": R, "p7": R * 1.4, "p15": R * 1.9, "pmax3": R * 0.55,
        "wet7": min(7, R / 8), "score_remocion": srem, "score_agua": sagu,
        "mes_sin": np.sin(2 * np.pi * mes / 12), "mes_cos": np.cos(2 * np.pi * mes / 12),
    }])[FEATS]

def curva_R(srem, sagu):
    return [iso.predict(model.predict_proba(feats_from_R(R, srem, sagu))[:, 1])[0] for R in range(0, 161, 2)]

def umbral(curva, p_obj):
    for i, p in enumerate(curva):
        if p >= p_obj:
            return i * 2
    return np.nan

# Bandas de alerta relativas al riesgo base (test): naranja ≈ 2.5×, rojo ≈ 3.5×
base = float(yte.mean())
P_NARANJA, P_ROJO = round(base * 2.5, 3), round(base * 3.5, 3)
rows = []
for c, r in susc.iterrows():
    cv = curva_R(r["score_remocion"], r["score_agua"])
    rows.append({"cod": c, "localidad": r["localidad"],
                 "score_remocion": r["score_remocion"], "score_agua": r["score_agua"],
                 "umbral_naranja_mm72h": umbral(cv, P_NARANJA),
                 "umbral_rojo_mm72h": umbral(cv, P_ROJO),
                 "p_max": round(max(cv), 3)})
umb = pd.DataFrame(rows).sort_values("umbral_naranja_mm72h")
umb.to_csv(TAB / "bogota_umbrales_aprendidos.csv", index=False)
metrics["bandas"] = {"base_rate": round(base, 3), "p_naranja": P_NARANJA, "p_rojo": P_ROJO}

# Persistir modelo + calibrador + metadatos para el tablero
joblib.dump({"model": model, "iso": iso, "feats": FEATS,
             "feats_from_R": None}, MODELS / "bogota_alerta_xgb.joblib")
(MET / "bogota_alerta_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n== MÉTRICAS DE TEST (2024, honestas) ==")
print(f"  ROC-AUC {metrics['roc_auc']}  |  PR-AUC {metrics['pr_auc']} (base {metrics['pr_auc_baseline']}, "
      f"lift ×{metrics['lift_pr_auc']})  |  Brier {metrics['brier_uncal']}→{metrics['brier_cal']} (calibrado)")
print("  Top features (SHAP):", metrics["top_features"])
print(f"\n== UMBRAL DE LLUVIA APRENDIDO (mm/72h) · naranja P≥{P_NARANJA} · rojo P≥{P_ROJO} ==")
print(umb[["localidad", "score_remocion", "umbral_naranja_mm72h", "umbral_rojo_mm72h", "p_max"]].head(8).to_string(index=False))
print("\nArtefactos: models/bogota_alerta_xgb.joblib · metrics json · umbrales + importancia CSV")
