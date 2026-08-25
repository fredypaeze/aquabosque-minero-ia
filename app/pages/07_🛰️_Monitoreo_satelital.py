import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import branding as B
from glosario import G, cc
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

# Frescura del dato: cobertura NACIONAL + refresco automático diario
_gen = str(resumen.get("generado", ""))[:10]
st.success(f"🛰️ **Cobertura nacional · {int(resumen.get('municipios_con_fuego', 0))} municipios con fuego activo** "
           f"· fuente NASA FIRMS (VIIRS + MODIS) · **última actualización: {_gen}** · "
           f"refresco automático diario.")

# ============================================================
# HERO: los ~30.000 focos REALES sobre imagen satelital NASA (GIBS)
# ============================================================
VIIRS_RAW = ROOT / "data" / "raw" / "satelital" / "firms_VIIRS_SNPP_7d.csv"
MODIS_RAW = ROOT / "data" / "raw" / "satelital" / "firms_MODIS_7d.csv"
if VIIRS_RAW.exists() or MODIS_RAW.exists():
    st.markdown("### 🔥 Colombia en llamas — vista desde el espacio (últimos 7 días)")

    @st.cache_data
    def _focos(mt):
        frames = []
        for f, src in [(VIIRS_RAW, "VIIRS"), (MODIS_RAW, "MODIS")]:
            if f.exists():
                d = pd.read_csv(f)[["latitude", "longitude", "frp", "confidence", "acq_date", "daynight"]].copy()
                d["sensor"] = src
                frames.append(d)
        p = pd.concat(frames, ignore_index=True)
        t = (p["frp"].clip(0, 300) / 300)
        p["color"] = [[255, int(255 * (1 - x)), 0, 170] for x in t]
        p["radius"] = (250 + p["frp"].clip(0, 600) * 3).astype(int)
        return p
    pts = _focos(VIIRS_RAW.stat().st_mtime if VIIRS_RAW.exists() else 0)
    fecha_sat = str(pts["acq_date"].max())
    # GIBS publica el true-color con rezago: la imagen del día en curso puede no existir aún
    # (tiles negros en la mañana) → se usa el día anterior al foco más reciente.
    fecha_gibs = (pd.to_datetime(fecha_sat) - pd.Timedelta(days=1)).date().isoformat()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔥 Focos activos", f"{len(pts):,}")
    m2.metric("Potencia radiativa total", f"{pts['frp'].sum():,.0f} MW")
    m3.metric("Foco más intenso", f"{pts['frp'].max():,.0f} MW")
    m4.metric("Sensores NASA", "VIIRS 375 m + MODIS")

    vista = st.radio("Vista del mapa", ["🔥 Puntos de fuego", "🌡️ Mapa de calor"],
                     horizontal=True, label_visibility="collapsed")

    # Imagen satelital REAL de la NASA (GIBS true-color) como capa raster — abierta, sin token
    # VIIRS SNPP: barrido ancho (~3.060 km) → sin la franja sin-dato de MODIS, y coherente con los focos VIIRS
    gibs_url = ("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
                "VIIRS_SNPP_CorrectedReflectance_TrueColor/default/" + fecha_gibs +
                "/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg")
    gibs_layer = {"below": "traces", "sourcetype": "raster",
                  "sourceattribution": "NASA GIBS / EOSDIS", "source": [gibs_url]}
    center = {"lat": 3.8, "lon": -73.5}
    if "Puntos" in vista:
        fig = px.scatter_mapbox(
            pts, lat="latitude", lon="longitude", color="frp",
            color_continuous_scale="YlOrRd", range_color=(0, float(pts["frp"].quantile(0.9))),
            hover_data={"frp": ":.0f", "acq_date": True, "sensor": True, "latitude": False, "longitude": False},
            zoom=4.4, center=center, height=580)
        fig.update_traces(marker={"size": 4, "opacity": 0.8})
    else:
        fig = px.density_mapbox(
            pts, lat="latitude", lon="longitude", z="frp", radius=7,
            color_continuous_scale="YlOrRd", zoom=4.4, center=center, height=580)
    fig.update_layout(mapbox_style="carto-darkmatter", mapbox_layers=[gibs_layer],
                      margin=dict(l=0, r=0, t=0, b=0),
                      coloraxis_colorbar=dict(title="FRP (MW)"))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(f"Base: **NASA GIBS · VIIRS SNPP true-color** ({fecha_gibs}, última imagen publicada) — imagen satelital real, dato abierto sin token. "
               f"Focos: **NASA FIRMS** (VIIRS+MODIS), cada punto es un fuego térmico real de los últimos 7 días; "
               f"color y tamaño por potencia radiativa (FRP). Se ve la frontera de quema y deforestación en vivo.")
    st.divider()

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
k[0].metric("🔥 Focos (7 días)", f"{int(resumen.get('total_focos_colombia', fuego.focos_7d.sum())):,}".replace(",", "."),
            help=G["focos"])
k[1].metric("Municipios con fuego", int((fuego.focos_7d > 0).sum()), help=G["municipios_fuego"])
k[2].metric("⚠️ Prioridad máxima", len(prioridad_max), help=G["prioridad_max"])
k[3].metric("🆕 Actividad nueva", len(nuevos), help=G["actividad_nueva"])

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
        .head(12)[["municipio", "departamento", "riesgo_nivel", "focos_7d", "frp_total", "ultima_fecha"]]
        .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                         "riesgo_nivel": "Nivel modelo", "focos_7d": "Focos 7d", "frp_total": "FRP",
                         "ultima_fecha": "Último foco"}),
        hide_index=True, use_container_width=True,
        column_config=cc({"Nivel modelo": "nivel", "Focos 7d": "focos", "FRP": "frp", "Último foco": "ultimo_foco"}))
with col2:
    st.markdown("#### 🆕 Actividad reciente no capturada por el índice estático")
    st.caption("Fuego intenso donde los datos históricos (2017-2021) no marcaban prioridad. "
               "El valor de la capa NRT: ver lo que el modelo estático no ve.")
    st.dataframe(
        nuevos.sort_values("frp_total", ascending=False)
        .head(12)[["municipio", "departamento", "riesgo_nivel", "focos_7d", "frp_total", "ultima_fecha"]]
        .rename(columns={"municipio": "Municipio", "departamento": "Departamento",
                         "riesgo_nivel": "Nivel modelo", "focos_7d": "Focos 7d", "frp_total": "FRP",
                         "ultima_fecha": "Último foco"}),
        hide_index=True, use_container_width=True,
        column_config=cc({"Nivel modelo": "nivel", "Focos 7d": "focos", "FRP": "frp", "Último foco": "ultimo_foco"}))

st.info("**Fuente:** NASA FIRMS (VIIRS SNPP + NOAA-20, MODIS C6.1) · datos abiertos · actualización diaria. "
        "**Honestidad:** señal satelital térmica NRT (proxy de deforestación/quema); la detección de deforestación "
        "por clasificación de imagen Sentinel-2 con deep learning corre en la infraestructura GPU del Ministerio (capa 2).")

# ============================================================
# EXPLORADOR SATELITAL DINÁMICO POR MUNICIPIO (los 1.122)
# ============================================================
try:
    _recent = fecha_sat
    _gibs = fecha_gibs
    _pts = pts
except NameError:
    _recent = str(fuego["ultima_fecha"].max())[:10] if "ultima_fecha" in fuego else "2026-08-07"
    _gibs = (pd.to_datetime(_recent) - pd.Timedelta(days=1)).date().isoformat()
    _pts = pd.DataFrame(columns=["latitude", "longitude", "frp", "acq_date", "sensor"])

st.divider()
st.markdown("### 🔭 Explorador satelital por municipio")
st.caption("Elige **cualquiera de los 1.122 municipios** y obsérvalo desde el espacio (NASA GIBS) en distintas fechas, "
           "con sus focos activos y su nivel de riesgo. Dinámico y para todo el país.")

@st.cache_data
def _extra(mt_v, mt_a):
    vp = ROOT / "outputs" / "tables" / "velocidad_degradacion.csv"
    ap = ROOT / "outputs" / "tables" / "anomalias_explicadas.csv"
    vel = pd.read_csv(vp) if vp.exists() else pd.DataFrame()
    ano = pd.read_csv(ap) if ap.exists() else pd.DataFrame()
    return vel, ano
_vp = ROOT / "outputs" / "tables" / "velocidad_degradacion.csv"
_ap = ROOT / "outputs" / "tables" / "anomalias_explicadas.csv"
vel_df, ano_df = _extra(_vp.stat().st_mtime if _vp.exists() else 0, _ap.stat().st_mtime if _ap.exists() else 0)

deptos = sorted(pred["departamento"].dropna().unique())
cA, cB, cC = st.columns([1.1, 1.5, 1.6])
_di = deptos.index("META") if "META" in deptos else 0
dep_sel = cA.selectbox("Departamento", deptos, index=_di)
munis = sorted(pred[pred["departamento"] == dep_sel]["municipio"].dropna().unique())
mun_sel = cB.selectbox("Municipio", munis)
_fechas = ["2023-06-15", "2024-06-15", "2025-06-15", "2026-03-15", _gibs]
fecha_e = cC.select_slider("Fecha de la imagen satelital", options=_fechas, value=_gibs)

row = pred[(pred["departamento"] == dep_sel) & (pred["municipio"] == mun_sel)].iloc[0]
lat, lon = float(row["lat"]), float(row["lon"])
cod = int(float(row["cod_mpio"]))

k1, k2, k3, k4 = st.columns(4)
k1.metric("Nivel de riesgo", str(row.get("riesgo_nivel", "—")),
          help="Priorización del modelo (índice compuesto sobre datos abiertos históricos).")
k2.metric("Presión minera", f"{row.get('idx_minero', 0):.2f}",
          help="Sub-índice del modelo [0-1] · fuentes ANM/RUCOM (corte del entrenamiento).")
k3.metric("Deforestación", f"{row.get('idx_deforestacion', 0):.2f}",
          help="Sub-índice del modelo [0-1] · fuente IDEAM/SMByC (histórico; 0 = sin registro en la fuente).")
# Señal de fuego FRESCA (fuego_municipal.csv, NRT): predicciones.csv es la foto de
# entrenamiento del modelo y puede decir 0 focos en un municipio que hoy arde.
_frow = fuego[fuego["cod_mpio"] == cod]
_focos_hoy = int(_frow.iloc[0]["focos_7d"]) if len(_frow) else 0
_vrow = vel_df[vel_df.get("cod_mpio").astype("Int64") == cod] if "cod_mpio" in getattr(vel_df, "columns", []) else pd.DataFrame()
if _focos_hoy > 0:
    k4.metric("🔥 Focos de calor (7 días)", _focos_hoy,
              delta=f"{_frow.iloc[0]['frp_total']:,.0f} MW FRP", delta_color="inverse",
              help="Señal NRT de NASA FIRMS (refresco diario), no la foto de entrenamiento del modelo.")
elif len(_vrow):
    k4.metric("Deforestación (dinámica)", str(_vrow.iloc[0]["dinamica"]),
              delta=f"{_vrow.iloc[0]['aceleracion_ha_ano']:+.0f} ha/año")
else:
    k4.metric("🔥 Focos de calor (7 días)", 0,
              help="Sin focos activos en la ventana de 7 días (NASA FIRMS, refresco diario).")

sub = _pts[(_pts["latitude"].between(lat - 0.45, lat + 0.45)) & (_pts["longitude"].between(lon - 0.45, lon + 0.45))]
gibs_e = ("https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
          "VIIRS_SNPP_CorrectedReflectance_TrueColor/default/" + str(fecha_e) +
          "/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg")
figm = px.scatter_mapbox(sub if len(sub) else pd.DataFrame({"latitude": [lat], "longitude": [lon], "frp": [0]}),
                         lat="latitude", lon="longitude", color="frp" if len(sub) else None,
                         color_continuous_scale="YlOrRd", zoom=9.2, center={"lat": lat, "lon": lon}, height=520)
figm.update_traces(marker={"size": 7 if len(sub) else 1, "opacity": 0.85})
figm.update_layout(mapbox_style="carto-darkmatter",
                   mapbox_layers=[{"below": "traces", "sourcetype": "raster",
                                   "sourceattribution": "NASA GIBS / EOSDIS", "source": [gibs_e]}],
                   margin=dict(l=0, r=0, t=0, b=0), coloraxis_colorbar=dict(title="FRP (MW)"))
st.plotly_chart(figm, use_container_width=True, config={"displayModeBar": False})
st.caption(f"**{mun_sel} ({dep_sel})** · imagen NASA GIBS VIIRS true-color del **{fecha_e}** · "
           f"{len(sub)} focos de calor en el entorno (últimos 7 días). Mueve la fecha para ver el cambio en el tiempo. "
           "Resolución satelital ~375 m (para detalle de 10 m con IA, ver la capa Sentinel-2 + U-Net abajo).")

# --- Capa 2: Deforestación REAL por municipio (Sentinel-2 · cambio NDVI) ---
st.divider()
st.markdown("### 🌳 Deforestación con Sentinel-2 · cambio NDVI real (por municipio)")
import json as _json
_NDVI = ROOT / "outputs" / "satelital_ndvi"
_res = sorted(_NDVI.glob("*/result.json")) if _NDVI.exists() else []
if not _res:
    st.info("Aún no hay municipios procesados. Ejecute "
            "`./venv/bin/python src/aquabosque/satelital/ndvi_change_real.py --lista` "
            "para generar los resultados reales de Sentinel-2.")
else:
    _items = {p.parent.name: _json.loads(p.read_text(encoding="utf-8")) for p in _res}
    _opts = {f"{v['municipio']} (~{v['hectareas_perdida']:.0f} ha)": k for k, v in _items.items()}
    # Sigue al municipio elegido en el explorador de arriba, si tiene resultado precomputado
    _keys = list(_opts.keys())
    _pre = next((i for i, _k in enumerate(_keys) if _opts[_k] == str(cod)), 0)
    _sel = st.selectbox("Municipio (frente de deforestación · precomputado)", _keys, index=_pre)
    _r = _items[_opts[_sel]]
    st.caption(f"Sentinel-2 (10 m) descargadas y procesadas localmente (Copernicus vía STAC Earth Search). "
               f"Ventana ~{_r['ventana_km']:.0f}×{_r['ventana_km']:.0f} km · **cambio NDVI bi-temporal, sin GPU**.")
    mc = st.columns(3)
    mc[0].metric("Hectáreas de pérdida (calculadas)", f"{_r['hectareas_perdida']:.0f} ha",
                 help="Cifra COMPUTADA en esta corrida (píxeles 'era bosque y perdió NDVI'), no estimada a mano.")
    mc[1].metric("Cobertura válida (sin nube)", f"{_r['cobertura_valida_pct']:.0f}%", help="Máscara de nube SCL.")
    mc[2].metric("Fechas", f"{_r['escena_antes']['fecha']} → {_r['escena_despues']['fecha']}")
    _d = _NDVI / _opts[_sel]
    ci = st.columns(3)
    for col, img, cap in [
        (ci[0], "antes.png", f"Antes · {_r['escena_antes']['fecha']} ({_r['escena_antes']['nube_pct']:.0f}% nube)"),
        (ci[1], "despues.png", f"Después · {_r['escena_despues']['fecha']} ({_r['escena_despues']['nube_pct']:.0f}% nube)"),
        (ci[2], "cambio.png", "Pérdida de cobertura detectada (en rojo)")]:
        if (_d / img).exists():
            col.image(str(_d / img), use_container_width=True, caption=cap)
    with st.expander("Procedencia y método (trazable)"):
        st.markdown(
            f"- **Fuente:** {_r['fuente']}.\n"
            f"- **Escena antes:** `{_r['escena_antes']['id']}` · **después:** `{_r['escena_despues']['id']}`.\n"
            f"- **Método:** {_r['metodo']}. Umbrales: era-bosque NDVI>{_r['umbrales']['forest_ndvi']}, "
            f"pérdida ΔNDVI<{_r['umbrales']['loss_dndvi']}.\n"
            f"- **Naturaleza:** {_r['naturaleza']} · computado {_r['computado_en'][:10]}.\n"
            f"- **Código reproducible:** `src/aquabosque/satelital/ndvi_change_real.py`."
        )
st.caption("🔒 Procesamiento local (no sale de la infraestructura del Estado). **Honestidad:** esto es "
           "**cambio NDVI**, no segmentación U-Net. La U-Net bosque/no-bosque con IoU validado es un paso aparte "
           "que requiere GPU (terramin) y validación contra Hansen/IDEAM — no se presenta como hecho hasta ejecutarse.")
B.footer()
