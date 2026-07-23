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

    # --- Conocimiento de metodología (para preguntas de defensa) ---
    conocimiento = [
        ("conoc-sensibilidad",
         "El índice de sensibilidad (idx_sensibilidad) mide el valor ambiental y social que hay que proteger en el "
         "territorio: se calcula con las hectáreas de áreas protegidas del RUNAP cercanas al municipio (normalizadas), "
         "más un incremento de 0.25 si el municipio es PDET (posconflicto). Va de 0 a 1: 0 = poco valor a proteger, "
         "1 = mucho valor ambiental o social en juego. No mide daño; mide la importancia de lo que está expuesto."),
        ("conoc-fuego-fuente",
         "La señal de fuego (idx_fuego, focos_7d, frp_total) proviene de NASA FIRMS: sensores satelitales VIIRS de "
         "375 m (satélites Suomi-NPP y NOAA-20) y MODIS de 1 km (Terra/Aqua, colección C6.1). Detecta focos de calor "
         "activos casi en tiempo real; se cuentan por municipio en los últimos 7 días (point-in-polygon) y se suma su "
         "potencia radiativa FRP en megavatios. Es dato abierto y se actualiza a diario."),
        ("conoc-lectura-indices",
         "Cómo se leen los índices: todos van de 0 a 1, donde 1 = mayor alerta y prioridad de revisión, y 0 = sin señal. "
         "NO es '0 malo, 1 bueno': es al revés, 1 es lo más urgente. idx_minero (presión minera), idx_deforestacion "
         "(pérdida de bosque), idx_fuego (quema reciente), idx_hidrico (agua degradada = 1 − ICA) e idx_sensibilidad "
         "(valor a proteger) apuntan todos en la misma dirección. En idx_hidrico, un 0 puede significar 'sin estación "
         "de medición' (sin dato observado), no 'agua sana'."),
        ("conoc-formula",
         "El score de riesgo se calcula como: 0.30·minero + 0.25·deforestación + 0.15·fuego + 0.20·hídrico + "
         "0.10·sensibilidad. El nivel se asigna por cuantiles del score: Crítico ≥ percentil 95, Alto ≥ p85, "
         "Medio ≥ p60, Bajo el resto. Es una priorización relativa, no una medición absoluta de daño."),
        ("conoc-arquitectura",
         "Arquitectura y software: todo en Python de código abierto. Integración territorial sin GDAL (cruce por "
         "código DANE exacto o por centroide con distancia haversine). Modelo XGBoost multiclase con explicabilidad "
         "SHAP; capas de rigor con Conformal Prediction e Isolation Forest (scikit-learn). Satélite profundo: "
         "Sentinel-2 vía STAC + rasterio y un U-Net en PyTorch sobre GPU NVIDIA L40S. Asistente con LLM local "
         "(Llama 3.3 70B / Qwen 2.5) y embeddings bge-m3. Aplicación en Streamlit + Plotly. Todo corre en la "
         "infraestructura del Ministerio: el dato no sale del Estado."),
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
