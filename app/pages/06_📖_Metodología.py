import streamlit as st
import branding as B
import importlib as _il
if not hasattr(B, "sidebar_nav"): B = _il.reload(B)
st.set_page_config(page_title="Metodología", page_icon="📖", layout="wide")
B.inject_css()
B.sidebar_nav()
st.title("📖 Metodología")
st.markdown("""
### Arquitectura
`Fuentes abiertas → ingesta → limpieza → dataset maestro municipal (1.122) → 4 índices 0-1 →
etiqueta técnica → XGBoost + SHAP → dashboard`

### Etiqueta técnica de priorización
Combina 4 dimensiones con pesos documentados (spec §11.2):
`riesgo = 0.35·minero + 0.30·deforestación + 0.25·hídrico + 0.10·sensibilidad`

**Hallazgo declarado:** con umbrales absolutos ningún municipio supera ~0.5 porque las señales
están **dispersas** (el minero no suele ser el deforestado). Como el objetivo es **priorización
relativa**, se clasifica por cuantiles (Crítico p95, Alto p85, Medio p60). Es un hallazgo, no un defecto.

### Índice hídrico
`(1 − ICA)` donde hay estación IDEAM; **sin estación = 0** (ausencia de señal = sin riesgo observado,
conservador — no se inventa riesgo).

### Honestidad del modelo
La etiqueta es una **fórmula compuesta**, por lo que XGBoost **re-aprende parcialmente la regla**: la
accuracy alta es por construcción y **NO se presenta como mérito predictivo**. El valor real es la
**explicabilidad (SHAP)**: qué factor pesa en cada municipio, para orientar revisión técnica.

### Límites
No prueba causalidad · no determina ilegalidad · no sanciona · minería solo formal (RUCOM) ·
actualización periódica (no tiempo real) · agua limitada a la red de estaciones IDEAM.

### Reproducibilidad
`01_download → 02_prepare → 03_build_features → 04_train → 05_generate_outputs → streamlit run` (puerto 8510).
""")
B.footer()
