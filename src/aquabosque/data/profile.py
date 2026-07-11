"""Perfilamiento genérico de datos crudos para AquaBosque Minero IA (Fase 3A).

Solo lee e inspecciona: no limpia, no transforma ni guarda datos procesados.
Las funciones de este módulo trabajan sobre `pandas.DataFrame` ya cargados en
memoria (a partir de XLSX o JSON crudos) y producen estructuras de perfil
(diccionarios) que luego se renderizan a Markdown.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

# Nombres de columna que sugieren una llave de integración.
KEY_NAME_HINTS = (
    "codigo",
    "código",
    "cod_",
    "id_",
    "_id",
    "expediente",
    "nit",
    "key",
    "clave",
)

# Nombres de columna que sugieren un campo de fecha.
DATE_NAME_HINTS = ("fecha", "date", "_dt", "año", "anio", "year")

# Nombres de columna que sugieren un campo geográfico/territorial.
GEO_NAME_HINTS = (
    "lat",
    "lon",
    "longitud",
    "latitud",
    "geom",
    "geometry",
    "departamento",
    "municipio",
    "coordenad",
    "zona_hidro",
    "subzona",
    "cuenca",
    "corriente",
)


def _name_matches(col: str, hints: tuple[str, ...]) -> bool:
    col_low = col.lower()
    return any(h in col_low for h in hints)


def infer_dtypes(df: pd.DataFrame) -> dict[str, str]:
    return {col: str(dtype) for col, dtype in df.dtypes.items()}


def null_percentages(df: pd.DataFrame) -> dict[str, float]:
    n = len(df)
    if n == 0:
        return {col: 0.0 for col in df.columns}
    return {col: round(df[col].isna().sum() / n * 100, 2) for col in df.columns}


def count_full_row_duplicates(df: pd.DataFrame) -> int:
    return int(df.duplicated().sum())


def detect_date_fields(df: pd.DataFrame, sample_size: int = 200) -> list[str]:
    detected = []
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            detected.append(col)
            continue
        if _name_matches(col, DATE_NAME_HINTS):
            detected.append(col)
            continue
        # Los códigos numéricos (int64/float64) sin pista de nombre no se
        # muestrean como fecha: pd.to_datetime interpreta números pequeños
        # como años o timestamps, dando falsos positivos (p. ej. un código
        # de subzona hidrográfica como 2618 no es una fecha).
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        sample = df[col].dropna().astype(str).head(sample_size)
        if len(sample) == 0:
            continue
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        if parsed.notna().mean() > 0.8:
            detected.append(col)
    return detected


def detect_geo_fields(df: pd.DataFrame) -> list[str]:
    return [col for col in df.columns if _name_matches(col, GEO_NAME_HINTS)]


def detect_candidate_keys(df: pd.DataFrame) -> list[dict[str, Any]]:
    n = len(df)
    candidates = []
    for col in df.columns:
        non_null = df[col].dropna()
        uniqueness = (non_null.nunique() / len(non_null)) if len(non_null) else 0.0
        name_hint = _name_matches(col, KEY_NAME_HINTS)
        if uniqueness >= 0.95 or (name_hint and uniqueness >= 0.5):
            razon = []
            if uniqueness >= 0.95:
                razon.append(f"unicidad {uniqueness * 100:.1f}%")
            if name_hint:
                razon.append("nombre sugiere llave/código")
            candidates.append(
                {
                    "columna": col,
                    "unicidad_pct": round(uniqueness * 100, 2),
                    "razon": ", ".join(razon),
                }
            )
    candidates.sort(key=lambda c: c["unicidad_pct"], reverse=True)
    return candidates


def generate_quality_observations(df: pd.DataFrame, null_pct: dict[str, float]) -> list[str]:
    observations: list[str] = []
    n = len(df)

    fully_null = [c for c, p in null_pct.items() if p == 100.0]
    if fully_null:
        observations.append(f"Columnas completamente vacías (100% nulos): {', '.join(fully_null)}")

    high_null = [c for c, p in null_pct.items() if 0 < p < 100 and p >= 50]
    if high_null:
        detalle = ", ".join(f"{c} ({null_pct[c]}%)" for c in high_null)
        observations.append(f"Columnas con alto porcentaje de nulos (>=50%): {detalle}")

    constant_cols = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    if constant_cols:
        observations.append(f"Columnas constantes o vacías de valores útiles: {', '.join(constant_cols)}")

    dup = count_full_row_duplicates(df)
    if dup > 0:
        observations.append(f"{dup} filas completamente duplicadas ({dup / n * 100:.2f}% del total)" if n else f"{dup} filas duplicadas")

    code_like_float = [
        c
        for c in df.columns
        if _name_matches(c, ("codigo", "código", "cod_")) and pd.api.types.is_float_dtype(df[c])
    ]
    if code_like_float:
        observations.append(
            "Columnas que parecen código (texto con ceros a la izquierda) pero se "
            f"infirieron como numéricas, con riesgo de perder ceros iniciales: {', '.join(code_like_float)}"
        )

    if not observations:
        observations.append("Sin observaciones de calidad relevantes detectadas por las validaciones genéricas.")

    return observations


def profile_dataframe(
    df: pd.DataFrame,
    *,
    fuente: str,
    ruta: str,
    extra_key_columns: list[str] | None = None,
) -> dict[str, Any]:
    """Perfil genérico de un DataFrame: estructura, tipos, nulos, duplicados,
    muestra de filas, candidatos a llave, campos de fecha/geográficos y
    observaciones de calidad automáticas.
    """
    null_pct = null_percentages(df)
    profile = {
        "fuente": fuente,
        "ruta": ruta,
        "n_filas": len(df),
        "n_columnas": len(df.columns),
        "columnas": list(df.columns),
        "tipos_inferidos": infer_dtypes(df),
        "pct_nulos": null_pct,
        "n_duplicados": count_full_row_duplicates(df),
        "primeras_filas": df.head(5),
        "ultimas_filas": df.tail(5),
        "candidatos_llave": detect_candidate_keys(df),
        "campos_fecha": detect_date_fields(df),
        "campos_geograficos": detect_geo_fields(df),
        "observaciones_calidad": generate_quality_observations(df, null_pct),
    }
    if extra_key_columns:
        existentes = [c for c in extra_key_columns if c in df.columns]
        if existentes:
            profile["observaciones_calidad"].append(
                f"Columnas señaladas manualmente como candidatas a llave de integración: {', '.join(existentes)}"
            )
    return profile


def _truncate_for_display(value: Any, max_len: int = 60) -> Any:
    """Recorta valores de texto largos SOLO para la vista del reporte; no
    modifica los datos originales en memoria ni en disco."""
    if isinstance(value, str) and len(value) > max_len:
        return value[: max_len - 3] + "..."
    return value


def _df_to_md_block(df: pd.DataFrame, max_len: int = 60) -> str:
    if df.empty:
        return "_(sin filas)_"
    display_df = df.map(lambda v: _truncate_for_display(v, max_len))
    return "```\n" + display_df.to_string(index=False) + "\n```"


def render_profile_markdown(profile: dict[str, Any], extra_sections: str = "") -> str:
    lines: list[str] = []
    lines.append(f"# Perfil: {profile['fuente']}")
    lines.append("")
    lines.append(f"- **Ruta:** `{profile['ruta']}`")
    lines.append(f"- **Filas:** {profile['n_filas']}")
    lines.append(f"- **Columnas:** {profile['n_columnas']}")
    lines.append(f"- **Filas duplicadas (completas):** {profile['n_duplicados']}")
    lines.append("")

    lines.append("## Columnas y tipos inferidos")
    lines.append("")
    lines.append("| Columna | Tipo inferido | % nulos |")
    lines.append("|---|---|---|")
    for col in profile["columnas"]:
        tipo = profile["tipos_inferidos"].get(col, "?")
        pct = profile["pct_nulos"].get(col, 0.0)
        lines.append(f"| `{col}` | {tipo} | {pct}% |")
    lines.append("")

    lines.append("## Primeras 5 filas")
    lines.append("")
    lines.append(_df_to_md_block(profile["primeras_filas"]))
    lines.append("")

    lines.append("## Últimas 5 filas")
    lines.append("")
    lines.append(_df_to_md_block(profile["ultimas_filas"]))
    lines.append("")

    lines.append("## Campos candidatos a llave de integración")
    lines.append("")
    if profile["candidatos_llave"]:
        lines.append("| Columna | Unicidad | Razón |")
        lines.append("|---|---|---|")
        for c in profile["candidatos_llave"]:
            lines.append(f"| `{c['columna']}` | {c['unicidad_pct']}% | {c['razon']} |")
    else:
        lines.append("_No se detectaron candidatos claros con las heurísticas genéricas._")
    lines.append("")

    lines.append("## Campos de fecha detectados")
    lines.append("")
    lines.append(", ".join(f"`{c}`" for c in profile["campos_fecha"]) or "_Ninguno detectado._")
    lines.append("")

    lines.append("## Campos geográficos detectados")
    lines.append("")
    lines.append(", ".join(f"`{c}`" for c in profile["campos_geograficos"]) or "_Ninguno detectado._")
    lines.append("")

    lines.append("## Observaciones de calidad")
    lines.append("")
    for obs in profile["observaciones_calidad"]:
        lines.append(f"- {obs}")
    lines.append("")

    if extra_sections:
        lines.append(extra_sections)
        lines.append("")

    return "\n".join(lines)


def value_counts_markdown(series: pd.Series, *, top_n: int | None = None, title: str = "") -> str:
    counts = series.value_counts(dropna=False)
    if top_n is not None:
        counts = counts.head(top_n)
    lines = []
    if title:
        lines.append(f"### {title}")
        lines.append("")
    lines.append("| Valor | Conteo |")
    lines.append("|---|---|")
    for value, n in counts.items():
        lines.append(f"| {value} | {n} |")
    return "\n".join(lines)


def describe_geometries(geometries: list[dict | None]) -> dict[str, Any]:
    """Perfila una lista de geometrías GeoJSON (una por feature, en paralelo
    a un DataFrame de propiedades, sin imprimir la geometría completa):
    nulas, distribución de tipos y validez geométrica.

    La validez se calcula con shapely si está disponible; si no lo está, el
    perfil lo deja explícito en vez de fingir que se validó.
    """
    n_total = len(geometries)
    n_nulas = sum(1 for g in geometries if not g)

    tipos: dict[str, int] = {}
    for g in geometries:
        if g:
            tipos[g.get("type", "desconocido")] = tipos.get(g.get("type", "desconocido"), 0) + 1

    resultado: dict[str, Any] = {
        "n_total": n_total,
        "n_geometrias_nulas": n_nulas,
        "tipos_geometria": tipos,
    }

    try:
        from shapely.geometry import shape
    except ImportError:
        resultado["n_geometrias_invalidas"] = None
        resultado["validez_verificada_con"] = None
        return resultado

    n_invalidas = 0
    for g in geometries:
        if not g:
            continue
        try:
            if not shape(g).is_valid:
                n_invalidas += 1
        except Exception:  # noqa: BLE001 - geometría corrupta también cuenta como inválida
            n_invalidas += 1

    resultado["n_geometrias_invalidas"] = n_invalidas
    resultado["validez_verificada_con"] = "shapely"
    return resultado
