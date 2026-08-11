# -*- coding: utf-8 -*-
"""AquaBosque — Trío insignia (mejoras de alto impacto):
 1) Velocidad de degradación (dimensión temporal 2017-2021): dónde EMPEORA más rápido.
 2) Detección de minería ilegal: presión minera alta SIN formalización (RUCOM/ANM).
 3) Anomalías explicadas: por qué las anomalías que el índice NO prioriza son anómalas.

No toca el pipeline existente; produce nuevas tablas en outputs/tables/ y un resumen.
"""
import json, unicodedata, re
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "tables"; OUT.mkdir(parents=True, exist_ok=True)
MET = ROOT / "models" / "metrics"

def norm(s):
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)

def dane(x):
    try: return str(int(float(x))).zfill(5)
    except (TypeError, ValueError): return None

pred = pd.read_csv(ROOT / "outputs" / "tables" / "predicciones.csv")
pred["cod_mpio"] = pred["cod_mpio"].map(dane)
name2cod = {(norm(r.municipio), norm(r.departamento)): r.cod_mpio for r in pred.itertuples()}
name2cod_solo = {norm(r.municipio): r.cod_mpio for r in pred.itertuples()}

# =========================================================
# 1) VELOCIDAD DE DEGRADACIÓN (deforestación 2017-2021)
# =========================================================
defo = pd.read_csv(ROOT / "data" / "raw" / "bosque" / "deforestacion.csv")
defo["mpio_n"] = defo["MPIO_CNMBR"].map(norm); defo["dpto_n"] = defo["DPTO_CNMBR"].map(norm)
piv = defo.pivot_table(index=["mpio_n", "dpto_n"], columns="Año", values="Defores", aggfunc="sum")
years = sorted(defo["Año"].unique())
rows = []
for (m, d), r in piv.iterrows():
    serie = [r.get(y, np.nan) for y in years]
    s = pd.Series(serie, index=years).dropna()
    if len(s) < 3: continue
    x = s.index.values.astype(float); y = s.values.astype(float)
    slope = np.polyfit(x - x.min(), y, 1)[0]                      # ha/año (tendencia)
    early = y[:2].mean(); late = y[-2:].mean()
    acel = late - early                                          # aceleración (ha/año)
    proy = max(0.0, y[-1] + slope)                               # proyección próximo año
    cod = name2cod.get((m, d)) or name2cod_solo.get(m)
    rows.append({"cod_mpio": cod, "municipio": m.title(), "departamento": d.title(),
                 "defo_total_5a_ha": round(float(np.nansum(serie)), 0),
                 "defo_ultimo_ano_ha": round(float(y[-1]), 0),
                 "tendencia_ha_ano": round(float(slope), 1),
                 "aceleracion_ha_ano": round(float(acel), 0),
                 "proyeccion_prox_ano_ha": round(float(proy), 0)})
vel = pd.DataFrame(rows)
def clasif(a):
    return "Acelerando" if a > 300 else "Al alza" if a > 0 else "Estable/baja" if a > -300 else "Desacelerando"
vel["dinamica"] = vel["aceleracion_ha_ano"].map(clasif)
vel = vel.sort_values("aceleracion_ha_ano", ascending=False)
vel.to_csv(OUT / "velocidad_degradacion.csv", index=False, encoding="utf-8")

# =========================================================
# 2) MINERÍA ILEGAL (presión minera sin formalización)
# =========================================================
rucom = pd.read_csv(ROOT / "data" / "raw" / "mineria" / "rucom.csv")
anm = pd.read_csv(ROOT / "data" / "raw" / "mineria" / "anm_volumen.csv")
rucom["cod"] = rucom["codigo_dane"].map(dane); anm["cod"] = anm["codigo_dane"].map(dane)
# Brecha de formalización: presión extractiva (minería+deforestación+fuego) vs. presencia formal
# (RUCOM + proyectos ANM + títulos). Alta presión con baja formalización = señal de actividad informal/ilegal.
rucom_cnt = rucom.groupby("cod").size().rename("rucom_registros")
anm_cnt = anm.groupby("cod").size().rename("anm_proyectos")
mi = pred[["cod_mpio", "municipio", "departamento", "idx_minero", "idx_deforestacion", "idx_fuego",
           "riesgo_nivel", "mineria_titulos"]].copy()
mi = mi.merge(rucom_cnt, left_on="cod_mpio", right_index=True, how="left") \
       .merge(anm_cnt, left_on="cod_mpio", right_index=True, how="left")
mi[["rucom_registros", "anm_proyectos"]] = mi[["rucom_registros", "anm_proyectos"]].fillna(0).astype(int)
mi["presion_extractiva"] = ((mi["idx_minero"].rank(pct=True) + mi["idx_deforestacion"].rank(pct=True)
                             + mi["idx_fuego"].rank(pct=True)) / 3).round(3)
mi["formalizacion"] = ((mi["rucom_registros"].rank(pct=True) + mi["anm_proyectos"].rank(pct=True)
                        + mi["mineria_titulos"].fillna(0).rank(pct=True)) / 3).round(3)
mi["brecha_formalizacion"] = (mi["presion_extractiva"] - mi["formalizacion"]).round(3)
p75_pres = mi["presion_extractiva"].quantile(0.75)
mi["alerta_informalidad"] = (mi["presion_extractiva"] >= p75_pres) & (mi["brecha_formalizacion"] >= 0.30)
ileg = mi[mi["presion_extractiva"] >= p75_pres].sort_values("brecha_formalizacion", ascending=False)
ileg.to_csv(OUT / "alertas_mineria_ilegal.csv", index=False, encoding="utf-8")
alertas = ileg[ileg["alerta_informalidad"]]

# =========================================================
# 3) ANOMALÍAS EXPLICADAS (por qué son anómalas)
# =========================================================
ano = pd.read_csv(ROOT / "data" / "processed" / "anomalias_municipal.csv")
idxcols = ["idx_minero", "idx_deforestacion", "idx_fuego", "idx_hidrico", "idx_sensibilidad"]
nombres = {"idx_minero": "presión minera", "idx_deforestacion": "deforestación", "idx_fuego": "focos de calor",
           "idx_hidrico": "estrés hídrico", "idx_sensibilidad": "sensibilidad ambiental"}
z = (ano[idxcols] - ano[idxcols].mean()) / ano[idxcols].std(ddof=0)
ano["cod_mpio"] = ano["cod_mpio"].map(dane)
expl = []
for i, r in ano.iterrows():
    zr = z.loc[i]
    orden = zr.sort_values(ascending=False)
    top = [f"{nombres[c]} (p{int((z[c] <= zr[c]).mean()*100)})" for c in orden.index[:2] if zr[c] > 1]
    driver = orden.index[0]
    prioriza_indice = str(r["riesgo_nivel"]).strip() in ("Alto", "Crítico")
    expl.append({"cod_mpio": r["cod_mpio"], "municipio": r["municipio"], "departamento": r["departamento"],
                 "riesgo_nivel": r["riesgo_nivel"], "score_anomalia": round(float(r["score_anomalia"]), 3),
                 "es_anomalia": bool(r["es_anomalia"]), "factor_dominante": nombres[driver],
                 "explicacion": "; ".join(top) or "combinación atípica de factores",
                 "prioriza_indice": prioriza_indice,
                 "oculta_para_indice": bool(r["es_anomalia"]) and not prioriza_indice})
ax = pd.DataFrame(expl)
anomdf = ax[ax["es_anomalia"]].sort_values("score_anomalia", ascending=False)
anomdf.to_csv(OUT / "anomalias_explicadas.csv", index=False, encoding="utf-8")
ocultas = anomdf[anomdf["oculta_para_indice"]]

# =========================================================
# RESUMEN
# =========================================================
resumen = {
    "velocidad": {
        "n_municipios": int(len(vel)),
        "acelerando": int((vel["dinamica"] == "Acelerando").sum()),
        "top5_aceleracion": vel.head(5)[["municipio", "departamento", "aceleracion_ha_ano", "defo_ultimo_ano_ha"]].to_dict("records"),
        "nota": "Tendencia y aceleración de la deforestación 2017-2021. 'Acelerando' = +300 ha/año o más de aumento.",
    },
    "mineria_ilegal": {
        "n_alertas": int(len(alertas)),
        "n_alta_presion": int(len(ileg)),
        "top5": alertas.head(5)[["municipio", "departamento", "presion_extractiva", "formalizacion", "brecha_formalizacion", "riesgo_nivel"]].to_dict("records"),
        "nota": "Brecha de formalización: presión extractiva alta (p75+) con formalización baja (p25-) en RUCOM/ANM/títulos → posible actividad informal/ilegal; prioridad de verificación en terreno.",
    },
    "anomalias": {
        "n_anomalias": int(len(anomdf)),
        "ocultas_para_indice": int(len(ocultas)),
        "top_ocultas": ocultas.head(8)[["municipio", "departamento", "riesgo_nivel", "factor_dominante", "explicacion"]].to_dict("records"),
        "nota": "Anomalías que el índice de riesgo NO prioriza (nivel Bajo/Medio) pero el modelo no supervisado sí detecta, con su factor explicativo.",
    },
}
(MET / "trio_insignia_summary.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

print("== TRÍO INSIGNIA — resultados ==")
print(f"\n1) VELOCIDAD: {resumen['velocidad']['n_municipios']} municipios con serie; {resumen['velocidad']['acelerando']} ACELERANDO.")
for r in resumen["velocidad"]["top5_aceleracion"]:
    print(f"   +{r['aceleracion_ha_ano']:>6.0f} ha/año  {r['municipio']} ({r['departamento']}) · último año {r['defo_ultimo_ano_ha']:.0f} ha")
print(f"\n2) MINERÍA ILEGAL: {resumen['mineria_ilegal']['n_alertas']} alertas de brecha de formalización (de {resumen['mineria_ilegal']['n_alta_presion']} de alta presión).")
for r in resumen["mineria_ilegal"]["top5"]:
    print(f"   brecha {r['brecha_formalizacion']:+.2f}  {r['municipio']} ({r['departamento']}) · presión {r['presion_extractiva']:.2f} vs formaliz {r['formalizacion']:.2f} · riesgo {r['riesgo_nivel']}")
print(f"\n3) ANOMALÍAS: {resumen['anomalias']['n_anomalias']} anómalos; {resumen['anomalias']['ocultas_para_indice']} OCULTAS para el índice.")
for r in resumen["anomalias"]["top_ocultas"]:
    print(f"   {r['municipio']} ({r['departamento']}) · nivel {r['riesgo_nivel']} → {r['explicacion']}")
print("\nSalidas: outputs/tables/{velocidad_degradacion,alertas_mineria_ilegal,anomalias_explicadas}.csv + models/metrics/trio_insignia_summary.json")
