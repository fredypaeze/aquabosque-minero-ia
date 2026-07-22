"""Fixtures compartidas para la batería de pruebas de AquaBosque."""
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

NIVELES = ["Bajo", "Medio", "Alto", "Crítico"]
PESOS = {"minero": 0.30, "deforestacion": 0.25, "fuego": 0.15, "hidrico": 0.20, "sensibilidad": 0.10}
FEATURES = ["idx_minero", "idx_deforestacion", "idx_fuego", "idx_hidrico", "idx_sensibilidad",
            "mineria_titulos", "mineria_minerales", "deforestacion_ha",
            "runap_areas", "runap_hectareas", "agua_estaciones",
            "mineria_volumen", "mineria_regalias", "es_pdet",
            "focos_7d"]


@pytest.fixture(scope="session")
def root():
    return ROOT


@pytest.fixture(scope="session")
def etiqueta():
    """Dataset maestro con etiqueta (una fila por municipio)."""
    p = ROOT / "data" / "processed" / "master_con_etiqueta.csv"
    assert p.exists(), f"Falta el dataset etiquetado: {p}"
    return pd.read_csv(p)


@pytest.fixture(scope="session")
def metricas():
    p = ROOT / "models" / "metrics" / "metricas.json"
    assert p.exists(), f"Faltan las métricas del modelo: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def modelo_bundle():
    import joblib
    p = ROOT / "models" / "trained" / "xgb_riesgo.joblib"
    assert p.exists(), f"Falta el modelo entrenado: {p}"
    return joblib.load(p)
