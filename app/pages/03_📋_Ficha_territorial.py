from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import branding as B
from glosario import G
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Ficha territorial", page_icon="📋", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
df = pd.read_csv(ROOT / "outputs" / "tables" / "predicciones.csv")

st.title("📋 Ficha territorial por municipio")
m = st.selectbox("Municipio", sorted(df.municipio + " (" + df.departamento + ")"))
row = df[(df.municipio + " (" + df.departamento + ")") == m].iloc[0]
color = B.RIESGO.get(row.riesgo_nivel, "#777")
emoji = {"Crítico": "🔴", "Alto": "🟠", "Medio": "🟡", "Bajo": "🟢"}.get(row.riesgo_nivel, "⚪")

st.markdown(
    f'<div style="background:linear-gradient(120deg,{color} 0%,#12261a 130%);border-radius:16px;'
    f'padding:20px 26px;color:#fff;box-shadow:0 8px 24px rgba(20,60,40,.18);margin-bottom:.4rem">'
    f'<div style="font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;opacity:.85">Ficha de priorización</div>'
    f'<div style="font-size:1.9rem;font-weight:800">{emoji} {row.municipio}, {row.departamento}</div></div>',
    unsafe_allow_html=True)

c = st.columns(4)
c[0].metric("Nivel de riesgo", row.riesgo_nivel, help=G["nivel"])
c[1].metric("Score de priorización", f"{row.riesgo_score:.3f}", help=G["score"])
c[2].metric("Predicción del modelo", row.riesgo_pred, help=G["prediccion"])
c[3].metric("Confianza", f"{row.confianza:.0%}", help=G["confianza"])

izq, der = st.columns([3, 2])
dims = ["Minero", "Deforestación", "Hídrico", "Sensibilidad"]
vals = [row.idx_minero, row.idx_deforestacion, row.idx_hidrico, row.idx_sensibilidad]
with izq:
    st.subheader("Perfil de riesgo por dimensión")
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]], theta=dims + [dims[0]], fill="toself",
        fillcolor="rgba(46,125,50,.22)", line=dict(color=B.VERDE2, width=2)))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 1], gridcolor="#dfeae2"), angularaxis=dict(gridcolor="#dfeae2"),
                   bgcolor="rgba(0,0,0,0)"),
        showlegend=False, height=360, margin=dict(l=40, r=40, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
with der:
    st.subheader("Factor dominante")
    fac = pd.DataFrame({"dim": dims, "val": vals}).sort_values("val", ascending=False)
    top = fac.iloc[0]
    st.markdown(
        f'<div style="background:#fff;border:1px solid #e7efe9;border-left:5px solid {color};'
        f'border-radius:12px;padding:16px 18px;box-shadow:0 4px 14px rgba(20,60,40,.06)">'
        f'<div style="color:#5a6b60;font-size:.85rem">Mayor factor de priorización</div>'
        f'<div style="font-size:1.5rem;font-weight:800;color:#12261a">{top["dim"]}</div>'
        f'<div style="color:#4c5b52">índice {top["val"]:.2f} / 1.00</div></div>',
        unsafe_allow_html=True)
    for _, r in fac.iloc[1:].iterrows():
        st.markdown(f"- {r['dim']}: **{r['val']:.2f}**")

st.info("**Recomendación técnica (no sancionatoria):** este municipio se prioriza para revisión "
        "institucional y monitoreo. La priorización integra señales de datos abiertos y NO constituye "
        "prueba de infracción, causalidad ni ilegalidad.")
B.footer()
