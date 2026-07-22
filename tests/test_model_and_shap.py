"""Modelo XGBoost, honestidad de métricas, SHAP y artefactos del dashboard."""
import numpy as np
from conftest import FEATURES, NIVELES


def test_bundle_bien_formado(modelo_bundle):
    assert set(modelo_bundle) >= {"modelo", "features", "niveles"}
    assert modelo_bundle["features"] == FEATURES
    assert modelo_bundle["niveles"] == NIVELES


def test_modelo_predice_clases_validas(modelo_bundle, etiqueta):
    X = etiqueta[FEATURES].fillna(0).astype(float)
    pred = modelo_bundle["modelo"].predict(X)
    assert len(pred) == len(etiqueta)
    assert set(np.unique(pred)).issubset(set(range(len(NIVELES))))


def test_modelo_supera_linea_base(metricas):
    """Honestidad: la accuracy alta es por construcción, pero DEBE superar a la
    línea base trivial (predecir la clase mayoritaria); si no, no generaliza."""
    assert metricas["accuracy"] > metricas["baseline_clase_mayoritaria"]
    assert metricas["f1_macro"] > 0.5  # las 4 clases se distinguen razonablemente


def test_nota_honestidad_presente(metricas):
    # el marco de honestidad debe viajar con las métricas (no venderse exactitud)
    assert "nota_honestidad" in metricas
    assert "EXPLICABILIDAD" in metricas["nota_honestidad"].upper()


def test_shap_importancia_completa(root):
    import pandas as pd
    p = root / "models" / "shap" / "importancia_global.csv"
    assert p.exists()
    imp = pd.read_csv(p)
    assert set(imp["feature"]) == set(FEATURES)      # todas las variables evaluadas
    assert (imp["importancia_shap"] >= 0).all()      # |SHAP| nunca negativo
    # los índices compuestos (incl. fuego satelital) deben dominar la explicación (núcleo)
    indices = {"idx_minero", "idx_deforestacion", "idx_fuego", "idx_hidrico", "idx_sensibilidad"}
    top5 = set(imp.nlargest(5, "importancia_shap")["feature"])
    assert len(indices & top5) >= 3


def test_predicciones_para_dashboard(root):
    import pandas as pd
    p = root / "outputs" / "tables" / "predicciones.csv"
    assert p.exists()
    pr = pd.read_csv(p)
    assert len(pr) == 1122
    assert pr["confianza"].between(0, 1).all()
    for c in ["cod_mpio", "municipio", "riesgo_nivel", "riesgo_pred", "lat", "lon"]:
        assert c in pr.columns
