"""Fase 4A: integración espacial minera por unidad territorial DIVIPOLA.

Intersecta los 6.294 títulos mineros vigentes de la ANM (spatial_ready,
Fase 3D.1) con las 1.122 unidades territoriales DIVIPOLA vigentes con
geometría (universo analítico reconciliado, Fase 3D.1), y agrega ANM
Anotaciones RMN (limpia, Fase 3B) para producir indicadores DESCRIPTIVOS de
presión minera formal registrada por título y por unidad territorial.

Integra únicamente: universo territorial reconciliado, geometrías
territoriales, catastro minero spatial_ready y ANM Anotaciones RMN. NO
integra calidad hídrica, deforestación, bosque, RUNAP, áreas protegidas,
variables sociales, ni calcula riesgo/score/causalidad/ilegalidad/modelo/
dashboard — eso queda fuera de alcance de esta fase.

Salidas:
  data/processed/integrated/mineria_titulo_unidad_territorial.csv (+ .metadata.json)
  data/processed/features/mineria_por_unidad_territorial.csv (+ .metadata.json)
  data/interim/spatial_cache/territorial_units_epsg9377.pkl (+ .metadata.json)
  outputs/reports/mining_integration/mining_spatial_intersection.md
  outputs/reports/mining_integration/mining_territorial_indicators.md
  outputs/reports/mining_integration/mining_quality_checks.md
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
from shapely.geometry import shape as shapely_shape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.features.mining import (  # noqa: E402
    FECHA_ACTUALIZACION_FUENTE_CATASTRO,
    FUENTE_CATASTRO_LABEL,
    TOLERANCIA_AREA_M2_DEFAULT,
    aggregate_anm_annotations,
    build_area_conservation_table,
    build_territorial_indicators_table,
    build_title_territorial_table,
    validate_annotation_correspondence,
)
from aquabosque.geo.intersection import build_transformer, reproject_geometry, run_national_intersection  # noqa: E402
from aquabosque.utils.io import (  # noqa: E402
    ensure_dir,
    file_size_bytes,
    format_bytes,
    utc_now_iso,
    write_json,
    write_metadata,
)
from aquabosque.utils.spatial_cache import load_cache_if_valid, save_cache  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "mining_integration"
SPATIAL_CACHE_DIR = DATA_INTERIM / "spatial_cache"

UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
LIMITES_DIR = DATA_PROCESSED / "territorio" / "limites_municipales_dane"
LIMITES_MANIFEST_PATH = LIMITES_DIR / "manifest.json"
BAJIRA_PATH = DATA_PROCESSED / "territorio" / "dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson"
CATASTRO_SPATIAL_READY_PATH = DATA_PROCESSED / "mineria" / "catastro_minero_anm_spatial_ready.geojson"
ANM_ANOTACIONES_PATH = DATA_PROCESSED / "mineria" / "anm_anotaciones_rmn_clean.csv"

INTEGRATED_DIR = DATA_PROCESSED / "integrated"
FEATURES_DIR = DATA_PROCESSED / "features"
REL_TABLE_PATH = INTEGRATED_DIR / "mineria_titulo_unidad_territorial.csv"
INDICATORS_TABLE_PATH = FEATURES_DIR / "mineria_por_unidad_territorial.csv"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
CODIGO_MAPIRIPANA = "94663"
CODIGO_BAJIRA = "27493"
PROGRESS_EVERY = 1000
M2_PER_HA = 10_000.0


# --------------------------------------------------------------------------
# B. Universo analítico
# --------------------------------------------------------------------------


def load_universo_completo() -> pd.DataFrame:
    return pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})


def build_universo_analitico(df_universo: pd.DataFrame) -> pd.DataFrame:
    """`presente_divipola_vigente == True AND tiene_geometria == True`.
    Debe dar exactamente 1.122 filas; incluye 27493, excluye 94663."""
    analitico = df_universo[df_universo["presente_divipola_vigente"] & df_universo["tiene_geometria"]].copy()
    return analitico.reset_index(drop=True)


def compute_metrics(set_a: set[str], set_b: set[str]) -> dict:
    interseccion = set_a & set_b
    union = set_a | set_b
    return {
        "cobertura_divipola_por_geometria_pct": round(len(interseccion) / len(set_a) * 100, 4) if set_a else 0.0,
        "precision_geometria_contra_divipola_pct": round(len(interseccion) / len(set_b) * 100, 4) if set_b else 0.0,
        "similitud_jaccard_pct": round(len(interseccion) / len(union) * 100, 4) if union else 0.0,
    }


# --------------------------------------------------------------------------
# A/D. Carga de geometrías y catastro
# --------------------------------------------------------------------------


def load_territorial_geometries_4326(codigos_analiticos: set[str]) -> tuple[list[tuple[str, dict]], list[Path]]:
    """Lee las geometrías (GeoJSON, EPSG:4326) de las 11 partes de límites
    municipales + el archivo recuperado de Bajirá, filtrando solo a los
    códigos del universo analítico (excluye 94663 automáticamente: no está
    en `codigos_analiticos`)."""
    with open(LIMITES_MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    geoms: list[tuple[str, dict]] = []
    source_paths: list[Path] = []
    for a in manifest["archivos_y_tamanos"]:
        part_path = LIMITES_DIR / a["archivo"]
        source_paths.append(part_path)
        with open(part_path, encoding="utf-8") as fh:
            fc = json.load(fh)
        for feat in fc["features"]:
            cod = feat["properties"]["cod_dane_mpio"]
            if cod in codigos_analiticos:
                geoms.append((cod, feat["geometry"]))

    source_paths.append(BAJIRA_PATH)
    with open(BAJIRA_PATH, encoding="utf-8") as fh:
        fc_bajira = json.load(fh)
    for feat in fc_bajira["features"]:
        cod = feat["properties"]["cod_dane_mpio"]
        if cod in codigos_analiticos:
            geoms.append((cod, feat["geometry"]))

    return geoms, source_paths


def load_catastro_spatial_ready() -> pd.DataFrame:
    with open(CATASTRO_SPATIAL_READY_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)
    props = []
    for feat in fc["features"]:
        p = dict(feat["properties"])
        p["_geometry"] = feat.get("geometry")
        props.append(p)
    return pd.DataFrame(props)


def get_or_build_territorial_cache(
    territorial_geoms_4326: list[tuple[str, dict]], source_paths: list[Path]
) -> tuple[list[tuple[str, Any]], bool, float]:
    """Devuelve (geometrías reproyectadas, usó_cache, tiempo_reproyeccion_s)."""
    cached = load_cache_if_valid(
        SPATIAL_CACHE_DIR, cache_name="territorial_units_epsg9377", source_paths=source_paths, crs=CRS_METRICO
    )
    if cached is not None:
        return cached, True, 0.0

    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    t0 = time.perf_counter()
    reproj = [(cod, reproject_geometry(shapely_shape(g), transformer)) for cod, g in territorial_geoms_4326]
    tiempo = time.perf_counter() - t0
    save_cache(SPATIAL_CACHE_DIR, cache_name="territorial_units_epsg9377", data=reproj, source_paths=source_paths, crs=CRS_METRICO)
    return reproj, False, tiempo


# --------------------------------------------------------------------------
# Escritura de salidas
# --------------------------------------------------------------------------


def write_relational_table(df_rel: pd.DataFrame) -> int:
    ensure_dir(REL_TABLE_PATH.parent)
    df_rel.to_csv(REL_TABLE_PATH, index=False, encoding="utf-8")
    return file_size_bytes(REL_TABLE_PATH)


def write_indicators_table(df_ind: pd.DataFrame) -> int:
    ensure_dir(INDICATORS_TABLE_PATH.parent)
    df_ind.to_csv(INDICATORS_TABLE_PATH, index=False, encoding="utf-8")
    return file_size_bytes(INDICATORS_TABLE_PATH)


def write_output_metadata(
    path: Path,
    *,
    fuentes: list[str],
    total_titulos: int,
    total_unidades: int,
    stats: dict,
    tamano_bytes: int,
    n_filas: int,
    observaciones: list[str],
) -> None:
    metadata = {
        "fuente": "Fase 4A - integración espacial minera por unidad territorial",
        "fuentes_integradas": fuentes,
        "fecha_generacion": utc_now_iso(),
        "crs_entrada": CRS_ORIGEN,
        "crs_calculo": CRS_METRICO,
        "total_titulos_mineros": total_titulos,
        "total_unidades_territoriales": total_unidades,
        "n_filas_salida": n_filas,
        "tamano_bytes": tamano_bytes,
        "pares_candidatos_strtree": stats.get("n_pares_candidatos"),
        "intersecciones_area_positiva": stats.get("n_intersecciones_area_positiva"),
        "contactos_sin_area": stats.get("n_contactos_sin_area"),
        "tolerancia_area_m2": TOLERANCIA_AREA_M2_DEFAULT,
        "metodologia_areas": (
            "Áreas calculadas en EPSG:9377 (MAGNA-SIRGAS 2018 / Origen-Nacional) tras "
            "reproyectar desde EPSG:4326. area_titulada_suma_ha permite superposición "
            "entre títulos (suma simple); area_titulada_union_ha es el área de la unión "
            "geométrica (sin doble conteo) y es la métrica preferida para interpretar "
            "proporción física del territorio cubierto."
        ),
        "limitaciones": (
            "Catastro minero declarado como actualizado el 22/03/2023 por el geoservicio "
            "ANM (no es la fecha de este análisis). No incluye minería informal/ilegal. "
            "instrumento_ambiental='N' no implica necesariamente ausencia real de gestión "
            "ambiental fuera del alcance de este campo de la fuente. No se calculan "
            "indicadores de riesgo, score, causalidad ni ilegalidad."
        ),
        "tiempo_ejecucion_s": stats.get("tiempo_total_s"),
        "memoria_pico_mb": stats.get("memoria_pico_mb"),
        "observaciones": observaciones,
    }
    write_json(path, metadata)


# --------------------------------------------------------------------------
# K. Validaciones
# --------------------------------------------------------------------------


def validate_all(
    df_analitico: pd.DataFrame,
    df_rel: pd.DataFrame,
    df_ind: pd.DataFrame,
    df_conservacion: pd.DataFrame,
    correspondencia_anotaciones: dict,
) -> list[str]:
    problems: list[str] = []

    if len(df_analitico) != 1122:
        problems.append(f"universo analítico tiene {len(df_analitico)} filas, se esperaban 1122")
    if CODIGO_BAJIRA not in set(df_analitico["cod_dane_mpio"]):
        problems.append("27493 no está incluido en el universo analítico")
    if CODIGO_MAPIRIPANA in set(df_analitico["cod_dane_mpio"]):
        problems.append("94663 NO debería estar en el universo analítico")

    if len(df_ind) != 1122:
        problems.append(f"tabla de indicadores territoriales tiene {len(df_ind)} filas, se esperaban 1122")
    if set(df_ind["cod_dane_mpio"]) != set(df_analitico["cod_dane_mpio"]):
        problems.append("la tabla de indicadores no cubre exactamente el universo analítico")

    if not df_rel.empty:
        dup = df_rel.duplicated(subset=["codigo_expediente", "cod_dane_mpio"]).sum()
        if dup:
            problems.append(f"{dup} pares codigo_expediente+cod_dane_mpio duplicados en la tabla relacional")

        if (df_rel["area_interseccion_ha"] <= 0).any():
            problems.append("hay filas con area_interseccion_ha <= 0 en la tabla relacional (no debería, se filtran antes)")

        tolerancia_pct = 0.01
        fuera_rango = df_rel[
            (df_rel["pct_area_titulo_en_unidad"] < -tolerancia_pct)
            | (df_rel["pct_area_titulo_en_unidad"] > 100 + tolerancia_pct)
        ]
        if len(fuera_rango):
            problems.append(
                f"{len(fuera_rango)} filas con pct_area_titulo_en_unidad fuera de [0,100] "
                f"(tolerancia {tolerancia_pct} pp)"
            )

    return problems


def summarize_area_quality(df_conservacion: pd.DataFrame) -> dict:
    return {
        "n_titulos": len(df_conservacion),
        "n_dentro_tolerancia": int(df_conservacion["dentro_de_tolerancia"].sum()),
        "n_fuera_tolerancia": int((~df_conservacion["dentro_de_tolerancia"]).sum()),
        "n_asignacion_superior_100": int(df_conservacion["asignacion_superior_100"].sum()),
        "n_sin_interseccion_territorial": int(df_conservacion["sin_interseccion_territorial"].sum()),
        "diferencia_no_asignada_ha_max": float(df_conservacion["diferencia_no_asignada_ha"].max()),
        "diferencia_no_asignada_ha_min": float(df_conservacion["diferencia_no_asignada_ha"].min()),
    }


def detect_possible_overlaps(df_ind: pd.DataFrame) -> pd.DataFrame:
    """Unidades donde pct_area_unidad_titulada_suma > 100%: posible indicio
    de títulos superpuestos entre sí (no se trunca, se documenta)."""
    return df_ind[df_ind["pct_area_unidad_titulada_suma"] > 100][
        ["cod_dane_mpio", "nombre_mpio", "nombre_dpto", "n_titulos_mineros", "pct_area_unidad_titulada_suma", "pct_area_unidad_titulada_union"]
    ].sort_values("pct_area_unidad_titulada_suma", ascending=False)


# --------------------------------------------------------------------------
# Reportes
# --------------------------------------------------------------------------


def build_spatial_intersection_report(stats, metrics_post_filtro, tiempo_reproy_unidades, uso_cache, rel_size, ind_size) -> str:
    lines = [
        "# Intersección espacial minera (Fase 4A)",
        "",
        "Intersección nacional completa: 6.294 títulos mineros (spatial_ready, Fase 3D.1) × "
        "1.122 unidades territoriales DIVIPOLA vigentes con geometría (universo analítico, "
        "Fase 3D.1), usando un índice `STRtree` construido **una sola vez**. No se ejecutó el "
        "producto cartesiano completo.",
        "",
        "## Universo analítico y métricas post-filtro",
        "",
        f"- Unidades territoriales analíticas: {stats.n_unidades} (deben ser 1.122)",
        f"- **cobertura_divipola_por_geometria:** {metrics_post_filtro['cobertura_divipola_por_geometria_pct']}%",
        f"- **precision_geometria_contra_divipola:** {metrics_post_filtro['precision_geometria_contra_divipola_pct']}%",
        f"- **similitud_jaccard:** {metrics_post_filtro['similitud_jaccard_pct']}%",
        "- Las tres deben ser 100% por construcción (el universo analítico se define como la "
        "intersección exacta de DIVIPOLA vigente y disponibilidad de geometría); si no lo son, "
        "el proceso se detiene con error antes de continuar.",
        "",
        "## Caché espacial",
        "",
        f"- {'Se reutilizó' if uso_cache else 'Se generó (no existía o estaba desactualizado)'} "
        f"el caché `data/interim/spatial_cache/territorial_units_epsg9377.pkl`.",
        f"- Tiempo de reproyección de las 1.122 unidades territoriales en esta corrida: "
        f"{tiempo_reproy_unidades:.4f} s"
        + (" (0 s porque se reutilizó el caché)." if uso_cache else "."),
        "",
        "## Rendimiento de la intersección nacional",
        "",
        f"- Títulos procesados: {stats.n_titulos}",
        f"- Unidades territoriales indexadas: {stats.n_unidades}",
        f"- Tiempo de reproyección de títulos: {stats.tiempo_reproyeccion_s} s",
        f"- Tiempo de construcción del índice STRtree: {stats.tiempo_construccion_indice_s} s",
        f"- Tiempo de consulta (bounding box): {stats.tiempo_consulta_s} s",
        f"- Tiempo de intersecciones geométricas reales: {stats.tiempo_interseccion_s} s",
        f"- Tiempo total del módulo de intersección: {stats.tiempo_total_s} s",
        f"- Memoria pico (tracemalloc, dentro del módulo de intersección): {stats.memoria_pico_mb} MB",
        "",
        "## Resultados de la intersección",
        "",
        f"- Pares candidatos por bounding box (STRtree): {stats.n_pares_candidatos:,}",
        f"- Intersecciones con área positiva: {stats.n_intersecciones_area_positiva:,}",
        f"- Contactos sin área (solo tocan el límite, línea/punto): {stats.n_contactos_sin_area:,}",
        f"- Títulos sin ninguna intersección con área positiva: {stats.n_titulos_sin_interseccion:,}",
        f"- Pares evitados frente al producto cartesiano completo "
        f"({stats.n_titulos:,} × {stats.n_unidades:,} = {stats.n_titulos * stats.n_unidades:,}): "
        f"{stats.n_titulos * stats.n_unidades - stats.n_pares_candidatos:,}",
        "",
        "## Archivos generados",
        "",
        f"- `data/processed/integrated/mineria_titulo_unidad_territorial.csv` ({format_bytes(rel_size)})",
        f"- `data/processed/features/mineria_por_unidad_territorial.csv` ({format_bytes(ind_size)})",
        "",
    ]
    return "\n".join(lines)


def build_territorial_indicators_report(df_ind: pd.DataFrame, overlaps: pd.DataFrame) -> str:
    con_titulos = df_ind[df_ind["tiene_titulos_mineros"]]
    top_n_titulos = df_ind.sort_values("n_titulos_mineros", ascending=False).head(15)
    top_pct_union = df_ind.sort_values("pct_area_unidad_titulada_union", ascending=False).head(15)

    lines = [
        "# Indicadores mineros territoriales (Fase 4A)",
        "",
        "Indicadores **descriptivos** de presión minera formal registrada, por unidad "
        "territorial DIVIPOLA vigente. No son indicadores de riesgo, ilegalidad ni "
        "causalidad ambiental.",
        "",
        f"- Unidades territoriales totales: {len(df_ind)} (deben ser 1.122)",
        f"- Unidades con al menos un título minero: {len(con_titulos)} "
        f"({len(con_titulos) / len(df_ind) * 100:.1f}%)",
        f"- Unidades sin ningún título minero (valores en cero, no filas ausentes): {len(df_ind) - len(con_titulos)}",
        f"- Total de títulos mineros considerados: {int(df_ind['n_titulos_mineros'].sum())} "
        "(cuenta repetida entre unidades cuando un título cruza varias: usar la tabla "
        "relacional para el conteo real de títulos únicos)",
        "",
        "## Top 15 unidades por número de títulos mineros",
        "",
        "| cod_dane_mpio | nombre_mpio | nombre_dpto | n_titulos_mineros | pct_area_unidad_titulada_union |",
        "|---|---|---|---|---|",
    ]
    for _, r in top_n_titulos.iterrows():
        lines.append(
            f"| {r['cod_dane_mpio']} | {r['nombre_mpio']} | {r['nombre_dpto']} | "
            f"{r['n_titulos_mineros']} | {r['pct_area_unidad_titulada_union']:.2f}% |"
        )
    lines.append("")

    lines.append("## Top 15 unidades por % de área titulada (unión, sin doble conteo)")
    lines.append("")
    lines.append("| cod_dane_mpio | nombre_mpio | nombre_dpto | pct_area_unidad_titulada_union | n_titulos_mineros |")
    lines.append("|---|---|---|---|---|")
    for _, r in top_pct_union.iterrows():
        lines.append(
            f"| {r['cod_dane_mpio']} | {r['nombre_mpio']} | {r['nombre_dpto']} | "
            f"{r['pct_area_unidad_titulada_union']:.2f}% | {r['n_titulos_mineros']} |"
        )
    lines.append("")

    lines.append("## Diferencia entre suma y unión de área titulada")
    lines.append("")
    lines.append(
        "`area_titulada_suma_ha` permite superposición entre títulos (suma simple de cada "
        "intersección); `area_titulada_union_ha` es el área de la **unión geométrica** de "
        "todos los títulos dentro de la unidad, sin doble conteo. Se recomienda usar "
        "`pct_area_unidad_titulada_union` para interpretar proporción física real del "
        "territorio cubierto."
    )
    lines.append("")
    diff = con_titulos[con_titulos["area_titulada_suma_ha"] > con_titulos["area_titulada_union_ha"] + 0.001]
    lines.append(
        f"- {len(diff)} unidades tienen `area_titulada_suma_ha` > `area_titulada_union_ha` "
        "(indicio de títulos superpuestos entre sí dentro de la misma unidad)."
    )
    lines.append("")

    lines.append("## Unidades con posible sobreposición de títulos (suma > 100% del área de la unidad)")
    lines.append("")
    if len(overlaps):
        lines.append("| cod_dane_mpio | nombre_mpio | nombre_dpto | n_titulos_mineros | pct_suma | pct_union |")
        lines.append("|---|---|---|---|---|---|")
        for _, r in overlaps.iterrows():
            lines.append(
                f"| {r['cod_dane_mpio']} | {r['nombre_mpio']} | {r['nombre_dpto']} | "
                f"{r['n_titulos_mineros']} | {r['pct_area_unidad_titulada_suma']:.2f}% | "
                f"{r['pct_area_unidad_titulada_union']:.2f}% |"
            )
        lines.append("")
        lines.append(
            "**No se truncó ningún valor automáticamente.** Un `pct_area_unidad_titulada_suma` "
            "por encima de 100% no es necesariamente un error: indica que existen títulos "
            "mineros superpuestos entre sí dentro de esa unidad territorial (p. ej. distintas "
            "modalidades o etapas sobre la misma área). `pct_area_unidad_titulada_union` da la "
            "proporción física real, que nunca puede superar 100%."
        )
    else:
        lines.append("_Ninguna unidad superó 100% en `pct_area_unidad_titulada_suma`._")
    lines.append("")

    return "\n".join(lines)


def build_quality_checks_report(
    df_conservacion,
    calidad_conservacion: dict,
    correspondencia_anotaciones: dict,
    df_analitico_validation: list[str],
    stats,
) -> str:
    peores = df_conservacion.reindex(
        df_conservacion["diferencia_no_asignada_ha"].abs().sort_values(ascending=False).index
    ).head(15)

    lines = [
        "# Controles de calidad (Fase 4A)",
        "",
        f"Tolerancia numérica explícita usada: `tolerancia_area_m2 = {TOLERANCIA_AREA_M2_DEFAULT}` "
        f"({TOLERANCIA_AREA_M2_DEFAULT / 10000} ha). Ninguna diferencia se ocultó bajo esta "
        "tolerancia: se documentan todas, la tolerancia solo se usa para clasificar "
        "`dentro_de_tolerancia` sí/no.",
        "",
        "## G. Control de conservación de área por título",
        "",
        f"- Títulos evaluados: {calidad_conservacion['n_titulos']}",
        f"- Dentro de tolerancia: {calidad_conservacion['n_dentro_tolerancia']}",
        f"- Fuera de tolerancia: {calidad_conservacion['n_fuera_tolerancia']}",
        f"- Con asignación superior a 100% (más allá de tolerancia): {calidad_conservacion['n_asignacion_superior_100']}",
        f"- Sin ninguna intersección territorial: {calidad_conservacion['n_sin_interseccion_territorial']}",
        f"- Diferencia no asignada (ha) — máx: {calidad_conservacion['diferencia_no_asignada_ha_max']:.4f}, "
        f"mín: {calidad_conservacion['diferencia_no_asignada_ha_min']:.4f}",
        "",
        "### 15 títulos con mayor diferencia absoluta de área no asignada",
        "",
        "| codigo_expediente | area_geometria_titulo_ha | suma_area_intersecciones_ha | diferencia_no_asignada_ha | pct_area_asignada | n_unidades_territoriales |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in peores.iterrows():
        pct = f"{r['pct_area_asignada']:.2f}%" if pd.notna(r["pct_area_asignada"]) else "N/D"
        lines.append(
            f"| {r['codigo_expediente']} | {r['area_geometria_titulo_ha']:.4f} | "
            f"{r['suma_area_intersecciones_ha']:.4f} | {r['diferencia_no_asignada_ha']:.4f} | "
            f"{pct} | {r['n_unidades_territoriales']} |"
        )
    lines.append("")

    lines.append("## H. Correspondencia con ANM Anotaciones RMN")
    lines.append("")
    lines.append(f"- Títulos en catastro: {correspondencia_anotaciones['titulos_catastro_total']}")
    lines.append(f"- Títulos con anotaciones: {correspondencia_anotaciones['titulos_con_anotaciones']}")
    lines.append(f"- Títulos sin anotaciones: {correspondencia_anotaciones['titulos_sin_anotaciones']}")
    lines.append(
        f"- Expedientes de anotaciones no encontrados en el catastro: "
        f"{correspondencia_anotaciones['expedientes_anotaciones_no_en_catastro']} "
        f"(muestra: {correspondencia_anotaciones['expedientes_anotaciones_no_en_catastro_muestra']})"
    )
    lines.append(f"- Porcentaje de correspondencia: {correspondencia_anotaciones['pct_correspondencia']}%")
    lines.append("")

    lines.append("## Otras validaciones (sección K)")
    lines.append("")
    if df_analitico_validation:
        for p in df_analitico_validation:
            lines.append(f"- ⚠ {p}")
    else:
        lines.append("- Todas las validaciones automáticas pasaron sin problemas.")
    lines.append("")

    lines.append("## Resumen de la corrida")
    lines.append("")
    lines.append(f"- Tiempo total del módulo de intersección: {stats.tiempo_total_s} s")
    lines.append(f"- Memoria pico: {stats.memoria_pico_mb} MB")
    lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Orquestación
# --------------------------------------------------------------------------


def _progress_cb(i: int, n: int) -> None:
    print(f"    procesados {i:,}/{n:,} títulos ({i / n * 100:.1f}%)...", flush=True)


def main() -> int:
    t_script_start = time.perf_counter()
    print("Fase 4A: integración espacial minera por unidad territorial DIVIPOLA")
    print("=" * 70)

    ensure_dir(INTEGRATED_DIR)
    ensure_dir(FEATURES_DIR)
    ensure_dir(REPORTS_DIR)
    ensure_dir(SPATIAL_CACHE_DIR)

    print("\n[1/9] Cargando y filtrando universo territorial DIVIPOLA...")
    df_universo = load_universo_completo()
    df_analitico = build_universo_analitico(df_universo)
    print(f"  Universo completo: {len(df_universo)} filas")
    print(f"  Universo analítico (vigente + con geometría): {len(df_analitico)} filas")

    if len(df_analitico) != 1122:
        print(f"ERROR: universo analítico tiene {len(df_analitico)} filas, se esperaban 1122. Proceso detenido.")
        return 1
    codigos_analiticos = set(df_analitico["cod_dane_mpio"])
    if CODIGO_BAJIRA not in codigos_analiticos:
        print("ERROR: 27493 (Nuevo Belén de Bajirá) no está en el universo analítico. Proceso detenido.")
        return 1
    if CODIGO_MAPIRIPANA in codigos_analiticos:
        print("ERROR: 94663 (Mapiripaná) no debería estar en el universo analítico. Proceso detenido.")
        return 1
    print("  OK: 1.122 unidades, 27493 incluida, 94663 excluida.")

    print("\n[2/9] Cargando geometrías territoriales (EPSG:4326) y validando correspondencia...")
    territorial_geoms_4326, source_paths = load_territorial_geometries_4326(codigos_analiticos)
    codigos_cargados = {cod for cod, _ in territorial_geoms_4326}
    metrics_post_filtro = compute_metrics(codigos_analiticos, codigos_cargados)
    print(f"  Geometrías cargadas: {len(territorial_geoms_4326)}")
    print(f"  cobertura_divipola_por_geometria: {metrics_post_filtro['cobertura_divipola_por_geometria_pct']}%")
    print(f"  precision_geometria_contra_divipola: {metrics_post_filtro['precision_geometria_contra_divipola_pct']}%")
    print(f"  similitud_jaccard: {metrics_post_filtro['similitud_jaccard_pct']}%")

    if (
        metrics_post_filtro["cobertura_divipola_por_geometria_pct"] != 100.0
        or metrics_post_filtro["precision_geometria_contra_divipola_pct"] != 100.0
        or metrics_post_filtro["similitud_jaccard_pct"] != 100.0
    ):
        print("ERROR: las tres métricas de correspondencia deberían ser 100%. Proceso detenido.")
        return 1
    if len(territorial_geoms_4326) != len(codigos_cargados):
        print("ERROR: hay códigos DANE duplicados entre las geometrías cargadas. Proceso detenido.")
        return 1
    print("  OK: correspondencia 100% / 100% / 100%, sin duplicados.")

    print("\n[3/9] Reproyectando unidades territoriales a EPSG:9377 (o reutilizando caché)...")
    reproj_geoms, uso_cache, tiempo_reproy_unidades = get_or_build_territorial_cache(
        territorial_geoms_4326, source_paths
    )
    territorial_areas_ha = {cod: geom.area / M2_PER_HA for cod, geom in reproj_geoms}
    print(f"  {'Caché reutilizado' if uso_cache else 'Caché generado'} ({tiempo_reproy_unidades:.4f} s de reproyección).")

    print("\n[4/9] Cargando catastro minero ANM spatial_ready...")
    df_catastro = load_catastro_spatial_ready()
    print(f"  Títulos mineros cargados: {len(df_catastro)}")
    title_geoms = [(row["codigo_expediente"], row["_geometry"]) for _, row in df_catastro.iterrows()]

    print("\n[5/9] Ejecutando intersección espacial nacional (STRtree, una sola construcción)...")
    result = run_national_intersection(
        title_geoms,
        reproj_geoms,
        crs_origen=CRS_ORIGEN,
        crs_metrico=CRS_METRICO,
        progress_every=PROGRESS_EVERY,
        on_progress=_progress_cb,
    )
    stats = result.stats
    print(f"  Pares candidatos (bbox): {stats.n_pares_candidatos:,}")
    print(f"  Intersecciones con área positiva: {stats.n_intersecciones_area_positiva:,}")
    print(f"  Contactos sin área: {stats.n_contactos_sin_area:,}")
    print(f"  Títulos sin intersección: {stats.n_titulos_sin_interseccion:,}")
    print(f"  Tiempo total del módulo: {stats.tiempo_total_s} s | Memoria pico: {stats.memoria_pico_mb} MB")

    print("\n[6/9] Agregando ANM Anotaciones RMN por codigo_expediente...")
    df_anotaciones = pd.read_csv(ANM_ANOTACIONES_PATH, dtype={"codigo_expediente": str})
    df_anotaciones_agg = aggregate_anm_annotations(df_anotaciones)
    correspondencia_anotaciones = validate_annotation_correspondence(df_catastro, df_anotaciones_agg)
    print(f"  Expedientes con anotaciones agregadas: {len(df_anotaciones_agg)}")
    print(f"  Correspondencia con catastro: {correspondencia_anotaciones['pct_correspondencia']}%")

    print("\n[7/9] Construyendo tabla título-unidad territorial y control de conservación de área...")
    df_rel = build_title_territorial_table(
        result.records, result.title_areas_m2, df_catastro, df_analitico, territorial_areas_ha
    )
    df_conservacion = build_area_conservation_table(
        df_rel, result.title_areas_m2, tolerancia_area_m2=TOLERANCIA_AREA_M2_DEFAULT
    )
    calidad_conservacion = summarize_area_quality(df_conservacion)
    print(f"  Filas relacionales (título x unidad, área positiva): {len(df_rel)}")
    print(f"  Títulos dentro de tolerancia de conservación de área: {calidad_conservacion['n_dentro_tolerancia']}/{calidad_conservacion['n_titulos']}")

    print("\n[8/9] Construyendo indicadores agregados por unidad territorial (1.122 filas)...")
    df_ind = build_territorial_indicators_table(
        df_analitico,
        territorial_areas_ha,
        df_rel,
        result.records,
        df_catastro,
        df_anotaciones_agg,
        df_conservacion,
        catastro_minerales_originales=df_catastro["minerales"],
    )
    overlaps = detect_possible_overlaps(df_ind)
    print(f"  Filas de indicadores: {len(df_ind)}")
    print(f"  Unidades con posible sobreposición de títulos (suma > 100%): {len(overlaps)}")

    problemas = validate_all(df_analitico, df_rel, df_ind, df_conservacion, correspondencia_anotaciones)
    if problemas:
        print("\n  ADVERTENCIAS de validación (no detienen el proceso, quedan documentadas):")
        for p in problemas:
            print(f"    - {p}")
    else:
        print("  Todas las validaciones automáticas (sección K) pasaron sin problemas.")

    print("\n[9/9] Escribiendo salidas, metadata y reportes...")
    rel_size = write_relational_table(df_rel)
    ind_size = write_indicators_table(df_ind)

    fuentes_comunes = [
        "data/processed/territorio/universo_territorial_divipola.csv (Fase 3D.1)",
        "data/processed/territorio/limites_municipales_dane/*.geojson (Fase 3D)",
        "data/processed/territorio/dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson (Fase 3D.1)",
        "data/processed/mineria/catastro_minero_anm_spatial_ready.geojson (Fase 3C)",
        "data/processed/mineria/anm_anotaciones_rmn_clean.csv (Fase 3B)",
    ]
    stats_dict = asdict(stats)

    write_output_metadata(
        REL_TABLE_PATH.with_suffix(REL_TABLE_PATH.suffix + ".metadata.json"),
        fuentes=fuentes_comunes,
        total_titulos=len(title_geoms),
        total_unidades=len(df_analitico),
        stats=stats_dict,
        tamano_bytes=rel_size,
        n_filas=len(df_rel),
        observaciones=[
            "Una fila por combinación real codigo_expediente + cod_dane_mpio con área de "
            "intersección positiva. Los contactos de solo línea/punto (solo_toca_limite=True) "
            "no aparecen en esta tabla; quedan solo en las estadísticas de la corrida.",
            f"Validaciones con advertencias: {len(problemas)}.",
        ],
    )
    write_output_metadata(
        INDICATORS_TABLE_PATH.with_suffix(INDICATORS_TABLE_PATH.suffix + ".metadata.json"),
        fuentes=fuentes_comunes,
        total_titulos=len(title_geoms),
        total_unidades=len(df_analitico),
        stats=stats_dict,
        tamano_bytes=ind_size,
        n_filas=len(df_ind),
        observaciones=[
            "Una fila por cada una de las 1.122 unidades del universo analítico, incluidas "
            "las que no tienen ningún título minero (valores en cero, no filas ausentes).",
            "instrumento_ambiental='N' o ausente no implica necesariamente ausencia real de "
            "gestión ambiental: es una limitación declarada de la fuente ANM, no se interpreta "
            "como causalidad.",
            f"Validaciones con advertencias: {len(problemas)}.",
        ],
    )

    reporte_espacial = build_spatial_intersection_report(
        stats, metrics_post_filtro, tiempo_reproy_unidades, uso_cache, rel_size, ind_size
    )
    (REPORTS_DIR / "mining_spatial_intersection.md").write_text(reporte_espacial, encoding="utf-8")

    reporte_indicadores = build_territorial_indicators_report(df_ind, overlaps)
    (REPORTS_DIR / "mining_territorial_indicators.md").write_text(reporte_indicadores, encoding="utf-8")

    reporte_calidad = build_quality_checks_report(
        df_conservacion, calidad_conservacion, correspondencia_anotaciones, problemas, stats
    )
    (REPORTS_DIR / "mining_quality_checks.md").write_text(reporte_calidad, encoding="utf-8")

    t_script_total = time.perf_counter() - t_script_start

    print("\n" + "=" * 70)
    print("RESUMEN FINAL - Fase 4A")
    print("=" * 70)
    print(f"Tiempo total del script: {t_script_total:.2f} s")
    print(f"Tiempo del módulo de intersección: {stats.tiempo_total_s} s | Memoria pico: {stats.memoria_pico_mb} MB")
    print(f"Títulos mineros procesados: {stats.n_titulos:,}")
    print(f"Unidades territoriales procesadas: {stats.n_unidades:,}")
    print(f"Pares candidatos (STRtree): {stats.n_pares_candidatos:,}")
    print(f"Intersecciones con área positiva: {stats.n_intersecciones_area_positiva:,}")
    print(f"Contactos sin área: {stats.n_contactos_sin_area:,}")
    print(f"Títulos sin ninguna asignación territorial: {stats.n_titulos_sin_interseccion:,}")
    print(
        f"Conservación de área: {calidad_conservacion['n_dentro_tolerancia']}/{calidad_conservacion['n_titulos']} "
        f"títulos dentro de tolerancia ({TOLERANCIA_AREA_M2_DEFAULT} m²)"
    )
    print(f"Correspondencia con ANM Anotaciones RMN: {correspondencia_anotaciones['pct_correspondencia']}%")
    print(f"Indicadores generados: {len(df_ind)} unidades territoriales ({len(df_ind[df_ind['tiene_titulos_mineros']])} con títulos mineros)")
    print(f"Unidades con posible sobreposición de títulos entre sí: {len(overlaps)}")
    print(f"Archivos generados: {REL_TABLE_PATH.name} ({format_bytes(rel_size)}), {INDICATORS_TABLE_PATH.name} ({format_bytes(ind_size)})")
    print(f"Validaciones con advertencias: {len(problemas)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
