from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Alertas anticipatorias", page_icon="🚀", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / "outputs" / "tables"

st.title("🚀 Alertas anticipatorias")
st.caption("De 'dónde hay riesgo' a 'dónde va a empeorar, dónde hay actividad informal y qué ve la IA que el índice no'. "
           "Priorización técnica para acción temprana — no constituye sanción.")

tab1, tab2, tab3 = st.tabs(["⏩ Velocidad de degradación", "⛏️ Minería informal", "🔬 Anomalías ocultas"])

# ------------------------------------------------------------------ 1) VELOCIDAD
with tab1:
    vel = pd.read_csv(T / "velocidad_degradacion.csv")
    acel = int((vel["dinamica"] == "Acelerando").sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("Municipios con serie temporal", len(vel))
    c2.metric("Acelerando (+300 ha/año o más)", acel)
    c3.metric("Peor aceleración", f"+{vel['aceleracion_ha_ano'].max():,.0f} ha/año")
    st.markdown("**No solo dónde hay deforestación — dónde está *acelerando*.** Tendencia y aceleración 2017–2021; "
                "la aceleración anticipa dónde intervenir antes de que se dispare.")
    top = vel.sort_values("aceleracion_ha_ano", ascending=False).head(20)
    fig = px.bar(top.iloc[::-1], x="aceleracion_ha_ano", y="municipio", orientation="h",
                 color="dinamica", color_discrete_map={"Acelerando": "#ce1126", "Al alza": "#ea580c",
                 "Estable/baja": "#94a3b8", "Desacelerando": "#16a34a"},
                 height=max(420, 20 * len(top)), hover_data={"departamento": True, "defo_ultimo_ano_ha": ":,.0f"})
    fig.update_layout(margin=dict(l=0, r=10, t=6, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      yaxis_title=None, xaxis_title="Aceleración de la deforestación (ha/año)",
                      legend=dict(orientation="h", y=1.02, title=None))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(vel.sort_values("aceleracion_ha_ano", ascending=False).reset_index(drop=True), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ 2) MINERÍA
with tab2:
    ile = pd.read_csv(T / "alertas_mineria_ilegal.csv")
    al = ile[ile["alerta_informalidad"]] if "alerta_informalidad" in ile.columns else ile.head(20)
    c1, c2, c3 = st.columns(3)
    c1.metric("Municipios de alta presión extractiva", len(ile))
    c2.metric("Alertas de brecha de formalización", len(al))
    c3.metric("En riesgo Crítico", int((al["riesgo_nivel"] == "Crítico").sum()))
    st.markdown("**Brecha de formalización = presión extractiva alta con formalización baja** (RUCOM + proyectos ANM + títulos). "
                "Señala posible **actividad minera informal/ilegal** — prioridad para verificación en terreno.")
    fig = px.scatter(ile, x="formalizacion", y="presion_extractiva", color="riesgo_nivel",
                     color_discrete_map=B.RIESGO, size=ile["brecha_formalizacion"].clip(lower=0.01),
                     hover_name="municipio", hover_data={"departamento": True, "brecha_formalizacion": ":.2f"},
                     height=460, category_orders={"riesgo_nivel": ["Crítico", "Alto", "Medio", "Bajo"]})
    fig.update_layout(margin=dict(l=0, r=10, t=6, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      xaxis_title="Formalización (percentil)", yaxis_title="Presión extractiva (percentil)",
                      legend=dict(orientation="h", y=1.02, title=None))
    fig.add_shape(type="line", x0=0, y0=0.75, x1=0.35, y1=0.75, line=dict(color="#ce1126", dash="dot"))
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("**Alertas prioritarias (mayor brecha):**")
    st.dataframe(al[["municipio", "departamento", "presion_extractiva", "formalizacion",
                     "brecha_formalizacion", "riesgo_nivel", "rucom_registros", "anm_proyectos"]].reset_index(drop=True),
                 use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ 3) ANOMALÍAS
with tab3:
    an = pd.read_csv(T / "anomalias_explicadas.csv")
    ocultas = an[an["oculta_para_indice"]] if "oculta_para_indice" in an.columns else an
    c1, c2 = st.columns(2)
    c1.metric("Anomalías detectadas (Isolation Forest)", len(an))
    c2.metric("Ocultas para el índice (nivel Bajo/Medio)", len(ocultas))
    st.markdown("**Lo que la IA ve y el índice no.** El detector no supervisado marca municipios atípicos que el índice de "
                "riesgo *no prioriza* (quedan en nivel Bajo/Medio). La mayoría se explican por **estrés hídrico** — una "
                "dimensión que el índice, dominado por minería y deforestación, pasa por alto.")
    st.dataframe(ocultas[["municipio", "departamento", "riesgo_nivel", "factor_dominante", "explicacion", "score_anomalia"]]
                 .reset_index(drop=True), use_container_width=True, hide_index=True)
    with st.expander("Ver todas las anomalías (57) con su factor explicativo"):
        st.dataframe(an[["municipio", "departamento", "riesgo_nivel", "factor_dominante", "explicacion",
                         "score_anomalia", "oculta_para_indice"]].reset_index(drop=True),
                     use_container_width=True, hide_index=True)

st.divider()
st.caption("Fuente: modelos de AquaBosque sobre dato oficial (IDEAM, FIRMS, ANM, RUCOM, RUNAP). "
           "Velocidad: deforestación 2017–2021. Minería: brecha de formalización (RUCOM/ANM/títulos). "
           "Anomalías: Isolation Forest + explicación por desviación de índices.")
