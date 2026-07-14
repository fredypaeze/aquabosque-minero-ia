"""AquaBosque Minero IA — dashboard (portada)."""
from pathlib import Path

import pandas as pd
import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="AquaBosque Minero IA", page_icon="🌿", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[1]


@st.cache_data
def cargar():
    return pd.read_csv(ROOT / "outputs" / "tables" / "predicciones.csv")


df = cargar()
n = len(df)
crit = int((df.riesgo_nivel == "Crítico").sum())
alto = int((df.riesgo_nivel == "Alto").sum())
medio = int((df.riesgo_nivel == "Medio").sum())

B.hero(
    eyebrow="Grupo de Datos Estratégicos · Ministerio de Minas y Energía",
    title="AquaBosque&nbsp;Minero&nbsp;IA",
    subtitle="Inteligencia artificial <b>explicable</b> que prioriza los municipios de Colombia "
             "donde confluye el mayor riesgo ambiental por presión minera, deforestación y "
             "afectación hídrica — integrando cinco fuentes abiertas oficiales.",
    pills=[{"t": "Demo en vivo", "live": True}, {"t": "1.122 municipios"},
           {"t": "5 fuentes oficiales"}, {"t": "XGBoost + SHAP"}],
)

B.kpis([
    {"lab": "Municipios analizados", "val": f"{n:,}".replace(",", "."), "foot": "cobertura nacional (DIVIPOLA)", "acc": B.AGUA},
    {"lab": "Riesgo crítico", "val": crit, "foot": "máxima prioridad", "acc": B.RIESGO["Crítico"]},
    {"lab": "Riesgo alto", "val": alto, "foot": "atención prioritaria", "acc": B.RIESGO["Alto"]},
    {"lab": "Riesgo medio", "val": medio, "foot": "seguimiento", "acc": B.RIESGO["Medio"]},
])

st.markdown("## Del dato disperso a la decisión priorizada")
B.features([
    {"ic": "🧭", "h": "Integra",
     "p": "Unifica minería, deforestación, calidad del agua, áreas protegidas y sensibilidad social "
          "en una sola vista municipal, con datos 100% oficiales y trazables."},
    {"ic": "🎯", "h": "Prioriza",
     "p": "Clasifica cada municipio en cuatro niveles (Bajo → Crítico) con una metodología "
          "transparente y auditable, no una caja negra."},
    {"ic": "🔬", "h": "Explica",
     "p": "Con SHAP muestra POR QUÉ cada territorio se prioriza — qué factor pesa más — "
          "para orientar la revisión técnica con evidencia."},
])

st.markdown("## Explore el sistema")
c1, c2, c3 = st.columns(3)
c1.page_link("pages/01_🗺️_Mapa_de_riesgo.py", label="🗺️  Mapa nacional de riesgo", use_container_width=True)
c2.page_link("pages/02_📊_Ranking.py", label="📊  Ranking de municipios", use_container_width=True)
c3.page_link("pages/04_🔬_Explicabilidad.py", label="🔬  Explicabilidad (SHAP)", use_container_width=True)
c1.page_link("pages/03_📋_Ficha_territorial.py", label="📋  Ficha por municipio", use_container_width=True)
c2.page_link("pages/05_📂_Datos_abiertos.py", label="📂  Datos abiertos", use_container_width=True)
c3.page_link("pages/06_📖_Metodología.py", label="📖  Metodología", use_container_width=True)

st.markdown("## Fuentes de datos — abiertas, oficiales y verificadas")
B.source_badges(["ANM · RUCOM", "ANM · Volumen de explotación", "IDEAM · Deforestación",
                 "IDEAM · Calidad de agua (ICA)", "RUNAP · Áreas protegidas",
                 "DANE · DIVIPOLA", "Municipios PDET"])

B.note(
    "<b>Uso responsable.</b> Esta es una <b>priorización técnica</b> a partir de señales integradas de "
    "datos abiertos. <b>No constituye prueba de infracción, sanción, causalidad directa ni determinación "
    "de minería ilegal.</b> Su propósito es apoyar el monitoreo estratégico y orientar el análisis "
    "institucional detallado.")

B.footer()
