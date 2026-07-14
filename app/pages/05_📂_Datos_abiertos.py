import streamlit as st, pandas as pd
import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)
st.set_page_config(page_title="Datos abiertos", page_icon="📂", layout="wide")
B.inject_css()
B.sidebar_nav()
st.title("📂 Fuentes de datos abiertos")
st.markdown("Todas las fuentes son **públicas, oficiales y verificadas**. `data/raw/*` es re-descargable.")
fuentes=pd.DataFrame([
 ["Minería — títulos/explotadores","ANM RUCOM","datos.gov.co 42ha-fhvj","12.914","codigo_dane","solo actividad formal"],
 ["Minería — volumen y regalías","ANM","datos.gov.co r85m-vv6c","75.888","codigo_dane","producción real por municipio"],
 ["Deforestación","Observatorio/IDEAM","ArcGIS FeatureServer","75 focos","nombre municipio","municipios sin registro = no significativo"],
 ["Calidad de agua (ICA)","IDEAM DHIME","dhime.ideam.gov.co FQA/ICA","167 estaciones","coordenada","índice ica5 0-1"],
 ["Áreas protegidas","RUNAP Portal30x30","ArcGIS capa 59","1.882","centroide","cruce espacial"],
 ["Municipios","DANE DIVIPOLA","datos.gov.co gdxc-w37w","1.122","cod_mpio+centroide","base territorial"],
 ["Sensibilidad social","Municipios PDET","datos.gov.co idrk-ba8y","170","cod_muni","posconflicto"],
], columns=["Dimensión","Entidad","Fuente/URL","Registros","Clave territorial","Limitación"])
st.dataframe(fuentes, use_container_width=True, height=340)
st.caption("Barreras encontradas fueron técnicas (sin API tabular), no de permiso. El grupo de Datos "
           "Estratégicos es el ente regulador del sector; la información es pública y su misión es hacerla visible.")
B.footer()
