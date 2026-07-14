"""Fase 5: feature engineering + etiqueta técnica de priorización.

Construye 4 índices 0-1 por municipio y la etiqueta compuesta documentada.

Índices (cada uno 0=sin señal, 1=máxima señal):
  - minero:      densidad de títulos mineros (log1p + min-max; cola pesada).
  - deforestacion: hectáreas deforestadas (log1p + min-max).
  - hidrico:     (1 - ICA) donde hay estación; SIN estación = 0 (ausencia de
                 señal = sin riesgo hídrico OBSERVADO, conservador, documentado).
  - sensibilidad: hectáreas de área protegida (log1p + min-max) — mayor valor
                 ambiental = mayor sensibilidad (más que perder).

Etiqueta técnica (fórmula documentada, spec §11.2; pesos ajustables):
  riesgo = 0.35*minero + 0.30*deforestacion + 0.25*hidrico + 0.10*sensibilidad
  Bajo [0-0.25) · Medio [0.25-0.50) · Alto [0.50-0.75) · Crítico [0.75-1.0]

La etiqueta es TÉCNICA DE PRIORIZACIÓN, no verdad oficial, daño probado ni
contaminación causada. No implica causalidad ni ilegalidad.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MASTER = ROOT / "data" / "processed" / "master_municipal.csv"
OUT = ROOT / "data" / "processed" / "master_con_etiqueta.csv"

PESOS = {"minero": 0.35, "deforestacion": 0.30, "hidrico": 0.25, "sensibilidad": 0.10}


def _minmax_log(valores: dict, cod, vmin, vmax):
    v = valores.get(cod, 0) or 0
    lv = math.log1p(v)
    return round((lv - vmin) / (vmax - vmin), 4) if vmax > vmin else 0.0


def _cuantil(scores):
    """Umbrales por cuantil (priorización RELATIVA). El proyecto prioriza
    territorios; como las señales están dispersas el score absoluto rara vez
    supera 0.45, por lo que umbrales absolutos dejarían Alto/Crítico vacíos.
    Se usan cuantiles (documentado, spec §11.2): Crítico p95, Alto p85,
    Medio p60, Bajo resto."""
    import statistics
    s = sorted(scores)
    def q(p): return s[min(len(s)-1, int(p*len(s)))]
    return {"p95": q(0.95), "p85": q(0.85), "p60": q(0.60)}


def _nivel(x, u):
    return ("Crítico" if x >= u["p95"] else "Alto" if x >= u["p85"]
            else "Medio" if x >= u["p60"] else "Bajo")


def run() -> dict:
    rows = list(csv.DictReader(MASTER.open(encoding="utf-8")))

    def col(name):
        return {r["cod_mpio"]: float(r[name]) for r in rows if r.get(name) not in ("", None)}

    # presión minera = títulos + volumen de explotación (producción real), combinados
    minero_raw = {r["cod_mpio"]: float(r["mineria_titulos"]) + float(r.get("mineria_volumen", 0) or 0) / 1000
                  for r in rows}
    defo_raw = {r["cod_mpio"]: float(r["deforestacion_ha"]) for r in rows}
    runap_raw = {r["cod_mpio"]: float(r["runap_hectareas"]) for r in rows}

    def rango_log(d):
        ls = [math.log1p(v) for v in d.values()]
        return min(ls), max(ls)

    m_lo, m_hi = rango_log(minero_raw)
    d_lo, d_hi = rango_log(defo_raw)
    r_lo, r_hi = rango_log(runap_raw)

    # primer pase: scores
    scores_tmp = []
    for r in rows:
        cod = r["cod_mpio"]
        im = _minmax_log(minero_raw, cod, m_lo, m_hi)
        idf = _minmax_log(defo_raw, cod, d_lo, d_hi)
        ic = r.get("agua_ica_medio")
        ih = round(1 - float(ic), 4) if ic not in ("", None) else 0.0
        isn = _minmax_log(runap_raw, cod, r_lo, r_hi)
        if r.get("es_pdet") == "1":
            isn = round(min(1.0, isn + 0.25), 4)
        scores_tmp.append(round(PESOS["minero"]*im+PESOS["deforestacion"]*idf+PESOS["hidrico"]*ih+PESOS["sensibilidad"]*isn,4))
    umb = _cuantil(scores_tmp)

    out = []
    for r in rows:
        cod = r["cod_mpio"]
        idx_min = _minmax_log(minero_raw, cod, m_lo, m_hi)
        idx_def = _minmax_log(defo_raw, cod, d_lo, d_hi)
        ica = r.get("agua_ica_medio")
        idx_hid = round(1 - float(ica), 4) if ica not in ("", None) else 0.0  # sin estación = 0
        idx_sen = _minmax_log(runap_raw, cod, r_lo, r_hi)
        if r.get("es_pdet") == "1":
            idx_sen = round(min(1.0, idx_sen + 0.25), 4)  # municipio PDET: +sensibilidad social
        riesgo = round(PESOS["minero"] * idx_min + PESOS["deforestacion"] * idx_def +
                       PESOS["hidrico"] * idx_hid + PESOS["sensibilidad"] * idx_sen, 4)
        out.append({**r, "idx_minero": idx_min, "idx_deforestacion": idx_def,
                    "idx_hidrico": idx_hid, "idx_sensibilidad": idx_sen,
                    "riesgo_score": riesgo, "riesgo_nivel": _nivel(riesgo, umb),
                    "hidrico_sin_dato": 1 if ica in ("", None) else 0})

    with OUT.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    dist = {}
    for o in out:
        dist[o["riesgo_nivel"]] = dist.get(o["riesgo_nivel"], 0) + 1
    top = sorted(out, key=lambda x: -x["riesgo_score"])[:10]
    print(f"Etiqueta técnica → {OUT.relative_to(ROOT)}")
    print("  distribución:", {k: dist.get(k, 0) for k in ["Bajo", "Medio", "Alto", "Crítico"]})
    print("  top 10 priorización:")
    for o in top:
        print(f"    {o['municipio'][:22]:22s} {o['departamento'][:14]:14s} "
              f"score {o['riesgo_score']:.3f} [{o['riesgo_nivel']}] "
              f"(M{o['idx_minero']:.2f} D{o['idx_deforestacion']:.2f} H{o['idx_hidrico']:.2f} S{o['idx_sensibilidad']:.2f})")
    return {"distribucion": dist, "n": len(out)}


if __name__ == "__main__":
    run()
