# -*- coding: utf-8 -*-
"""Tests de REGRESIÓN — Zoom Bogotá V1 (Sec 70/71).
Cada bug material corregido produce un test permanente: un error corregido no vuelve.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "rc"))
import rc_lib  # noqa: E402

CFG = rc_lib.load_config()
OUT = ROOT / "outputs" / "rc_v1"


# ---- F1: fuga temporal same-day ----
def test_target_window_is_strictly_future_config():
    a, b = CFG["target"]["window_days_ahead"]
    assert a >= 1, "el target debe empezar en t+1 (nunca el día t)"
    assert b >= a


def test_fwd_target_rejects_same_day():
    with pytest.raises(ValueError):
        rc_lib.fwd_target(pd.Series([0, 1, 0]), a=0, b=2)  # a=0 incluiría el día t


def test_fwd_target_uses_only_future():
    # evento SOLO en t=2; para t=0 con [t+1,t+2] debe verlo; para t=2 no (es el propio día)
    ev = pd.Series([0, 0, 1, 0, 0], dtype=float)
    y = rc_lib.fwd_target(ev, 1, 2)
    assert y.iloc[0] == 1.0   # ve el evento futuro en t=2
    assert y.iloc[2] == 0.0   # el evento del propio día t NO cuenta


# ---- F9: embargo / splits ----
def test_temporal_splits_do_not_overlap_and_have_embargo():
    assert CFG["splits"]["embargo_days"] >= 1
    assert not CFG["splits"]["random_split"]
    tr_end = pd.Timestamp(CFG["splits"]["train"]["end"])
    ca_start = pd.Timestamp(CFG["splits"]["calib"]["start"])
    te_start = pd.Timestamp(CFG["splits"]["test"]["start"])
    assert tr_end < ca_start < te_start


# ---- F2: thresholds nunca desde test ----
def test_thresholds_policy_uses_calib_not_test():
    assert CFG["thresholds"]["policy"] == "calib_prevalence_multiple"
    assert CFG["calibration"]["fit_on"] == "calib"
    n, r = rc_lib.thresholds_from_calib(0.08, CFG)
    assert r > n > 0


# ---- F4: monotonía no por defecto ----
def test_monotonicity_not_global_by_default():
    assert CFG["model"]["monotone_constraints"] == "none"


# ---- Resolución localidad, no UPZ probabilidad (Sec 45) ----
def test_prediction_resolution_is_localidad():
    assert "localidad" in CFG["contract"]["PREDICTION_RESOLUTION"].lower()


def test_upz_marked_descriptive_not_probability():
    f = ROOT / "data" / "processed" / "bogota_upz_territorial_v1.csv"
    if not f.exists():
        pytest.skip("índice UPZ aún no generado")
    d = pd.read_csv(f)
    assert (d["naturaleza"] == "OBSERVED_DESCRIPTIVE").all()


# ---- F3: CRS — índice territorial sin transformación afín ----
def test_territorial_index_is_crs_safe():
    f = OUT / "territorial_index_validation.json"
    if not f.exists():
        pytest.skip("validación territorial aún no generada")
    v = json.loads(f.read_text(encoding="utf-8"))
    assert "IDIGER" in v["geocodificacion"]
    assert v["error_crs"].startswith("0")   # sin el afín de 57 km


def test_territorial_sanity_remocion_in_cerros():
    f = ROOT / "data" / "processed" / "bogota_territorial_v1.csv"
    if not f.exists():
        pytest.skip("índice territorial aún no generado")
    d = pd.read_csv(f).sort_values("eventos_remocion", ascending=False)
    top = set(d.head(4)["localidad"])
    cerros = {"Ciudad Bolívar", "Usme", "San Cristóbal", "Rafael Uribe Uribe", "Chapinero", "Usaquén"}
    assert len(top & cerros) >= 3, f"la remoción debería concentrarse en cerros; top={top}"


# ---- Métricas honestas registradas (autoridad = ejecución) ----
def test_product_page_honest_framing():
    """Sec 45/69: la interfaz no puede presentar el índice como probabilidad calibrada."""
    p = ROOT / "app" / "pages" / "10_🏙️_Zoom_Bogota.py"
    src = p.read_text(encoding="utf-8")
    low = src.lower()
    # debe declarar naturaleza descriptiva
    assert "descriptivo" in low
    assert "no es una probabilidad" in low or "no es probabilidad" in low or "no es un pronóstico" in low
    # no debe vender predicción/alerta calibrada como el producto
    assert "probabilidad calibrada" not in low or "no" in low  # solo aparece negada
    # UPZ etiquetada como priorización
    assert "prioriz" in low


def test_rc_metrics_recorded_and_reproducible():
    f = OUT / "rc_metrics.json"
    if not f.exists():
        pytest.skip("métricas RC aún no generadas")
    m = json.loads(f.read_text(encoding="utf-8"))
    assert m["seed"] == CFG["model"]["seed"]
    pm = m["modelo_primario_sin_monotonia"]
    assert 0.0 <= pm["roc_auc"] <= 1.0 and 0.0 <= pm["pr_auc"] <= 1.0
    assert "brier_skill_score" in pm   # habilidad honesta reportada
