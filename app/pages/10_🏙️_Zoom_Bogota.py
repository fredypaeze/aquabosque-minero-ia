from pathlib import Path

import pandas as pd
import plotly.express as px
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
ORDEN = ["Crítico", "Alto", "Medio", "Bajo"]
EJES = {
    "Cerros y fuego": "score_fuego_estructural",
    "Agua y anegamiento": "score_agua",
    "Ladera y remocion": "score_remocion",
    "Señal operativa": "score_operativo",
}


@st.cache_data
def cargar():
    df = pd.read_csv(DATA)
    return df.sort_values("indice_presion_ecoterritorial_bogota", ascending=False)


df = cargar()

B.hero(
    eyebrow="Demo conceptual · Bogota",
    title="Zoom Bogota · presion eco-territorial",
    subtitle="Prototipo de como se veria la extension de AquaBosque para Bogota: "
             "una lectura por localidad que combina <b>cerros e incendios</b>, <b>agua</b>, "
             "<b>ladera</b> y <b>senal operativa</b> reciente.",
    pills=[{"t": "Demo visual"}, {"t": f"{len(df)} localidades"}, {"t": "SIRE + SAB + IDIGER"}, {"t": "MVP por localidad", "live": True}],
)

B.note(
    "<b>Demo ilustrativo.</b> Los valores de esta pagina son una simulacion de producto para mostrar "
    "la experiencia deseada. La siguiente fase es reemplazarlos por capas verificadas de "
    "<b>SIRE, SAB e IDIGER</b>."
)

st.markdown("## Vista ejecutiva")
B.kpis([
    {"lab": "Localidades demo", "val": f"{len(df)}", "foot": "muestra ilustrativa inicial", "acc": B.AGUA},
    {"lab": "Prioridad critica", "val": int((df.nivel == "Crítico").sum()), "foot": "intervencion inmediata", "acc": B.RIESGO["Crítico"]},
    {"lab": "Prioridad alta", "val": int((df.nivel == "Alto").sum()), "foot": "seguimiento reforzado", "acc": B.RIESGO["Alto"]},
    {"lab": "Lluvia 72h max", "val": f"{int(df.lluvia_72h_mm.max())} mm", "foot": "senal dinamica ejemplo", "acc": B.AGUA2},
])

c1, c2, c3 = st.columns([1.15, 1.1, 0.95])
eje = c1.selectbox("Eje a resaltar", list(EJES.keys()))
niveles = c2.multiselect("Niveles", ORDEN, default=ORDEN)
vista = c3.radio("Mapa", ["Score total", "Eje seleccionado"], horizontal=True)

d = df[df["nivel"].isin(niveles)].copy()
col_color = "indice_presion_ecoterritorial_bogota" if vista == "Score total" else EJES[eje]

fig = px.scatter_map(
    d,
    lat="lat",
    lon="lon",
    color="nivel",
    size=col_color,
    size_max=35,
    hover_name="localidad",
    hover_data={
        "indice_presion_ecoterritorial_bogota": ":.2f",
        "score_fuego_estructural": ":.2f",
        "score_agua": ":.2f",
        "score_remocion": ":.2f",
        "score_operativo": ":.2f",
        "incidentes_7d": True,
        "lluvia_72h_mm": True,
        "lat": False,
        "lon": False,
    },
    category_orders={"nivel": ORDEN},
    color_discrete_map=B.RIESGO,
    center={"lat": 4.61, "lon": -74.10},
    zoom=9.1,
    height=620,
)
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
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown("## Lectura por ejes")
B.features([
    {"ic": "🔥", "h": "Cerros y fuego",
     "p": "Localidades de borde como Usme, San Cristobal y Santa Fe subirian por interfaz urbano-rural, cobertura vegetal y susceptibilidad a incendio forestal."},
    {"ic": "💧", "h": "Agua y anegamiento",
     "p": "Suba, Bosa y Kennedy ganan peso por humedales, corredores hidricos y anegamiento recurrente ligado a lluvia intensa."},
    {"ic": "⛰️", "h": "Ladera y remocion",
     "p": "Ciudad Bolivar y San Cristobal resaltan por pendientes, laderas inestables y recurrencia de movimientos en masa."},
    {"ic": "📡", "h": "Señal operativa",
     "p": "La capa dinamica integraria lluvia 24h/72h/7d, radar y boletines del SAB para ver que zonas requieren atencion hoy."},
])

top = d.sort_values("indice_presion_ecoterritorial_bogota", ascending=False).head(8)
bars = px.bar(
    top,
    x="localidad",
    y=["score_fuego_estructural", "score_agua", "score_remocion", "score_operativo"],
    barmode="group",
    color_discrete_sequence=["#dc2626", "#0277bd", "#8d6e63", "#16a34a"],
    height=420,
)
bars.update_layout(
    margin=dict(l=0, r=0, t=10, b=0),
    legend_title_text="Drivers",
    xaxis_title="",
    yaxis_title="Score",
)
st.plotly_chart(bars, use_container_width=True, config={"displayModeBar": False})

c4, c5 = st.columns([1.15, 1])
with c4:
    st.markdown("## Ranking de localidades")
    st.dataframe(
        d[[
            "localidad",
            "nivel",
            "indice_presion_ecoterritorial_bogota",
            "driver_principal",
            "incidentes_7d",
            "lluvia_72h_mm",
        ]]
        .rename(columns={
            "localidad": "Localidad",
            "nivel": "Nivel",
            "indice_presion_ecoterritorial_bogota": "Indice total",
            "driver_principal": "Driver principal",
            "incidentes_7d": "Incidentes 7d",
            "lluvia_72h_mm": "Lluvia 72h (mm)",
        }),
        hide_index=True,
        use_container_width=True,
    )
with c5:
    st.markdown("## Ficha demo")
    loc = st.selectbox("Localidad", d["localidad"].tolist(), index=0)
    row = d[d["localidad"] == loc].iloc[0]
    st.metric("Indice total", f"{row['indice_presion_ecoterritorial_bogota']:.2f}")
    st.metric("Nivel", row["nivel"])
    st.metric("Incidentes recientes", int(row["incidentes_7d"]))
    st.metric("Lluvia acumulada 72h", f"{int(row['lluvia_72h_mm'])} mm")
    st.markdown(
        f"**Driver principal:** {row['driver_principal']}\n\n"
        f"- Cerros y fuego: `{row['score_fuego_estructural']:.2f}`\n"
        f"- Agua y anegamiento: `{row['score_agua']:.2f}`\n"
        f"- Ladera y remocion: `{row['score_remocion']:.2f}`\n"
        f"- Senal operativa: `{row['score_operativo']:.2f}`"
    )

st.markdown("## Como se conectaria al dato real")
st.markdown(
    "1. `SIRE/IDIGER`: zonificacion de incendio forestal, puntos criticos de inundacion y remocion.\n"
    "2. `SAB`: lluvia reciente, radar y reportes diarios.\n"
    "3. `Geometrias de Bogota`: localidades y luego UPZ.\n"
    "4. `Pipeline AquaBosque`: construccion de `bogota_zoom.csv` y refresco operativo."
)

B.footer()
