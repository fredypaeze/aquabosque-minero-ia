"""Asistente RAG soberano de AquaBosque (IA generativa sobre datos abiertos).

Recupera información de los resultados de AquaBosque (priorización municipal,
metodología, capa satelital) y responde en lenguaje natural, **aterrizado en la
evidencia** — sin inventar. Corre sobre el LLM local del Ministerio (Ollama en las
NVIDIA L40S): embeddings con `bge-m3` y generación con un modelo local. El dato
ciudadano/ambiental **nunca sale de la infraestructura del Estado** (soberanía).

Config por entorno (no hardcodear secretos):
  AQB_LLM_URL    (def http://10.250.171.9:8080)
  AQB_LLM_TOKEN  (API key de Open WebUI)
  AQB_EMBED_MODEL(def bge-m3:latest) · AQB_CHAT_MODEL(def qwen2.5:32b)

Uso:
  python -m aquabosque.asistente.rag build          # construye el índice
  python -m aquabosque.asistente.rag ask "pregunta" # responde aterrizado
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PRED = ROOT / "outputs" / "tables" / "predicciones.csv"
FUEGO = ROOT / "data" / "processed" / "fuego_municipal.csv"
DOCS = [ROOT / "docs" / "CRISP_ML.md", ROOT / "README.md"]
INDEX = ROOT / "data" / "processed" / "rag_index.npz"
META = ROOT / "data" / "processed" / "rag_meta.json"

LLM_URL = os.environ.get("AQB_LLM_URL", "http://10.250.171.9:8080").rstrip("/")
LLM_TOKEN = os.environ.get("AQB_LLM_TOKEN", "")
EMBED_MODEL = os.environ.get("AQB_EMBED_MODEL", "bge-m3:latest")
CHAT_MODEL = os.environ.get("AQB_CHAT_MODEL", "qwen2.5:32b")


def _post(path: str, payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        LLM_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {LLM_TOKEN}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def embed(textos: list[str]) -> np.ndarray:
    """Embeddings bge-m3 (batches). Devuelve matriz (n, 1024) normalizada."""
    vecs: list[list[float]] = []
    for i in range(0, len(textos), 64):
        lote = textos[i:i + 64]
        d = _post("/ollama/api/embed", {"model": EMBED_MODEL, "input": lote})
        emb = d.get("embeddings") or d.get("embedding")
        vecs.extend(emb if isinstance(emb[0], list) else [emb])
    m = np.asarray(vecs, dtype="float32")
    m /= (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
    return m


# ---------------------------------------------------------------------------
def construir_corpus() -> list[dict]:
    """Un chunk por municipio (hechos verificables) + chunks de metodología."""
    pred = pd.read_csv(PRED)
    pred["cod_mpio"] = pred["cod_mpio"].astype(float).astype(int)
    # predicciones.csv ya trae focos_7d (feature del modelo): evitar colisión al cruzar.
    pred = pred.drop(columns=[c for c in ["focos_7d", "frp_total"] if c in pred.columns])
    if FUEGO.exists():
        fuego = pd.read_csv(FUEGO)[["cod_mpio", "focos_7d", "frp_total"]]
        pred = pred.merge(fuego, on="cod_mpio", how="left")
    for c in ["focos_7d", "frp_total"]:
        if c not in pred:
            pred[c] = 0
    pred[["focos_7d", "frp_total"]] = pred[["focos_7d", "frp_total"]].fillna(0)

    corpus = []
    for _, r in pred.iterrows():
        txt = (f"Municipio {r['municipio']} ({r['departamento']}). "
               f"Nivel de priorización: {r['riesgo_nivel']} (score {r['riesgo_score']:.3f}, "
               f"predicción del modelo {r.get('riesgo_pred', r['riesgo_nivel'])}). "
               f"Índices 0-1 → minero {r['idx_minero']:.2f}, deforestación {r['idx_deforestacion']:.2f}, "
               f"fuego satelital {r.get('idx_fuego', 0):.2f}, hídrico {r['idx_hidrico']:.2f}, "
               f"sensibilidad {r['idx_sensibilidad']:.2f}. "
               f"Focos de calor activos (7 días, satélite FIRMS): {int(r['focos_7d'])}.")
        corpus.append({"id": f"mpio-{int(r['cod_mpio'])}", "tipo": "municipio",
                       "municipio": r["municipio"], "texto": txt})

    # --- Chunks de RESUMEN (para preguntas de ranking/agregación) ---
    def top_txt(df, col, etiqueta, n=10, fmt="{:.0f}"):
        d = df.sort_values(col, ascending=False).head(n)
        return ", ".join(f"{r['municipio']} ({r['departamento']}) {fmt.format(r[col])}"
                         for _, r in d.iterrows())

    corpus.append({"id": "resumen-nacional-focos", "tipo": "resumen", "municipio": "",
                   "texto": "Ranking NACIONAL de municipios con más focos de calor activos por satélite "
                            f"(FIRMS, 7 días): {top_txt(pred, 'focos_7d', 'focos')}."})
    corpus.append({"id": "resumen-nacional-score", "tipo": "resumen", "municipio": "",
                   "texto": "Ranking NACIONAL de municipios por score de priorización ambiental (mayor a menor): "
                            f"{top_txt(pred, 'riesgo_score', 'score', fmt='{:.3f}')}."})
    dist = pred["riesgo_nivel"].value_counts().to_dict()
    corpus.append({"id": "resumen-distribucion", "tipo": "resumen", "municipio": "",
                   "texto": "Distribución de niveles de priorización (1.122 municipios): "
                            f"Crítico {dist.get('Crítico',0)}, Alto {dist.get('Alto',0)}, "
                            f"Medio {dist.get('Medio',0)}, Bajo {dist.get('Bajo',0)}. "
                            f"Municipios con fuego activo por satélite: {int((pred['focos_7d']>0).sum())}."})
    # Resumen por departamento (solo los relevantes: con priorización alta o fuego)
    for dep, g in pred.groupby("departamento"):
        gf = g[g["focos_7d"] > 0]
        if g["riesgo_nivel"].isin(["Alto", "Crítico"]).sum() == 0 and len(gf) == 0:
            continue
        partes = [f"Departamento {dep}."]
        crit = g[g["riesgo_nivel"].isin(["Crítico", "Alto"])].sort_values("riesgo_score", ascending=False).head(6)
        if len(crit):
            partes.append("Municipios más priorizados: " +
                          ", ".join(f"{r['municipio']} ({r['riesgo_nivel']}, score {r['riesgo_score']:.3f})"
                                    for _, r in crit.iterrows()) + ".")
        if len(gf):
            partes.append("Municipios con más focos de calor activos (satélite): " +
                          ", ".join(f"{r['municipio']} {int(r['focos_7d'])}"
                                    for _, r in gf.sort_values("focos_7d", ascending=False).head(6).iterrows()) + ".")
        corpus.append({"id": f"resumen-dep-{dep}", "tipo": "resumen", "municipio": "", "texto": " ".join(partes)})

    # --- Base de conocimiento del sistema (para responder cualquier pregunta de defensa) ---
    conocimiento = [
        ("conoc-que-es",
         "AquaBosque Minero IA es una herramienta del Ministerio de Minas y Energía (Grupo de Datos Estratégicos) "
         "que prioriza en qué municipios de Colombia actuar por riesgo ambiental, cruzando minería, deforestación, "
         "fuego, agua y sensibilidad en una sola plataforma con datos oficiales. Compite en el concurso Datos al "
         "Ecosistema 2026, categoría Sostenibilidad y Medio Ambiente. No prueba causalidad ni ilegalidad: orienta revisión."),
        ("conoc-cobertura",
         "El sistema cubre los 1.122 municipios del país (base DANE DIVIPOLA, dataset gdxc-w37w de datos.gov.co, "
         "coincide 100% con la fuente oficial). Distribución de prioridad: 57 Crítico, 112 Alto, 280 Medio, 673 Bajo."),
        ("conoc-fuente-mineria",
         "Datos de minería: Agencia Nacional de Minería (ANM). Títulos y explotadores del registro RUCOM "
         "(datos.gov.co 42ha-fhvj) y volumen de explotación y regalías de ANM (r85m-vv6c). Se cruzan al municipio por "
         "código DANE (cruce exacto, validado). Mide presión minera FORMAL; no observa minería ilegal."),
        ("conoc-fuente-deforestacion",
         "Datos de deforestación: IDEAM / Sistema de Monitoreo de Bosques (SMByC). Hectáreas deforestadas por "
         "municipio (último año disponible). Se cruza por nombre de municipio; los municipios sin registro se toman "
         "como deforestación no significativa (0), documentado."),
        ("conoc-fuente-agua",
         "Datos de agua: IDEAM, plataforma DHIME, Índice de Calidad del Agua (ICA, campo ica5). Cada estación se "
         "asigna al municipio más cercano por distancia al centroide (haversine) si está a menos de 50 km; se agrega "
         "el ICA medio y el número de estaciones. Solo unos 71 municipios tienen estación cercana."),
        ("conoc-fuente-runap-pdet",
         "Sensibilidad: áreas protegidas del RUNAP (Registro Único Nacional de Áreas Protegidas), asignadas por "
         "cercanía al centroide (número de áreas y hectáreas), más los municipios PDET (posconflicto, dato DANE). "
         "A más área protegida o condición PDET, mayor sensibilidad."),
        ("conoc-fuente-fuego",
         "La señal de fuego (idx_fuego, focos_7d, frp_total) proviene de NASA FIRMS: sensores satelitales VIIRS de "
         "375 m (satélites Suomi-NPP y NOAA-20) y MODIS de 1 km (Terra/Aqua, colección C6.1). Detecta focos de calor "
         "activos casi en tiempo real; se cuentan por municipio en los últimos 7 días con point-in-polygon y se suma "
         "su potencia radiativa (FRP) en megavatios. Es dato abierto y se actualiza automáticamente a diario."),
        ("conoc-indices-def",
         "El sistema tiene 5 índices normalizados de 0 a 1: idx_minero (presión minera formal), idx_deforestacion "
         "(pérdida de bosque), idx_fuego (quema reciente por satélite), idx_hidrico (calidad del agua degradada, "
         "calculado como 1 menos el ICA) e idx_sensibilidad (valor ambiental y social a proteger)."),
        ("conoc-sensibilidad",
         "El índice de sensibilidad (idx_sensibilidad) mide el valor ambiental y social que hay que proteger en el "
         "territorio. Se calcula con las hectáreas de áreas protegidas del RUNAP cercanas al municipio (normalizadas), "
         "más un incremento de 0.25 si el municipio es PDET (posconflicto). 0 = poco valor a proteger, 1 = mucho. "
         "No mide daño; mide la importancia de lo que está expuesto."),
        ("conoc-lectura-indices",
         "Cómo se leen los índices: todos van de 0 a 1, donde 1 = mayor alerta y prioridad de revisión, y 0 = sin señal. "
         "NO es '0 malo, 1 bueno': es al revés, 1 es lo más urgente. En idx_hidrico un 0 puede significar 'sin "
         "estación de medición' (sin dato observado), no 'agua sana'; el sistema lo marca como ausencia de dato."),
        ("conoc-normalizacion",
         "La normalización de los índices usa transformación logarítmica (log1p) seguida de min-max a [0,1]. Se usa "
         "log porque las señales tienen colas largas (pocos municipios con valores muy altos). idx_hidrico es la "
         "excepción: es directamente 1 menos el ICA. Todo es reproducible desde el código."),
        ("conoc-formula-etiqueta",
         "El score de riesgo se calcula como: 0.30·minero + 0.25·deforestación + 0.15·fuego + 0.20·hídrico + "
         "0.10·sensibilidad (rango real aproximado 0 a 0.5). El nivel se asigna por cuantiles del score: Crítico si "
         "está en el 5% superior (percentil 95), Alto entre p85 y p95, Medio entre p60 y p85, Bajo el resto. Se usan "
         "cuantiles (priorización relativa) porque con umbrales absolutos las clases altas quedarían casi vacías."),
        ("conoc-modelo",
         "El modelo es un XGBoost multiclase que clasifica el municipio en 4 niveles (Bajo, Medio, Alto, Crítico) a "
         "partir de 15 variables: los 5 índices más 10 variables crudas (títulos y volumen minero, deforestación, "
         "áreas y hectáreas RUNAP, estaciones de agua, focos_7d, PDET). Hiperparámetros: 300 árboles, profundidad 4, "
         "tasa de aprendizaje 0.08, partición estratificada 75/25."),
        ("conoc-metricas",
         "Métricas del modelo en prueba: accuracy 0.89, línea base (clase mayoritaria) 0.60, F1-macro 0.78. "
         "Honestidad declarada: la etiqueta es una fórmula, así que el modelo la re-aprende y la accuracy es alta por "
         "construcción; el valor real no es la exactitud sino la priorización interpretable. Por eso se reporta la "
         "línea base para comparar con transparencia."),
        ("conoc-shap",
         "La explicabilidad usa SHAP (TreeExplainer): para cada municipio muestra qué variables pesaron más en su "
         "clasificación. A nivel global, las variables más influyentes son la presión minera, la deforestación y el "
         "fuego. SHAP es el núcleo defendible: explica el porqué, no solo el qué."),
        ("conoc-conformal",
         "Conformal Prediction: capa de rigor que da una garantía estadística. Con 90% de confianza objetivo, el "
         "nivel real de un municipio cae dentro del conjunto de predicción; verificado empíricamente en 91.4% "
         "(promedio sobre 100 particiones). Es rigor usado en medicina y finanzas; convierte la 'confianza' (softmax) "
         "en una certeza calibrada. Envuelve al modelo sin reemplazarlo."),
        ("conoc-anomalias",
         "Detección de anomalías con Isolation Forest (no supervisada, sin usar etiquetas): identifica municipios con "
         "combinaciones atípicas de presión. Detectó 57 municipios atípicos; 43 coinciden con Alto/Crítico "
         "(confirmación independiente) y 14 son atípicos que el índice ponderado no destacaba."),
        ("conoc-sentinel2",
         "Capa satelital profunda: imágenes Sentinel-2 de 10 metros descargadas vía STAC y procesadas con rasterio en "
         "la GPU NVIDIA L40S del Ministerio. Detección de cambio NDVI entre dos fechas y un modelo de deep learning "
         "U-Net (PyTorch) que segmenta bosque. En una zona de La Macarena detectó cerca de 985 hectáreas de pérdida; "
         "el U-Net alcanzó un IoU de 0.77. Es prueba de capacidad sobre una zona; el procesamiento no sale del Estado."),
        ("conoc-asistente",
         "El asistente de IA generativa usa recuperación (RAG): embeddings con el modelo bge-m3 sobre la evidencia del "
         "sistema y generación con un modelo de lenguaje grande local (Llama 3.3 70B o Qwen 2.5). Corre en la "
         "infraestructura del Ministerio, así que el dato no sale del Estado. Está configurado para no inventar: solo "
         "responde con la evidencia recuperada y cita la fuente."),
        ("conoc-arquitectura",
         "Arquitectura y software: todo en Python de código abierto. Integración territorial sin GDAL (cruce por "
         "código DANE exacto o por centroide con distancia haversine). Modelo XGBoost multiclase con explicabilidad "
         "SHAP; capas de rigor con Conformal Prediction e Isolation Forest (scikit-learn). Satélite profundo con "
         "Sentinel-2, rasterio y U-Net en PyTorch sobre GPU NVIDIA L40S. Asistente con LLM local y embeddings bge-m3. "
         "Aplicación en Streamlit y Plotly, desplegada como servicio; repositorio abierto en GitHub con integración "
         "continua y 16 pruebas automáticas. Todo en la infraestructura del Ministerio."),
        ("conoc-honestidad",
         "Principios de honestidad del sistema: no prueba causalidad ni ilegalidad, orienta revisión y no sanciona. "
         "Las ausencias de dato se marcan, no se inventan. La accuracy alta no se vende como mérito (la etiqueta es "
         "una fórmula). La detección de deforestación por imagen Sentinel-2 es prueba de capacidad sobre zonas, no "
         "cobertura nacional operativa. Todo el código y los datos son abiertos y auditables."),
        ("conoc-actualizacion",
         "Actualización: la capa de fuego (NASA FIRMS) se refresca automáticamente a diario con un temporizador; es "
         "cobertura nacional. El modelo estructural (minería, deforestación, agua, sensibilidad) es estable y se "
         "re-entrena cuando entran datos nuevos, no cada día. El análisis Sentinel-2 se corre por zonas en la GPU."),
    ]
    for cid, txt in conocimiento:
        corpus.append({"id": cid, "tipo": "conocimiento", "municipio": "", "texto": txt})

    for doc in DOCS:
        if not doc.exists():
            continue
        partes = [p.strip() for p in doc.read_text(encoding="utf-8").split("\n## ") if p.strip()]
        for j, p in enumerate(partes):
            corpus.append({"id": f"{doc.stem}-{j}", "tipo": "doc",
                           "municipio": "", "texto": p[:1200]})
    return corpus


def build() -> None:
    if not LLM_TOKEN:
        sys.exit("Falta AQB_LLM_TOKEN (API key de Open WebUI).")
    corpus = construir_corpus()
    print(f"Corpus: {len(corpus)} chunks · embeddings con {EMBED_MODEL} …")
    M = embed([c["texto"] for c in corpus])
    np.savez_compressed(INDEX, vectors=M)
    META.write_text(json.dumps(corpus, ensure_ascii=False), encoding="utf-8")
    print(f"OK índice: {INDEX.name} {M.shape} · {META.name}")


def retrieve(pregunta: str, k: int = 6) -> list[dict]:
    corpus = json.loads(META.read_text(encoding="utf-8"))
    M = np.load(INDEX)["vectors"]
    q = embed([pregunta])[0]
    sims = M @ q
    idx = np.argsort(-sims)[:k]
    return [{**corpus[i], "score": float(sims[i])} for i in idx]


SYSTEM_PROMPT = (
    "Eres el asistente de AquaBosque, sistema de priorización ambiental territorial de Colombia "
    "basado en datos abiertos e IA. Responde SOLO con la información del CONTEXTO. Si no está, dilo. "
    "No inventes cifras. Cita los municipios/fuentes usados. Aclara que la priorización no prueba "
    "causalidad ni ilegalidad: orienta revisión.")


def responder(pregunta: str, k: int = 6) -> dict:
    """Devuelve {'respuesta', 'fuentes'} usando el LLM local (una sola recuperación)."""
    if not LLM_TOKEN:
        raise RuntimeError("Falta AQB_LLM_TOKEN (API key de Open WebUI).")
    ctx = retrieve(pregunta, k)
    contexto = "\n".join(f"[{c['id']}] {c['texto']}" for c in ctx)
    user = f"CONTEXTO:\n{contexto}\n\nPREGUNTA: {pregunta}"
    d = _post("/api/chat/completions", {
        "model": CHAT_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}],
        "stream": False, "temperature": 0.2})
    return {"respuesta": d["choices"][0]["message"]["content"], "fuentes": ctx}


def ask(pregunta: str) -> str:
    return responder(pregunta)["respuesta"]


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "build":
        build()
    elif len(sys.argv) >= 3 and sys.argv[1] == "ask":
        print(ask(" ".join(sys.argv[2:])))
    else:
        print(__doc__)
