"""Indicadores mineros descriptivos por título y por unidad territorial (Fase 4A).

Esta fase produce **indicadores descriptivos de presión minera formal
registrada**. NO calcula riesgo, score, probabilidad de contaminación,
probabilidad de deforestación, minería ilegal, afectación causada por
minería ni ningún índice compuesto — eso queda fuera de alcance
explícitamente.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from ..geo.intersection import IntersectionRecord, unary_union

M2_PER_HA = 10_000.0
TOLERANCIA_AREA_M2_DEFAULT = 1.0
UMBRAL_FRAGMENTO_HA = 0.01

FUENTE_CATASTRO_LABEL = "ANM WFS Titulo_Vigente (geo.anm.gov.co)"
FECHA_ACTUALIZACION_FUENTE_CATASTRO = "2023-03-22"  # declarada por el geoservicio; NO es la fecha del análisis


# ---------------------------------------------------------------------------
# H. Agregación de ANM Anotaciones RMN por codigo_expediente
# ---------------------------------------------------------------------------


def aggregate_anm_annotations(df_anotaciones: pd.DataFrame) -> pd.DataFrame:
    """Agrega las anotaciones ANM a nivel de `codigo_expediente` ANTES de
    unir con el catastro, para no duplicar área por la relación 1-a-muchos
    (varias anotaciones por expediente)."""
    df = df_anotaciones.copy()
    df["fecha_anotacion_dt"] = pd.to_datetime(df["fecha_anotacion"], errors="coerce")

    ultimo_anio_disponible = df["fecha_anotacion_dt"].dt.year.max()

    grouped = df.groupby("codigo_expediente")
    agg = grouped.agg(
        n_anotaciones=("codigo_expediente", "size"),
        n_tipos_anotacion=("tipo_de_anotacion", "nunique"),
        fecha_primera_anotacion=("fecha_anotacion_dt", "min"),
        fecha_ultima_anotacion=("fecha_anotacion_dt", "max"),
    ).reset_index()

    n_ultimo_anio = (
        df[df["fecha_anotacion_dt"].dt.year == ultimo_anio_disponible]
        .groupby("codigo_expediente")
        .size()
    )
    agg["n_anotaciones_ultimo_anio_disponible"] = (
        agg["codigo_expediente"].map(n_ultimo_anio).fillna(0).astype(int)
    )

    tipos_distintos = grouped["tipo_de_anotacion"].apply(lambda s: sorted(set(s.dropna())))
    agg["tipos_anotacion_distintos"] = agg["codigo_expediente"].map(tipos_distintos).apply(
        lambda lst: "; ".join(lst) if isinstance(lst, list) else ""
    )

    modalidades_distintas = grouped["modalidad"].apply(lambda s: sorted(set(s.dropna())))
    agg["modalidades_anotaciones_distintas"] = agg["codigo_expediente"].map(modalidades_distintas).apply(
        lambda lst: "; ".join(lst) if isinstance(lst, list) else ""
    )

    agg["tiene_anotaciones"] = True
    agg["fecha_primera_anotacion"] = agg["fecha_primera_anotacion"].dt.strftime("%Y-%m-%d")
    agg["fecha_ultima_anotacion"] = agg["fecha_ultima_anotacion"].dt.strftime("%Y-%m-%d")

    return agg[
        [
            "codigo_expediente",
            "n_anotaciones",
            "n_tipos_anotacion",
            "fecha_primera_anotacion",
            "fecha_ultima_anotacion",
            "n_anotaciones_ultimo_anio_disponible",
            "tiene_anotaciones",
            "tipos_anotacion_distintos",
            "modalidades_anotaciones_distintas",
        ]
    ]


def validate_annotation_correspondence(df_catastro: pd.DataFrame, df_anotaciones_agg: pd.DataFrame) -> dict:
    """Valida la correspondencia por `codigo_expediente` entre catastro y
    anotaciones agregadas, ANTES de unirlas."""
    set_catastro = set(df_catastro["codigo_expediente"])
    set_anotaciones = set(df_anotaciones_agg["codigo_expediente"])

    con_anotaciones = set_catastro & set_anotaciones
    sin_anotaciones = set_catastro - set_anotaciones
    anotaciones_sin_catastro = sorted(set_anotaciones - set_catastro)

    return {
        "titulos_catastro_total": len(set_catastro),
        "titulos_con_anotaciones": len(con_anotaciones),
        "titulos_sin_anotaciones": len(sin_anotaciones),
        "expedientes_anotaciones_no_en_catastro": len(anotaciones_sin_catastro),
        "expedientes_anotaciones_no_en_catastro_muestra": anotaciones_sin_catastro[:20],
        "pct_correspondencia": round(len(con_anotaciones) / len(set_catastro) * 100, 2) if set_catastro else 0.0,
    }


# ---------------------------------------------------------------------------
# F/G. Tabla título–unidad territorial y control de conservación de área
# ---------------------------------------------------------------------------


def build_title_territorial_table(
    records: list[IntersectionRecord],
    title_areas_m2: dict[str, float],
    df_catastro_full: pd.DataFrame,
    df_universo_analitico: pd.DataFrame,
    territorial_areas_ha: dict[str, float],
    *,
    fuente_geometria_territorial: str | None = None,
    version_geometria_territorial: str | None = None,
) -> pd.DataFrame:
    """Construye `mineria_titulo_unidad_territorial.csv`: una fila por
    combinación real `codigo_expediente` + `cod_dane_mpio` con área de
    intersección **positiva** (regla E.1: los contactos de solo línea/punto,
    `solo_toca_limite=True`, NO entran en esta tabla; quedan solo en las
    estadísticas de la corrida).

    `fuente_geometria_territorial`/`version_geometria_territorial` son
    opcionales (por defecto `None`, y entonces NO se agregan columnas, para
    no cambiar el esquema de 26 columnas de la Fase 4A original). Se usan en
    la Fase 4A.2 para dejar explícito en cada fila qué base geométrica
    territorial (MGN2025 vs. la capa mixta anterior) produjo la intersección."""
    filas = []
    for rec in records:
        if rec.solo_toca_limite or rec.area_interseccion_m2 <= 0:
            continue
        area_ha = rec.area_interseccion_m2 / M2_PER_HA
        titulo_area_ha = title_areas_m2[rec.title_id] / M2_PER_HA
        unidad_area_ha = territorial_areas_ha[rec.territorial_id]

        filas.append(
            {
                "codigo_expediente": rec.title_id,
                "cod_dane_mpio": rec.territorial_id,
                "area_interseccion_m2": rec.area_interseccion_m2,
                "area_interseccion_ha": area_ha,
                "area_geometria_titulo_ha": titulo_area_ha,
                "pct_area_titulo_en_unidad": (area_ha / titulo_area_ha * 100) if titulo_area_ha > 0 else None,
                "area_unidad_territorial_ha": unidad_area_ha,
                "pct_area_unidad_titulada_por_este_titulo": (area_ha / unidad_area_ha * 100) if unidad_area_ha > 0 else None,
                "es_fragmento_menor_0_01_ha": bool(area_ha < UMBRAL_FRAGMENTO_HA),
            }
        )

    df_rel = pd.DataFrame(filas)
    if df_rel.empty:
        return df_rel

    cols_catastro = [
        "codigo_expediente",
        "area_ha",
        "modalidad_norm",
        "etapa_norm",
        "estado_norm",
        "minerales_norm",
        "instrumento_ambiental",
        "fecha_de_inscripcion",
        "anio_inscripcion",
        "fecha_terminacion",
        "anio_terminacion",
    ]
    df_rel = df_rel.merge(
        df_catastro_full[cols_catastro].rename(columns={"area_ha": "area_reportada_anm_ha"}),
        on="codigo_expediente",
        how="left",
    )

    df_rel["diferencia_area_ha"] = df_rel["area_geometria_titulo_ha"] - df_rel["area_reportada_anm_ha"]
    df_rel["ratio_area_geometria_reportada"] = np.where(
        df_rel["area_reportada_anm_ha"] > 0,
        df_rel["area_geometria_titulo_ha"] / df_rel["area_reportada_anm_ha"],
        np.nan,
    )

    df_rel = df_rel.merge(
        df_universo_analitico[["cod_dane_mpio", "cod_dane_dpto", "nombre_mpio", "nombre_dpto", "tipo_unidad_territorial"]],
        on="cod_dane_mpio",
        how="left",
    )

    df_rel["fuente_catastro"] = FUENTE_CATASTRO_LABEL
    df_rel["fecha_actualizacion_fuente_catastro"] = FECHA_ACTUALIZACION_FUENTE_CATASTRO

    columnas_finales = [
        "codigo_expediente",
        "cod_dane_mpio",
        "cod_dane_dpto",
        "nombre_mpio",
        "nombre_dpto",
        "tipo_unidad_territorial",
        "area_interseccion_m2",
        "area_interseccion_ha",
        "area_geometria_titulo_ha",
        "area_reportada_anm_ha",
        "pct_area_titulo_en_unidad",
        "area_unidad_territorial_ha",
        "pct_area_unidad_titulada_por_este_titulo",
        "es_fragmento_menor_0_01_ha",
        "modalidad_norm",
        "etapa_norm",
        "estado_norm",
        "minerales_norm",
        "instrumento_ambiental",
        "fecha_de_inscripcion",
        "anio_inscripcion",
        "fecha_terminacion",
        "anio_terminacion",
        "diferencia_area_ha",
        "ratio_area_geometria_reportada",
        "fuente_catastro",
        "fecha_actualizacion_fuente_catastro",
    ]

    if fuente_geometria_territorial is not None:
        df_rel["fuente_geometria_territorial"] = fuente_geometria_territorial
        columnas_finales.append("fuente_geometria_territorial")
    if version_geometria_territorial is not None:
        df_rel["version_geometria_territorial"] = version_geometria_territorial
        columnas_finales.append("version_geometria_territorial")

    return df_rel[columnas_finales].reset_index(drop=True)


def build_area_conservation_table(
    df_rel: pd.DataFrame, title_areas_m2: dict[str, float], *, tolerancia_area_m2: float = TOLERANCIA_AREA_M2_DEFAULT
) -> pd.DataFrame:
    """Control de conservación de área por `codigo_expediente` (sección G):
    compara el área propia del título contra la suma de sus intersecciones
    territoriales con área positiva."""
    if df_rel.empty:
        titulos_con_interseccion = set()
    else:
        titulos_con_interseccion = set(df_rel["codigo_expediente"].unique())

    filas = []
    for title_id, area_m2 in title_areas_m2.items():
        area_titulo_ha = area_m2 / M2_PER_HA
        if title_id in titulos_con_interseccion:
            subset = df_rel[df_rel["codigo_expediente"] == title_id]
            suma_ha = subset["area_interseccion_ha"].sum()
            n_unidades = subset["cod_dane_mpio"].nunique()
        else:
            suma_ha = 0.0
            n_unidades = 0

        diferencia_ha = area_titulo_ha - suma_ha
        pct_asignada = (suma_ha / area_titulo_ha * 100) if area_titulo_ha > 0 else None
        tolerancia_ha = tolerancia_area_m2 / M2_PER_HA

        filas.append(
            {
                "codigo_expediente": title_id,
                "area_geometria_titulo_ha": area_titulo_ha,
                "suma_area_intersecciones_ha": suma_ha,
                "diferencia_no_asignada_ha": diferencia_ha,
                "pct_area_asignada": pct_asignada,
                "n_unidades_territoriales": n_unidades,
                "dentro_de_tolerancia": bool(abs(diferencia_ha) <= tolerancia_ha),
                "asignacion_superior_100": bool(pct_asignada is not None and pct_asignada > 100 and abs(diferencia_ha) > tolerancia_ha),
                "sin_interseccion_territorial": n_unidades == 0,
            }
        )

    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# I. Indicadores agregados por unidad territorial
# ---------------------------------------------------------------------------


def _split_minerales(valor: str | float | None) -> list[str]:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return []
    return [m.strip() for m in str(valor).split(",") if m.strip()]


def compute_union_areas_by_territorial(records: list[IntersectionRecord]) -> dict[str, float]:
    """Área (m²) de la UNIÓN geométrica de todas las intersecciones
    título∩unidad dentro de cada unidad territorial (sin doble conteo,
    a diferencia de la simple suma de áreas por título)."""
    grouped: dict[str, list] = defaultdict(list)
    for rec in records:
        if rec.solo_toca_limite or rec.geometria_interseccion is None:
            continue
        grouped[rec.territorial_id].append(rec.geometria_interseccion)

    result = {}
    for tid, geoms in grouped.items():
        union_geom = unary_union(geoms)
        result[tid] = union_geom.area
    return result


def build_territorial_indicators_table(
    df_universo_analitico: pd.DataFrame,
    territorial_areas_ha: dict[str, float],
    df_rel: pd.DataFrame,
    records: list[IntersectionRecord],
    df_catastro_full: pd.DataFrame,
    df_anotaciones_agg: pd.DataFrame,
    df_conservacion: pd.DataFrame,
    *,
    catastro_minerales_originales: pd.Series,
) -> pd.DataFrame:
    """Construye `mineria_por_unidad_territorial.csv`: una fila por cada una
    de las 1.122 unidades del universo analítico, incluidas las que no
    tienen ningún título minero (con valores en cero, no filas ausentes)."""
    union_areas_m2 = compute_union_areas_by_territorial(records)

    # Diccionario codigo_expediente -> minerales originales (sin normalizar,
    # separados por coma), para reconstruir la lista de minerales distintos
    # por unidad territorial sin depender de minerales_norm (que pierde la
    # coma como separador al normalizar texto).
    minerales_por_titulo = {
        cod: _split_minerales(val) for cod, val in zip(df_catastro_full["codigo_expediente"], catastro_minerales_originales)
    }

    catastro_idx = df_catastro_full.set_index("codigo_expediente")
    anotaciones_idx = df_anotaciones_agg.set_index("codigo_expediente") if not df_anotaciones_agg.empty else pd.DataFrame()
    conservacion_idx = df_conservacion.set_index("codigo_expediente")

    filas_por_unidad: dict[str, list[str]] = defaultdict(list)
    fragmentos_por_unidad: dict[str, int] = defaultdict(int)
    if not df_rel.empty:
        for cod_mpio, grupo in df_rel.groupby("cod_dane_mpio"):
            filas_por_unidad[cod_mpio] = sorted(grupo["codigo_expediente"].unique().tolist())
            fragmentos_por_unidad[cod_mpio] = int(grupo["es_fragmento_menor_0_01_ha"].sum())

    filas_salida = []
    for _, unidad in df_universo_analitico.iterrows():
        cod_mpio = unidad["cod_dane_mpio"]
        area_unidad_ha = territorial_areas_ha[cod_mpio]
        titulos_en_unidad = filas_por_unidad.get(cod_mpio, [])
        n_titulos = len(titulos_en_unidad)

        area_suma_ha = 0.0
        if n_titulos and not df_rel.empty:
            area_suma_ha = df_rel[df_rel["cod_dane_mpio"] == cod_mpio]["area_interseccion_ha"].sum()
        area_union_ha = union_areas_m2.get(cod_mpio, 0.0) / M2_PER_HA

        area_unidad_km2 = area_unidad_ha / 100.0

        etapas = catastro_idx.loc[titulos_en_unidad, "etapa_norm"] if n_titulos else pd.Series(dtype=object)
        n_explotacion = int((etapas == "EXPLOTACION").sum()) if n_titulos else 0

        modalidades = catastro_idx.loc[titulos_en_unidad, "modalidad_norm"] if n_titulos else pd.Series(dtype=object)
        modalidades_distintas = sorted(set(modalidades.dropna())) if n_titulos else []

        minerales_distintos: set[str] = set()
        for cod in titulos_en_unidad:
            minerales_distintos.update(minerales_por_titulo.get(cod, []))

        instrumento = catastro_idx.loc[titulos_en_unidad, "instrumento_ambiental"] if n_titulos else pd.Series(dtype=object)
        n_con_instrumento = int((instrumento == "Y").sum()) if n_titulos else 0

        if n_titulos and not anotaciones_idx.empty:
            titulos_con_anot = [c for c in titulos_en_unidad if c in anotaciones_idx.index]
            anotaciones_total = int(anotaciones_idx.loc[titulos_con_anot, "n_anotaciones"].sum()) if titulos_con_anot else 0
            expedientes_con_anot = len(titulos_con_anot)
            fecha_ultima = anotaciones_idx.loc[titulos_con_anot, "fecha_ultima_anotacion"].max() if titulos_con_anot else None
        else:
            anotaciones_total = 0
            expedientes_con_anot = 0
            fecha_ultima = None

        n_titulos_area_no_asignada = 0
        if n_titulos:
            n_titulos_area_no_asignada = int((~conservacion_idx.loc[titulos_en_unidad, "dentro_de_tolerancia"]).sum())

        filas_salida.append(
            {
                "cod_dane_mpio": cod_mpio,
                "cod_dane_dpto": unidad["cod_dane_dpto"],
                "nombre_mpio": unidad["nombre_mpio"],
                "nombre_dpto": unidad["nombre_dpto"],
                "tipo_unidad_territorial": unidad["tipo_unidad_territorial"],
                "area_unidad_territorial_ha": area_unidad_ha,
                "n_titulos_mineros": n_titulos,
                "tiene_titulos_mineros": n_titulos > 0,
                "area_titulada_suma_ha": area_suma_ha,
                "area_titulada_union_ha": area_union_ha,
                "pct_area_unidad_titulada_suma": (area_suma_ha / area_unidad_ha * 100) if area_unidad_ha > 0 else None,
                "pct_area_unidad_titulada_union": (area_union_ha / area_unidad_ha * 100) if area_unidad_ha > 0 else None,
                "titulos_por_100_km2": (n_titulos / area_unidad_km2 * 100) if area_unidad_km2 > 0 else None,
                "area_titulada_ha_por_100_km2": (area_suma_ha / area_unidad_km2 * 100) if area_unidad_km2 > 0 else None,
                "n_titulos_explotacion": n_explotacion,
                "pct_titulos_explotacion": (n_explotacion / n_titulos * 100) if n_titulos else None,
                "n_modalidades_distintas": len(modalidades_distintas),
                "modalidades_distintas": "; ".join(modalidades_distintas),
                "n_minerales_distintos": len(minerales_distintos),
                "minerales_distintos": "; ".join(sorted(minerales_distintos)),
                "n_titulos_con_instrumento_ambiental": n_con_instrumento,
                "pct_titulos_con_instrumento_ambiental": (n_con_instrumento / n_titulos * 100) if n_titulos else None,
                "anotaciones_total": anotaciones_total,
                "expedientes_con_anotaciones": expedientes_con_anot,
                "promedio_anotaciones_por_titulo": (anotaciones_total / n_titulos) if n_titulos else None,
                "fecha_ultima_anotacion_unidad": fecha_ultima,
                "n_fragmentos_menores_0_01_ha": fragmentos_por_unidad.get(cod_mpio, 0),
                "n_titulos_con_area_no_asignada": n_titulos_area_no_asignada,
                "fuente_catastro_fecha_actualizacion": FECHA_ACTUALIZACION_FUENTE_CATASTRO,
            }
        )

    return pd.DataFrame(filas_salida)
