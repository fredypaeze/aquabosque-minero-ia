"""Coherencia de la etiqueta técnica de priorización (fórmula + cuantiles)."""
from conftest import PESOS


def test_pesos_suman_uno():
    assert abs(sum(PESOS.values()) - 1.0) < 1e-9


def test_score_reproduce_la_formula(etiqueta):
    """riesgo_score == 0.30*minero + 0.25*defo + 0.15*fuego + 0.20*hidrico + 0.10*sensibilidad."""
    recomputado = (PESOS["minero"] * etiqueta["idx_minero"]
                   + PESOS["deforestacion"] * etiqueta["idx_deforestacion"]
                   + PESOS["fuego"] * etiqueta["idx_fuego"]
                   + PESOS["hidrico"] * etiqueta["idx_hidrico"]
                   + PESOS["sensibilidad"] * etiqueta["idx_sensibilidad"])
    dif = (recomputado - etiqueta["riesgo_score"]).abs()
    assert dif.max() < 1e-3, f"La fórmula no reproduce el score (dif máx {dif.max():.5f})"


def test_monotonia_score_nivel(etiqueta):
    """Los umbrales por cuantil no se solapan: el score mínimo de una clase
    superior debe ser >= al score máximo de la inferior."""
    orden = ["Bajo", "Medio", "Alto", "Crítico"]
    maxs = {n: etiqueta.loc[etiqueta["riesgo_nivel"] == n, "riesgo_score"].max() for n in orden}
    mins = {n: etiqueta.loc[etiqueta["riesgo_nivel"] == n, "riesgo_score"].min() for n in orden}
    for lo, hi in zip(orden, orden[1:]):
        assert mins[hi] >= maxs[lo] - 1e-9, f"Solapamiento entre {lo} y {hi}"


def test_distribucion_por_cuantil_plausible(etiqueta):
    """Crítico ~top 5%, Alto ~siguiente 10% (p85-p95). Se valida el orden de
    magnitud de la clasificación relativa, no cifras exactas."""
    n = len(etiqueta)
    d = etiqueta["riesgo_nivel"].value_counts().to_dict()
    assert d.get("Crítico", 0) <= 0.10 * n     # cola superior, minoría
    assert d.get("Bajo", 0) >= 0.40 * n         # mayoría en la base
    assert d.get("Alto", 0) < d.get("Medio", 0)  # pirámide de riesgo
