"""Identidad visual AquaBosque — CSS institucional premium + componentes reutilizables.
Se importa desde cada página: `import branding as B; B.inject_css()`.
"""
import streamlit as st

# Paleta: bosque (verde) + agua (azul/teal) + niveles de riesgo
VERDE = "#1b5e20"; VERDE2 = "#2e7d32"; AGUA = "#0277bd"; AGUA2 = "#01579b"
TINTA = "#12261a"
RIESGO = {"Crítico": "#7f1d1d", "Alto": "#dc2626", "Medio": "#f59e0b", "Bajo": "#16a34a"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp, [data-testid="stMarkdownContainer"] {
  font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
}
.stApp { background: linear-gradient(180deg,#f6faf6 0%,#eef4f2 100%); }

/* Ocultar cromo por defecto para look de producto */
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }

/* FIX: mantener visible el botón para VOLVER A MOSTRAR el panel lateral tras ocultarlo
   (el cromo oculto arriba se lo llevaba; un hijo puede re-mostrarse aunque el padre esté oculto) */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] {
  visibility: visible !important;
  display: inline-flex !important;
  opacity: 1 !important;
  z-index: 1000001 !important;
}
[data-testid="stExpandSidebarButton"] svg { color:#12261a !important; fill:#12261a !important; }
[data-testid="stExpandSidebarButton"] { background: rgba(255,255,255,.85) !important; border-radius:8px !important; }
.block-container { padding-top: 1.4rem; max-width: 1180px; }

/* Sidebar institucional */
[data-testid="stSidebar"] { background: linear-gradient(180deg,#12261a 0%,#0d3b4a 100%); }
[data-testid="stSidebar"] * { color: #dbe7e0 !important; }
[data-testid="stSidebar"] a { color: #bfe3cf !important; }

/* Ocultamos la navegación por defecto de Streamlit y usamos una propia con marca */
[data-testid="stSidebarNav"]{display:none;}
.ab-brand{font:800 1.4rem/1.1 'Inter',sans-serif;color:#eafff4 !important;padding:.55rem .25rem 0;letter-spacing:-.01em;}
.ab-brand span{font-weight:600;color:#bfe3cf !important;font-size:1.02rem;}
.ab-brand-sub{font-size:.68rem;color:#8fd0ac !important;padding:.2rem .25rem .7rem;
  border-bottom:1px solid rgba(255,255,255,.12);margin-bottom:.5rem;}
[data-testid="stSidebar"] [data-testid="stPageLink"]{margin:.05rem 0;}
[data-testid="stSidebar"] a:hover{background:rgba(46,125,50,.26) !important;border-radius:8px;}
[data-testid="stSidebar"] a[aria-current="page"]{background:rgba(46,125,50,.34) !important;border-radius:8px;}

/* Títulos */
h1,h2,h3 { color: #12261a; font-weight: 800; letter-spacing:-.01em; }
h2 { border-left: 5px solid #2e7d32; padding-left:.55rem; margin-top:1.4rem; }

/* HERO */
.ab-hero {
  position:relative; overflow:hidden; border-radius:20px; padding:34px 40px; margin:.2rem 0 1.4rem;
  background: linear-gradient(120deg,#1b5e20 0%,#0f6b53 48%,#01579b 100%);
  box-shadow: 0 14px 38px rgba(16,60,40,.28);
}
.ab-hero::after{content:"";position:absolute;right:-60px;top:-60px;width:280px;height:280px;
  background:radial-gradient(circle,rgba(255,255,255,.16),transparent 70%);border-radius:50%;}
.ab-hero::before{content:"";position:absolute;left:-40px;bottom:-80px;width:240px;height:240px;
  background:radial-gradient(circle,rgba(255,255,255,.08),transparent 70%);border-radius:50%;}
.ab-hero h1{color:#fff;font-size:2.35rem;line-height:1.08;margin:0 0 .3rem;font-weight:800;}
.ab-hero .sub{color:#eafff4;font-size:1.06rem;max-width:760px;line-height:1.5;font-weight:400;}
.ab-hero .eyebrow{color:#bff3d6;font-weight:700;letter-spacing:.14em;font-size:.72rem;text-transform:uppercase;margin-bottom:.5rem;}
.ab-pills{margin-top:1rem;display:flex;gap:.5rem;flex-wrap:wrap;}
.ab-pill{background:rgba(255,255,255,.16);color:#fff;border:1px solid rgba(255,255,255,.28);
  padding:.32rem .8rem;border-radius:999px;font-size:.82rem;font-weight:600;backdrop-filter:blur(4px);}
.ab-pill.live::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;
  background:#5cf29a;margin-right:.4rem;box-shadow:0 0 0 3px rgba(92,242,154,.35);vertical-align:middle;}

/* KPI cards */
.ab-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:.2rem 0 .6rem;}
.ab-kpi{background:#fff;border-radius:16px;padding:18px 20px;box-shadow:0 6px 20px rgba(20,60,40,.08);
  border:1px solid #e7efe9;border-top:4px solid var(--acc,#2e7d32);}
.ab-kpi .lab{color:#5a6b60;font-size:.82rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em;}
.ab-kpi .val{color:#12261a;font-size:2.15rem;font-weight:800;line-height:1.1;margin-top:.1rem;}
.ab-kpi .foot{color:#8a978f;font-size:.78rem;margin-top:.15rem;}

/* Feature cards */
.ab-feats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:.4rem 0;}
.ab-feat{background:#fff;border-radius:16px;padding:20px 22px;box-shadow:0 6px 20px rgba(20,60,40,.07);
  border:1px solid #e7efe9;}
.ab-feat .ic{font-size:1.7rem;} .ab-feat h4{margin:.4rem 0 .3rem;color:#12261a;font-size:1.06rem;font-weight:700;}
.ab-feat p{color:#4c5b52;font-size:.92rem;line-height:1.5;margin:0;}

/* Callout de uso responsable */
.ab-note{background:#fff7ed;border:1px solid #fed7aa;border-left:5px solid #f59e0b;border-radius:12px;
  padding:14px 18px;color:#7c4a03;font-size:.9rem;line-height:1.5;margin:.6rem 0 1rem;}
.ab-note b{color:#663a02;}

/* Badges de fuentes */
.ab-src{display:flex;gap:.5rem;flex-wrap:wrap;margin:.3rem 0;}
.ab-badge{background:#eaf3ee;color:#1b5e20;border:1px solid #cfe6d8;padding:.3rem .7rem;border-radius:8px;
  font-size:.82rem;font-weight:600;}

/* Métricas nativas (otras páginas) */
[data-testid="stMetric"]{background:#fff;border:1px solid #e7efe9;border-radius:14px;padding:14px 16px;
  box-shadow:0 4px 14px rgba(20,60,40,.06);}
[data-testid="stMetricValue"]{color:#12261a;font-weight:800;}

/* Footer propio */
.ab-foot{color:#7c8b81;font-size:.8rem;text-align:center;margin-top:1.6rem;padding-top:1rem;
  border-top:1px solid #e2ebe5;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def hero(eyebrow, title, subtitle, pills=None):
    pill_html = ""
    if pills:
        pill_html = '<div class="ab-pills">' + "".join(
            f'<span class="ab-pill{" live" if p.get("live") else ""}">{p["t"]}</span>' for p in pills
        ) + "</div>"
    st.markdown(
        f'<div class="ab-hero"><div class="eyebrow">{eyebrow}</div>'
        f'<h1>{title}</h1><div class="sub">{subtitle}</div>{pill_html}</div>',
        unsafe_allow_html=True)


def kpis(items):
    """items: lista de dicts {lab, val, foot, acc}."""
    cards = "".join(
        f'<div class="ab-kpi" style="--acc:{it.get("acc","#2e7d32")}">'
        f'<div class="lab">{it["lab"]}</div><div class="val">{it["val"]}</div>'
        f'<div class="foot">{it.get("foot","")}</div></div>' for it in items)
    st.markdown(f'<div class="ab-kpis">{cards}</div>', unsafe_allow_html=True)


def features(items):
    """items: lista de dicts {ic, h, p}."""
    cards = "".join(
        f'<div class="ab-feat"><div class="ic">{it["ic"]}</div><h4>{it["h"]}</h4><p>{it["p"]}</p></div>'
        for it in items)
    st.markdown(f'<div class="ab-feats">{cards}</div>', unsafe_allow_html=True)


def note(html):
    st.markdown(f'<div class="ab-note">{html}</div>', unsafe_allow_html=True)


def source_badges(sources):
    b = "".join(f'<span class="ab-badge">{s}</span>' for s in sources)
    st.markdown(f'<div class="ab-src">{b}</div>', unsafe_allow_html=True)


def footer():
    st.markdown(
        '<div class="ab-foot">Ministerio de Minas y Energía</div>',
        unsafe_allow_html=True)


# Navegación propia (reemplaza la de fábrica: control total de nombres/íconos)
PAGES = [
    ("streamlit_app.py", "Inicio", "🏠"),
    ("pages/01_🗺️_Mapa_de_riesgo.py", "Mapa de riesgo", "🗺️"),
    ("pages/02_📊_Ranking.py", "Ranking", "📊"),
    ("pages/03_📋_Ficha_territorial.py", "Ficha territorial", "📋"),
    ("pages/04_🔬_Explicabilidad.py", "Explicabilidad", "🔬"),
    ("pages/05_📂_Datos_abiertos.py", "Datos abiertos", "📂"),
    ("pages/07_🛰️_Monitoreo_satelital.py", "Monitoreo satelital", "🛰️"),
    ("pages/08_🤖_Asistente.py", "Asistente IA", "🤖"),
    ("pages/06_📖_Metodología.py", "Metodología", "📖"),
]


def sidebar_nav():
    with st.sidebar:
        st.markdown(
            '<div class="ab-brand">🌿 AquaBosque <span>Minero IA</span></div>'
            '<div class="ab-brand-sub">Priorización de riesgo ambiental · MinEnergía</div>',
            unsafe_allow_html=True)
        for path, label, icon in PAGES:
            st.page_link(path, label=label, icon=icon)
