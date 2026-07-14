"""Integridad del dataset maestro municipal etiquetado."""
from conftest import NIVELES, FEATURES


def test_una_fila_por_municipio(etiqueta):
    # DIVIPOLA: 1.122 municipios; sin duplicados de código
    assert len(etiqueta) == 1122
    assert etiqueta["cod_mpio"].is_unique
    assert etiqueta["cod_mpio"].notna().all()


def test_columnas_requeridas_presentes(etiqueta):
    requeridas = set(FEATURES) | {
        "cod_mpio", "municipio", "departamento", "lat", "lon",
        "idx_minero", "idx_deforestacion", "idx_hidrico", "idx_sensibilidad",
        "riesgo_score", "riesgo_nivel", "hidrico_sin_dato"}
    faltan = requeridas - set(etiqueta.columns)
    assert not faltan, f"Faltan columnas: {faltan}"


def test_indices_en_rango_0_1(etiqueta):
    for c in ["idx_minero", "idx_deforestacion", "idx_hidrico", "idx_sensibilidad", "riesgo_score"]:
        assert etiqueta[c].min() >= 0.0, f"{c} tiene valores < 0"
        assert etiqueta[c].max() <= 1.0, f"{c} tiene valores > 1"


def test_nivel_riesgo_es_valido(etiqueta):
    assert set(etiqueta["riesgo_nivel"].unique()).issubset(set(NIVELES))
    # las 4 clases deben existir (la clasificación por cuantil las puebla todas)
    assert set(NIVELES) == set(etiqueta["riesgo_nivel"].unique())


def test_coordenadas_dentro_de_colombia(etiqueta):
    # Colombia continental + insular, con holgura
    assert etiqueta["lat"].between(-4.5, 13.5).all()
    assert etiqueta["lon"].between(-82.0, -66.0).all()


def test_sin_señal_hidrica_marcada(etiqueta):
    # Regla documentada: sin estación → idx_hidrico = 0 y bandera hidrico_sin_dato = 1
    sin_dato = etiqueta[etiqueta["hidrico_sin_dato"] == 1]
    assert (sin_dato["idx_hidrico"] == 0).all()
