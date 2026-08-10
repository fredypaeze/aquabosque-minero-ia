import json
from pathlib import Path

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
DATA = ROOT / "data" / "processed" / "bogota_zoom_demo.csv"
GEO = ROOT / "data" / "processed" / "bogota_localidades.geojson"
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
    df = pd.read_csv(DATA, dtype={"codigo": str})
    return df.sort_values("indice_presion_ecoterritorial_bogota", ascending=False)


@st.cache_data
def cargar_geojson(mtime):
    with open(GEO, encoding="utf-8") as f:
        return json.load(f)


df = cargar()
geo = cargar_geojson(GEO.stat().st_mtime)

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
    "SIRE / IDIGER",
    "SAB Bogotá",
    "AquaBosque · estructura de score",
])

B.note(
    "<b>Estado actual.</b> Esta pantalla ya usa la <b>geometría oficial de localidades de Bogotá</b>. "
    "Los puntajes todavía son <b>ilustrativos</b> y muestran la experiencia objetivo; la siguiente fase "
    "es sustituirlos por un dataset real validado contra SIRE, SAB e IDIGER."
)

crit = int((df.nivel == "Crítico").sum())
alto = int((df.nivel == "Alto").sum())
medio = int((df.nivel == "Medio").sum())
mm72 = int(df.lluvia_72h_mm.max())

B.kpis([
    {"lab": "Localidades oficiales", "val": f"{len(df)}", "foot": "cobertura Bogotá D.C.", "acc": B.AGUA},
    {"lab": "Criticas", "val": crit, "foot": "accion inmediata", "acc": B.RIESGO["Crítico"]},
    {"lab": "Altas", "val": alto, "foot": "seguimiento reforzado", "acc": B.RIESGO["Alto"]},
    {"lab": "Pico lluvia 72h", "val": f"{mm72} mm", "foot": "señal operativa demo", "acc": B.AGUA2},
])

tab1, tab2, tab3 = st.tabs(["Mapa estrategico", "Ficha territorial", "Integracion real"])

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
        st.dataframe(
            d[[
                "localidad",
                "nivel",
                "indice_presion_ecoterritorial_bogota",
                "driver_principal",
                "corredor_estrategico",
                "incidentes_7d",
                "lluvia_72h_mm",
            ]]
            .rename(columns={
                "localidad": "Localidad",
                "nivel": "Nivel",
                "indice_presion_ecoterritorial_bogota": "Indice total",
                "driver_principal": "Driver principal",
                "corredor_estrategico": "Corredor",
                "incidentes_7d": "Incidentes 7d",
                "lluvia_72h_mm": "Lluvia 72h (mm)",
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

B.footer()
