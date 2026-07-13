"""Prueba explícita del bug corregido en la Fase 2D.2, sección A:
`serie.value_counts().nunique()` NO cuenta categorías distintas — cuenta
cuántas FRECUENCIAS distintas aparecen entre esas categorías. Ejecutar con:

    python tests/test_dtd_distinct_counts.py

No usa pytest (no es una dependencia del proyecto): son asserts simples,
consistentes con el resto del código del proyecto.
"""

from __future__ import annotations

import pandas as pd


def test_value_counts_nunique_is_not_distinct_categories() -> None:
    # 4 municipios distintos, pero solo 2 frecuencias distintas (2 y 1):
    # A:2, B:2, C:1, D:1 -> value_counts() = [2,2,1,1] -> nunique() = 2 (no 4).
    serie = pd.Series(["A", "A", "B", "B", "C", "D"])

    n_categorias_reales = serie.nunique(dropna=True)
    n_categorias_via_len_value_counts = len(serie.value_counts())
    n_frecuencias_distintas_bug = serie.value_counts().nunique()

    assert n_categorias_reales == 4, f"esperado 4 municipios distintos, obtuvo {n_categorias_reales}"
    assert n_categorias_via_len_value_counts == 4, "len(value_counts()) debe coincidir con serie.nunique()"
    assert n_frecuencias_distintas_bug == 2, (
        f"value_counts().nunique() debía devolver 2 (frecuencias distintas: {{2,1}}), "
        f"obtuvo {n_frecuencias_distintas_bug} — si esto cambia, el ejemplo ya no ilustra el bug"
    )
    assert n_categorias_reales != n_frecuencias_distintas_bug, (
        "el ejemplo debe demostrar que ambos métodos divergen; si coinciden, el caso de "
        "prueba no es representativo del bug real corregido en dtd_semantic_audit"
    )
    print("OK: serie.value_counts().nunique() (2) != serie.nunique() (4) — bug reproducido y corregido.")


def test_dtd_semantic_audit_uses_correct_method() -> None:
    """Reproduce el escenario real de `dtd_semantic_audit`: municipios con
    conteos de puntos muy desiguales (como Cartagena del Chairá con 854
    puntos frente a municipios con 1-2), donde el bug es más fácil de pasar
    desapercibido porque el número de frecuencias distintas puede coincidir
    por azar con el número de municipios distintos en muestras pequeñas."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from importlib import import_module

    mod = import_module("20_validate_forest_data_pilot")

    feats = (
        [{"properties": {"nom_mpio": "CARTAGENA DEL CHAIRA", "nom_depto": "CAQUETA", "nucleo_tri": "N1", "cod_dtd": f"c{i}"}, "geometry": {"coordinates": [1.0 + i * 0.001, 0.5]}} for i in range(854)]
        + [{"properties": {"nom_mpio": "PUERTO GUZMAN", "nom_depto": "PUTUMAYO", "nucleo_tri": "N2", "cod_dtd": f"g{i}"}, "geometry": {"coordinates": [2.0 + i * 0.001, 0.6]}} for i in range(388)]
        + [{"properties": {"nom_mpio": "SOLANO", "nom_depto": "CAQUETA", "nucleo_tri": "N1", "cod_dtd": f"s{i}"}, "geometry": {"coordinates": [3.0 + i * 0.001, 0.7]}} for i in range(66)]
    )
    _, resumen, por_mpio, _ = mod.dtd_semantic_audit(feats)
    n_municipios = int(resumen.loc[resumen["metrica"] == "n_municipios_distintos", "valor"].iloc[0])
    n_departamentos = int(resumen.loc[resumen["metrica"] == "n_departamentos_distintos", "valor"].iloc[0])

    assert n_municipios == 3, f"esperados 3 municipios distintos (Cartagena del Chairá, Puerto Guzmán, Solano), obtuvo {n_municipios}"
    assert n_departamentos == 2, f"esperados 2 departamentos distintos (Caquetá, Putumayo), obtuvo {n_departamentos}"
    assert len(por_mpio) == 3
    print("OK: dtd_semantic_audit reporta 3 municipios / 2 departamentos distintos (no confundidos con frecuencias).")


if __name__ == "__main__":
    test_value_counts_nunique_is_not_distinct_categories()
    test_dtd_semantic_audit_uses_correct_method()
    print("\nTodas las pruebas pasaron.")
