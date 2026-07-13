"""AquaBosque Minero IA — aplicación de demostración del MVP.

Prioriza territorios para revisión técnica ambiental combinando presión
minera formal registrada, señales hídricas estadísticas, detecciones
tempranas de posible deforestación y brechas de monitoreo. No afirma
causalidad ambiental, no detecta minería ilegal, no clasifica legalmente la
calidad del agua y no opera en tiempo real.

Ejecutar con: python -m streamlit run app.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
MVP_DIR = PROJECT_ROOT / "data" / "processed" / "mvp"

MUNICIPIOS_PATH = MVP_DIR / "aquabosque_municipios_mvp.csv"
PRIORIZACION_PATH = MVP_DIR / "aquabosque_priorizacion_mvp.csv"
TOP20_PATH = MVP_DIR / "aquabosque_top20_mvp.csv"
DEMO_PATH = MVP_DIR / "municipios_demo.csv"
GEOJSON_PATH = MVP_DIR / "municipios_mvp_simplificado.geojson"

st.set_page_config(page_title="AquaBosque Minero IA", page_icon="🌳", layout="wide")

PALETA_VERDE_AZUL = ["#F1F8F5", "#A8DAB5", "#4C9A5B", "#1B5E3A", "#0B3D5C"]


def _asegurar_datos() -> None:
    if MUNICIPIOS_PATH.exists() and GEOJSON_PATH.exists():
        return
    st.warning("Generando el dataset del MVP por primera vez (puede tardar un par de minutos)...")
    resultado = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "24_build_mvp_dataset.py")],
        cwd=str(PROJECT_ROOT), capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        st.error("No se pudo generar el dataset del MVP. Ejecuta manualmente: python scripts/24_build_mvp_dataset.py")
        st.code(resultado.stderr[-3000:])
        st.stop()


@st.cache_data
def cargar_datos() -> dict[str, pd.DataFrame]:
    municipios = pd.read_csv(MUNICIPIOS_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    priorizacion = pd.read_csv(PRIORIZACION_PATH, dtype={"cod_dane_mpio": str})
    top20 = pd.read_csv(TOP20_PATH, dtype={"cod_dane_mpio": str})
    demo = pd.read_csv(DEMO_PATH, dtype={"cod_dane_mpio": str})
    return {"municipios": municipios, "priorizacion": priorizacion, "top20": top20, "demo": demo}


@st.cache_data
def cargar_geojson() -> dict:
    with open(GEOJSON_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def tarjeta_kpi(columna, titulo: str, valor: str, ayuda: str = "") -> None:
    with columna:
        st.metric(titulo, valor, help=ayuda or None)


def render_inicio(municipios: pd.DataFrame) -> None:
    st.title("🌳 AquaBosque Minero IA")
    st.caption(
        "AquaBosque Minero IA prioriza territorios para revisión técnica ambiental combinando presión minera "
        "formal registrada, señales hídricas estadísticas, detecciones tempranas de posible deforestación y "
        "brechas de monitoreo."
    )
    st.info("⚠️ Actualización periódica, no tiempo real. Ver pestaña *Metodología y limitaciones* antes de interpretar cualquier resultado.")

    c1, c2, c3, c4, c5 = st.columns(5)
    tarjeta_kpi(c1, "Territorios cubiertos", f"{len(municipios):,}", "Unidades DIVIPOLA vigentes (municipios + áreas no municipalizadas)")
    tarjeta_kpi(c2, "Títulos mineros vigentes", f"{int(municipios['n_titulos_mineros'].sum()):,}", "Catastro Minero ANM")
    tarjeta_kpi(c3, "Municipios con monitoreo hídrico", f"{int(municipios['tiene_monitoreo_agua'].sum()):,}", "IDEAM, Fase 4B.2")
    tarjeta_kpi(c4, "Sitios de monitoreo hídrico", f"{int(municipios['n_sitios_monitoreo'].sum()):,}")
    tarjeta_kpi(c5, "Registros DTD (2025-IV)", f"{int(municipios['n_registros_dtd'].sum()):,}", "Detecciones Tempranas de Deforestación, IDEAM")

    st.markdown("### ¿Qué NO es AquaBosque Minero IA?")
    st.markdown(
        "- No afirma causalidad ambiental ni relaciona directamente minería con deterioro hídrico.\n"
        "- No detecta ni acusa minería ilegal — solo usa el catastro minero formal vigente.\n"
        "- No clasifica legalmente la calidad del agua (no aplica límites normativos).\n"
        "- No confirma deforestación a nivel nacional — solo Puerto Rico (Meta) tiene validación forestal piloto.\n"
        "- No opera en tiempo real — los datos tienen cortes específicos (ver Metodología)."
    )


def render_mapa(municipios: pd.DataFrame, geojson: dict) -> None:
    st.header("🗺️ Mapa nacional de priorización")
    col_filtro, col_variable = st.columns([2, 1])
    with col_filtro:
        deptos = ["(Todos)"] + sorted(municipios["nombre_dpto"].dropna().unique().tolist())
        depto_sel = st.selectbox("Filtrar por departamento", deptos)
    with col_variable:
        variable = st.radio("Colorear por", ["Prioridad de evidencia", "Anomalía IA"], horizontal=False)

    df = municipios.copy()
    if depto_sel != "(Todos)":
        df = df[df["nombre_dpto"] == depto_sel]

    df_prior = st.session_state.get("_df_priorizacion")
    if df_prior is None:
        df_prior = pd.read_csv(PRIORIZACION_PATH, dtype={"cod_dane_mpio": str})
        st.session_state["_df_priorizacion"] = df_prior
    df = df.merge(df_prior[["cod_dane_mpio", "anomalia_ia_percentil", "nivel_prioridad", "score_prioridad_evidencia"]], on="cod_dane_mpio", how="left", suffixes=("", "_r"))

    color_col = "score_prioridad_evidencia" if variable == "Prioridad de evidencia" else "anomalia_ia_percentil"
    titulo_leyenda = "Prioridad de evidencia (percentil)" if variable == "Prioridad de evidencia" else "Anomalía IA (percentil)"

    fig = px.choropleth_mapbox(
        df, geojson=geojson, locations="cod_dane_mpio", featureidkey="properties.cod_dane_mpio",
        color=color_col, color_continuous_scale=[PALETA_VERDE_AZUL[0], PALETA_VERDE_AZUL[2], PALETA_VERDE_AZUL[4]],
        mapbox_style="carto-positron", zoom=4.2, center={"lat": 4.6, "lon": -74.1}, opacity=0.75,
        hover_name="nombre_mpio",
        hover_data={"nombre_dpto": True, "score_prioridad_evidencia": ":.1f", "score_presion_minera": ":.1f",
                    "score_senal_hidrica": ":.1f", "n_registros_dtd": True, "cobertura_forestal_confirmada_mvp": True,
                    "cod_dane_mpio": False},
        labels={color_col: titulo_leyenda},
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=650)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Fuente del color seleccionable: score de prioridad por evidencia o percentil de anomalía IA. El tooltip muestra minería, agua, DTD y cobertura forestal confirmada.")


def render_ranking(priorizacion: pd.DataFrame, municipios: pd.DataFrame) -> None:
    st.header("📊 Ranking de priorización")
    df = priorizacion.merge(
        municipios[["cod_dane_mpio", "disponible_agua", "tiene_dtd_reciente"]],
        on="cod_dane_mpio", how="left",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        deptos = ["(Todos)"] + sorted(df["nombre_dpto"].dropna().unique().tolist())
        f_depto = st.selectbox("Departamento", deptos, key="rk_depto")
    with c2:
        f_nivel = st.multiselect("Nivel de prioridad", ["Muy alta", "Alta", "Media", "Baja"], default=["Muy alta", "Alta"])
    with c3:
        f_agua = st.selectbox("Disponibilidad de agua", ["(Todos)", "Con monitoreo", "Sin monitoreo"])
    with c4:
        f_dtd = st.selectbox("Presencia DTD reciente", ["(Todos)", "Con detecciones", "Sin detecciones"])

    if f_depto != "(Todos)":
        df = df[df["nombre_dpto"] == f_depto]
    if f_nivel:
        df = df[df["nivel_prioridad"].isin(f_nivel)]
    if f_agua == "Con monitoreo":
        df = df[df["disponible_agua"] == True]  # noqa: E712
    elif f_agua == "Sin monitoreo":
        df = df[df["disponible_agua"] == False]  # noqa: E712
    if f_dtd == "Con detecciones":
        df = df[df["tiene_dtd_reciente"] == True]  # noqa: E712
    elif f_dtd == "Sin detecciones":
        df = df[df["tiene_dtd_reciente"] == False]  # noqa: E712

    st.caption(f"{len(df)} municipios coinciden con los filtros — top 20 nacional siempre disponible para descarga completa.")
    columnas_mostrar = [
        "nombre_mpio", "nombre_dpto", "score_prioridad_evidencia", "nivel_prioridad",
        "anomalia_ia_percentil", "es_perfil_atipico", "principales_razones", "advertencias_datos",
    ]
    st.dataframe(df[columnas_mostrar].sort_values("score_prioridad_evidencia", ascending=False), use_container_width=True, height=450)
    st.download_button("⬇️ Descargar ranking filtrado (CSV)", df.to_csv(index=False).encode("utf-8"), "aquabosque_ranking_filtrado.csv", "text/csv")


def render_detalle(municipios: pd.DataFrame, priorizacion: pd.DataFrame) -> None:
    st.header("🔎 Detalle territorial")
    opciones = municipios.sort_values("nombre_mpio").apply(lambda r: f"{r['nombre_mpio']} ({r['nombre_dpto']})", axis=1)
    mapa_opciones = dict(zip(opciones, municipios["cod_dane_mpio"]))
    seleccion = st.selectbox("Selecciona un municipio", list(mapa_opciones.keys()), index=list(mapa_opciones.values()).index("50590") if "50590" in mapa_opciones.values() else 0)
    cod = mapa_opciones[seleccion]

    fila = municipios[municipios["cod_dane_mpio"] == cod].iloc[0]
    fila_p = priorizacion[priorizacion["cod_dane_mpio"] == cod].iloc[0]

    st.subheader(f"{fila['nombre_mpio']}, {fila['nombre_dpto']}")
    st.markdown(f"**Nivel de prioridad:** {fila_p['nivel_prioridad']} (score {fila_p['score_prioridad_evidencia']:.1f})")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("##### ⛏️ Presión minera")
        st.metric("Score", f"{fila['score_presion_minera']:.1f}")
        st.write(f"Títulos: {int(fila['n_titulos_mineros'])}")
        st.write(f"% territorio titulado (unión): {fila['pct_area_unidad_titulada_union']:.2f}%")
        st.write(f"Anotaciones: {int(fila['anotaciones_total'])}")
    with c2:
        st.markdown("##### 💧 Señal hídrica")
        if fila["disponible_agua"]:
            st.metric("Score", f"{fila['score_senal_hidrica']:.1f}")
            st.write(f"Parámetro más atípico: {fila['principal_parametro_atipico']}")
            st.write(f"Parámetros evaluables: {int(fila['n_parametros_hidricos_evaluables'])}")
        else:
            st.metric("Score", "No disponible")
            st.write("Sin parámetros Nivel A evaluables en este municipio.")
        st.write(f"Sitios de monitoreo: {int(fila['n_sitios_monitoreo'])}")
        st.write(f"Última observación: {fila['ultima_observacion_agua'] if pd.notna(fila['ultima_observacion_agua']) else 'N/D'}")
    with c3:
        st.markdown("##### 🌲 DTD (2025-IV)")
        st.metric("Score", f"{fila['score_deteccion_temprana']:.1f}")
        st.write(f"Registros: {int(fila['n_registros_dtd'])}")
        st.write(f"Coordenadas únicas: {int(fila['n_coordenadas_dtd_unicas'])}")
        st.write(f"Núcleos: {int(fila['n_nucleos_dtd'])}")
    with c4:
        st.markdown("##### 🤖 Anomalía IA")
        st.metric("Percentil", f"{fila_p['anomalia_ia_percentil']:.0f}")
        st.write("Perfil atípico" if fila_p["es_perfil_atipico"] else "Perfil dentro del rango esperado")
        st.caption(fila_p["explicacion_anomalia"])

    st.markdown("##### 🌳 Evidencia forestal confirmada")
    if fila["cobertura_forestal_confirmada_mvp"]:
        st.success(
            f"Bosque 2024: {fila['pct_bosque_2024']:.1f}% del área piloto | "
            f"Deforestación 2023-2024: {fila['deforestacion_2023_2024_ha']:.1f} ha | Fuente: {fila['fuente_forestal']}"
        )
    else:
        st.warning("No disponible en el MVP nacional. No equivale a cero deforestación.")

    st.markdown("##### 📝 Explicación y advertencias")
    st.write(fila_p["resumen_explicativo"])
    st.warning(fila_p["advertencias_datos"])


def render_metodologia() -> None:
    st.header("📚 Metodología y limitaciones")
    st.markdown(
        """
**Fuentes de datos**
- Catastro Minero ANM (títulos mineros vigentes, anotaciones) — datos.gov.co.
- Calidad de agua IDEAM (Fase 4B.2: normalización canónica de parámetros y clasificación de idoneidad Nivel A/B/C/D).
- Detecciones Tempranas de Deforestación (DTD) IDEAM, periodo 2025-IV.
- Ráster de bosque y cambio de cobertura IDEAM (WCS), piloto validado en Puerto Rico (Meta) — Fases 2D.1/2D.2.
- Unidades territoriales DIVIPOLA/MGN2025 (DANE), 1.122 unidades vigentes.

**Score de prioridad por evidencia**: media ponderada (minería 40%, agua 35%, DTD 25%) renormalizada sobre
los componentes realmente disponibles para cada municipio — un componente ausente NUNCA se sustituye por
cero. Niveles (Muy alta/Alta/Media/Baja) definidos por percentiles nacionales (≥P90, P75-P90, P40-P75, <P40).

**IsolationForest**: modelo no supervisado de detección de patrones territoriales atípicos (`random_state=42`,
`contamination=0.10`, 200 árboles). Variables: log(títulos mineros), % área titulada (unión), señal hídrica,
log(registros DTD), sitios de monitoreo, parámetros hídricos evaluables, banderas de disponibilidad. Los
valores faltantes se imputan por mediana ÚNICAMENTE para el modelo — el dataset canónico conserva `NaN` y
banderas explícitas de ausencia.

**Tratamiento de datos faltantes y censurados**: los resultados de agua bajo el límite de detección
(censurados) se excluyen del cálculo de la señal estadística (solo se usan valores cuantificados). La
ausencia de monitoreo hídrico o de detecciones DTD nunca se traduce en un score igual a cero — se marca con
una bandera de disponibilidad explícita.

**Cobertura forestal**: solo Puerto Rico (Meta) tiene bosque/deforestación confirmados con el piloto WCS
IDEAM real (Fases 2D.1/2D.2). Los demás municipios no tienen cobertura forestal nacional confirmada en este
MVP — la ausencia de dato NUNCA se interpreta como cero deforestación.

**Catastro Minero**: con corte de actualización disponible en la metadata de la fuente (ver
`data/raw/mineria/catastro_minero_anm/*.metadata.json`) — no es un dato en tiempo real.

**Lo que este producto NO hace**
- No establece causalidad ambiental entre minería, agua o bosque.
- No detecta ni acusa minería ilegal (solo usa el catastro formal vigente).
- No clasifica legalmente la calidad del agua (no aplica límites normativos/resolución).
- No opera en tiempo real — cada fuente tiene su propio corte temporal.
        """
    )


def main() -> None:
    _asegurar_datos()
    datos = cargar_datos()
    geojson = cargar_geojson()

    tabs = st.tabs(["Inicio", "Mapa nacional", "Ranking", "Detalle territorial", "Metodología y limitaciones"])
    with tabs[0]:
        render_inicio(datos["municipios"])
    with tabs[1]:
        render_mapa(datos["municipios"], geojson)
    with tabs[2]:
        render_ranking(datos["priorizacion"], datos["municipios"])
    with tabs[3]:
        render_detalle(datos["municipios"], datos["priorizacion"])
    with tabs[4]:
        render_metodologia()


if __name__ == "__main__":
    main()
