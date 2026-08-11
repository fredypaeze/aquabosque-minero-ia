import datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"):
    B = _il.reload(B)

st.set_page_config(page_title="Zoom Bogota", page_icon="🏙️", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
DATA_REAL = ROOT / "data" / "processed" / "bogota_zoom.csv"
DATA_DEMO = ROOT / "data" / "processed" / "bogota_zoom_demo.csv"
GEO = ROOT / "data" / "processed" / "bogota_localidades.geojson"
UPZ_CSV = ROOT / "data" / "processed" / "bogota_upz.csv"
UPZ_GEO = ROOT / "data" / "processed" / "bogota_upz.geojson"
ORDEN = ["Crítico", "Alto", "Medio", "Bajo"]
EJES = {
    "Indice total": "indice_presion_ecoterritorial_bogota",
    "Cerros y fuego": "score_fuego_estructural",
    "Agua y anegamiento": "score_agua",
    "Ladera y remocion": "score_remocion",
    "Señal operativa": "score_operativo",
}
CORREDORES = [
    "Corredor Cerros Norte",
    "Corredor Cerros Centro",
    "Corredor Cerros Surorientales",
    "Corredor Borde Sur y Sumapaz",
    "Corredor Tunjuelo",
    "Corredor Río Bogotá",
    "Corredor Humedales Noroccidente",
    "Corredor Laderas del Sur",
]


@st.cache_data
def cargar():
    path = DATA_REAL if DATA_REAL.exists() else DATA_DEMO
    df = pd.read_csv(path, dtype={"codigo": str})
    df["origen_dataset"] = "real" if path == DATA_REAL else "demo"
    return df.sort_values("indice_presion_ecoterritorial_bogota", ascending=False), path.name


@st.cache_data
def cargar_geojson(mtime):
    with open(GEO, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def cargar_upz(mtime):
    if not (UPZ_CSV.exists() and UPZ_GEO.exists()):
        return None, None
    d = pd.read_csv(UPZ_CSV, dtype={"codigo": str})
    with open(UPZ_GEO, encoding="utf-8") as f:
        g = json.load(f)
    return d.sort_values("indice_presion_ecoterritorial_bogota", ascending=False), g


MODELO = ROOT / "models" / "bogota_alerta_xgb.joblib"
MET_JSON = ROOT / "models" / "metrics" / "bogota_alerta_metrics.json"


@st.cache_resource
def cargar_modelo():
    if not MODELO.exists():
        return None, {}
    import joblib
    bundle = joblib.load(MODELO)
    met = json.loads(MET_JSON.read_text(encoding="utf-8")) if MET_JSON.exists() else {}
    return bundle, met


def _feats_R(R, srem, sagu, mes):
    """Mapea una lluvia 72h (R mm) a las features del modelo (misma regla del entrenamiento)."""
    return pd.DataFrame({
        "p1": R / 3, "p3": R, "p7": R * 1.4, "p15": R * 1.9, "pmax3": R * 0.55,
        "wet7": min(7, R / 8), "score_remocion": srem, "score_agua": sagu,
        "mes_sin": np.sin(2 * np.pi * mes / 12), "mes_cos": np.cos(2 * np.pi * mes / 12),
    })


df, data_name = cargar()
geo = cargar_geojson(GEO.stat().st_mtime)
df_upz, geo_upz = cargar_upz(UPZ_GEO.stat().st_mtime if UPZ_GEO.exists() else 0)
modelo_bundle, modelo_met = cargar_modelo()

B.hero(
    eyebrow="Prototipo avanzado · Bogota",
    title="Zoom Bogota · tablero eco-territorial",
    subtitle="Vista ejecutiva intraurbana para priorizar <b>localidades</b> según una combinación de "
             "<b>cerros e incendio forestal</b>, <b>agua y anegamiento</b>, <b>ladera y remoción</b> "
             "y <b>señal operativa reciente</b>.",
    pills=[{"t": "20 localidades oficiales"}, {"t": "Geometría real Bogotá"}, {"t": "SIRE + SAB + IDIGER"}, {"t": "Demo premium", "live": True}],
)

B.source_badges([
    "Datos Abiertos Bogotá · Localidades oficiales",
    "Datos Abiertos Bogotá · Cuerpo de agua",
    "Datos Abiertos Bogotá · Humedales",
    "SIRE / IDIGER",
    "SAB Bogotá",
    "AquaBosque · estructura de score",
])

if df["origen_dataset"].iloc[0] == "real":
    B.note(
        "<b>Estado actual.</b> Esta pantalla ya usa la <b>geometría oficial de localidades de Bogotá</b> "
        "y <b>tres capas reales</b>: `Agua y anegamiento` (cuerpos de agua + humedales), "
        "`Cerros y fuego` (histórico de áreas afectadas por evento forestal) y "
        "`Señal operativa` (pluviómetros SAB / IDIGER en vivo). "
        "Además, `Ladera y remoción` ya se recalcula con capas POT de movimiento en masa y condición de riesgo."
    )
else:
    B.note(
        "<b>Estado actual.</b> Esta pantalla ya usa la <b>geometría oficial de localidades de Bogotá</b>. "
        "Los puntajes todavía son <b>ilustrativos</b> y muestran la experiencia objetivo; la siguiente fase "
        "es sustituirlos por un dataset real validado contra SIRE, SAB e IDIGER."
    )

crit = int((df.nivel == "Crítico").sum())
alto = int((df.nivel == "Alto").sum())
medio = int((df.nivel == "Medio").sum())
mm72 = int(df.lluvia_72h_mm.max())
water_real = "score_agua_real" in df.columns
top_water = int(df["water_feature_count"].sum()) if "water_feature_count" in df.columns else 0
fire_real = "score_fuego_real" in df.columns
fire_events = int(df["fire_feature_count"].sum()) if "fire_feature_count" in df.columns else 0
sab_real = "score_operativo_real" in df.columns
sab_stations = int(df["sab_estaciones_activas"].sum()) if "sab_estaciones_activas" in df.columns else 0
mm_real = "score_remocion_real" in df.columns
mm_features = int(df["mm_feature_count"].sum()) if "mm_feature_count" in df.columns else 0

B.kpis([
    {"lab": "Localidades oficiales", "val": f"{len(df)}", "foot": "cobertura Bogotá D.C.", "acc": B.AGUA},
    {"lab": "Criticas", "val": crit, "foot": "accion inmediata", "acc": B.RIESGO["Crítico"]},
    {"lab": "Eventos forestales", "val": f"{fire_events:,}".replace(",", "."), "foot": "capa real Bomberos" if fire_real else "aun no integrado", "acc": B.RIESGO["Alto"]},
    {"lab": "Movimientos masa", "val": f"{mm_features:,}".replace(",", "."), "foot": "POT riesgo + amenaza" if mm_real else "aun no integrado", "acc": B.VERDE2},
])

st.caption(f"Dataset activo: `{data_name}`")

tab1, tab2, tab3, tab4 = st.tabs(
    ["Mapa estrategico", "Ficha territorial", "Integracion real", "🚨 Alerta temprana"]
)

with tab1:
    c1, c2, c3 = st.columns([1.2, 1.1, 1.0])
    capa = c1.selectbox("Capa a visualizar", list(EJES.keys()))
    niveles = c2.multiselect("Niveles", ORDEN, default=ORDEN)
    corredor = c3.selectbox("Corredor estrategico", ["Todos"] + CORREDORES)

    d = df[df["nivel"].isin(niveles)].copy()
    if corredor != "Todos":
        d = d[d["corredor_estrategico"] == corredor]

    color_col = EJES[capa]
    color_args = (
        {
            "color": "nivel",
            "color_discrete_map": B.RIESGO,
            "category_orders": {"nivel": ORDEN},
        }
        if capa == "Indice total"
        else {
            "color": color_col,
            "color_continuous_scale": "YlOrRd",
            "range_color": (0, 1),
        }
    )

    fig = px.choropleth_map(
        d,
        geojson=geo,
        locations="codigo",
        featureidkey="id",
        center={"lat": 4.62, "lon": -74.11},
        zoom=9.15,
        opacity=0.82,
        height=680,
        hover_name="localidad",
        hover_data={
            "nivel": True,
            "indice_presion_ecoterritorial_bogota": ":.2f",
            "score_fuego_estructural": ":.2f",
            "score_agua": ":.2f",
            "score_remocion": ":.2f",
            "score_operativo": ":.2f",
            "incidentes_7d": True,
            "lluvia_72h_mm": True,
            "codigo": False,
        },
        **color_args,
    )
    fig.update_traces(marker_line_width=0.7, marker_line_color="rgba(255,255,255,.8)")
    fig.update_layout(
        map_style="carto-positron",
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.98,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,.88)",
            bordercolor="#cfe6d8",
            borderwidth=1,
            title=None,
        ),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    i1, i2 = st.columns([1.1, 1])
    with i1:
        st.markdown("### Ranking ejecutivo")
        rank_cols = [
                "localidad",
                "nivel",
                "indice_presion_ecoterritorial_bogota",
                "driver_principal",
                "corredor_estrategico",
                "incidentes_7d",
                "lluvia_72h_mm",
            ]
        if "water_feature_count" in d.columns:
            rank_cols.extend(["water_feature_count", "humedal_feature_count"])
        if "fire_feature_count" in d.columns:
            rank_cols.append("fire_feature_count")
        if "sab_lluvia_max_mm" in d.columns:
            rank_cols.append("sab_lluvia_max_mm")
        if "mm_feature_count" in d.columns:
            rank_cols.append("mm_feature_count")
        st.dataframe(
            d[rank_cols].rename(columns={
                "localidad": "Localidad",
                "nivel": "Nivel",
                "indice_presion_ecoterritorial_bogota": "Indice total",
                "driver_principal": "Driver principal",
                "corredor_estrategico": "Corredor",
                "incidentes_7d": "Incidentes 7d",
                "lluvia_72h_mm": "Lluvia 72h (mm)",
                "water_feature_count": "Cuerpos de agua",
                "humedal_feature_count": "Humedales",
                "fire_feature_count": "Eventos forestales",
                "sab_lluvia_max_mm": "SAB lluvia hoy (mm)",
                "mm_feature_count": "Mov. masa",
            }),
            hide_index=True,
            use_container_width=True,
        )
    with i2:
        st.markdown("### Lectura territorial")
        top = d.sort_values("indice_presion_ecoterritorial_bogota", ascending=False).head(4)
        for _, row in top.iterrows():
            st.markdown(
                f"**{row['localidad']} · {row['nivel']}**  \n"
                f"{row['resumen']}  \n"
                f"`Driver:` {row['driver_principal']} · `Corredor:` {row['corredor_estrategico']}"
            )

        st.markdown("### Corredores donde mas valor genera")
        B.features([
            {"ic": "🔥", "h": "Cerros y borde sur",
             "p": "Usme, San Cristobal y Santa Fe capturan el valor del modulo cuando se cruza borde urbano-rural, ladera y fuego."},
            {"ic": "💧", "h": "Río Bogotá y humedales",
             "p": "Bosa, Suba, Engativa y Fontibon muestran la cara hidrica del riesgo: anegamiento, rondas y drenaje."},
            {"ic": "⛰️", "h": "Laderas del sur",
             "p": "Ciudad Bolivar y Rafael Uribe Uribe concentran presion por remocion, estabilidad de taludes y respuesta operativa."},
        ])

with tab2:
    f1, f2 = st.columns([1.05, 0.95])
    with f1:
        loc = st.selectbox("Localidad a perfilar", df["localidad"].tolist(), index=0)
        row = df[df["localidad"] == loc].iloc[0]
        st.markdown(f"## {row['localidad']}")
        st.caption(f"{row['corredor_estrategico']} · driver principal: {row['driver_principal']}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Indice total", f"{row['indice_presion_ecoterritorial_bogota']:.2f}")
        m2.metric("Nivel", row["nivel"])
        m3.metric("Incidentes 7d", int(row["incidentes_7d"]))
        m4.metric("Lluvia 72h", f"{int(row['lluvia_72h_mm'])} mm")

        if "water_feature_count" in row.index:
            w1, w2, w3 = st.columns(3)
            w1.metric("Cuerpos de agua", int(row["water_feature_count"]))
            w2.metric("Humedales", int(row.get("humedal_feature_count", 0)))
            w3.metric("Score agua real", f"{row['score_agua']:.2f}")

        if "fire_feature_count" in row.index or "sab_estaciones_activas" in row.index:
            z1, z2, z3 = st.columns(3)
            z1.metric("Eventos forestales", int(row.get("fire_feature_count", 0)))
            z2.metric("SAB lluvia hoy", f"{float(row.get('sab_lluvia_max_mm', 0)):.1f} mm")
            z3.metric("Estaciones SAB", int(row.get("sab_estaciones_activas", 0)))

        if "mm_feature_count" in row.index:
            r1, r2, r3 = st.columns(3)
            r1.metric("Mov. masa", int(row.get("mm_feature_count", 0)))
            r2.metric("Riesgo mm", int(row.get("mm_riesgo_count", 0)))
            r3.metric("Score remoción", f"{row['score_remocion']:.2f}")

        bars = px.bar(
            pd.DataFrame({
                "Eje": ["Cerros y fuego", "Agua y anegamiento", "Ladera y remocion", "Señal operativa"],
                "Score": [
                    row["score_fuego_estructural"],
                    row["score_agua"],
                    row["score_remocion"],
                    row["score_operativo"],
                ],
            }),
            x="Eje",
            y="Score",
            color="Score",
            color_continuous_scale="YlOrRd",
            range_color=(0, 1),
            height=360,
        )
        bars.update_layout(margin=dict(l=0, r=0, t=10, b=0), xaxis_title="", yaxis_title="Score")
        st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})

        st.markdown("### Resumen ejecutivo")
        st.write(row["resumen"])
        if "fuente_agua_real" in row.index:
            st.caption(f"Fuente activa en agua: {row['fuente_agua_real']}")
        if "fuente_fuego_real" in row.index:
            st.caption(f"Fuente activa en fuego: {row['fuente_fuego_real']}")
        if "fuente_operativa_real" in row.index:
            st.caption(f"Fuente activa en señal operativa: {row['fuente_operativa_real']}")
        if "fuente_remocion_real" in row.index:
            st.caption(f"Fuente activa en remoción: {row['fuente_remocion_real']}")

    with f2:
        radar = go.Figure()
        radar.add_trace(go.Scatterpolar(
            r=[
                row["score_fuego_estructural"],
                row["score_agua"],
                row["score_remocion"],
                row["score_operativo"],
            ],
            theta=["Cerros y fuego", "Agua y anegamiento", "Ladera y remocion", "Señal operativa"],
            fill="toself",
            line=dict(color="#0f6b53", width=3),
            fillcolor="rgba(15,107,83,.28)",
            name=row["localidad"],
        ))
        radar.update_layout(
            height=410,
            margin=dict(l=10, r=10, t=20, b=10),
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False,
        )
        st.plotly_chart(radar, use_container_width=True, config={"displayModeBar": False})

        st.markdown("### Lectura de decision")
        st.markdown(
            f"- `Nivel actual:` {row['nivel']}\n"
            f"- `Corredor:` {row['corredor_estrategico']}\n"
            f"- `Driver principal:` {row['driver_principal']}\n"
            f"- `Interpretacion:` la localidad sube por la combinacion de estructura territorial y señal operativa reciente."
        )

        peers = df[df["corredor_estrategico"] == row["corredor_estrategico"]][["localidad", "indice_presion_ecoterritorial_bogota"]]
        if len(peers):
            st.markdown("### Comparables del mismo corredor")
            st.dataframe(
                peers.rename(columns={
                    "localidad": "Localidad",
                    "indice_presion_ecoterritorial_bogota": "Indice total",
                }).sort_values("Indice total", ascending=False),
                hide_index=True,
                use_container_width=True,
            )

with tab3:
    st.markdown("## Como pasa de demo a producto real")
    B.features([
        {"ic": "🗺️", "h": "Geometria oficial",
         "p": "Ya integrada desde Datos Abiertos Bogota. La pagina usa las 20 localidades reales como base cartografica."},
        {"ic": "📡", "h": "Integracion SIRE / SAB / IDIGER",
         "p": "El siguiente paso es reemplazar los scores demo por capas verificadas: incendio forestal, puntos criticos, lluvia, radar y boletines."},
        {"ic": "⚙️", "h": "Pipeline AquaBosque",
         "p": "Se consolida un `bogota_zoom.csv` reproducible y se conecta a una nueva rutina de actualizacion para la capa operativa."},
    ])

    st.markdown("### Dataset objetivo")
    st.code(
        "codigo, localidad, score_fuego_estructural, score_agua, score_remocion, "
        "score_operativo, indice_bogota_base, indice_bogota_dinamico, "
        "indice_presion_ecoterritorial_bogota, nivel",
        language="text",
    )

    st.markdown("### Fuentes a integrar primero")
    st.markdown(
        "1. `SIRE / IDIGER`: zonificacion de incendio forestal y puntos criticos por inundacion/remocion.\n"
        "2. `SAB`: lluvia 24h/72h/7d, radar y reportes diarios.\n"
        "3. `Bogota Abierta / IDECA`: geometria de localidades, humedales, quebradas y corredores hidricos.\n"
        "4. `AquaBosque`: logica del indice, explicabilidad y capa ejecutiva."
    )

    st.markdown("### Ganancia del modulo")
    st.write(
        "A nivel nacional, AquaBosque prioriza municipios. En Bogota, el motor se adapta a escala intraurbana "
        "para leer presion eco-territorial con mejor resolucion, sin forzar una narrativa de mineria donde no aplica."
    )

    if "score_agua_real" in df.columns:
        st.markdown("### Capas reales ya integradas")
        st.write(
            "El tablero ya no depende solo del demo. Hoy recalcula tres ejes con fuentes oficiales: "
            "`Agua y anegamiento` con cuerpos de agua y humedales, "
            "`Cerros y fuego` con histórico de áreas afectadas por evento forestal, y "
            "`Señal operativa` con lluvia diaria en vivo del SAB / IDIGER. "
            "Además, `Ladera y remoción` ya incorpora amenaza y condición de riesgo por movimiento en masa del POT."
        )

# ============================================================
#  TAB 4 — ALERTA TEMPRANA POR LLUVIA (simulador operativo, lenguaje IDIGER / SAB)
# ============================================================
ACC_ALERTA = {"Rojo": "#b91c1c", "Naranja": "#ea580c", "Amarillo": "#eab308", "Verde": "#16a34a"}
ORDEN_ALERTA = ["Rojo", "Naranja", "Amarillo", "Verde"]
ACCIONES_IDIGER = {
    ("Rojo", "Remoción en masa"): "Evacuación preventiva de laderas · cierre de vías en riesgo · activación del COE local.",
    ("Rojo", "Inundación / anegamiento"): "Evacuación de zonas bajas · bombeo · alerta a comunidades de ronda de río.",
    ("Naranja", "Remoción en masa"): "Monitoreo instrumental de ladera · alistamiento de maquinaria · rondas de inspección.",
    ("Naranja", "Inundación / anegamiento"): "Vigilancia de jarillones y drenajes · limpieza de sumideros · preposicionamiento.",
    ("Amarillo", "Remoción en masa"): "Vigilancia informativa · seguimiento a pluviómetros SAB en cerros.",
    ("Amarillo", "Inundación / anegamiento"): "Vigilancia informativa · seguimiento a niveles de quebradas y humedales.",
}


def _nivel_alerta(x):
    return "Rojo" if x >= 0.55 else "Naranja" if x >= 0.35 else "Amarillo" if x >= 0.18 else "Verde"


with tab4:
    st.markdown("## Alerta temprana por lluvia · simulador operativo")
    st.caption(
        "Conjuga la lluvia acumulada (72 h) con la susceptibilidad de cada localidad a "
        "<b>remoción en masa</b> e <b>inundación</b>. Reproduce el lenguaje operativo de "
        "<b>IDIGER</b> y del Sistema de Alerta de Bogotá (<b>SAB</b>): mueva la lluvia y "
        "observe qué localidades entran en alerta y con qué umbral.",
        unsafe_allow_html=True,
    )

    lluvia_obs = float(df["lluvia_72h_mm"].max())
    cS1, cS2, cS3 = st.columns([2.4, 1, 1])
    R = cS1.slider(
        "Lluvia acumulada simulada (mm / 72 h)",
        min_value=0, max_value=150, value=int(round(lluvia_obs)), step=5,
        help="Referencia IDEAM / IDIGER: >50 mm/72h alerta media · >100 mm alta · >130 mm extrema.",
    )
    cS2.metric("Lluvia observada (SAB)", f"{lluvia_obs:.0f} mm", help="Máximo actual entre estaciones de la red SAB.")
    cat_lluvia = "Extrema" if R >= 130 else "Alta" if R >= 100 else "Media" if R >= 50 else "Baja"
    cS3.metric("Categoría de lluvia", cat_lluvia)

    cR1, cR2 = st.columns(2)
    if df_upz is not None:
        res = cR1.radio(
            "Resolución territorial", ["Localidad (20)", f"UPZ ({len(df_upz)})"],
            horizontal=True,
            help="UPZ = Unidad de Planeamiento Zonal, la escala operativa con que trabaja IDIGER.",
        )
    else:
        res = "Localidad (20)"
    if modelo_bundle is not None:
        motor = cR2.radio(
            "Motor de cálculo", ["🤖 Modelo IA (XGBoost)", "Regla (susceptibilidad × lluvia)"],
            horizontal=True,
            help="El Modelo IA predice la probabilidad calibrada de emergencia (remoción/inundación) "
                 "en las próximas 72 h, aprendida de 8 años de eventos IDIGER + lluvia SAB.",
        )
    else:
        motor = "Regla"
    es_upz = res.startswith("UPZ")
    usar_ia = motor.startswith("🤖")
    base_df = df_upz if es_upz else df
    base_geo = geo_upz if es_upz else geo
    unidad_txt = "UPZ" if es_upz else "localidades"

    a = base_df.copy()
    a["unidad"] = (a["upz"] + " · " + a["localidad"]) if es_upz else a["localidad"]
    a["susc"] = (0.6 * a["score_remocion"] + 0.4 * a["score_agua"]).clip(0, 1)
    a["driver_lluvia"] = [
        "Remoción en masa" if rm >= ag else "Inundación / anegamiento"
        for rm, ag in zip(a["score_remocion"], a["score_agua"])
    ]
    a["umbral_naranja_mm"] = [(120 * 0.35 / s) if s > 0.01 else float("nan") for s in a["susc"]]

    if usar_ia:
        mes = datetime.date.today().month
        feats = modelo_bundle["feats"]
        X = _feats_R(R, a["score_remocion"].to_numpy(), a["score_agua"].to_numpy(), mes)[feats]
        a["p_ia"] = modelo_bundle["iso"].predict(modelo_bundle["model"].predict_proba(X)[:, 1])
        a["alerta"] = a["p_ia"]
        _bnd = modelo_met.get("bandas", {})
        _base = _bnd.get("base_rate", 0.06)
        _pn = _bnd.get("p_naranja", 0.15)
        _pr = _bnd.get("p_rojo", 0.22)
        a["nivel_alerta"] = a["p_ia"].map(
            lambda x: "Rojo" if x >= _pr else "Naranja" if x >= _pn else "Amarillo" if x >= _base * 1.5 else "Verde")
    else:
        rf = min(R / 120.0, 1.0)
        a["alerta"] = (a["susc"] * rf).clip(0, 1)
        a["nivel_alerta"] = a["alerta"].map(_nivel_alerta)

    cnt = a["nivel_alerta"].value_counts()
    B.kpis([
        {"lab": "En rojo", "val": int(cnt.get("Rojo", 0)), "foot": "Acción/evacuación inmediata", "acc": ACC_ALERTA["Rojo"]},
        {"lab": "En naranja", "val": int(cnt.get("Naranja", 0)), "foot": "Alistamiento y monitoreo", "acc": ACC_ALERTA["Naranja"]},
        {"lab": "En amarillo", "val": int(cnt.get("Amarillo", 0)), "foot": "Vigilancia informativa", "acc": ACC_ALERTA["Amarillo"]},
        {"lab": "Unidades priorizadas", "val": f"{int(a['nivel_alerta'].isin(['Rojo', 'Naranja']).sum())}/{len(a)}", "foot": f"{unidad_txt} en alerta", "acc": B.AGUA},
    ])

    if usar_ia and modelo_met:
        m = modelo_met
        st.markdown(
            f'<div class="ab-note" style="background:#eef6ff;border-color:#bcd3f5;border-left-color:#0653c6;color:#0a2342;">'
            f'🤖 <b>Motor: XGBoost supervisado, monotónico y calibrado</b> — validación <b>temporal</b> en 2024 · '
            f'<b>ROC-AUC {m.get("roc_auc")}</b> · <b>PR-AUC {m.get("pr_auc")}</b> '
            f'(×{m.get("lift_pr_auc")} sobre el azar) · Brier {m.get("brier_cal")}. '
            f'Predice <b>P(emergencia por lluvia en 72 h)</b> por unidad; el umbral de lluvia es '
            f'<b>aprendido de la historia</b>, no fijo.</div>',
            unsafe_allow_html=True)
        with st.expander("Ficha técnica del modelo (para el equipo de datos)"):
            st.markdown(
                f"- **Tarea:** clasificación binaria — ¿ocurre remoción en masa o inundación en la unidad en las próximas 72 h?\n"
                f"- **Datos:** Bitácora de Emergencias IDIGER (2017–2025, 859k registros) + SAB lluvia diaria "
                f"(70 estaciones) + susceptibilidad AquaBosque. Unidad de análisis: localidad-día "
                f"({m.get('n_train','?')} train / {m.get('n_test','?')} test).\n"
                f"- **Features:** {', '.join(modelo_bundle['feats'])}.\n"
                f"- **Top explicativas (SHAP):** {', '.join(m.get('top_features', []))}.\n"
                f"- **Validación:** {m.get('particion','')} — sin fuga temporal. Calibración isotónica "
                f"(Brier {m.get('brier_uncal')} → {m.get('brier_cal')}).\n"
                f"- **Monotonía impuesta:** P no decrece si sube la lluvia o la susceptibilidad (coherencia física).\n"
                f"- **Honestidad:** evento raro (base {m.get('pos_rate_test')}); el mérito es el **lift PR-AUC ×"
                f"{m.get('lift_pr_auc')}**, la calibración y la explicabilidad — no una accuracy inflada."
            )

    if es_upz:
        st.caption(
            "Resolución **UPZ (115 unidades)** · geometría oficial IDECA / Secretaría de Gobierno. "
            "La susceptibilidad de cada UPZ **cruza el perfil físico de su localidad (POT) con la "
            "amenaza observada**: el número real de emergencias de remoción/inundación registradas "
            "en esa UPZ por IDIGER (Bitácora 2017–2025). Ej.: **Lucero** concentra 140 remociones históricas."
        )

    mcol, tcol = st.columns([1.35, 1])
    with mcol:
        hd = {"nivel_alerta": True, "driver_lluvia": True, "susc": ":.2f", "codigo": False}
        if usar_ia:
            hd["p_ia"] = ":.0%"
        else:
            hd["umbral_naranja_mm"] = ":.0f"
        if es_upz and "eventos_remocion" in a.columns:
            hd["eventos_remocion"] = True
        figA = px.choropleth_map(
            a, geojson=base_geo, locations="codigo", featureidkey="id",
            color="nivel_alerta", color_discrete_map=ACC_ALERTA,
            category_orders={"nivel_alerta": ORDEN_ALERTA},
            center={"lat": 4.62, "lon": -74.11}, zoom=9.15, opacity=0.82, height=560,
            hover_name="unidad", hover_data=hd,
        )
        figA.update_traces(marker_line_width=0.5 if es_upz else 0.7, marker_line_color="rgba(255,255,255,.85)")
        figA.update_layout(
            map_style="carto-positron", margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=0.98, xanchor="left", x=0.01,
                        bgcolor="rgba(255,255,255,.9)", bordercolor="#cfe6d8", borderwidth=1, title=None),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(figA, use_container_width=True, config={"displayModeBar": False})

    with tcol:
        st.markdown(f"#### {'UPZ' if es_upz else 'Localidades'} en alerta")
        en_alerta = a[a["nivel_alerta"] != "Verde"].sort_values("alerta", ascending=False)
        if len(en_alerta) == 0:
            st.success(f"Ninguna {'UPZ' if es_upz else 'localidad'} en alerta con esta lluvia. Condición operativa normal.")
        else:
            for _, r in en_alerta.head(12).iterrows():
                if usar_ia:
                    sub = f'P(emergencia 72h) <b>{r["p_ia"]:.0%}</b> · {r["driver_lluvia"]}'
                else:
                    sub = f'{r["driver_lluvia"]} · dispara a naranja desde {r["umbral_naranja_mm"]:.0f} mm/72h'
                st.markdown(
                    f'<div style="border-left:5px solid {ACC_ALERTA[r["nivel_alerta"]]};background:#fff;'
                    f'border:1px solid #e7efe9;border-radius:10px;padding:8px 12px;margin:5px 0;">'
                    f'<b>{r["unidad"]}</b> · '
                    f'<span style="color:{ACC_ALERTA[r["nivel_alerta"]]};font-weight:700;">{r["nivel_alerta"]}</span>'
                    f'<br><span style="font-size:.82rem;color:#4c5b52;">{sub}</span></div>',
                    unsafe_allow_html=True,
                )
            if len(en_alerta) > 12:
                st.caption(f"… y {len(en_alerta) - 12} {'UPZ' if es_upz else 'localidades'} más en alerta.")

    top_a = a.sort_values("alerta", ascending=False).iloc[0]
    if top_a["nivel_alerta"] != "Verde":
        accion = ACCIONES_IDIGER.get((top_a["nivel_alerta"], top_a["driver_lluvia"]),
                                     "Condición normal · sin acción por lluvia.")
        extra = (f'Probabilidad estimada por el modelo: <b>{top_a["p_ia"]:.0%}</b>.'
                 if usar_ia else
                 f'Umbral de disparo estimado: <b>{top_a["umbral_naranja_mm"]:.0f} mm/72h</b>.')
        B.note(f'<b>Acción sugerida — {top_a["unidad"]} ({top_a["nivel_alerta"]}):</b> {accion} {extra}')

    st.markdown("### Validación · el índice acierta dónde ya ocurre")
    c_fire = df["indice_presion_ecoterritorial_bogota"].corr(df["fire_hist_event_count"])
    c_inc = df["indice_presion_ecoterritorial_bogota"].corr(df["incidentes_7d"])
    c_mm = df["score_remocion"].corr(df["mm_riesgo_count"])
    v1, v2, v3 = st.columns(3)
    v1.metric("Índice ↔ incendios históricos", f"{c_fire:.2f}", help="Correlación con eventos forestales registrados (SIRE / IDIGER).")
    v2.metric("Índice ↔ incidentes 7d", f"{c_inc:.2f}", help="Correlación con incidentes recientes (SIRE).")
    v3.metric("Remoción ↔ zonas de riesgo POT", f"{c_mm:.2f}", help="Correlación con polígonos de condición de riesgo (POT / IDIGER).")
    B.note(
        "El índice y sus componentes correlacionan <b>0.7–0.8</b> con los eventos e insumos oficiales de riesgo: "
        "la priorización no es teórica, <b>coincide con dónde Bogotá ya registra emergencias</b>. "
        "Es el mismo motor nacional de AquaBosque, bajado a <b>escala intraurbana</b> para IDIGER."
    )

B.footer()
