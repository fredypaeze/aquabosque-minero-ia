import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import branding as B
from glosario import cc
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Incendios", page_icon="🔥", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "data" / "processed" / "municipios.geojson"
FUEGO = ROOT / "data" / "processed" / "fuego_municipal.csv"
QUEMA = ROOT / "data" / "processed" / "area_quemada_municipal.csv"
Q_SUM = ROOT / "data" / "processed" / "area_quemada_summary.json"
F_SUM = ROOT / "data" / "processed" / "fuego_summary.json"
PRED = ROOT / "outputs" / "tables" / "predicciones.csv"


@st.cache_data
def geojson(mtime):
    with open(GEO, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar(mt_f, mt_q, mt_p):
    fuego = pd.read_csv(FUEGO)
    fuego["cod_mpio"] = fuego["cod_mpio"].astype(int)
    quema = pd.read_csv(QUEMA) if QUEMA.exists() else pd.DataFrame()
    if len(quema):
        quema["cod_mpio"] = quema["cod_mpio"].astype(int)
    pred = pd.read_csv(PRED)
    pred["cod_mpio"] = pred["cod_mpio"].astype(float).astype(int)
    return fuego, quema, pred


st.title("🔥 Incendios — mapa nacional de crisis")
st.caption("Capa operativa para la temporada de incendios: **detectar** (focos térmicos NRT, NASA FIRMS), "
           "**medir** (área quemada por dNBR sobre Sentinel-2, procesada en la GPU institucional) y "
           "**priorizar** (cruce con el nivel de riesgo del modelo y la sensibilidad territorial).")

if not FUEGO.exists():
    st.warning("Aún no se ha generado la señal de fuego. Ejecuta `python -m aquabosque.satelital.firms_signal`.")
    st.stop()

fuego, quema, pred = cargar(FUEGO.stat().st_mtime,
                            QUEMA.stat().st_mtime if QUEMA.exists() else 0,
                            PRED.stat().st_mtime)
try:
    f_sum = json.loads(F_SUM.read_text(encoding="utf-8"))
except Exception:
    f_sum = {}
try:
    q_sum = json.loads(Q_SUM.read_text(encoding="utf-8"))
except Exception:
    q_sum = {}

k = st.columns(4)
k[0].metric("🔥 Focos activos (7 días)", f"{int(f_sum.get('total_focos_colombia', fuego.focos_7d.sum())):,}".replace(",", "."),
            help="Focos térmicos detectados por VIIRS (375 m) y MODIS en los últimos 7 días — NASA FIRMS.")
k[1].metric("Municipios con fuego", int((fuego.focos_7d > 0).sum()),
            help="Municipios con al menos un foco en la ventana de 7 días.")
k[2].metric("📏 Área quemada medida", f"{quema.ha_quemada_dnbr.sum():,.0f} ha".replace(",", ".") if len(quema) else "—",
            help="Suma del área quemada medida por dNBR (Sentinel-2, 10 m) en los municipios procesados. Cobertura parcial.")
k[3].metric("Municipios medidos (dNBR)", len(quema) if len(quema) else 0,
            help="Municipios priorizados por potencia radiativa (FRP) con medición satelital de área quemada.")

# ---------------- Mapa nacional ----------------
fuego_map = fuego[fuego.focos_7d > 0]
fig = px.choropleth_map(
    fuego_map, geojson=geojson(GEO.stat().st_mtime), locations="cod_mpio", featureidkey="id",
    color="focos_7d", color_continuous_scale="YlOrRd",
    range_color=(0, float(fuego_map.focos_7d.quantile(0.95))),
    center={"lat": 4.6, "lon": -73.8}, zoom=4.3, opacity=0.8, height=640,
    hover_name="municipio",
    hover_data={"departamento": True, "focos_7d": True, "frp_total": ":.0f", "cod_mpio": False},
    labels={"focos_7d": "Focos 7 días"})
fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0),
                  coloraxis_colorbar=dict(title="Focos 7 días"))

# Municipios con área quemada medida: marcador + etiqueta en hectáreas
if len(quema):
    qq = quema.merge(pred[["cod_mpio", "lat", "lon"]], on="cod_mpio", how="left").dropna(subset=["lat", "lon"])
    fig.add_trace(go.Scattermap(
        lat=qq["lat"], lon=qq["lon"], mode="markers+text", name="Área quemada medida",
        marker=dict(size=(qq["ha_quemada_dnbr"] / qq["ha_quemada_dnbr"].max() * 26 + 10), color="#7f1d1d"),
        text=[f"{m.title()}<br>{h:,.0f} ha".replace(",", ".") for m, h in zip(qq["municipio"], qq["ha_quemada_dnbr"])],
        textposition="top right", textfont=dict(size=11, color="#7f1d1d"),
        hovertemplate="<b>%{text}</b><br>medición dNBR (Sentinel-2)<extra></extra>"))
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
st.caption("Coropleta: focos térmicos de 7 días por municipio (NASA FIRMS, VIIRS + MODIS). "
           "Marcadores vinotinto: municipios con **área quemada medida** por dNBR sobre Sentinel-2 (etiqueta en hectáreas). "
           "Fuente: NASA FIRMS y Copernicus Sentinel-2; cálculos propios. Corte: "
           f"{str(f_sum.get('generado', ''))[:10]}.")

st.divider()

# ---------------- Área quemada medida ----------------
c1, c2 = st.columns([3, 2])
with c1:
    st.markdown("#### 📏 Área quemada medida (Sentinel-2 · dNBR)")
    if len(quema):
        q = quema.sort_values("ha_quemada_dnbr", ascending=False).copy()
        q["ha_txt"] = q["ha_quemada_dnbr"].map(lambda v: f"{v:,.0f}".replace(",", "."))
        st.dataframe(
            q[["municipio", "departamento", "ha_txt", "periodo_antes", "periodo_despues"]]
            .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                             "ha_txt": "Ha quemadas (dNBR ≥ 0,27)",
                             "periodo_antes": "Ventana antes", "periodo_despues": "Ventana después"}),
            hide_index=True, use_container_width=True)
        st.caption("Municipios priorizados por potencia radiativa (FRP) de la crisis de agosto de 2026. "
                   "**Cobertura parcial en expansión**, no censo nacional.")
    else:
        st.info("Aún no hay mediciones de área quemada cargadas (`data/processed/area_quemada_municipal.csv`).")
with c2:
    st.markdown("#### Cómo se mide")
    st.markdown(
        "El **NBR** (Normalized Burn Ratio) usa el infrarrojo de onda corta, sensible al carbón y suelo expuesto:\n\n"
        "$NBR = \\dfrac{NIR - SWIR}{NIR + SWIR}$\n\n"
        "El cambio entre la escena previa y la posterior marca quema:\n\n"
        "$dNBR = NBR_{antes} - NBR_{después} \\;\\geq\\; 0{,}27$\n\n"
        "El umbral 0,27 corresponde a **severidad moderada-alta según el referente USGS**. "
        "Píxeles de 10 m (0,01 ha); SWIR de 20 m remuestreado; escenas con más de 40 % de nube descartadas. "
        "Procesado por mosaicos en la **GPU institucional (NVIDIA L40S)**.")

st.divider()

# ---------------- Priorización: cruce con modelo y sensibilidad ----------------
st.markdown("#### 🎯 Priorización de la respuesta")
mix = pred.drop(columns=[c for c in ["focos_7d", "frp_total", "idx_fuego"] if c in pred.columns]) \
          .merge(fuego[["cod_mpio", "focos_7d", "frp_total"]], on="cod_mpio", how="inner")
mix = mix[mix.focos_7d > 0]

p1, p2 = st.columns(2)
with p1:
    st.markdown("**Fuego activo en municipios de prioridad Alta / Crítica del modelo**")
    st.caption("Donde la presión socioambiental histórica y el fuego actual coinciden.")
    t = (mix[mix.riesgo_nivel.isin(["Alto", "Crítico"])]
         .sort_values("frp_total", ascending=False).head(12)
         [["municipio", "departamento", "riesgo_nivel", "focos_7d", "frp_total"]]
         .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                          "riesgo_nivel": "Nivel modelo", "focos_7d": "Focos 7d", "frp_total": "FRP"}))
    st.dataframe(t, hide_index=True, use_container_width=True,
                 column_config=cc({"Nivel modelo": "nivel", "Focos 7d": "focos", "FRP": "frp"}))
with p2:
    st.markdown("**Fuego activo con área protegida cercana (RUNAP)**")
    st.caption("Municipios con hectáreas protegidas asignadas y fuego en la ventana de 7 días.")
    t = (mix[mix.runap_hectareas > 0]
         .sort_values("frp_total", ascending=False).head(12)
         [["municipio", "departamento", "runap_hectareas", "focos_7d", "frp_total"]]
         .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                          "runap_hectareas": "Ha protegidas", "focos_7d": "Focos 7d", "frp_total": "FRP"}))
    st.dataframe(t, hide_index=True, use_container_width=True,
                 column_config=cc({"Focos 7d": "focos", "FRP": "frp"}))

st.info("**Fuentes:** NASA FIRMS (VIIRS SNPP + NOAA-20, MODIS C6.1) · Copernicus Sentinel-2 L2A · RUNAP · datos abiertos. "
        "**Honestidad:** los focos térmicos son un proxy (incluyen quemas agrícolas); el dNBR mide cambio espectral "
        "consistente con quema y no distingue causa natural o antrópica. La medición dNBR cubre por ahora los "
        "municipios de mayor FRP; el resto del país conserva la señal NRT de focos.")
B.footer()
