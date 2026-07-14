import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Explicabilidad", page_icon="🔬", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
st.title("🔬 Explicabilidad del modelo (SHAP)")
st.caption("Qué factores pesan más en la priorización — el corazón defendible del sistema.")

imp = pd.read_csv(ROOT / "models" / "shap" / "importancia_global.csv").sort_values("importancia_shap")
etq = {"idx_minero": "Índice minero", "idx_deforestacion": "Índice deforestación",
       "idx_hidrico": "Índice hídrico", "idx_sensibilidad": "Índice sensibilidad",
       "mineria_titulos": "Títulos mineros", "mineria_minerales": "Minerales",
       "deforestacion_ha": "Deforestación (ha)", "runap_areas": "Áreas RUNAP",
       "runap_hectareas": "RUNAP (ha)", "agua_estaciones": "Estaciones de agua",
       "mineria_volumen": "Volumen explotación", "mineria_regalias": "Regalías", "es_pdet": "Municipio PDET"}
imp["Variable"] = imp["feature"].map(lambda x: etq.get(x, x))

fig = px.bar(imp, x="importancia_shap", y="Variable", orientation="h",
             color="importancia_shap", color_continuous_scale=["#a5d6a7", "#2e7d32", "#01579b"],
             height=460)
fig.update_layout(margin=dict(l=0, r=10, t=6, b=0), plot_bgcolor="rgba(0,0,0,0)",
                  paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False,
                  xaxis_title="Importancia SHAP (media |valor|)", yaxis_title=None)
fig.update_xaxes(gridcolor="#e7efe9")
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

met = json.loads((ROOT / "models" / "metrics" / "metricas.json").read_text())
c = st.columns(3)
c[0].metric("Accuracy", f"{met['accuracy']:.1%}")
c[1].metric("Línea base (clase mayoritaria)", f"{met['baseline_clase_mayoritaria']:.1%}")
c[2].metric("F1-macro", f"{met['f1_macro']:.2f}")

B.note("<b>Honestidad metodológica.</b> " + met["nota_honestidad"])
B.footer()
