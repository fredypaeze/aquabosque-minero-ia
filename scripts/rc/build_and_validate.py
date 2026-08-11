# -*- coding: utf-8 -*-
"""Zoom Bogotá V1 — Pipeline RC (Capa 1 Datos + Capa 2 Modelo).

Corrige los hallazgos de auditoría y REVALIDA honestamente:
  - Target ESTRICTAMENTE FUTURO [t+1, t+3] (elimina fuga same-day, F1).
  - EMBARGO entre splits (impide bleed de la ventana de target, F9).
  - Calibración y thresholds desde CALIB, nunca test (F2).
  - Sin monotonía global por defecto (F4); se evalúa como variante.
  - Baselines M0-M6, ablation, controles negativos, bootstrap CI (dependencia temporal).

Todo lee de config/release_zoom_bogota_v1.yaml. Salidas machine-readable a outputs/rc_v1/.
Ejecutar:  PYTHONHASHSEED=0 ./venv/bin/python scripts/rc/build_and_validate.py
"""
import json, re, unicodedata
from pathlib import Path
import numpy as np, pandas as pd, yaml
import xgboost as xgb
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, roc_auc_score,
                             precision_score, recall_score, f1_score, confusion_matrix)

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((ROOT / "config" / "release_zoom_bogota_v1.yaml").read_text(encoding="utf-8"))
OUT = ROOT / "outputs" / "rc_v1"; OUT.mkdir(parents=True, exist_ok=True)
SEED = CFG["model"]["seed"]; np.random.seed(SEED)

def norm(s):
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)

def num_coma(x):
    try:
        s = str(x)
        v = float(s.replace(".", "").replace(",", ".")) if s.count(",") else float(s.replace(",", "."))
    except (ValueError, TypeError):
        return np.nan
    return v if 0 <= v <= CFG["data"]["rain_max_valid_mm"] else np.nan

# ------------------------------------------------------------------ BRONZE
susc = pd.read_csv(ROOT / CFG["data"]["bronze"]["susceptibilidad"], dtype={"codigo": str})
susc["cod"] = susc["codigo"].str.zfill(2)
name2cod = {norm(r.localidad): c for c, r in susc.set_index("cod").iterrows()}
SUS = susc.set_index("cod")[["localidad", "score_remocion", "score_agua"]]

bit = pd.read_csv(ROOT / CFG["data"]["bronze"]["bitacora"], sep=";", encoding="latin-1", skiprows=2, low_memory=False)
bit.columns = [c.strip() for c in bit.columns]
bit["fecha"] = pd.to_datetime(bit["Fecha reporte"], format="%d/%m/%Y", errors="coerce")
bit["cod"] = bit["Localidad"].astype(str).str.extract(r"^\s*(\d+)").astype(float)
bit = bit.dropna(subset=["fecha", "cod"])
bit["cod"] = bit["cod"].astype(int).astype(str).str.zfill(2)
rx = CFG["target"]["event_types_included_regex"]
bit["evento"] = bit["Tipo de afectación"].astype(str).str.contains(rx, case=False, regex=True)
ev = bit[bit["evento"]].groupby(["cod", "fecha"]).size().rename("n").reset_index()
N_EVENTOS = int(bit["evento"].sum())

rain = pd.read_csv(ROOT / CFG["data"]["bronze"]["sab_lluvia"], sep=";", encoding="latin-1", skiprows=2, low_memory=False)
rain = rain.rename(columns={rain.columns[0]: "fecha"}); rain["fecha"] = pd.to_datetime(rain["fecha"], errors="coerce")
rain = rain.dropna(subset=["fecha"])
long = rain.melt(id_vars="fecha", var_name="estacion", value_name="mm"); long["mm"] = long["mm"].map(num_coma)
est = pd.read_csv(ROOT / CFG["data"]["bronze"]["sab_estaciones"], sep=";", encoding="latin-1", skiprows=2, low_memory=False)
est.columns = [c.strip() for c in est.columns]
est["est_n"] = est["Estación"].astype(str).str.replace(r"(?i)^estaci[oó]n\s+", "", regex=True).map(norm)
est["cod"] = est["Localidad"].map(lambda x: name2cod.get(norm(x)))
sta2cod = {r.est_n: r.cod for r in est.itertuples() if r.cod}
long["cod"] = long["estacion"].map(norm).map(sta2cod)
N_EST_MATCH = long[long["cod"].notna()]["estacion"].nunique(); N_EST_TOT = long["estacion"].nunique()

# ------------------------------------------------------------------ GOLD (features backward, target forward)
loc_day = long.dropna(subset=["cod"]).groupby(["cod", "fecha"])["mm"].mean().rename("p1").reset_index()
city_day = long.groupby("fecha")["mm"].mean().rename("p1_city").reset_index()
fechas = pd.date_range(loc_day["fecha"].min(), loc_day["fecha"].max(), freq="D")
g = (pd.MultiIndex.from_product([SUS.index, fechas], names=["cod", "fecha"]).to_frame(index=False)
     .merge(loc_day, on=["cod", "fecha"], how="left").merge(city_day, on="fecha", how="left"))
g["p1_missing"] = g["p1"].isna().astype(int)          # trazabilidad observado vs imputado
g["p1"] = g["p1"].fillna(g["p1_city"]).fillna(0.0)     # respaldo media-ciudad (documentado)
g = g.sort_values(["cod", "fecha"]).reset_index(drop=True)
grp = g.groupby("cod")["p1"]
wt = CFG["data"]["wet_day_threshold_mm"]
g["p3"] = grp.transform(lambda s: s.rolling(3, min_periods=1).sum())
g["p7"] = grp.transform(lambda s: s.rolling(7, min_periods=1).sum())
g["p15"] = grp.transform(lambda s: s.rolling(15, min_periods=1).sum())
g["pmax3"] = grp.transform(lambda s: s.rolling(3, min_periods=1).max())
g["wet7"] = grp.transform(lambda s: (s > wt).rolling(7, min_periods=1).sum())
g = g.merge(SUS.reset_index()[["cod", "score_remocion", "score_agua"]], on="cod", how="left")
g["mes_sin"] = np.sin(2 * np.pi * g["fecha"].dt.month / 12)
g["mes_cos"] = np.cos(2 * np.pi * g["fecha"].dt.month / 12)

# TARGET estrictamente futuro [t+1, t+3]
evf = ev.assign(e=1)[["cod", "fecha", "e"]]
g = g.merge(evf, on=["cod", "fecha"], how="left"); g["e"] = g["e"].fillna(0).astype(int)
a, b = CFG["target"]["window_days_ahead"]
def fwd(s):
    m = np.zeros(len(s))
    for k in range(a, b + 1):
        m = np.maximum(m, s.shift(-k).to_numpy())
    return pd.Series(m, index=s.index)
g["y"] = g.groupby("cod")["e"].transform(fwd)
# filas con ventana futura incompleta (fin de la serie) -> target desconocido -> fuera
g["y_known"] = g.groupby("cod")["e"].transform(lambda s: (~s.shift(-b).isna()).astype(int))
g = g[g["y_known"] == 1].copy(); g["y"] = g["y"].astype(int)

FEATS = CFG["features"]["list"]
g[["cod", "fecha"] + FEATS + ["y", "p1_missing"]].to_csv(OUT / "gold_localidad_dia.csv", index=False)

# ------------------------------------------------------------------ SPLITS + EMBARGO
emb = pd.Timedelta(days=CFG["splits"]["embargo_days"])
def win(name):
    s = pd.Timestamp(CFG["splits"][name]["start"]); e = pd.Timestamp(CFG["splits"][name]["end"])
    return g[(g["fecha"] >= s) & (g["fecha"] <= e - emb)]   # embargo: recorta el final
train, calib, test = win("train"), win("calib"), win("test")
assert train["fecha"].max() < calib["fecha"].min(), "solapamiento train/calib"
assert calib["fecha"].max() < test["fecha"].min(), "solapamiento calib/test"

RAIN = ["p1","p3","p7","p15","pmax3","wet7"]; SUSf = ["score_remocion","score_agua"]; SEAS = ["mes_sin","mes_cos"]

def fit_predict(feats, tr, te, monotone=False, shuffle=False, add_locid=False, seed=SEED):
    Xtr = tr[feats].copy(); ytr = tr["y"].to_numpy().copy(); Xte = te[feats].copy(); yte = te["y"].to_numpy()
    mono = [1 if f in RAIN + SUSf else 0 for f in feats]
    if add_locid:
        d = pd.get_dummies(pd.concat([tr["cod"], te["cod"]]).astype("category")).astype(int)
        Xtr = pd.concat([Xtr.reset_index(drop=True), d.iloc[:len(tr)].reset_index(drop=True)], axis=1)
        Xte = pd.concat([Xte.reset_index(drop=True), d.iloc[len(tr):].reset_index(drop=True)], axis=1)
        mono += [0] * d.shape[1]
    if shuffle:
        ytr = np.random.default_rng(seed).permutation(ytr)
    spw = (ytr == 0).sum() / max(1, (ytr == 1).sum())
    kw = dict(CFG["model"]["params"]); kw.update(random_state=seed, n_jobs=CFG["model"]["n_jobs"], scale_pos_weight=spw)
    if monotone:
        kw["monotone_constraints"] = tuple(mono)
    m = xgb.XGBClassifier(**kw); m.fit(Xtr, ytr)
    return m, m.predict_proba(Xte)[:, 1], yte

def metrics(y, p):
    return {"roc_auc": round(roc_auc_score(y, p), 3), "pr_auc": round(average_precision_score(y, p), 3),
            "pr_auc_baseline": round(float(y.mean()), 3), "brier": round(brier_score_loss(y, p), 4)}

# ------------------------------------------------------------------ MODELO PRIMARIO (sin monotonía) + CALIBRACIÓN
m6, p_te_raw, yte = fit_predict(FEATS, train, test, monotone=False)
_, p_ca_raw, yca = fit_predict(FEATS, train, calib, monotone=False)   # para calibrar
iso = IsotonicRegression(out_of_bounds="clip").fit(p_ca_raw, yca)
p_te = iso.predict(p_te_raw)
p_ca = iso.predict(p_ca_raw)

prev_train = float(train["y"].mean())
brier_trivial = brier_score_loss(yte, np.full(len(yte), prev_train))   # trivial usa prevalencia TRAIN
bss = 1 - brier_score_loss(yte, p_te) / brier_trivial

# thresholds desde CALIB (no test)
prev_calib = float(calib["y"].mean())
p_naranja = round(prev_calib * CFG["thresholds"]["naranja_x"], 4)
p_rojo = round(prev_calib * CFG["thresholds"]["rojo_x"], 4)
def oppoint(y, p, thr):
    pred = (p >= thr).astype(int); tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"thr": thr, "precision": round(tp / (tp + fp + 1e-9), 3), "recall": round(tp / (tp + fn + 1e-9), 3),
            "specificity": round(tn / (tn + fp + 1e-9), 3), "fp": int(fp), "fn": int(fn), "tp": int(tp), "alertas": int(pred.sum())}

# ------------------------------------------------------------------ BOOTSTRAP por bloque de localidad
def block_bootstrap(y, p, cods, nboot=None, ci=None):
    nboot = nboot or CFG["evaluation"]["bootstrap"]["n"]; ci = ci or CFG["evaluation"]["bootstrap"]["ci"]
    cods = np.asarray(cods); uniq = np.unique(cods); rng = np.random.default_rng(SEED)
    idx_by = {c: np.where(cods == c)[0] for c in uniq}
    roc, pr = [], []
    for _ in range(nboot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        ix = np.concatenate([idx_by[c] for c in pick])
        yy, pp = y[ix], p[ix]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        roc.append(roc_auc_score(yy, pp)); pr.append(average_precision_score(yy, pp))
    lo, hi = (1 - ci) / 2 * 100, (1 + ci) / 2 * 100
    return {"roc_auc_ci": [round(np.percentile(roc, lo), 3), round(np.percentile(roc, hi), 3)],
            "pr_auc_ci": [round(np.percentile(pr, lo), 3), round(np.percentile(pr, hi), 3)]}

boot = block_bootstrap(yte, p_te, test["cod"].to_numpy())

# ------------------------------------------------------------------ BASELINES + ABLATION + CONTROLES
tabla = []
def run(name, feats, **kw):
    _, p, y = fit_predict(feats, train, test, **kw); mt = metrics(y, p); mt["modelo"] = name; tabla.append(mt)
    return mt
run("M0_prevalencia", RAIN[:1])              # (aprox; se sustituye por prev abajo)
run("M1_estacionalidad", SEAS)
run("M2_territorio(susc)", SUSf)
run("M3_lluvia", RAIN)
run("M4_lluvia+estacion", RAIN + SEAS)
run("M5_lluvia+territorio", RAIN + SUSf)
run("M6_completo", FEATS)
run("M6_completo_monotono", FEATS, monotone=True)
run("LOCID_solo_localidad", [], add_locid=True)
# controles negativos
run("CTRL_shuffle_sin_monotonia", FEATS, shuffle=True)
run("CTRL_shuffle_con_monotonia", FEATS, shuffle=True, monotone=True)
# M0 prevalencia real (constante = prev train): AUC=0.5, PR=base
tabla[0] = {"modelo": "M0_prevalencia_train", "roc_auc": 0.5, "pr_auc": round(float(yte.mean()), 3),
            "pr_auc_baseline": round(float(yte.mean()), 3), "brier": round(brier_trivial, 4)}
# random feature (no debe dominar)
gr = g.copy(); gr["rand"] = np.random.default_rng(SEED).random(len(gr))
tr2 = gr.loc[train.index]; te2 = gr.loc[test.index]
_, pr_rand, yr = fit_predict(FEATS + ["rand"], tr2, te2)
run_rand = metrics(yr, pr_rand); run_rand["modelo"] = "M6+random_feature"; tabla.append(run_rand)

pd.DataFrame(tabla)[["modelo","roc_auc","pr_auc","pr_auc_baseline","brier"]].to_csv(OUT / "baselines_ablation_controls.csv", index=False)

# ------------------------------------------------------------------ RESUMEN MACHINE-READABLE
res = {
    "product_version": CFG["contract"]["PRODUCT_VERSION"],
    "target": "evento remoción/inundación en [t+1,t+3] (estrictamente futuro)",
    "n_gold": int(len(g)), "n_train": int(len(train)), "n_calib": int(len(calib)), "n_test": int(len(test)),
    "prev_train": round(prev_train, 4), "prev_calib": round(prev_calib, 4), "prev_test": round(float(yte.mean()), 4),
    "pos_train": int(train["y"].sum()), "pos_calib": int(calib["y"].sum()), "pos_test": int(yte.sum()),
    "eventos_incluidos": N_EVENTOS, "estaciones_mapeadas": f"{N_EST_MATCH}/{N_EST_TOT}",
    "fechas": {"train": [str(train['fecha'].min().date()), str(train['fecha'].max().date())],
               "calib": [str(calib['fecha'].min().date()), str(calib['fecha'].max().date())],
               "test": [str(test['fecha'].min().date()), str(test['fecha'].max().date())]},
    "modelo_primario_sin_monotonia": {**metrics(yte, p_te_raw),
        "brier_calibrado": round(brier_score_loss(yte, p_te), 4),
        "brier_trivial_prevtrain": round(brier_trivial, 4),
        "brier_skill_score": round(bss, 3), **boot},
    "thresholds_desde_calib": {"prev_calib": round(prev_calib, 4), "p_naranja": p_naranja, "p_rojo": p_rojo,
        "op_naranja": oppoint(yte, p_te, p_naranja), "op_rojo": oppoint(yte, p_te, p_rojo)},
    "seed": SEED,
}
(OUT / "rc_metrics.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

print("== ZOOM BOGOTÁ RC — CAPA 1+2 (target estrictamente futuro, sin fuga) ==")
print(f"Gold {res['n_gold']}  Train {res['n_train']} (pos {res['pos_train']})  Calib {res['n_calib']} (pos {res['pos_calib']})  Test {res['n_test']} (pos {res['pos_test']})")
print(f"Prevalencia  train {res['prev_train']}  calib {res['prev_calib']}  test {res['prev_test']}")
pm = res["modelo_primario_sin_monotonia"]
print(f"\nMODELO PRIMARIO (sin monotonía, calibrado):")
print(f"  ROC-AUC {pm['roc_auc']} IC95 {pm['roc_auc_ci']}  |  PR-AUC {pm['pr_auc']} (base {pm['pr_auc_baseline']}) IC95 {pm['pr_auc_ci']}")
print(f"  Brier {pm['brier_calibrado']} vs trivial {pm['brier_trivial_prevtrain']}  → Brier Skill Score {pm['brier_skill_score']}")
print("\nBASELINES / ABLATION / CONTROLES:")
print(pd.DataFrame(tabla)[["modelo","roc_auc","pr_auc","brier"]].to_string(index=False))
print(f"\nThresholds desde CALIB: naranja>={p_naranja} rojo>={p_rojo}")
print(f"  op naranja: {res['thresholds_desde_calib']['op_naranja']}")
print(f"  op rojo:    {res['thresholds_desde_calib']['op_rojo']}")
print("\nArtefactos -> outputs/rc_v1/{gold_localidad_dia,baselines_ablation_controls}.csv + rc_metrics.json")
