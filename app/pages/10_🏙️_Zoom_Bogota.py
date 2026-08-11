# -*- coding: utf-8 -*-
"""Zoom Bogotá V1 — ÍNDICE TERRITORIAL DE EMERGENCIAS (descriptivo).

Encuadre honesto (Opción A del release): este tablero muestra un ÍNDICE DESCRIPTIVO de
densidad histórica de emergencias asociadas a lluvia (remoción / inundación), geocodificado
por IDIGER (2017–2025). NO es una probabilidad predictiva ni un pronóstico. La lluvia se
muestra como ESCENARIO etiquetado para priorización, no como probabilidad calibrada.
Fuente de verdad: data/processed/bogota_territorial_v1.csv + config/release_zoom_bogota_v1.yaml.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"):
    B = _il.reload(B)

st.set_page_config(page_title="Zoom Bogota — Índice territorial", page_icon="🏙️", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
TERR = ROOT / "data" / "processed" / "bogota_territorial_v1.csv"
TERR_UPZ = ROOT / "data" / "processed" / "bogota_upz_territorial_v1.csv"
GEO_LOC = ROOT / "data" / "processed" / "bogota_localidades.geojson"
GEO_UPZ = ROOT / "data" / "processed" / "bogota_upz.geojson"
VALJSON = ROOT / "outputs" / "rc_v1" / "territorial_index_validation.json"
CFGYML = ROOT / "config" / "release_zoom_bogota_v1.yaml"


@st.cache_data
def cargar():
    if not TERR.exists():
        return None
    d = pd.read_csv(TERR, dtype={"cod": str})
    d["cod"] = d["cod"].str.zfill(2)
    return d


@st.cache_data
def cargar_upz():
    if not (TERR_UPZ.exists() and GEO_UPZ.exists()):
        return None, None
    d = pd.read_csv(TERR_UPZ, dtype={"codigo": str})
    with open(GEO_UPZ, encoding="utf-8") as f:
        g = json.load(f)
    # nombre por UPZ desde el geojson
    nombres = {ft["id"]: ft["properties"].get("upz", ft["id"]) for ft in g["features"]}
    loc_by = {ft["id"]: ft["properties"].get("localidad", "") for ft in g["features"]}
    d["upz"] = d["codigo"].map(nombres).fillna(d["codigo"])
    d["localidad"] = d["codigo"].map(loc_by).fillna("")
    return d, g


@st.cache_data
def cargar_geo(mtime):
    with open(GEO_LOC, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def meta():
    v = json.loads(VALJSON.read_text(encoding="utf-8")) if VALJSON.exists() else {}
    ver = "1.0.0-rc1"
    try:
        import yaml
        ver = yaml.safe_load(CFGYML.read_text(encoding="utf-8"))["contract"]["PRODUCT_VERSION"]
    except Exception:
        pass
    return v, ver


# ---- FAIL-SAFE (Sec 47): si falta el dato, no inventar; avisar ----
terr = cargar()
val, VERSION = meta()
if terr is None:
    st.error("⚠️ No se encuentra el índice territorial (`data/processed/bogota_territorial_v1.csv`). "
             "Ejecute `./venv/bin/python scripts/rc/build_territorial_index.py`. No se muestra información no verificada.")
    st.stop()
geo_loc = cargar_geo(GEO_LOC.stat().st_mtime)
terr_upz, geo_upz = cargar_upz()

periodo = val.get("periodo", ["?", "?"])
COLS = "YlOrRd"

B.hero(
    eyebrow=f"Zoom Bogotá · V{VERSION} · índice DESCRIPTIVO",
    title="Índice territorial de emergencias por lluvia — Bogotá",
    subtitle="Densidad histórica de emergencias (remoción en masa e inundación) por localidad, "
             "<b>geocodificada por IDIGER</b>. Es un índice <b>descriptivo</b> para priorización, "
             "<b>no</b> una probabilidad ni un pronóstico.",
    pills=[{"t": f"IDIGER {periodo[0]}→{periodo[1]}"}, {"t": "20 localidades"}, {"t": "Descriptivo · no predictivo"}],
)

# ---- BANNER de honestidad + FRESHNESS (Sec 48/69) ----
B.note(
    f"<b>¿Qué estás viendo?</b> Un <b>índice descriptivo</b> = cuántas emergencias por lluvia registró "
    f"IDIGER en cada territorio ({periodo[0]} a {periodo[1]}). "
    f"<b>¿Es probabilidad?</b> No. Es densidad histórica observada, útil para <b>priorizar vigilancia</b>. "
    f"<b>Limitación:</b> sesgo de reporte (zonas más pobladas/monitoreadas reportan más). "
    f"<b>Horizonte:</b> ninguno (es histórico, no pronóstico). <b>Territorio:</b> Bogotá D.C."
)

rem = int(terr["eventos_remocion"].sum())
inu = int(terr["eventos_inundacion"].sum())
B.kpis([
    {"lab": "Emergencias remoción", "val": f"{rem:,}".replace(",", "."), "foot": f"IDIGER {periodo[0]}–{periodo[1]}", "acc": B.RIESGO["Alto"]},
    {"lab": "Emergencias inundación", "val": f"{inu:,}".replace(",", "."), "foot": "observado", "acc": B.AGUA},
    {"lab": "Localidades", "val": f"{len(terr)}", "foot": "geocodificación IDIGER", "acc": B.VERDE2},
    {"lab": "Error de georreferenciación", "val": "0 m", "foot": "sin transformación CRS", "acc": "#16a34a"},
])

tab1, tab2, tab3, tab4 = st.tabs(
    ["Mapa del índice", "Ficha por localidad", "Escenario de lluvia", "Metodología y límites"]
)

# ============================================================ TAB 1 — MAPA
with tab1:
    c1, c2 = st.columns([1.3, 1])
    eje = c1.selectbox("Capa", ["Índice total", "Remoción en masa", "Inundación"])
    col = {"Índice total": "idx_territorial_obs", "Remoción en masa": "idx_remocion_obs", "Inundación": "idx_inundacion_obs"}[eje]
    evcol = {"Índice total": "eventos_total", "Remoción en masa": "eventos_remocion", "Inundación": "eventos_inundacion"}[eje]
    usar_upz = c2.radio("Resolución", ["Localidad (20)", "UPZ"], horizontal=True) == "UPZ" and terr_upz is not None

    if usar_upz:
        st.caption("UPZ = **priorización espacial** (densidad histórica por UPZ). No es una probabilidad (Sec 45 del contrato).")
        a = terr_upz.copy()
        fig = px.choropleth_map(a, geojson=geo_upz, locations="codigo", featureidkey="id",
            color=col, color_continuous_scale=COLS, range_color=(0, 1),
            center={"lat": 4.62, "lon": -74.11}, zoom=9.2, opacity=0.82, height=560,
            hover_name="upz", hover_data={"localidad": True, "eventos_remocion": True, "eventos_inundacion": True, "codigo": False})
    else:
        a = terr.copy()
        fig = px.choropleth_map(a, geojson=geo_loc, locations="cod", featureidkey="id",
            color=col, color_continuous_scale=COLS, range_color=(0, 1),
            center={"lat": 4.62, "lon": -74.11}, zoom=9.2, opacity=0.82, height=560,
            hover_name="localidad", hover_data={"eventos_remocion": True, "eventos_inundacion": True, "cod": False})
    fig.update_traces(marker_line_width=0.6, marker_line_color="rgba(255,255,255,.85)")
    fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(f"#### Ranking por {eje.lower()} (emergencias observadas)")
    base = (terr_upz if usar_upz else terr)
    show = base.nlargest(12, evcol)
    cols = (["upz", "localidad"] if usar_upz else ["localidad"]) + ["eventos_remocion", "eventos_inundacion"]
    st.dataframe(show[cols].rename(columns={"upz": "UPZ", "localidad": "Localidad",
        "eventos_remocion": "Remoción", "eventos_inundacion": "Inundación"}), hide_index=True, use_container_width=True)

# ============================================================ TAB 2 — FICHA
with tab2:
    loc = st.selectbox("Localidad", terr.sort_values("localidad")["localidad"].tolist())
    r = terr[terr["localidad"] == loc].iloc[0]
    m1, m2, m3 = st.columns(3)
    m1.metric("Emergencias remoción", int(r["eventos_remocion"]))
    m2.metric("Emergencias inundación", int(r["eventos_inundacion"]))
    m3.metric("Índice territorial (percentil)", f"{r['idx_territorial_obs']:.2f}")
    driver = "Remoción en masa" if r["eventos_remocion"] >= r["eventos_inundacion"] else "Inundación / anegamiento"
    st.markdown(f"**Peligro dominante (histórico):** {driver}")
    bars = px.bar(pd.DataFrame({"Tipo": ["Remoción", "Inundación"],
                                "Emergencias": [r["eventos_remocion"], r["eventos_inundacion"]]}),
                  x="Tipo", y="Emergencias", color="Tipo",
                  color_discrete_map={"Remoción": B.RIESGO["Alto"], "Inundación": B.AGUA}, height=320)
    bars.update_layout(margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})
    st.caption(f"Fuente: IDIGER Bitácora de Emergencias, {periodo[0]}–{periodo[1]}. "
               "Cada conteo es rastreable a registros de la Bitácora (localidad + tipo + fecha).")

# ============================================================ TAB 3 — ESCENARIO
with tab3:
    st.markdown("## Escenario de lluvia — priorización (no es pronóstico)")
    B.note(
        "<b>SYNTHETIC / SCENARIO.</b> Este panel NO predice. Es un ejercicio de priorización: "
        "combina el <b>índice histórico</b> de cada territorio con un <b>supuesto</b> de intensidad de lluvia "
        "que tú defines. Responde: <i>“si llueve fuerte, ¿qué territorios han respondido históricamente con más "
        "emergencias?”</i> — no <i>“qué probabilidad hay”</i>."
    )
    R = st.slider("Supuesto de lluvia (relativo, 0=seco · 100=extremo)", 0, 100, 60, 5)
    factor = R / 100.0
    a = terr.copy()
    a["prioridad_relativa"] = (a["idx_territorial_obs"] * factor).round(3)
    a["banda"] = pd.cut(a["prioridad_relativa"], [-1, 0.15, 0.35, 0.6, 1.01],
                        labels=["Baja", "Media", "Observar", "Prioritaria"])
    ACC = {"Prioritaria": "#b91c1c", "Observar": "#ea580c", "Media": "#eab308", "Baja": "#16a34a"}
    fig = px.choropleth_map(a, geojson=geo_loc, locations="cod", featureidkey="id",
        color="banda", color_discrete_map=ACC, category_orders={"banda": ["Prioritaria", "Observar", "Media", "Baja"]},
        center={"lat": 4.62, "lon": -74.11}, zoom=9.2, opacity=0.82, height=520,
        hover_name="localidad", hover_data={"prioridad_relativa": ":.2f", "eventos_remocion": True, "cod": False})
    fig.update_traces(marker_line_width=0.6, marker_line_color="rgba(255,255,255,.85)")
    fig.update_layout(map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Prioridad relativa = índice histórico × supuesto de lluvia. Es un ORDENAMIENTO para vigilancia, "
               "no una probabilidad. Supuesto declarado; sin modelo predictivo (ver Metodología).")

# ============================================================ TAB 4 — METODOLOGÍA
with tab4:
    st.markdown("## Metodología y límites (transparencia)")
    B.features([
        {"ic": "📓", "h": "De dónde sale", "p": f"IDIGER Bitácora de Emergencias ({periodo[0]}–{periodo[1]}), "
         "geocodificada por IDIGER a localidad/UPZ. Sin transformación de coordenadas (error 0)."},
        {"ic": "🧮", "h": "Qué significa", "p": "Densidad histórica de emergencias por lluvia. Índice = percentil "
         "de eventos observados. Es descriptivo, no probabilidad ni susceptibilidad física."},
        {"ic": "⚠️", "h": "Qué NO es", "p": "No es pronóstico ni alerta temprana calibrada. La resolución UPZ es "
         "priorización, no probabilidad. La lluvia es escenario, no predicción."},
    ])
    st.markdown("### Honestidad sobre el componente predictivo")
    st.markdown(
        "Se evaluó un modelo predictivo por lluvia (XGBoost, ventana estrictamente futura [t+1,t+3]) y se "
        "**descartó como producto**: con la fuga corregida no supera a un baseline territorial "
        "(ROC-AUC 0.735 ≤ 0.740 de territorio-solo; Brier Skill Score 0.035; recall operativo 17%). "
        "Por eso V1 se presenta como **índice descriptivo**, no como pronóstico. "
        "Detalle reproducible en `docs/MODEL_CARD_ZOOM_BOGOTA.md` y `validation/validation_results.json`."
    )
    st.markdown("### Limitaciones materiales")
    st.markdown(
        "- **Sesgo de reporte:** más población/monitoreo → más registros; no es susceptibilidad física.\n"
        "- **Cobertura UPZ ~73%** de los registros trae código de UPZ.\n"
        "- **Capas POT** de amenaza física quedan diferidas hasta reproyectar con el CRS autoritativo de IDECA "
        "(el método afín previo tenía ~57 km de error y fue retirado)."
    )
    st.caption(f"Zoom Bogotá V{VERSION} · fuente de verdad: config + data + validation (reproducible). "
               "Ejecutar `./venv/bin/python validation/run_validation.py` para el estado de validación.")

B.footer()
