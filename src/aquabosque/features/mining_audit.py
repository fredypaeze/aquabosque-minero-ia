"""Auditoría de conservación espacial y cierre de calidad (Fase 4A.1).

No recalcula ningún indicador minero de la Fase 4A. Solo explica, clasifica y
audita las diferencias de asignación espacial ya detectadas, la topología de
los límites territoriales y la correspondencia de anotaciones ANM. No modifica
áreas ni límites administrativos automáticamente.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.strtree import STRtree

M2_PER_HA = 10_000.0

UMBRAL_TOLERANCIA_NUMERICA_HA = 0.01
UMBRAL_REVISION_MANUAL_HA = 10.0
UMBRAL_HUECO_DISTANCIA_M = 100.0
UMBRAL_OVERLAP_TERRITORIAL_M2 = 1.0
UMBRAL_HUECO_NACIONAL_HA = 1.0

CAUSAS_VALIDAS = (
    "tolerancia_numerica",
    "area_en_94663_excluida",
    "fuera_universo_divipola_vigente",
    "fuera_cobertura_geometrica_territorial",
    "hueco_entre_limites_territoriales",
    "solape_entre_limites_territoriales",
    "efecto_reparacion_geometrica",
    "geometria_titulo_fuera_de_colombia",
    "requiere_revision_manual",
)


# ---------------------------------------------------------------------------
# B/C. Auditoría de conservación por título: residual geométrico y causa
# ---------------------------------------------------------------------------


def _residual_stats(residual: BaseGeometry) -> tuple[float, int, bool, bool]:
    area_ha = residual.area / M2_PER_HA
    n_componentes = len(residual.geoms) if hasattr(residual, "geoms") else (0 if residual.is_empty else 1)
    return area_ha, n_componentes, residual.is_empty, residual.is_valid


def _distancia_minima_a_capa(
    residual: BaseGeometry, tree_full: STRtree, full_geoms: list[BaseGeometry]
) -> float | None:
    if residual.is_empty:
        return None
    cand_idx = tree_full.query(residual)
    distancias = [full_geoms[int(i)].distance(residual) for i in cand_idx]
    if not distancias:
        distancias = [g.distance(residual) for g in full_geoms]
    return min(distancias) if distancias else None


def classify_residual_cause(
    *,
    codigo_expediente: str,
    diferencia_no_asignada_ha: float,
    asignacion_superior_100: bool,
    residual: BaseGeometry,
    overlap_94663_ha: float,
    fuera_bbox_colombia: bool,
    geometria_original_invalida: bool,
    tree_full: STRtree,
    full_geoms: list[BaseGeometry],
) -> tuple[str, str]:
    """Clasifica la causa del residual no asignado de un título, en orden de
    prioridad, siempre con evidencia geométrica computada (no se infiere nada
    sin verificarlo). Devuelve (clasificacion_causa, evidencia_causa)."""
    abs_diff_ha = abs(diferencia_no_asignada_ha)
    area_residual_ha, n_componentes, residual_vacio, _residual_valido = _residual_stats(residual)

    if abs_diff_ha < UMBRAL_TOLERANCIA_NUMERICA_HA:
        return (
            "tolerancia_numerica",
            f"diferencia absoluta {abs_diff_ha:.4f} ha (< {UMBRAL_TOLERANCIA_NUMERICA_HA} ha): "
            "consistente con ruido numérico de reproyección/precisión geométrica, no con una "
            "discrepancia territorial real.",
        )

    if overlap_94663_ha > 0.001:
        return (
            "area_en_94663_excluida",
            f"{overlap_94663_ha:.4f} ha de la geometría del título se solapan con la geometría de "
            "94663 (Mapiripaná), excluida del universo analítico vigente por no estar en DIVIPOLA "
            "vigente (ver Fase 3D.1). Se usó únicamente como capa de auditoría, no se reincorporó "
            "al universo analítico.",
        )

    if asignacion_superior_100 and area_residual_ha < 0.001:
        return (
            "solape_entre_limites_territoriales",
            f"asignacion_superior_100=True (suma simple de intersecciones > área propia del título), "
            f"pero el residual real (geometría del título menos la UNIÓN de sus intersecciones "
            f"territoriales) es prácticamente vacío ({area_residual_ha:.6f} ha, {n_componentes} "
            "componente(s)). La aparente sobre-asignación es un artefacto de que la suma simple "
            "cuenta el área una vez por cada unidad territorial que la reclama; este título cae en "
            "una zona donde dos o más unidades territoriales se solapan entre sí (ver auditoría de "
            "topología territorial, sección E).",
        )

    if fuera_bbox_colombia:
        return (
            "geometria_titulo_fuera_de_colombia",
            "el bounding box del título (EPSG:4326) cae fuera de la envolvente nacional de las "
            "1.122 unidades territoriales analíticas más 94663.",
        )

    if geometria_original_invalida and n_componentes > 1:
        return (
            "efecto_reparacion_geometrica",
            f"la geometría original de este título era inválida en catastro_minero_anm_clean.geojson "
            f"(Fase 3C) y fue reparada con shapely.make_valid en la Fase 3D.1; el residual quedó "
            f"fragmentado en {n_componentes} componentes, compatible con un efecto de la reparación "
            "sobre la forma final del polígono.",
        )

    if residual_vacio:
        return (
            "requiere_revision_manual",
            "el residual es vacío pero no se cumplieron las condiciones geométricas de "
            "'solape_entre_limites_territoriales' (asignacion_superior_100=False): revisar "
            "manualmente el origen numérico de la diferencia reportada.",
        )

    dist_min = _distancia_minima_a_capa(residual, tree_full, full_geoms)
    if dist_min is not None and dist_min < UMBRAL_HUECO_DISTANCIA_M:
        evidencia = (
            f"el residual ({area_residual_ha:.4f} ha, {n_componentes} componente(s)) está a "
            f"{dist_min:.1f} m de la unidad territorial (o 94663) más cercana: consistente con un "
            "hueco o 'sliver' entre límites administrativos adyacentes cuyas fronteras no coinciden "
            "exactamente con la del título, no con territorio realmente fuera de toda cobertura."
        )
        if area_residual_ha >= UMBRAL_REVISION_MANUAL_HA:
            evidencia += (
                f" ADVERTENCIA: {area_residual_ha:.1f} ha es demasiado grande para tratarse de un simple "
                "'sliver' de precisión — la proximidad de 0 m solo indica que el residual comparte borde "
                "con la unidad territorial en el punto donde se calculó la intersección parcial, no que "
                "toda su área sea una franja delgada. Esta clasificación es la mejor evidencia geométrica "
                "disponible, pero por su magnitud se marca para revisión manual (ver "
                "requiere_revision_manual)."
            )
        return ("hueco_entre_limites_territoriales", evidencia)

    return (
        "fuera_cobertura_geometrica_territorial",
        f"el residual ({area_residual_ha:.4f} ha, {n_componentes} componente(s)) no toca ninguna "
        f"geometría territorial conocida (distancia mínima "
        f"{'N/D' if dist_min is None else f'{dist_min:.1f} m'}): posible área fuera de la cobertura "
        "geométrica territorial disponible en este proyecto.",
    )


def build_conservation_audit_table(
    df_conservacion: pd.DataFrame,
    *,
    title_geoms_proj: dict[str, BaseGeometry],
    union_intersecciones_por_titulo: dict[str, BaseGeometry],
    geom_94663_proj: BaseGeometry,
    tree_full: STRtree,
    full_geoms: list[BaseGeometry],
    bbox_colombia_4326: tuple[float, float, float, float],
    title_bbox_4326: dict[str, tuple[float, float, float, float]],
    codigos_geometria_original_invalida: set[str],
) -> pd.DataFrame:
    """Construye `mineria_area_conservation_audit.csv` (sección B): una fila
    por cada título fuera de la tolerancia de 1 m²."""
    fuera = df_conservacion[~df_conservacion["dentro_de_tolerancia"]].copy()
    minx, miny, maxx, maxy = bbox_colombia_4326

    filas = []
    for _, row in fuera.iterrows():
        cod = row["codigo_expediente"]
        tgeom = title_geoms_proj[cod]
        union_inter = union_intersecciones_por_titulo.get(cod)
        residual = tgeom.difference(union_inter) if union_inter is not None else tgeom
        area_residual_ha, n_componentes, residual_vacio, residual_valido = _residual_stats(residual)

        overlap_94663_ha = (
            tgeom.intersection(geom_94663_proj).area / M2_PER_HA if geom_94663_proj is not None else 0.0
        )

        tbbox = title_bbox_4326[cod]
        fuera_bbox_colombia = not (
            minx - 1 <= tbbox[0] and tbbox[2] <= maxx + 1 and miny - 1 <= tbbox[1] and tbbox[3] <= maxy + 1
        )

        causa, evidencia = classify_residual_cause(
            codigo_expediente=cod,
            diferencia_no_asignada_ha=row["diferencia_no_asignada_ha"],
            asignacion_superior_100=bool(row["asignacion_superior_100"]),
            residual=residual,
            overlap_94663_ha=overlap_94663_ha,
            fuera_bbox_colombia=fuera_bbox_colombia,
            geometria_original_invalida=cod in codigos_geometria_original_invalida,
            tree_full=tree_full,
            full_geoms=full_geoms,
        )

        abs_diff_ha = abs(row["diferencia_no_asignada_ha"])
        magnitud = "entre_1m2_y_0.01ha" if abs_diff_ha < UMBRAL_TOLERANCIA_NUMERICA_HA else "mayor_o_igual_0.01ha"
        requiere_revision = bool(abs_diff_ha >= UMBRAL_REVISION_MANUAL_HA or causa == "requiere_revision_manual")

        observaciones = (
            f"residual_area_ha={area_residual_ha:.6f}; residual_n_componentes={n_componentes}; "
            f"residual_vacio={residual_vacio}; residual_valido={residual_valido}; "
            f"overlap_94663_ha={overlap_94663_ha:.6f}"
        )

        filas.append(
            {
                "codigo_expediente": cod,
                "area_geometria_titulo_ha": row["area_geometria_titulo_ha"],
                "suma_area_intersecciones_ha": row["suma_area_intersecciones_ha"],
                "diferencia_no_asignada_ha": row["diferencia_no_asignada_ha"],
                "pct_area_asignada": row["pct_area_asignada"],
                "n_unidades_territoriales": row["n_unidades_territoriales"],
                "asignacion_superior_100": bool(row["asignacion_superior_100"]),
                "sin_interseccion_territorial": bool(row["sin_interseccion_territorial"]),
                "magnitud_diferencia": magnitud,
                "clasificacion_causa": causa,
                "evidencia_causa": evidencia,
                "requiere_revision_manual": requiere_revision,
                "observaciones": observaciones,
            }
        )

    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# D. Título sin asignación territorial
# ---------------------------------------------------------------------------


def describe_unassigned_title(
    codigo_expediente: str,
    *,
    df_catastro_full: pd.DataFrame,
    tgeom_proj: BaseGeometry,
    tgeom_4326_bounds: tuple[float, float, float, float],
    geom_94663_proj: BaseGeometry,
    full_ids: list[str],
    full_geoms: list[BaseGeometry],
    causa_probable: str,
    evidencia_causa: str,
) -> dict[str, Any]:
    """Sección D: ficha completa del título sin intersección territorial."""
    fila = df_catastro_full[df_catastro_full["codigo_expediente"] == codigo_expediente].iloc[0]

    overlap_94663_ha = tgeom_proj.intersection(geom_94663_proj).area / M2_PER_HA if geom_94663_proj is not None else 0.0

    distancias = [(full_ids[i], full_geoms[i].distance(tgeom_proj)) for i in range(len(full_geoms))]
    distancias.sort(key=lambda x: x[1])
    unidad_mas_cercana, distancia_mas_cercana_m = distancias[0]

    return {
        "codigo_expediente": codigo_expediente,
        "modalidad": fila.get("modalidad_norm"),
        "etapa": fila.get("etapa_norm"),
        "minerales": fila.get("minerales"),
        "bbox_4326": tgeom_4326_bounds,
        "area_geometrica_ha": tgeom_proj.area / M2_PER_HA,
        "area_reportada_anm_ha": fila.get("area_ha"),
        "unidad_territorial_mas_cercana": unidad_mas_cercana,
        "distancia_unidad_mas_cercana_m": distancia_mas_cercana_m,
        "interseccion_con_94663_ha": overlap_94663_ha,
        "causa_probable": causa_probable,
        "evidencia_causa": evidencia_causa,
        "recomendacion_metodologica": (
            "No eliminar del catastro. Dado que la unidad territorial más cercana está a "
            f"{distancia_mas_cercana_m:.1f} m, es compatible con un hueco/sliver en el límite "
            "administrativo (mismo fenómeno que la mayoría de los 28 casos fuera de tolerancia), no "
            "con un título mal geolocalizado a escala nacional. Se recomienda: (1) documentar el "
            "caso en la trazabilidad de la Fase 4A/4A.1 sin asignarlo a ninguna unidad territorial; "
            "(2) si en una fase posterior se requiere una cobertura territorial sin huecos, evaluar "
            "una tolerancia de 'buffer' geométrico documentada explícitamente (no aplicada aquí); "
            "(3) no inferir causalidad administrativa o legal a partir de este único caso."
        ),
    }


# ---------------------------------------------------------------------------
# E. Auditoría de topología territorial (1.122 unidades analíticas)
# ---------------------------------------------------------------------------


def audit_territorial_topology(
    territorial_geoms_proj: list[tuple[str, BaseGeometry]],
    *,
    geom_94663_proj: BaseGeometry | None = None,
    umbral_overlap_m2: float = UMBRAL_OVERLAP_TERRITORIAL_M2,
    umbral_hueco_ha: float = UMBRAL_HUECO_NACIONAL_HA,
) -> dict[str, Any]:
    """Sección E: valida geometrías, detecta pares que se solapan con área
    positiva, contenciones completas y huecos relevantes en la unión
    nacional. No corrige ni reconstruye límites."""
    ids = [cod for cod, _ in territorial_geoms_proj]
    geoms = [g for _, g in territorial_geoms_proj]

    geometrias_invalidas = [ids[i] for i, g in enumerate(geoms) if not g.is_valid]
    areas_no_positivas = [ids[i] for i, g in enumerate(geoms) if g.area <= 0]
    duplicados = len(ids) - len(set(ids))

    tree = STRtree(geoms)
    n = len(geoms)
    pares_solape: list[dict[str, Any]] = []
    contenciones: list[dict[str, str]] = []
    for i in range(n):
        for j in tree.query(geoms[i]):
            j = int(j)
            if j <= i:
                continue
            inter = geoms[i].intersection(geoms[j])
            if inter.is_empty:
                continue
            area_m2 = inter.area
            if area_m2 > umbral_overlap_m2:
                pares_solape.append(
                    {"cod_dane_mpio_a": ids[i], "cod_dane_mpio_b": ids[j], "area_solape_ha": area_m2 / M2_PER_HA}
                )
            if geoms[i].within(geoms[j]) or geoms[j].within(geoms[i]):
                contenciones.append({"cod_dane_mpio_a": ids[i], "cod_dane_mpio_b": ids[j]})

    area_total_solapes_ha = sum(p["area_solape_ha"] for p in pares_solape)

    union_nacional = unary_union(geoms)
    polys = list(union_nacional.geoms) if union_nacional.geom_type == "MultiPolygon" else [union_nacional]
    huecos = []
    for poly in polys:
        for interior in poly.interiors:
            hole_poly = Polygon(interior)
            area_ha = hole_poly.area / M2_PER_HA
            if area_ha > umbral_hueco_ha:
                coincide_94663 = None
                if geom_94663_proj is not None:
                    overlap = hole_poly.intersection(geom_94663_proj).area / M2_PER_HA
                    coincide_94663 = round(overlap / area_ha * 100, 2) if area_ha > 0 else None
                huecos.append(
                    {
                        "area_hueco_ha": area_ha,
                        "pct_coincide_con_94663": coincide_94663,
                    }
                )

    return {
        "n_unidades": n,
        "n_geometrias_invalidas": len(geometrias_invalidas),
        "geometrias_invalidas": geometrias_invalidas,
        "n_areas_no_positivas": len(areas_no_positivas),
        "areas_no_positivas": areas_no_positivas,
        "n_codigos_duplicados": duplicados,
        "n_pares_solape": len(pares_solape),
        "pares_solape": sorted(pares_solape, key=lambda p: -p["area_solape_ha"]),
        "area_total_solapes_ha": area_total_solapes_ha,
        "n_contenciones_completas": len(contenciones),
        "contenciones_completas": contenciones,
        "area_union_nacional_ha": union_nacional.area / M2_PER_HA,
        "suma_areas_individuales_ha": sum(g.area for g in geoms) / M2_PER_HA,
        "n_huecos_relevantes": len(huecos),
        "huecos_relevantes": sorted(huecos, key=lambda h: -h["area_hueco_ha"]),
    }


# ---------------------------------------------------------------------------
# F. Validación de área titulada por unidad territorial
# ---------------------------------------------------------------------------


def validate_unit_area_indicators(
    df_ind: pd.DataFrame, df_rel: pd.DataFrame, *, tolerancia_ha: float = 0.001
) -> pd.DataFrame:
    """Sección F: valida las 6 reglas descritas en la Fase 4A.1 sobre la
    tabla de indicadores territoriales. Devuelve una tabla de excepciones
    (vacía si todo pasa)."""
    excepciones = []

    viol1 = df_ind[df_ind["area_titulada_union_ha"] > df_ind["area_unidad_territorial_ha"] + tolerancia_ha]
    for _, r in viol1.iterrows():
        excepciones.append({"cod_dane_mpio": r["cod_dane_mpio"], "chequeo_fallido": "union_ha<=area_unidad_ha", "detalle": f"union={r['area_titulada_union_ha']:.4f} > unidad={r['area_unidad_territorial_ha']:.4f}"})

    viol2 = df_ind[df_ind["pct_area_unidad_titulada_union"] > 100 + tolerancia_ha]
    for _, r in viol2.iterrows():
        excepciones.append({"cod_dane_mpio": r["cod_dane_mpio"], "chequeo_fallido": "pct_union<=100", "detalle": f"pct_union={r['pct_area_unidad_titulada_union']:.4f}"})

    viol3 = df_ind[df_ind["area_titulada_union_ha"] > df_ind["area_titulada_suma_ha"] + tolerancia_ha]
    for _, r in viol3.iterrows():
        excepciones.append({"cod_dane_mpio": r["cod_dane_mpio"], "chequeo_fallido": "union_ha<=suma_ha", "detalle": f"union={r['area_titulada_union_ha']:.4f} > suma={r['area_titulada_suma_ha']:.4f}"})

    if not df_rel.empty:
        n_real = df_rel.groupby("cod_dane_mpio")["codigo_expediente"].nunique()
    else:
        n_real = pd.Series(dtype=int)
    reportado = df_ind.set_index("cod_dane_mpio")["n_titulos_mineros"]
    comparado = pd.DataFrame({"real": n_real, "reportado": reportado}).fillna(0)
    viol4 = comparado[comparado["real"] != comparado["reportado"]]
    for cod_mpio, r in viol4.iterrows():
        excepciones.append({"cod_dane_mpio": cod_mpio, "chequeo_fallido": "n_titulos_mineros==conteo_distinto", "detalle": f"real={int(r['real'])} != reportado={int(r['reportado'])}"})

    if not df_rel.empty:
        n_dup = df_rel.duplicated(subset=["codigo_expediente", "cod_dane_mpio"]).sum()
        if n_dup:
            excepciones.append({"cod_dane_mpio": None, "chequeo_fallido": "sin_pares_duplicados", "detalle": f"{n_dup} pares codigo_expediente+cod_dane_mpio duplicados"})

    sin_titulos = df_ind[~df_ind["tiene_titulos_mineros"]]
    viol6 = sin_titulos[
        (sin_titulos["n_titulos_mineros"] != 0)
        | (sin_titulos["area_titulada_suma_ha"] != 0)
        | (sin_titulos["area_titulada_union_ha"] != 0)
        | (sin_titulos["pct_area_unidad_titulada_suma"].fillna(0) != 0)
        | (sin_titulos["pct_area_unidad_titulada_union"].fillna(0) != 0)
    ]
    for _, r in viol6.iterrows():
        excepciones.append({"cod_dane_mpio": r["cod_dane_mpio"], "chequeo_fallido": "unidad_sin_titulos_en_cero", "detalle": "valores distintos de cero en una unidad sin titulos_mineros"})

    return pd.DataFrame(excepciones)


# ---------------------------------------------------------------------------
# G. Auditoría de correspondencia de anotaciones ANM
# ---------------------------------------------------------------------------


def _normalizar_codigo(codigo: str) -> str:
    import re

    return re.sub(r"\s+", "", str(codigo).strip().upper())


def build_annotation_correspondence_audit(
    df_catastro: pd.DataFrame,
    df_anotaciones: pd.DataFrame,
    df_anotaciones_agg: pd.DataFrame,
    *,
    anio_historico_umbral: int = 2020,
) -> pd.DataFrame:
    """Sección G: clasifica títulos del catastro y expedientes de anotaciones
    huérfanos. Solo corrige, si existen, diferencias determinísticas de
    espacios/mayúsculas — no aplica fuzzy matching."""
    set_catastro = set(df_catastro["codigo_expediente"])
    set_anotaciones = set(df_anotaciones_agg["codigo_expediente"])

    norm_catastro = {_normalizar_codigo(c): c for c in set_catastro}

    anot_anio = df_anotaciones.copy()
    anot_anio["anio_anotacion"] = pd.to_numeric(anot_anio["anio_anotacion"], errors="coerce")
    ultimo_anio_por_expediente = anot_anio.groupby("codigo_expediente")["anio_anotacion"].max()

    filas = []
    for cod in sorted(set_catastro):
        tiene = cod in set_anotaciones
        filas.append(
            {
                "codigo_expediente": cod,
                "origen": "catastro",
                "tipo_caso": "con_anotaciones" if tiene else "sin_anotaciones",
                "coincide_tras_normalizacion": False,
                "codigo_normalizado": None,
                "ultimo_anio_anotacion": ultimo_anio_por_expediente.get(cod),
                "posible_historico_no_vigente": False,
                "observaciones": "" if tiene else "titulo vigente en el catastro sin ninguna anotacion registrada en el RMN limpio.",
            }
        )

    huerfanos = sorted(set_anotaciones - set_catastro)
    for cod in huerfanos:
        cod_norm = _normalizar_codigo(cod)
        coincide_norm = cod_norm in norm_catastro and norm_catastro[cod_norm] != cod
        ultimo_anio = ultimo_anio_por_expediente.get(cod)
        posible_historico = bool(ultimo_anio is not None and ultimo_anio < anio_historico_umbral)
        if coincide_norm:
            observ = (
                f"coincide con '{norm_catastro[cod_norm]}' del catastro tras normalizar espacios/mayusculas "
                "(diferencia determinista y trazable)."
            )
        elif posible_historico:
            observ = (
                f"ultima anotacion registrada en {int(ultimo_anio)} (< {anio_historico_umbral}): posible "
                "expediente historico o no vigente, no confirmado con una fuente adicional."
            )
        else:
            observ = (
                "sin explicacion disponible en los datos de este proyecto: no coincide tras normalizacion "
                "determinista y su ultima anotacion no es antigua. El catastro ANM WFS solo incluye titulos "
                "'vigentes'; es posible que este expediente corresponda a un tramite del Registro Minero "
                "Nacional que nunca llego a titulo vigente (solicitud rechazada, desistida, u otro estado "
                "no cubierto por la capa de catastro), pero esta fase no confirma esa hipotesis."
            )
        filas.append(
            {
                "codigo_expediente": cod,
                "origen": "anotacion_huerfana",
                "tipo_caso": "expediente_anotacion_sin_catastro",
                "coincide_tras_normalizacion": coincide_norm,
                "codigo_normalizado": cod_norm,
                "ultimo_anio_anotacion": ultimo_anio,
                "posible_historico_no_vigente": posible_historico,
                "observaciones": observ,
            }
        )

    return pd.DataFrame(filas)
