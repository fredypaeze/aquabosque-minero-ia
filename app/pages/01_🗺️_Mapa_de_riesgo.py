import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Mapa de riesgo", page_icon="🗺️", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]


@st.cache_data
def cargar():
    df = pd.read_csv(ROOT / "outputs" / "tables" / "predicciones.csv")
    df["cod_mpio"] = df["cod_mpio"].astype(float).astype(int)
    return df


GEO = ROOT / "data" / "processed" / "municipios.geojson"


@st.cache_data
def geojson(mtime):  # mtime en la firma: invalida el cache al cambiar el archivo
    with open(GEO, encoding="utf-8") as f:
        return json.load(f)


df = cargar()
ORDEN = ["Crítico", "Alto", "Medio", "Bajo"]

st.title("🗺️ Mapa nacional de riesgo ambiental")
st.caption("Municipios de Colombia coloreados por nivel de priorización. "
           "La priorización integra datos abiertos y no implica causalidad ni ilegalidad.")

c = st.columns([2, 3, 2])
dep = c[0].selectbox("Departamento", ["Todos"] + sorted(df.departamento.dropna().unique()))
niv = c[1].multiselect("Niveles a mostrar", ORDEN, default=ORDEN)
vista = c[2].radio("Vista", ["Polígonos", "Puntos"], horizontal=True)

d = df.copy()
if dep != "Todos":
    d = d[d.departamento == dep]
if niv:
    d = d[d.riesgo_nivel.isin(niv)]

k = st.columns(4)
k[0].metric("Municipios en vista", f"{len(d):,}".replace(",", "."))
k[1].metric("🔴 Crítico", int((d.riesgo_nivel == "Crítico").sum()))
k[2].metric("🟠 Alto", int((d.riesgo_nivel == "Alto").sum()))
k[3].metric("Score máx.", f"{d.riesgo_score.max():.3f}" if len(d) else "—")

centro = {"lat": 4.6, "lon": -73.8}
comun = dict(color="riesgo_nivel", color_discrete_map=B.RIESGO,
             category_orders={"riesgo_nivel": ORDEN}, hover_name="municipio", height=650)

if vista == "Polígonos":
    fig = px.choropleth_map(
        d, geojson=geojson(GEO.stat().st_mtime), locations="cod_mpio", featureidkey="id",
        center=centro, zoom=4.3, opacity=0.72, **comun,
        hover_data={"departamento": True, "riesgo_score": ":.3f",
                    "riesgo_nivel": True, "cod_mpio": False})
    fig.update_traces(marker_line_width=0.2, marker_line_color="rgba(255,255,255,.5)")
else:
    fig = px.scatter_map(
        d, lat="lat", lon="lon", size="riesgo_score", size_max=20,
        center=centro, zoom=4.3, opacity=0.82, **comun,
        hover_data={"departamento": True, "riesgo_score": ":.3f", "riesgo_nivel": True})

fig.update_layout(
    map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0),
    legend=dict(orientation="h", yanchor="bottom", y=0.97, xanchor="left", x=0.01,
                bgcolor="rgba(255,255,255,.88)", bordercolor="#cfe6d8", borderwidth=1,
                title=None, font=dict(size=12)),
    paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

top = d.sort_values("riesgo_score", ascending=False).head(5)
if len(top):
    st.markdown("**Top 5 en la vista actual**")
    st.dataframe(
        top[["municipio", "departamento", "riesgo_nivel", "riesgo_score"]]
        .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                         "riesgo_nivel": "Nivel", "riesgo_score": "Score"}),
        hide_index=True, use_container_width=True)
B.footer()
