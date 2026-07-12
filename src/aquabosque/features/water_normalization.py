"""Normalización especializada de nombres de parámetros hídricos
(Fase 4B.2), separada de `aquabosque.data.clean.normalize_text`.

La normalización genérica de texto (Fase 3B) usa el filtro `[^A-Z0-9 ]` para
eliminar signos de puntuación. Ese filtro trata los prefijos de letra griega
de isómero (α/β/γ/ɣ/δ) como "signos no alfanuméricos" y los elimina, porque
no son letras A-Z: el resultado es que `α-ENDOSULFAN` y `β-ENDOSULFAN` (dos
sustancias distintas, con distinto número CAS) terminan normalizados al
mismo texto. Esta función corrige eso traduciendo cada letra griega a su
nombre en español ANTES de aplicar la limpieza genérica, para que el
distintivo de isómero sobreviva como texto ASCII.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from ..data.clean import normalize_text

VERSION_NORMALIZACION_PARAMETROS = "water_parameter_normalization_v2"

# Letra griega (mayúscula y minúscula, incluida la variante "ɣ" observada en
# la fuente para gamma) -> nombre en español, en mayúsculas, para que
# sobreviva al filtro [^A-Z0-9 ] de normalize_text.
_GREEK_ISOMER_MAP: dict[str, str] = {
    "α": "ALFA", "Α": "ALFA",
    "β": "BETA", "Β": "BETA",
    "γ": "GAMMA", "Γ": "GAMMA",
    "ɣ": "GAMMA",
    "δ": "DELTA", "Δ": "DELTA",
}

# Variantes ya escritas en letras latinas que deben unificarse a la misma
# forma canónica en español (alpha/alfa son la misma partícula).
_SPELLED_ISOMER_RE = re.compile(r"\bALPHA\b")

# Variante de deletreo observada en la fuente para delta-HCH
# ("HEXACLOROCICLOHEXA", sin el sufijo "NO") frente a la forma usada por los
# otros tres isómeros ("HEXACLOROCICLOHEXANO"). Es la MISMA sustancia base;
# unificar el nombre base para que los 4 isómeros de HCH sean comparables
# entre sí y solo se diferencien por el prefijo de isómero (nunca se
# corrigen otras variantes de deletreo sin documentarlo aquí explícitamente).
_HEXACLOROCICLOHEXA_RE = re.compile(r"\bHEXACLOROCICLOHEXA\b")


def _preservar_isomeros(text: str) -> str:
    for griego, latino in _GREEK_ISOMER_MAP.items():
        if griego in text:
            text = text.replace(griego, f" {latino} ")
    text = _SPELLED_ISOMER_RE.sub("ALFA", text.upper())
    text = _HEXACLOROCICLOHEXA_RE.sub("HEXACLOROCICLOHEXANO", text)
    return text


def normalize_water_parameter_name(value: Any) -> str | None:
    """Normalización especializada para `propiedad_observada` de calidad
    hídrica: preserva de forma determinística isómeros (α/alfa/alpha,
    β/beta, γ/ɣ/gamma, δ/delta), números de isómero, prefijos químicos
    (p,p'-, trans-), estado (total/disuelto/potencialmente biodisponible) y
    método analítico cuando forman parte del nombre — todos ellos ya
    sobreviven la normalización genérica porque son texto ASCII; el único
    caso que la normalización genérica rompía era el de los prefijos de
    letra griega, que es lo único que esta función corrige explícitamente.
    Nunca fusiona compuestos distintos entre sí (p. ej. DDD/DDE/DDT) ni crea
    una categoría genérica "HCH" o "endosulfan" que colapse los isómeros."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value)
    text = _preservar_isomeros(text)
    return normalize_text(text)


def build_normalization_comparison(
    df_assigned: pd.DataFrame, propiedad_norm_v1_col: str = "propiedad_observada_norm"
) -> pd.DataFrame:
    """Sección C: tabla de correspondencia antes (Fase 4B, `propiedad_norm_v1_col`)
    vs. después (Fase 4B.2, `normalize_water_parameter_name`), a nivel de
    combinación propiedad_original + unidad_original observada realmente."""
    combos = (
        df_assigned.groupby(["propiedad_observada", propiedad_norm_v1_col, "unidad_del_resultado", "unidad_norm"])
        .size()
        .reset_index(name="n_observaciones")
    )
    combos["propiedad_norm_corregida"] = combos["propiedad_observada"].map(normalize_water_parameter_name)

    conteo_v1 = combos.groupby(propiedad_norm_v1_col)["propiedad_observada"].nunique()
    conteo_v2 = combos.groupby("propiedad_norm_corregida")["propiedad_observada"].nunique()

    marcadores_especie = ("ALFA", "BETA", "GAMMA", "DELTA", "P P", "TRANS", "ISOMERO")

    filas = []
    for _, row in combos.iterrows():
        orig = row["propiedad_observada"]
        norm_v1 = row[propiedad_norm_v1_col]
        norm_v2 = row["propiedad_norm_corregida"]

        cambio = norm_v1 != norm_v2
        estaba_fusionado_v1 = conteo_v1.get(norm_v1, 1) > 1
        sigue_fusionado_v2 = conteo_v2.get(norm_v2, 1) > 1
        separacion_isomero = cambio and estaba_fusionado_v1 and not sigue_fusionado_v2

        if not cambio:
            razon = "sin cambio: la normalización genérica ya distinguía correctamente este nombre."
        elif separacion_isomero:
            razon = (
                f"separación de isómero: '{orig}' dejó de fusionarse bajo '{norm_v1}' junto con otros nombres "
                f"originales distintos; ahora normaliza a '{norm_v2}', exclusivo de este isómero/especie."
            )
        elif estaba_fusionado_v1 and sigue_fusionado_v2:
            razon = f"el nombre normalizado cambió de texto ('{norm_v1}' -> '{norm_v2}') pero el grupo resultante sigue teniendo más de un nombre original asociado."
        else:
            razon = f"el nombre normalizado cambió de texto ('{norm_v1}' -> '{norm_v2}') sin relación con fusión de isómeros."

        contiene_marcador_especie = any(m in orig.upper() for m in marcadores_especie)
        requiere_revision = bool(sigue_fusionado_v2 and contiene_marcador_especie)
        if requiere_revision:
            razon += " ADVERTENCIA: aun después de la corrección, este nombre contiene un marcador de isómero/especie y sigue agrupado con otro nombre distinto — requiere revisión técnica manual."

        filas.append(
            {
                "propiedad_observada_original": orig,
                "propiedad_norm_fase4b": norm_v1,
                "propiedad_norm_corregida": norm_v2,
                "unidad_norm": row["unidad_norm"],
                "n_observaciones": row["n_observaciones"],
                "cambio_normalizacion": bool(cambio),
                "razon_cambio": razon,
                "separacion_isomero": bool(separacion_isomero),
                "requiere_revision_tecnica": requiere_revision,
            }
        )
    return pd.DataFrame(filas).sort_values(["cambio_normalizacion", "propiedad_observada_original"], ascending=[False, True]).reset_index(drop=True)
