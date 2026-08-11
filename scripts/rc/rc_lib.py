# -*- coding: utf-8 -*-
"""Zoom Bogotá V1 — funciones canónicas reutilizables (una sola fuente de verdad).
Se importan desde el pipeline Y desde los tests de regresión, para que la propiedad
que valida un test sea EXACTAMENTE la que ejecuta el pipeline.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    path = path or (ROOT / "config" / "release_zoom_bogota_v1.yaml")
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def fwd_target(ev_series: pd.Series, a: int, b: int) -> pd.Series:
    """Target ESTRICTAMENTE FUTURO: y_t = 1 si hay evento en {t+a, ..., t+b}.
    Requiere a >= 1 (el día t NUNCA cuenta). Devuelve NaN donde la ventana futura
    es incompleta (no se puede conocer el target)."""
    if a < 1:
        raise ValueError(f"a debe ser >= 1 (ventana estrictamente futura); recibido a={a}")
    m = None
    for k in range(a, b + 1):
        s = ev_series.shift(-k)
        m = s if m is None else np.maximum(m, s)
    return m  # NaN al final (ventana incompleta) se filtra aguas arriba


def split_with_embargo(g: pd.DataFrame, cfg: dict, name: str) -> pd.DataFrame:
    """Recorta el final de cada split por 'embargo_days' para impedir bleed de la
    ventana de target hacia el split siguiente."""
    import pandas as pd
    emb = pd.Timedelta(days=cfg["splits"]["embargo_days"])
    s = pd.Timestamp(cfg["splits"][name]["start"])
    e = pd.Timestamp(cfg["splits"][name]["end"])
    return g[(g["fecha"] >= s) & (g["fecha"] <= e - emb)]


def thresholds_from_calib(prev_calib: float, cfg: dict):
    """Bandas de alerta derivadas SOLO de calibración (nunca test)."""
    return (round(prev_calib * cfg["thresholds"]["naranja_x"], 4),
            round(prev_calib * cfg["thresholds"]["rojo_x"], 4))
