# 🌿 AquaBosque Minero IA

**Sistema explicable de IA geoespacial para priorizar municipios colombianos con riesgo ambiental asociado a presión minera, deforestación y afectación hídrica, usando datos abiertos.**

[![tests](https://img.shields.io/badge/tests-16%20passing-brightgreen)](tests/)
[![demo](https://img.shields.io/badge/demo-en%20vivo-2e7d32)](https://streamlit.spartanit.pro/)
[![python](https://img.shields.io/badge/python-3.12-blue)](requirements.txt)
[![modelo](https://img.shields.io/badge/modelo-XGBoost%20%2B%20SHAP-orange)](docs/MODEL_CARD.md)
[![license](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

> **🔗 Demo en vivo:** **https://streamlit.spartanit.pro/**
> Categoría: Desarrollo Sostenible y Medio Ambiente · Grupo de Datos Estratégicos — Ministerio de Minas y Energía

---

## ⚠️ Uso responsable (principio rector)

AquaBosque Minero IA **no prueba causalidad, no acusa, no sanciona y no determina ilegalidad**. Integra datos abiertos e IA explicable para **priorizar** territorios donde confluyen señales de presión minera, deforestación y afectación hídrica, facilitando el monitoreo estratégico y la toma de decisiones públicas basada en evidencia.

---

## Qué resuelve

Colombia carece de una vista integrada que cruce **actividad minera + deforestación + calidad del agua + sensibilidad ambiental** a nivel municipal. AquaBosque unifica fuentes oficiales en un dataset, calcula una **priorización transparente** y la explica con SHAP, para responder no solo *qué* municipios priorizar sino **por qué**.

## Arquitectura

```
Fuentes abiertas oficiales → ingesta → integración municipal (centroides + haversine, sin GDAL)
  → dataset maestro (1.122 municipios) → 4 índices 0-1 (minero, deforestación, hídrico, sensibilidad)
  → etiqueta técnica por cuantiles → XGBoost multiclase + SHAP
  → dashboard Streamlit (mapa, ranking, ficha, explicabilidad, datos abiertos, metodología)
```

## Resultados (verificados)

| | |
|---|---|
| Municipios | **1.122** (DIVIPOLA 2025) |
| Fuentes reales integradas | **5/5** — sin datos sintéticos |
| Priorización | Bajo 672 · Medio 281 · Alto 112 · **Crítico 57** |
| Modelo | XGBoost · accuracy **0.911** (línea base 0.598) · F1-macro **0.784** |
| Explicabilidad | SHAP global + por municipio |
| Pruebas | **16/16** (integridad, fórmula, modelo, SHAP, artefactos) |

> **Honestidad declarada:** la etiqueta es una fórmula documentada, por lo que el modelo re-aprende parcialmente la regla; la accuracy **no** se vende como mérito predictivo. El valor es la **explicabilidad** y la trazabilidad total. Ver [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md).

## Instalación y ejecución

```bash
python3 -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Arranque de un paso (reconstruye modelo desde el raw y abre el dashboard):
./run_mvp.sh                                          # Windows: .\run_mvp.ps1
```

O por fases:

```bash
python scripts/01_download_data.py    # fuentes tabulares (Socrata datos.gov.co)
python scripts/02_prepare_data.py     # fuentes geoespaciales (ArcGIS: deforestación, RUNAP)
python scripts/03_build_features.py   # dataset maestro + 4 índices + etiqueta
python scripts/04_train_model.py      # XGBoost + SHAP + métricas + predicciones
python scripts/05_generate_outputs.py # verifica artefactos
python scripts/06_run_app.py          # dashboard en http://localhost:8510
```

> El `data/raw/` viene incluido: se puede reconstruir el modelo **sin conexión** (fases 3-4). Las fases 1-2 son solo para re-descargar las fuentes.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

Validan integridad del dataset, que la fórmula de la etiqueta se reproduce, que **el modelo supera la línea base**, la completitud de SHAP y los artefactos del dashboard. CI en GitHub Actions (`.github/workflows/tests.yml`).

## Fuentes de datos (5 dimensiones, 100% oficiales)

| Dimensión | Fuente | Detalle |
|---|---|---|
| Minera | **ANM — RUCOM** (datos.gov.co) | 12.914 registros de comercialización + volumen de explotación + regalías → **actividad minera real** |
| Territorio | **DANE — DIVIPOLA** | 1.122 municipios, centroides |
| Deforestación | **Observatorio/IDEAM** (ArcGIS FeatureServer) | hectáreas por municipio |
| Hídrica | **IDEAM — DHIME** (ICA) | índice de calidad del agua por estación |
| Sensibilidad | **RUNAP** (áreas protegidas) + **PDET** | valor ambiental y social a proteger |

Detalle con estado de verificación y limitaciones en `config/data_sources.yaml` y [`docs/diccionario_datos.md`](docs/diccionario_datos.md).

## Estructura

```
app/         dashboard Streamlit (6 páginas)
src/aquabosque/  data (Socrata/ArcGIS) · features (master + target) · models (train + SHAP)
scripts/     pipeline ejecutable por fases (01-06) + arranque de un paso
data/raw/    fuentes descargadas (incluidas para reconstrucción offline)
models/      modelo entrenado · métricas · importancia SHAP
docs/        MODEL_CARD, metodología, resultados, limitaciones, defensa, diccionario
tests/       batería pytest (16)
outputs/     PDF técnico · pitch PPTX · tablas
```

## Reproducibilidad y honestidad

- Cada fuente documenta origen, fecha y limitaciones; nada sintético.
- La etiqueta de riesgo es **técnica y documentada**, no verdad oficial.
- No se afirma causalidad ni ilegalidad; **lo que no se verifica se declara, no se inventa**.
- Modelo determinista (`random_state=42`): la reconstrucción reproduce las mismas cifras.

## Licencia

MIT — ver [`LICENSE`](LICENSE).
