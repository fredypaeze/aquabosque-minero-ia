"""Fase 4A.2: regeneración de la integración minera territorial usando
exclusivamente la base geométrica nacional homogénea DANE MGN2025.

Repite la intersección minera nacional, los indicadores territoriales y los
controles de calidad de las Fases 4A/4A.1, reemplazando la base geométrica
mixta (capa ArcGIS Divipola + geometría puntual de Bajirá) por
`data/processed/territorio/base_geometrica_divipola_mgn2025/` (Fase 3D.2).

No integra calidad hídrica. No construye índice de riesgo. No entrena modelo.
No crea dashboard. No modifica datos crudos. No borra los resultados
anteriores de Fase 4A/4A.1 (quedan intactos como referencia histórica).
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from shapely.geometry import shape as shapely_shape
from shapely.strtree import STRtree

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
from aquabosque.features.mining_audit import (  # noqa: E402
    UMBRAL_REVISION_MANUAL_HA,
    audit_territorial_topology,
    build_annotation_correspondence_audit,
    build_conservation_audit_table,
    describe_unassigned_title,
    validate_unit_area_indicators,
)
from aquabosque.geo.intersection import build_transformer, reproject_geometry, run_national_intersection  # noqa: E402
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402
from aquabosque.utils.spatial_cache import compute_source_fingerprint, load_cache_if_valid, save_cache  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "mining_integration_mgn2025"
SPATIAL_CACHE_DIR = DATA_INTERIM / "spatial_cache"

BASE_GEOM_DIR = DATA_PROCESSED / "territorio" / "base_geometrica_divipola_mgn2025"
BASE_GEOM_MANIFEST = BASE_GEOM_DIR / "manifest.json"
UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
CATASTRO_SPATIAL_READY_PATH = DATA_PROCESSED / "mineria" / "catastro_minero_anm_spatial_ready.geojson"
ANM_ANOTACIONES_PATH = DATA_PROCESSED / "mineria" / "anm_anotaciones_rmn_clean.csv"

INTEGRATED_DIR = DATA_PROCESSED / "integrated"
FEATURES_DIR = DATA_PROCESSED / "features"
AUDIT_DIR = DATA_PROCESSED / "audit"

# Entradas de la Fase 4A/4A.1 (solo para comparación, nunca como entrada geométrica)
LEGACY_REL_PATH = INTEGRATED_DIR / "mineria_titulo_unidad_territorial.csv"
LEGACY_IND_PATH = FEATURES_DIR / "mineria_por_unidad_territorial.csv"
LEGACY_CONS_AUDIT_PATH = AUDIT_DIR / "mineria_area_conservation_audit.csv"

# Nuevas salidas MGN2025
REL_MGN2025_PATH = INTEGRATED_DIR / "mineria_titulo_unidad_territorial_mgn2025.csv"
IND_MGN2025_PATH = FEATURES_DIR / "mineria_por_unidad_territorial_mgn2025.csv"
CONS_AUDIT_MGN2025_PATH = AUDIT_DIR / "mineria_area_conservation_audit_mgn2025.csv"
ANNOT_AUDIT_MGN2025_PATH = AUDIT_DIR / "anm_annotation_correspondence_audit_mgn2025.csv"
TITLE_COMPARISON_PATH = AUDIT_DIR / "mining_mgn2025_comparison.csv"
INDICATOR_COMPARISON_PATH = AUDIT_DIR / "mining_territorial_indicators_mgn2025_comparison.csv"

# "Legacy" explícito (copia congelada, sección M) — no se borra la versión anterior
LEGACY_REL_COPY_PATH = INTEGRATED_DIR / "mineria_titulo_unidad_territorial_legacy_mixed_geometry.csv"
LEGACY_IND_COPY_PATH = FEATURES_DIR / "mineria_por_unidad_territorial_legacy_mixed_geometry.csv"
CANONICAL_SOURCE_PATH = DATA_PROCESSED / "CANONICAL_SOURCE.json"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
CODIGO_BAJIRA = "27493"
CODIGO_MAPIRIPANA = "94663"
ZONA_BAJIRA = ["27493", "27615", "05480", "05837", "27150", "05234"]
CASOS_NOTABLES_4A1 = ["ICQ-080212X", "HCA-144", "HCA-145", "HCA-146", "GLL-15R", "GLL-15T", "LI9-10311"]
TITULO_SIN_ASIGNACION_4A1 = "583"
M2_PER_HA = 10_000.0
FUENTE_GEOMETRIA_TERRITORIAL_MGN2025 = "DANE Marco Geoestadístico Nacional 2025"
VERSION_GEOMETRIA_TERRITORIAL_MGN2025 = "MGN2025"
PROGRESS_EVERY = 1000


# --------------------------------------------------------------------------
# A/B. Carga y verificación previa obligatoria
# --------------------------------------------------------------------------


def load_universo_vigente() -> pd.DataFrame:
    df = pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    return df[df["presente_divipola_vigente"]].reset_index(drop=True)


def load_mgn2025_geometries_4326() -> tuple[list[tuple[str, dict]], list[Path]]:
    with open(BASE_GEOM_MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)
    geoms: list[tuple[str, dict]] = []
    source_paths: list[Path] = []
    for a in manifest["archivos_y_tamanos"]:
        part_path = BASE_GEOM_DIR / a["archivo"]
        source_paths.append(part_path)
        with open(part_path, encoding="utf-8") as fh:
            fc = json.load(fh)
        if "crs" in fc:
            raise ValueError(f"{part_path.name} tiene un miembro top-level 'crs': viola RFC 7946.")
        for feat in fc["features"]:
            geoms.append((feat["properties"]["cod_dane_mpio"], feat["geometry"]))
    return geoms, source_paths


def run_pre_flight_validations(df_vigente: pd.DataFrame, mgn_geoms_4326: list[tuple[str, dict]]) -> list[str]:
    """Sección B: 11 validaciones obligatorias. Devuelve la lista de
    problemas encontrados (vacía si todo pasa); el llamador decide detenerse."""
    problemas: list[str] = []

    if len(df_vigente) != 1122:
        problemas.append(f"universo DIVIPOLA vigente tiene {len(df_vigente)} filas, se esperaban 1122")
    if len(mgn_geoms_4326) != 1122:
        problemas.append(f"MGN2025 tiene {len(mgn_geoms_4326)} geometrías, se esperaban 1122")

    codigos_vigente = set(df_vigente["cod_dane_mpio"])
    codigos_mgn = [cod for cod, _ in mgn_geoms_4326]
    codigos_mgn_set = set(codigos_mgn)

    if codigos_vigente != codigos_mgn_set:
        problemas.append(
            f"correspondencia no exacta: {len(codigos_vigente - codigos_mgn_set)} solo en DIVIPOLA, "
            f"{len(codigos_mgn_set - codigos_vigente)} solo en MGN2025"
        )
    if len(codigos_mgn) != len(codigos_mgn_set):
        problemas.append(f"{len(codigos_mgn) - len(codigos_mgn_set)} códigos duplicados en MGN2025")
    if df_vigente["cod_dane_mpio"].duplicated().any():
        problemas.append("códigos duplicados en el universo DIVIPOLA vigente")

    if CODIGO_BAJIRA not in codigos_mgn_set:
        problemas.append("27493 no está presente en MGN2025")
    if CODIGO_MAPIRIPANA in codigos_mgn_set:
        problemas.append("94663 SÍ está presente en MGN2025 (no debería)")

    n_nulas = sum(1 for _, g in mgn_geoms_4326 if g is None)
    if n_nulas:
        problemas.append(f"{n_nulas} geometrías nulas en MGN2025")

    n_vacias = 0
    n_invalidas = 0
    for cod, g in mgn_geoms_4326:
        if g is None:
            continue
        s = shapely_shape(g)
        if s.is_empty:
            n_vacias += 1
        if not s.is_valid:
            n_invalidas += 1
    if n_vacias:
        problemas.append(f"{n_vacias} geometrías vacías en MGN2025")
    if n_invalidas:
        problemas.append(f"{n_invalidas} geometrías inválidas en MGN2025")

    # Transformación válida a EPSG:9377 (verificación funcional, no solo declarativa)
    try:
        transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
        muestra_cod, muestra_geom = mgn_geoms_4326[0]
        reproj = reproject_geometry(shapely_shape(muestra_geom), transformer)
        if not reproj.is_valid or reproj.area <= 0:
            problemas.append("la transformación de prueba a EPSG:9377 produjo una geometría inválida o de área no positiva")
    except Exception as exc:  # noqa: BLE001
        problemas.append(f"fallo al construir/transformar con EPSG:9377: {exc}")

    return problemas


def check_zero_overlaps(mgn_geoms_proj: list[tuple[str, Any]]) -> tuple[bool, dict]:
    """Sección B: cero solapes territoriales con área positiva (reutiliza la
    auditoría de topología de la Fase 3D.2/4A.1, recalculada aquí, no
    reutilizada de memoria)."""
    topo = audit_territorial_topology(mgn_geoms_proj, geom_94663_proj=None)
    return topo["n_pares_solape"] == 0, topo


# --------------------------------------------------------------------------
# C. Caché espacial (exclusivo MGN2025, con verificación de hash)
# --------------------------------------------------------------------------


def get_or_build_mgn2025_cache(
    mgn_geoms_4326: list[tuple[str, dict]], source_paths: list[Path]
) -> tuple[list[tuple[str, Any]], bool, float]:
    huella = compute_source_fingerprint(source_paths)
    cached = load_cache_if_valid(
        SPATIAL_CACHE_DIR, cache_name="territorial_units_mgn2025_epsg9377", source_paths=source_paths, crs=CRS_METRICO
    )
    if cached is not None:
        print(f"  Caché válido reutilizado (huella verificada contra {len(huella)} archivos MGN2025 actuales).")
        return cached, True, 0.0

    print("  Caché inválido o ausente: reproyectando desde cero (NO se reutiliza el caché de la capa mixta).")
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    t0 = time.perf_counter()
    reproj = [(cod, reproject_geometry(shapely_shape(g), transformer)) for cod, g in mgn_geoms_4326]
    tiempo = time.perf_counter() - t0
    save_cache(SPATIAL_CACHE_DIR, cache_name="territorial_units_mgn2025_epsg9377", data=reproj, source_paths=source_paths, crs=CRS_METRICO)
    return reproj, False, tiempo


# --------------------------------------------------------------------------
# Catastro / anotaciones
# --------------------------------------------------------------------------


def load_catastro_spatial_ready() -> pd.DataFrame:
    with open(CATASTRO_SPATIAL_READY_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)
    props = []
    for feat in fc["features"]:
        p = dict(feat["properties"])
        p["_geometry"] = feat.get("geometry")
        props.append(p)
    return pd.DataFrame(props)


# --------------------------------------------------------------------------
# J. Comparación contra la Fase 4A anterior (capa mixta)
# --------------------------------------------------------------------------


def build_title_comparison(df_rel_legacy: pd.DataFrame, df_rel_mgn2025: pd.DataFrame) -> pd.DataFrame:
    key = ["codigo_expediente", "cod_dane_mpio"]
    left = df_rel_legacy[key + ["area_interseccion_ha"]].rename(columns={"area_interseccion_ha": "area_legacy_ha"})
    right = df_rel_mgn2025[key + ["area_interseccion_ha"]].rename(columns={"area_interseccion_ha": "area_mgn2025_ha"})
    merged = left.merge(right, on=key, how="outer", indicator=True)

    merged["relacion_anterior"] = merged["_merge"].isin(["left_only", "both"])
    merged["relacion_mgn2025"] = merged["_merge"].isin(["right_only", "both"])
    merged["aparecio"] = merged["_merge"] == "right_only"
    merged["desaparecio"] = merged["_merge"] == "left_only"
    merged["diferencia_absoluta_ha"] = merged["area_mgn2025_ha"].fillna(0) - merged["area_legacy_ha"].fillna(0)
    merged["diferencia_pct"] = np.where(
        merged["area_legacy_ha"].fillna(0) > 0,
        merged["diferencia_absoluta_ha"] / merged["area_legacy_ha"] * 100,
        np.nan,
    )

    unidades_legacy_por_titulo = df_rel_legacy.groupby("codigo_expediente")["cod_dane_mpio"].apply(set)
    unidades_mgn2025_por_titulo = df_rel_mgn2025.groupby("codigo_expediente")["cod_dane_mpio"].apply(set)
    todos_titulos = set(unidades_legacy_por_titulo.index) | set(unidades_mgn2025_por_titulo.index)
    cambio_unidad = {
        cod: unidades_legacy_por_titulo.get(cod, set()) != unidades_mgn2025_por_titulo.get(cod, set())
        for cod in todos_titulos
    }
    merged["cambio_de_unidad"] = merged["codigo_expediente"].map(cambio_unidad).fillna(False)
    merged["afectado_por_zona_bajira"] = merged["cod_dane_mpio"].isin(ZONA_BAJIRA)

    def observacion(row) -> str:
        if row["aparecio"]:
            return "nueva asignación (no existía en la capa mixta)"
        if row["desaparecio"]:
            return "asignación desaparecida (existía en la capa mixta, no en MGN2025)"
        if abs(row["diferencia_absoluta_ha"]) > 1.0:
            return "cambio de área mayor a 1 ha"
        if abs(row["diferencia_absoluta_ha"]) > 0.001:
            return "cambio de área menor (posible diferencia de trazado de límite)"
        return "sin cambio significativo"

    merged["observacion"] = merged.apply(observacion, axis=1)
    merged = merged.drop(columns=["_merge"])
    return merged


def build_indicator_comparison(df_ind_legacy: pd.DataFrame, df_ind_mgn2025: pd.DataFrame) -> pd.DataFrame:
    cols_comparar = [
        "n_titulos_mineros", "area_titulada_suma_ha", "area_titulada_union_ha",
        "pct_area_unidad_titulada_union", "anotaciones_total", "n_titulos_explotacion",
        "n_modalidades_distintas", "n_minerales_distintos",
    ]
    left = df_ind_legacy[["cod_dane_mpio", "nombre_mpio", "nombre_dpto"] + cols_comparar].copy()
    right = df_ind_mgn2025[["cod_dane_mpio"] + cols_comparar].copy()
    merged = left.merge(right, on="cod_dane_mpio", how="outer", suffixes=("_legacy", "_mgn2025"))
    for col in cols_comparar:
        merged[f"diferencia_{col}"] = merged[f"{col}_mgn2025"].fillna(0) - merged[f"{col}_legacy"].fillna(0)
    return merged


# --------------------------------------------------------------------------
# Metadata
# --------------------------------------------------------------------------


def write_output_metadata_mgn2025(
    path: Path, *, tamano_bytes: int, n_filas: int, stats: dict, fuentes: list[str], hash_base_geometrica: str, observaciones: list[str]
) -> None:
    metadata = {
        "fuente": "Fase 4A.2 - regeneración de la integración minera territorial con base geométrica MGN2025",
        "fuentes_integradas": fuentes,
        "base_geometrica": FUENTE_GEOMETRIA_TERRITORIAL_MGN2025,
        "version_geometrica": VERSION_GEOMETRIA_TERRITORIAL_MGN2025,
        "entidad": "DANE (Departamento Administrativo Nacional de Estadística)",
        "crs_entrada": CRS_ORIGEN,
        "crs_calculo": CRS_METRICO,
        "hash_base_geometrica_sha256_combinado": hash_base_geometrica,
        "fecha_procesamiento": utc_now_iso(),
        "n_filas_salida": n_filas,
        "tamano_bytes": tamano_bytes,
        "tolerancia_area_m2": TOLERANCIA_AREA_M2_DEFAULT,
        "fase_productora": "4A.2",
        "estadisticas_interseccion": stats,
        "observaciones": observaciones,
    }
    write_json(path, metadata)


def main() -> int:
    t_start = time.perf_counter()
    print("Fase 4A.2: regeneración de la integración minera territorial con MGN2025")
    print("=" * 70)

    ensure_dir(INTEGRATED_DIR)
    ensure_dir(FEATURES_DIR)
    ensure_dir(AUDIT_DIR)
    ensure_dir(REPORTS_DIR)

    print("\n[B] Verificación previa obligatoria...")
    df_vigente = load_universo_vigente()
    mgn_geoms_4326, source_paths = load_mgn2025_geometries_4326()
    print(f"  DIVIPOLA vigente: {len(df_vigente)} | MGN2025 geometrías: {len(mgn_geoms_4326)}")

    problemas_b = run_pre_flight_validations(df_vigente, mgn_geoms_4326)
    if problemas_b:
        print("ERROR: fallaron validaciones obligatorias de la sección B. Proceso detenido.")
        for p in problemas_b:
            print(f"  - {p}")
        return 1
    print("  OK: 1.122=1.122, correspondencia 100%, únicos, 27493 presente, 94663 ausente, "
          "0 nulas/vacías/inválidas, transformación EPSG:9377 verificada.")

    print("\n[C] Caché espacial (exclusivo MGN2025)...")
    mgn_geoms_proj, uso_cache, tiempo_reproy_unidades = get_or_build_mgn2025_cache(mgn_geoms_4326, source_paths)
    hash_base_geometrica = "|".join(
        f"{name}:{info['sha256'][:16]}" for name, info in sorted(compute_source_fingerprint(source_paths).items())
    )

    print("  Verificando cero solapes territoriales (recalculado, no asumido)...")
    sin_solapes, topo_mgn2025 = check_zero_overlaps(mgn_geoms_proj)
    if not sin_solapes:
        print(f"ERROR: {topo_mgn2025['n_pares_solape']} pares con solape en MGN2025. Proceso detenido.")
        return 1
    print(f"  OK: 0 pares con solape ({topo_mgn2025['area_total_solapes_ha']:.4f} ha de área total de solape).")

    territorial_areas_ha = {cod: geom.area / M2_PER_HA for cod, geom in mgn_geoms_proj}

    print("\n[F] Cargando catastro minero y ejecutando la intersección nacional...")
    df_catastro = load_catastro_spatial_ready()
    title_geoms = [(row["codigo_expediente"], row["_geometry"]) for _, row in df_catastro.iterrows()]
    print(f"  {len(df_catastro)} títulos mineros cargados.")

    def progreso(i: int, n: int) -> None:
        print(f"    procesados {i:,}/{n:,} títulos ({i / n * 100:.1f}%)...", flush=True)

    result = run_national_intersection(
        title_geoms, mgn_geoms_proj, crs_origen=CRS_ORIGEN, crs_metrico=CRS_METRICO,
        progress_every=PROGRESS_EVERY, on_progress=progreso,
    )
    stats = result.stats
    print(f"  Pares candidatos: {stats.n_pares_candidatos:,} | Intersecciones positivas: {stats.n_intersecciones_area_positiva:,} | "
          f"Contactos sin área: {stats.n_contactos_sin_area:,} | Sin asignación: {stats.n_titulos_sin_interseccion:,}")
    print(f"  Tiempo total: {stats.tiempo_total_s} s | Memoria pico: {stats.memoria_pico_mb} MB")

    print("\n[G] Construyendo tabla título-unidad territorial (MGN2025)...")
    df_rel_mgn2025 = build_title_territorial_table(
        result.records, result.title_areas_m2, df_catastro, df_vigente, territorial_areas_ha,
        fuente_geometria_territorial=FUENTE_GEOMETRIA_TERRITORIAL_MGN2025,
        version_geometria_territorial=VERSION_GEOMETRIA_TERRITORIAL_MGN2025,
    )
    print(f"  {len(df_rel_mgn2025)} filas relacionales (título x unidad, área positiva).")

    print("\n[H] Construyendo indicadores territoriales (1.122 unidades, MGN2025)...")
    df_anotaciones = pd.read_csv(ANM_ANOTACIONES_PATH, dtype={"codigo_expediente": str})
    df_anotaciones_agg = aggregate_anm_annotations(df_anotaciones)
    correspondencia_anotaciones = validate_annotation_correspondence(df_catastro, df_anotaciones_agg)

    df_conservacion_mgn2025 = build_area_conservation_table(
        df_rel_mgn2025, result.title_areas_m2, tolerancia_area_m2=TOLERANCIA_AREA_M2_DEFAULT
    )
    df_ind_mgn2025 = build_territorial_indicators_table(
        df_vigente, territorial_areas_ha, df_rel_mgn2025, result.records, df_catastro,
        df_anotaciones_agg, df_conservacion_mgn2025, catastro_minerales_originales=df_catastro["minerales"],
    )
    print(f"  {len(df_ind_mgn2025)} filas de indicadores (debe ser 1122).")
    if len(df_ind_mgn2025) != 1122:
        print("ERROR: la tabla de indicadores MGN2025 no tiene 1122 filas. Proceso detenido.")
        return 1

    print("\n[I] Repitiendo la auditoría de conservación completa (sin reutilizar clasificaciones anteriores)...")
    fuera_tolerancia_mgn2025 = df_conservacion_mgn2025[~df_conservacion_mgn2025["dentro_de_tolerancia"]]
    print(f"  Títulos fuera de tolerancia: {len(fuera_tolerancia_mgn2025)}")

    codigos_fuera = set(fuera_tolerancia_mgn2025["codigo_expediente"])
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    title_geoms_proj_fuera = {
        cod: reproject_geometry(shapely_shape(g), transformer) for cod, g in title_geoms if cod in codigos_fuera
    }
    from shapely.ops import unary_union

    union_inter_por_titulo: dict[str, Any] = {}
    grouped: dict[str, list] = {}
    for rec in result.records:
        if rec.title_id in codigos_fuera and not rec.solo_toca_limite and rec.geometria_interseccion is not None:
            grouped.setdefault(rec.title_id, []).append(rec.geometria_interseccion)
    for cod, geoms_list in grouped.items():
        union_inter_por_titulo[cod] = unary_union(geoms_list)

    title_bbox_4326 = {cod: shapely_shape(g).bounds for cod, g in title_geoms if cod in codigos_fuera}
    all_4326 = [shapely_shape(g) for _, g in mgn_geoms_4326]
    bbox_colombia_4326 = (
        min(g.bounds[0] for g in all_4326), min(g.bounds[1] for g in all_4326),
        max(g.bounds[2] for g in all_4326), max(g.bounds[3] for g in all_4326),
    )
    mgn_ids_proj = [cod for cod, _ in mgn_geoms_proj]
    mgn_full_geoms = [g for _, g in mgn_geoms_proj]
    tree_full_mgn2025 = STRtree(mgn_full_geoms)

    df_audit_conservacion_mgn2025 = build_conservation_audit_table(
        df_conservacion_mgn2025,
        title_geoms_proj=title_geoms_proj_fuera,
        union_intersecciones_por_titulo=union_inter_por_titulo,
        geom_94663_proj=None,
        tree_full=tree_full_mgn2025,
        full_geoms=mgn_full_geoms,
        bbox_colombia_4326=bbox_colombia_4326,
        title_bbox_4326=title_bbox_4326,
        codigos_geometria_original_invalida=set(),
    )
    print("  Distribución de causas (recalculada):", df_audit_conservacion_mgn2025["clasificacion_causa"].value_counts().to_dict() if not df_audit_conservacion_mgn2025.empty else {})

    df_exceptions_mgn2025 = validate_unit_area_indicators(df_ind_mgn2025, df_rel_mgn2025)
    print(f"  Excepciones de validación de área por unidad: {len(df_exceptions_mgn2025)}")

    df_annot_audit_mgn2025 = build_annotation_correspondence_audit(df_catastro, df_anotaciones, df_anotaciones_agg)

    print("\n[Escribiendo salidas MGN2025]...")
    df_rel_mgn2025.to_csv(REL_MGN2025_PATH, index=False, encoding="utf-8")
    rel_size = file_size_bytes(REL_MGN2025_PATH)
    df_ind_mgn2025.to_csv(IND_MGN2025_PATH, index=False, encoding="utf-8")
    ind_size = file_size_bytes(IND_MGN2025_PATH)
    df_audit_conservacion_mgn2025.to_csv(CONS_AUDIT_MGN2025_PATH, index=False, encoding="utf-8")
    cons_audit_size = file_size_bytes(CONS_AUDIT_MGN2025_PATH)
    df_annot_audit_mgn2025.to_csv(ANNOT_AUDIT_MGN2025_PATH, index=False, encoding="utf-8")
    annot_audit_size = file_size_bytes(ANNOT_AUDIT_MGN2025_PATH)

    stats_dict = asdict(stats)
    fuentes_comunes = [
        "data/processed/territorio/base_geometrica_divipola_mgn2025/*.geojson (Fase 3D.2)",
        "data/processed/territorio/universo_territorial_divipola.csv (Fase 3D.1)",
        "data/processed/mineria/catastro_minero_anm_spatial_ready.geojson (Fase 3D.1)",
        "data/processed/mineria/anm_anotaciones_rmn_clean.csv (Fase 3B)",
    ]
    write_output_metadata_mgn2025(
        REL_MGN2025_PATH.with_suffix(REL_MGN2025_PATH.suffix + ".metadata.json"),
        tamano_bytes=rel_size, n_filas=len(df_rel_mgn2025), stats=stats_dict, fuentes=fuentes_comunes,
        hash_base_geometrica=hash_base_geometrica,
        observaciones=["Reemplaza la base geométrica mixta de la Fase 4A por MGN2025 (Fase 3D.2), homogénea."],
    )
    write_output_metadata_mgn2025(
        IND_MGN2025_PATH.with_suffix(IND_MGN2025_PATH.suffix + ".metadata.json"),
        tamano_bytes=ind_size, n_filas=len(df_ind_mgn2025), stats=stats_dict, fuentes=fuentes_comunes,
        hash_base_geometrica=hash_base_geometrica,
        observaciones=["1.122 filas (universo DIVIPOLA vigente completo), incluidas unidades sin títulos."],
    )
    write_output_metadata_mgn2025(
        CONS_AUDIT_MGN2025_PATH.with_suffix(CONS_AUDIT_MGN2025_PATH.suffix + ".metadata.json"),
        tamano_bytes=cons_audit_size, n_filas=len(df_audit_conservacion_mgn2025), stats=stats_dict, fuentes=fuentes_comunes,
        hash_base_geometrica=hash_base_geometrica,
        observaciones=["94663 no se usó como capa de auditoría: MGN2025 no la incluye (no está en DIVIPOLA vigente)."],
    )
    write_output_metadata_mgn2025(
        ANNOT_AUDIT_MGN2025_PATH.with_suffix(ANNOT_AUDIT_MGN2025_PATH.suffix + ".metadata.json"),
        tamano_bytes=annot_audit_size, n_filas=len(df_annot_audit_mgn2025), stats=stats_dict, fuentes=fuentes_comunes,
        hash_base_geometrica=hash_base_geometrica,
        observaciones=["Misma agregación determinística de anotaciones por codigo_expediente; sin fuzzy matching."],
    )

    print("\n[J] Comparando contra la Fase 4A anterior (capa mixta)...")
    df_rel_legacy = pd.read_csv(LEGACY_REL_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    df_ind_legacy = pd.read_csv(LEGACY_IND_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    df_cons_audit_legacy = pd.read_csv(LEGACY_CONS_AUDIT_PATH)

    df_title_comparison = build_title_comparison(df_rel_legacy, df_rel_mgn2025)
    df_title_comparison.to_csv(TITLE_COMPARISON_PATH, index=False, encoding="utf-8")
    df_indicator_comparison = build_indicator_comparison(df_ind_legacy, df_ind_mgn2025)
    df_indicator_comparison.to_csv(INDICATOR_COMPARISON_PATH, index=False, encoding="utf-8")
    print(f"  {TITLE_COMPARISON_PATH.name}: {len(df_title_comparison)} filas")
    print(f"  {INDICATOR_COMPARISON_PATH.name}: {len(df_indicator_comparison)} filas")

    print("\n[M] Promoviendo resultados canónicos (solo si todo lo anterior validó, sin sobrescribir archivos "
          "que otros scripts regeneran)...")
    import shutil

    shutil.copy2(LEGACY_REL_PATH, LEGACY_REL_COPY_PATH)
    shutil.copy2(LEGACY_IND_PATH, LEGACY_IND_COPY_PATH)
    write_json(
        CANONICAL_SOURCE_PATH,
        {
            "fase_productora": "4A.2",
            "fecha": utc_now_iso(),
            "decision": "alias_documentado",
            "canonico_actual": {
                "tabla_relacional": REL_MGN2025_PATH.name,
                "tabla_indicadores": IND_MGN2025_PATH.name,
                "base_geometrica": "data/processed/territorio/base_geometrica_divipola_mgn2025/",
            },
            "historico_preservado_sin_borrar": {
                "tabla_relacional_original": LEGACY_REL_PATH.name,
                "tabla_indicadores_original": LEGACY_IND_PATH.name,
                "copia_legacy_explicita": [LEGACY_REL_COPY_PATH.name, LEGACY_IND_COPY_PATH.name],
            },
            "observaciones": (
                "Se optó por 'alias documentado' (no por sobrescribir el nombre canónico anterior ni por "
                "regenerar el nombre canónico): mineria_titulo_unidad_territorial.csv y "
                "mineria_por_unidad_territorial.csv siguen siendo escritos por scripts/06 (Fase 4A, capa "
                "mixta) y NO se sobrescriben aquí, para no romper la reproducibilidad de ese script. Los "
                "archivos MGN2025 (*_mgn2025.csv) son los resultados canónicos recomendados para todo uso "
                "posterior a la Fase 4A.2; este archivo documenta esa decisión inequívocamente."
            ),
        },
    )
    print(f"  Copias legacy explícitas: {LEGACY_REL_COPY_PATH.name}, {LEGACY_IND_COPY_PATH.name}")
    print(f"  Alias documentado escrito: {CANONICAL_SOURCE_PATH.name}")

    tiempo_total = time.perf_counter() - t_start

    resultados_finales = {
        "stats": stats,
        "uso_cache": uso_cache,
        "tiempo_reproy_unidades": tiempo_reproy_unidades,
        "topo_mgn2025": topo_mgn2025,
        "df_conservacion_mgn2025": df_conservacion_mgn2025,
        "df_audit_conservacion_mgn2025": df_audit_conservacion_mgn2025,
        "df_cons_audit_legacy": df_cons_audit_legacy,
        "correspondencia_anotaciones": correspondencia_anotaciones,
        "df_exceptions_mgn2025": df_exceptions_mgn2025,
        "df_title_comparison": df_title_comparison,
        "df_indicator_comparison": df_indicator_comparison,
        "rel_size": rel_size, "ind_size": ind_size,
        "n_rel_legacy": len(df_rel_legacy), "n_rel_mgn2025": len(df_rel_mgn2025),
        "tiempo_total_s": tiempo_total,
    }
    import pickle
    with open(DATA_INTERIM / "fase4a2_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 4A.2")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s | Memoria pico intersección: {stats.memoria_pico_mb} MB")
    print(f"Pares candidatos: {stats.n_pares_candidatos:,} | Intersecciones positivas: {stats.n_intersecciones_area_positiva:,}")
    print(f"Filas relacionales: legacy={len(df_rel_legacy)} vs mgn2025={len(df_rel_mgn2025)}")
    print(f"Títulos sin asignación: legacy={int(df_cons_audit_legacy['sin_interseccion_territorial'].sum())} vs "
          f"mgn2025={int(df_conservacion_mgn2025['sin_interseccion_territorial'].sum())}")
    print(f"Fuera de tolerancia: legacy={len(df_cons_audit_legacy)} (mineria_area_conservation_audit.csv ya "
          f"filtrado a fuera-de-tolerancia) vs mgn2025={(~df_conservacion_mgn2025['dentro_de_tolerancia']).sum()}")
    print("Resultados intermedios guardados en data/interim/fase4a2_resultados.pkl para reportes/docs/09.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
