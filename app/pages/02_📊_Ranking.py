from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Ranking", page_icon="📊", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(ROOT / "outputs" / "tables" / "predicciones.csv").sort_values("riesgo_score", ascending=False)

st.title("📊 Ranking territorial de priorización")
st.caption("Municipios ordenados por score de riesgo ambiental (0–1). Priorización técnica, no sanción.")

n = st.slider("Mostrar top N", 10, 200, 25, 5)
cols = ["municipio", "departamento", "riesgo_nivel", "riesgo_score",
        "idx_minero", "idx_deforestacion", "idx_hidrico", "idx_sensibilidad"]
t = df[cols].head(n).reset_index(drop=True)

fig = px.bar(
    t.iloc[::-1], x="riesgo_score", y="municipio", color="riesgo_nivel", orientation="h",
    color_discrete_map=B.RIESGO, height=max(420, 18 * len(t)),
    category_orders={"riesgo_nivel": ["Crítico", "Alto", "Medio", "Bajo"]},
    hover_data={"departamento": True, "riesgo_score": ":.3f"})
fig.update_layout(
    margin=dict(l=0, r=10, t=6, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    yaxis_title=None, xaxis_title="Score de priorización",
    legend=dict(orientation="h", y=1.02, x=0, title=None), bargap=0.25)
fig.update_xaxes(gridcolor="#e7efe9")
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

t.index += 1
st.dataframe(
    t.style.format({"riesgo_score": "{:.3f}", "idx_minero": "{:.2f}", "idx_deforestacion": "{:.2f}",
                    "idx_hidrico": "{:.2f}", "idx_sensibilidad": "{:.2f}"}),
    use_container_width=True, height=460)
st.download_button("⬇️ Descargar ranking completo (CSV)",
                   df[cols].to_csv(index=False).encode(), "ranking_aquabosque.csv")
B.footer()
