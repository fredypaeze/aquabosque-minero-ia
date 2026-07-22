import os
import sys
from pathlib import Path

import streamlit as st

import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)

st.set_page_config(page_title="Asistente IA", page_icon="🤖", layout="wide")
B.inject_css()
B.sidebar_nav()

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

st.title("🤖 Asistente IA · pregunta a los datos")
st.caption("Asistente generativo **soberano**: recupera la evidencia de AquaBosque (priorización municipal, "
           "señal satelital, metodología) y responde en lenguaje natural. Corre sobre el LLM local del "
           "Ministerio (NVIDIA L40S) — **el dato no sale del Estado**. No inventa: se aterriza en los datos.")


@st.cache_resource
def _rag():
    from aquabosque.asistente import rag
    return rag


try:
    rag = _rag()
    listo = (ROOT / "data" / "processed" / "rag_index.npz").exists() and bool(rag.LLM_TOKEN)
except Exception as e:  # noqa: BLE001
    rag, listo = None, False
    st.error(f"No se pudo cargar el asistente: {e}")

if rag and not rag.LLM_TOKEN:
    st.warning("El asistente necesita `AQB_LLM_TOKEN` (API key de Open WebUI) y `AQB_LLM_URL` en el entorno "
               "del despliegue para conectarse al LLM local. La página está lista; falta la credencial de servicio.")

ejemplos = [
    "¿Por qué La Macarena aparece priorizada?",
    "¿Los 5 municipios con más focos de calor del país?",
    "¿Qué municipios del Cesar tienen fuego activo?",
    "¿Qué significa el nivel Crítico y qué NO significa?",
]
st.write("**Ejemplos:**")
cols = st.columns(len(ejemplos))
if "pregunta" not in st.session_state:
    st.session_state.pregunta = ""
for c, ej in zip(cols, ejemplos):
    if c.button(ej, use_container_width=True):
        st.session_state.pregunta = ej

pregunta = st.text_input("Tu pregunta", value=st.session_state.pregunta,
                         placeholder="Escribe una pregunta sobre priorización, satélite o metodología…")

# Compuerta de demo: si hay clave configurada, se exige para consultar el LLM
# (evita exponer la GPU del Ministerio al público abierto).
demo_pass = os.environ.get("AQB_ASSISTANT_PASS", "")
autorizado = True
if listo and demo_pass:
    ingresada = st.text_input("Clave de demo", type="password",
                              help="Solicítala al equipo. Protege el LLM interno de uso público abierto.")
    autorizado = (ingresada == demo_pass)
    if ingresada and not autorizado:
        st.error("Clave incorrecta.")

if st.button("Preguntar", type="primary", disabled=not (listo and pregunta and autorizado)):
    with st.spinner("Consultando el LLM local…"):
        try:
            out = rag.responder(pregunta)
            st.markdown("### Respuesta")
            st.write(out["respuesta"])
            with st.expander("Fuentes recuperadas (evidencia usada)"):
                for f in out["fuentes"]:
                    st.markdown(f"**[{f['id']}]** · relevancia {f['score']:.2f}")
                    st.caption(f["texto"][:400])
        except Exception as e:  # noqa: BLE001
            st.error(f"Error consultando el asistente: {e}")

st.divider()
st.caption("Modelo de embeddings: bge-m3 · generación: LLM local · La priorización orienta revisión; "
           "no prueba causalidad ni ilegalidad.")
B.footer()
