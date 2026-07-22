import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Monitoreo satelital NRT", page_icon="🛰️", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "data" / "processed" / "municipios.geojson"
FUEGO = ROOT / "data" / "processed" / "fuego_municipal.csv"
PRED = ROOT / "outputs" / "tables" / "predicciones.csv"
SUMMARY = ROOT / "data" / "processed" / "fuego_summary.json"


@st.cache_data
def geojson(mtime):
    with open(GEO, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar(mtime_f, mtime_p):
    fuego = pd.read_csv(FUEGO)
    pred = pd.read_csv(PRED)
    pred["cod_mpio"] = pred["cod_mpio"].astype(float).astype(int)
    fuego["cod_mpio"] = fuego["cod_mpio"].astype(int)
    return fuego, pred


st.title("🛰️ Monitoreo satelital · near-real-time")
st.caption("Focos de calor activos (sensores satelitales VIIRS 375 m + MODIS, NASA FIRMS) agregados por municipio, "
           "últimos 7 días. Los focos son un **proxy de frontera de deforestación y quema**. Señal térmica NRT, "
           "no clasificación de imagen cruda (eso es la capa de deep learning sobre Sentinel-2).")

if not FUEGO.exists():
    st.warning("Aún no se ha generado la señal satelital. Ejecuta "
               "`python -m aquabosque.satelital.firms_signal`.")
    st.stop()

fuego, pred = cargar(FUEGO.stat().st_mtime, PRED.stat().st_mtime)

try:
    resumen = json.loads(SUMMARY.read_text(encoding="utf-8"))
except Exception:
    resumen = {}

# --- Cruce con el modelo: prioridad combinada ---
# predicciones.csv ya trae focos_7d/idx_fuego (features del modelo): se descartan
# para tomar la señal fresca de fuego_municipal.csv sin colisión de columnas.
pred = pred.drop(columns=[c for c in ["focos_7d", "frp_total", "idx_fuego"] if c in pred.columns])
mix = pred.merge(fuego[["cod_mpio", "focos_7d", "frp_total", "idx_fuego", "ultima_fecha"]],
                 on="cod_mpio", how="left")
mix[["focos_7d", "frp_total", "idx_fuego"]] = mix[["focos_7d", "frp_total", "idx_fuego"]].fillna(0)
prioridad_max = mix[(mix.riesgo_nivel.isin(["Alto", "Crítico"])) & (mix.focos_7d > 0)]
nuevos = mix[(mix.frp_total > 200) & (mix.riesgo_nivel.isin(["Bajo", "Medio"]))]

k = st.columns(4)
k[0].metric("🔥 Focos (7 días)", f"{int(resumen.get('total_focos_colombia', fuego.focos_7d.sum())):,}".replace(",", "."))
k[1].metric("Municipios con fuego", int((fuego.focos_7d > 0).sum()))
k[2].metric("⚠️ Prioridad máxima", len(prioridad_max),
            help="Municipios Alto/Crítico del modelo QUE ADEMÁS tienen fuego activo ahora.")
k[3].metric("🆕 Actividad nueva", len(nuevos),
            help="Fuego intenso (FRP>200) en municipios que el índice estático no priorizaba.")

# --- Mapa ---
fuego_map = fuego[fuego.focos_7d > 0]
fig = px.choropleth_map(
    fuego_map, geojson=geojson(GEO.stat().st_mtime), locations="cod_mpio", featureidkey="id",
    color="focos_7d", color_continuous_scale="YlOrRd", range_color=(0, fuego_map.focos_7d.quantile(0.95)),
    center={"lat": 4.6, "lon": -73.8}, zoom=4.3, opacity=0.8, height=620,
    hover_name="municipio",
    hover_data={"departamento": True, "focos_7d": True, "frp_total": ":.0f", "cod_mpio": False},
    labels={"focos_7d": "Focos 7d"})
fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0),
                  paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

col1, col2 = st.columns(2)
with col1:
    st.markdown("#### ⚠️ Prioridad máxima de verificación")
    st.caption("El modelo los prioriza **y** el satélite confirma fuego activo ahora.")
    st.dataframe(
        prioridad_max.sort_values("frp_total", ascending=False)
        .head(12)[["municipio", "departamento", "riesgo_nivel", "focos_7d", "frp_total"]]
        .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                         "riesgo_nivel": "Nivel modelo", "focos_7d": "Focos 7d", "frp_total": "FRP"}),
        hide_index=True, use_container_width=True)
with col2:
    st.markdown("#### 🆕 Actividad reciente no capturada por el índice estático")
    st.caption("Fuego intenso donde los datos históricos (2017-2021) no marcaban prioridad. "
               "El valor de la capa NRT: ver lo que el modelo estático no ve.")
    st.dataframe(
        nuevos.sort_values("frp_total", ascending=False)
        .head(12)[["municipio", "departamento", "riesgo_nivel", "focos_7d", "frp_total"]]
        .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                         "riesgo_nivel": "Nivel modelo", "focos_7d": "Focos 7d", "frp_total": "FRP"}),
        hide_index=True, use_container_width=True)

st.info("**Fuente:** NASA FIRMS (VIIRS SNPP + NOAA-20, MODIS C6.1) · datos abiertos · actualización diaria. "
        "**Honestidad:** señal satelital térmica NRT (proxy de deforestación/quema); la detección de deforestación "
        "por clasificación de imagen Sentinel-2 con deep learning corre en la infraestructura GPU del Ministerio (capa 2).")
B.footer()
