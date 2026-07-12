"""Fase 4B: integración de observaciones de calidad hídrica por unidad
territorial DIVIPOLA, usando exclusivamente la base geométrica nacional
homogénea DANE MGN2025.

Asigna espacialmente las observaciones históricas de calidad del agua del
IDEAM a las 1.122 unidades territoriales DIVIPOLA vigentes y genera
indicadores DESCRIPTIVOS de cobertura, monitoreo y resultados observados por
parámetro.

Esta fase NO afirma contaminación, NO atribuye resultados a minería, NO
construye índice de riesgo, NO entrena modelo, NO integra deforestación, NO
integra áreas protegidas, NO crea dashboard, NO descarga fuentes nuevas y NO
modifica datos crudos.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from shapely.geometry import shape as shapely_shape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.features.water import (  # noqa: E402
    PRECISION_REDONDEO_COORDENADAS,
    UMBRAL_PARAMETRO_MIN_MUNICIPIOS,
    UMBRAL_PARAMETRO_MIN_OBSERVACIONES,
    build_parameter_catalog,
    build_site_ids,
    build_site_parameter_year_table,
    build_territorial_water_indicators,
    build_trends_table,
    parse_censored_results,
    summarize_censoring,
)
from aquabosque.geo.intersection import build_transformer, reproject_geometry  # noqa: E402
from aquabosque.geo.point_assignment import (  # noqa: E402
    UMBRAL_PROXIMIDAD_M_DEFAULT,
    assign_point,
    build_territorial_point_index,
)
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402
from aquabosque.utils.spatial_cache import load_cache_if_valid  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "water_integration"
SPATIAL_CACHE_DIR = DATA_INTERIM / "spatial_cache"

BASE_GEOM_DIR = DATA_PROCESSED / "territorio" / "base_geometrica_divipola_mgn2025"
BASE_GEOM_MANIFEST = BASE_GEOM_DIR / "manifest.json"
UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
AGUA_CLEAN_PATH = DATA_PROCESSED / "agua" / "ideam_calidad_agua_clean.csv"

REFERENCE_DIR = DATA_PROCESSED / "reference"
INTEGRATED_DIR = DATA_PROCESSED / "integrated"
FEATURES_DIR = DATA_PROCESSED / "features"
AUDIT_DIR = DATA_PROCESSED / "audit"

CATALOGO_PATH = REFERENCE_DIR / "catalogo_parametros_calidad_agua.csv"
GEOREF_PATH = INTEGRATED_DIR / "calidad_agua_observaciones_georreferenciadas.csv"
SITE_PARAM_YEAR_PATH = INTEGRATED_DIR / "calidad_agua_sitio_parametro_anio.csv"
IND_TERRITORIAL_PATH = FEATURES_DIR / "calidad_agua_por_unidad_territorial.csv"
TENDENCIAS_PATH = FEATURES_DIR / "calidad_agua_tendencias_territoriales.csv"
AUDIT_ASIGNACION_PATH = AUDIT_DIR / "calidad_agua_asignacion_territorial_audit.csv"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
N_REGISTROS_ESPERADOS = 134216
FECHA_DESCARGA_IDEAM = "2026-07-11T23:38:11+00:00"
FUENTE_IDEAM = "IDEAM - Data Histórica de Calidad de Agua (datos.gov.co, recurso 62gv-3857)"


# --------------------------------------------------------------------------
# A. Carga
# --------------------------------------------------------------------------


def load_universo_vigente() -> pd.DataFrame:
    df = pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    return df[df["presente_divipola_vigente"]].reset_index(drop=True)


def load_mgn2025_geometries_4326() -> list[tuple[str, dict]]:
    with open(BASE_GEOM_MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)
    geoms: list[tuple[str, dict]] = []
    for a in manifest["archivos_y_tamanos"]:
        with open(BASE_GEOM_DIR / a["archivo"], encoding="utf-8") as fh:
            fc = json.load(fh)
        for feat in fc["features"]:
            geoms.append((feat["properties"]["cod_dane_mpio"], feat["geometry"]))
    return geoms


def get_mgn2025_cache_or_reproject(mgn_geoms_4326: list[tuple[str, dict]]) -> list[tuple[str, Any]]:
    with open(BASE_GEOM_MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)
    source_paths = [BASE_GEOM_DIR / a["archivo"] for a in manifest["archivos_y_tamanos"]]
    cached = load_cache_if_valid(
        SPATIAL_CACHE_DIR, cache_name="territorial_units_mgn2025_epsg9377", source_paths=source_paths, crs=CRS_METRICO
    )
    if cached is not None:
        return cached
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    return [(cod, reproject_geometry(shapely_shape(g), transformer)) for cod, g in mgn_geoms_4326]


# --------------------------------------------------------------------------
# C. Verificación inicial
# --------------------------------------------------------------------------


def run_pre_flight_validations(df_agua: pd.DataFrame, df_vigente: pd.DataFrame, mgn_geoms_4326: list[tuple[str, dict]]) -> list[str]:
    problemas = []
    if len(df_agua) != N_REGISTROS_ESPERADOS:
        problemas.append(f"{len(df_agua)} registros, se esperaban {N_REGISTROS_ESPERADOS}")
    for col in ("latitud", "longitud"):
        if not pd.api.types.is_numeric_dtype(df_agua[col]):
            problemas.append(f"{col} no es numérica")
    if df_agua["fecha"].isna().any():
        problemas.append("fechas nulas presentes")
    if df_agua["anio"].isna().any():
        problemas.append("años nulos presentes")
    if df_agua["propiedad_observada"].isna().any():
        problemas.append("propiedad_observada con nulos")
    if df_agua["unidad_del_resultado"].isna().any():
        problemas.append("unidad_del_resultado con nulos")
    if "resultado" not in df_agua.columns or "resultado_numerico" not in df_agua.columns:
        problemas.append("faltan columnas resultado/resultado_numerico")
    if not pd.api.types.is_string_dtype(df_agua["departamento"]) and not pd.api.types.is_object_dtype(df_agua["departamento"]):
        problemas.append("departamento no es texto")
    if "codigo_subzona_hidrografica" not in df_agua.columns:
        problemas.append("falta codigo_subzona_hidrografica")

    if len(df_vigente) != 1122:
        problemas.append(f"universo DIVIPOLA vigente tiene {len(df_vigente)} filas, se esperaban 1122")
    if df_vigente["cod_dane_mpio"].duplicated().any():
        problemas.append("códigos duplicados en el universo DIVIPOLA vigente")
    if len(mgn_geoms_4326) != 1122:
        problemas.append(f"MGN2025 tiene {len(mgn_geoms_4326)} geometrías, se esperaban 1122")
    n_invalidas = sum(1 for _, g in mgn_geoms_4326 if not shapely_shape(g).is_valid)
    if n_invalidas:
        problemas.append(f"{n_invalidas} geometrías MGN2025 inválidas")

    return problemas


# --------------------------------------------------------------------------
# G. Asignación espacial (por sitio único, no por fila — 243 sitios)
# --------------------------------------------------------------------------


def assign_sites(
    df_sites: pd.DataFrame, index, lookup_texto: dict[tuple[str, str], str], umbral_proximidad_m: float
) -> pd.DataFrame:
    """`df_sites`: una fila por `sitio_monitoreo_id` único (lat/lon/municipio_norm/departamento_norm)."""
    filas = []
    for _, row in df_sites.iterrows():
        codigo_esperado = lookup_texto.get((row["departamento_norm"], row["municipio_norm"]))
        resultado = assign_point(
            row["longitud"], row["latitud"], index,
            codigo_esperado_por_texto=codigo_esperado, umbral_proximidad_m=umbral_proximidad_m,
        )
        filas.append(
            {
                "sitio_monitoreo_id": row["sitio_monitoreo_id"],
                "latitud": row["latitud"],
                "longitud": row["longitud"],
                "cod_dane_mpio_asignado": resultado.cod_dane_mpio_asignado,
                "metodo_asignacion": resultado.metodo_asignacion,
                "asignacion_ambigua": resultado.asignacion_ambigua,
                "n_unidades_candidatas": resultado.n_unidades_candidatas,
                "distancia_unidad_mas_cercana_m": resultado.distancia_unidad_mas_cercana_m,
                "codigos_candidatos": ";".join(resultado.codigos_candidatos),
                "calidad_asignacion": resultado.calidad_asignacion,
            }
        )
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------
# H. Validaciones geográficas / sospechas de coordenadas
# --------------------------------------------------------------------------


def detect_coordinate_anomalies(df_sites: pd.DataFrame, bbox_colombia_4326: tuple[float, float, float, float]) -> dict[str, Any]:
    minx, miny, maxx, maxy = bbox_colombia_4326
    fuera_bbox = df_sites[(df_sites["longitud"] < minx) | (df_sites["longitud"] > maxx) | (df_sites["latitud"] < miny) | (df_sites["latitud"] > maxy)]
    lon_positiva = df_sites[df_sites["longitud"] > 0]
    lat_lon_cero = df_sites[(df_sites["latitud"] == 0) & (df_sites["longitud"] == 0)]
    dup_coords = df_sites[df_sites.duplicated(subset=["latitud", "longitud"], keep=False)]
    # Firma de un intercambio lat/lon: la longitud registrada cae en un rango
    # típico de LATITUD (numero pequeno) y la latitud registrada cae en un
    # rango típico de LONGITUD (numero grande negativo) — independiente del
    # bbox ajustado a MGN2025, para no repetir el mismo chequeo dos veces.
    posible_intercambio = df_sites[df_sites["longitud"].between(-15, 15) & df_sites["latitud"].between(-85, -60)]
    return {
        "n_sitios": len(df_sites),
        "n_fuera_bbox_colombia": len(fuera_bbox),
        "sitios_fuera_bbox": fuera_bbox["sitio_monitoreo_id"].tolist(),
        "n_longitud_positiva": len(lon_positiva),
        "n_lat_lon_cero": len(lat_lon_cero),
        "n_coordenadas_duplicadas_entre_sitios": len(dup_coords),
        "n_posible_intercambio_lat_lon": len(posible_intercambio),
    }


# --------------------------------------------------------------------------
# K. Evaluación de candidatos a indicadores por parámetro específico
# --------------------------------------------------------------------------

CANDIDATOS_PARAMETRO_K = [
    "PH", "OXIGENO DISUELTO OD", "CONDUCTIVIDAD ELECTRICA", "TURBIDEZ",
    "DEMANDA BIOQUIMICA DE OXIGENO DBO5", "DEMANDA QUIMICA DE OXIGENO DQO",
    "SOLIDOS SUSPENDIDOS TOTALES", "COLIFORMES TOTALES POR SUSTRATO DEFINIDO",
    "ESCHERICHIA COLI POR SUSTRATO DEFINIDO", "MERCURIO TOTAL EN AGUA",
    "ARSENICO TOTAL EN AGUA", "PLOMO TOTAL EN AGUA", "CADMIO TOTAL EN AGUA",
]


def evaluate_parameter_candidates(catalogo: pd.DataFrame, df_assigned: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for nombre in CANDIDATOS_PARAMETRO_K:
        filas_catalogo = catalogo[catalogo["propiedad_observada_norm"] == nombre]
        if filas_catalogo.empty:
            filas.append(
                {
                    "nombre_original": nombre, "nombre_normalizado": nombre, "unidades_observadas": "",
                    "n_observaciones_total": 0, "n_municipios_con_dato": 0, "pct_censurado": None,
                    "anio_min": None, "anio_max": None, "idoneo_para_agregacion": False,
                    "razon": "no está presente en la fuente de datos (0 observaciones en todo el dataset)",
                }
            )
            continue

        unidades = sorted(filas_catalogo["unidad_norm"].unique())
        obs = df_assigned[(df_assigned["propiedad_observada_norm"] == nombre) & (df_assigned["cod_dane_mpio_asignado"].notna())]
        n_obs = len(obs)
        n_mpios = obs["cod_dane_mpio_asignado"].nunique()
        n_cens = int((obs["resultado_es_censurado_inferior"] | obs["resultado_es_censurado_superior"]).sum())
        pct_cens = round(n_cens / n_obs * 100, 2) if n_obs else None

        razones = []
        if len(unidades) > 1:
            razones.append(f"{len(unidades)} unidades distintas observadas ({unidades}): no se agregan sin regla de conversión explícita")
        if n_obs < UMBRAL_PARAMETRO_MIN_OBSERVACIONES:
            razones.append(f"{n_obs} observaciones asignadas (< {UMBRAL_PARAMETRO_MIN_OBSERVACIONES})")
        if n_mpios < UMBRAL_PARAMETRO_MIN_MUNICIPIOS:
            razones.append(f"{n_mpios} municipios con dato (< {UMBRAL_PARAMETRO_MIN_MUNICIPIOS})")

        idoneo = len(razones) == 0
        filas.append(
            {
                "nombre_original": filas_catalogo["propiedad_observada_original"].iloc[0],
                "nombre_normalizado": nombre,
                "unidades_observadas": "; ".join(unidades),
                "n_observaciones_total": n_obs,
                "n_municipios_con_dato": n_mpios,
                "pct_censurado": pct_cens,
                "anio_min": int(obs["anio"].min()) if n_obs else None,
                "anio_max": int(obs["anio"].max()) if n_obs else None,
                "idoneo_para_agregacion": idoneo,
                "razon": "cumple todos los criterios documentados" if idoneo else "; ".join(razones),
            }
        )
    return pd.DataFrame(filas)


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 4B: integración de calidad hídrica por unidad territorial (MGN2025)")
    print("=" * 70)

    for d in (REFERENCE_DIR, INTEGRATED_DIR, FEATURES_DIR, AUDIT_DIR, REPORTS_DIR):
        ensure_dir(d)

    print("\n[C] Verificación inicial...")
    df_agua_raw = pd.read_csv(AGUA_CLEAN_PATH, low_memory=False)
    df_vigente = load_universo_vigente()
    mgn_geoms_4326 = load_mgn2025_geometries_4326()
    print(f"  {len(df_agua_raw)} registros | {len(df_vigente)} unidades vigentes | {len(mgn_geoms_4326)} geometrías MGN2025")

    problemas = run_pre_flight_validations(df_agua_raw, df_vigente, mgn_geoms_4326)
    if problemas:
        print("ERROR: fallaron validaciones obligatorias. Proceso detenido.")
        for p in problemas:
            print(f"  - {p}")
        return 1
    print("  OK: todas las validaciones de la sección C pasaron.")

    print("\n[D/E/F] Catálogo de parámetros, censura, identificación de sitios...")
    df_parsed = parse_censored_results(df_agua_raw)
    censura = summarize_censoring(df_parsed)
    print(f"  Censura: {censura}")
    df_parsed = build_site_ids(df_parsed)
    df_parsed["unidad_norm"] = df_parsed["unidad_del_resultado"].str.strip()
    from aquabosque.features.water import normalize_unit_text

    df_parsed["unidad_norm"] = df_parsed["unidad_del_resultado"].map(normalize_unit_text)
    n_sitios = df_parsed["sitio_monitoreo_id"].nunique()
    print(f"  Sitios de monitoreo identificados: {n_sitios}")

    catalogo = build_parameter_catalog(df_parsed)
    catalogo.to_csv(CATALOGO_PATH, index=False, encoding="utf-8")
    print(f"  {CATALOGO_PATH.name}: {len(catalogo)} filas (combinaciones propiedad+unidad)")

    print("\n[G] Asignación espacial punto-territorio (STRtree, una sola construcción)...")
    mgn_geoms_proj = get_mgn2025_cache_or_reproject(mgn_geoms_4326)
    mgn_geoms_4326_shapely = [(cod, shapely_shape(g)) for cod, g in mgn_geoms_4326]
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    index = build_territorial_point_index(mgn_geoms_4326_shapely, mgn_geoms_proj, transformer)

    lookup_texto = {
        (row["nombre_dpto_norm"], row["nombre_mpio_norm"]): row["cod_dane_mpio"] for _, row in df_vigente.iterrows()
    }

    df_sites_unicos = df_parsed[["sitio_monitoreo_id", "latitud", "longitud", "municipio_norm", "departamento_norm"]].drop_duplicates(subset=["sitio_monitoreo_id"])
    t_asig0 = time.perf_counter()
    df_asignacion_sitios = assign_sites(df_sites_unicos, index, lookup_texto, UMBRAL_PROXIMIDAD_M_DEFAULT)
    t_asig = time.perf_counter() - t_asig0
    print(f"  {len(df_asignacion_sitios)} sitios asignados en {t_asig:.4f} s")
    print("  Métodos de asignación:", df_asignacion_sitios["metodo_asignacion"].value_counts().to_dict())

    df_assigned = df_parsed.merge(
        df_asignacion_sitios.drop(columns=["latitud", "longitud"]), on="sitio_monitoreo_id", how="left"
    )

    universo_idx = df_vigente.set_index("cod_dane_mpio")
    df_assigned["cod_dane_dpto_asignado"] = df_assigned["cod_dane_mpio_asignado"].map(universo_idx["cod_dane_dpto"])
    nombre_mpio_espacial = df_assigned["cod_dane_mpio_asignado"].map(universo_idx["nombre_mpio_norm"])
    nombre_dpto_espacial = df_assigned["cod_dane_mpio_asignado"].map(universo_idx["nombre_dpto_norm"])
    df_assigned["coincide_municipio_texto"] = np.where(
        df_assigned["cod_dane_mpio_asignado"].isna(), None, nombre_mpio_espacial == df_assigned["municipio_norm"]
    )
    df_assigned["coincide_departamento_texto"] = np.where(
        df_assigned["cod_dane_mpio_asignado"].isna(), None, nombre_dpto_espacial == df_assigned["departamento_norm"]
    )

    print("\n[H] Validaciones geográficas...")
    all_4326 = [shapely_shape(g) for _, g in mgn_geoms_4326]
    bbox_colombia = (
        min(g.bounds[0] for g in all_4326), min(g.bounds[1] for g in all_4326),
        max(g.bounds[2] for g in all_4326), max(g.bounds[3] for g in all_4326),
    )
    anomalias = detect_coordinate_anomalies(df_sites_unicos, bbox_colombia)
    print(f"  Anomalías de coordenadas: {anomalias}")

    n_directo = int((df_assigned["metodo_asignacion"] == "covers_directo").sum())
    n_desamb = int((df_assigned["metodo_asignacion"] == "covers_desambiguado_texto").sum())
    n_proximidad = int((df_assigned["metodo_asignacion"] == "proximidad_menor_100m").sum())
    n_ambigua = int((df_assigned["metodo_asignacion"] == "ambigua").sum())
    n_sin_asignacion = int((df_assigned["metodo_asignacion"] == "sin_asignacion").sum())
    print(f"  Directas: {n_directo} | Desambiguadas por texto: {n_desamb} | Por proximidad: {n_proximidad} | "
          f"Ambiguas: {n_ambigua} | Sin asignación: {n_sin_asignacion}")

    print("\n[Escribiendo observaciones georreferenciadas]...")
    df_assigned.to_csv(GEOREF_PATH, index=False, encoding="utf-8")
    georef_size = file_size_bytes(GEOREF_PATH)
    print(f"  {GEOREF_PATH.name}: {len(df_assigned)} filas, {format_bytes(georef_size)}")

    print("\n[I] Tabla sitio-parámetro-año...")
    df_site_param_year = build_site_parameter_year_table(df_assigned)
    df_site_param_year.to_csv(SITE_PARAM_YEAR_PATH, index=False, encoding="utf-8")
    print(f"  {SITE_PARAM_YEAR_PATH.name}: {len(df_site_param_year)} filas")

    print("\n[N] Auditoría de asignación territorial (texto vs. geometría)...")
    mask_auditar = (
        (df_assigned["coincide_municipio_texto"] == False)  # noqa: E712
        | (df_assigned["coincide_departamento_texto"] == False)  # noqa: E712
        | df_assigned["asignacion_ambigua"]
        | (df_assigned["metodo_asignacion"] == "proximidad_menor_100m")
        | (df_assigned["metodo_asignacion"] == "sin_asignacion")
    )
    cols_auditoria = [
        "sitio_monitoreo_id", "nombre_del_punto_de_monitoreo", "latitud", "longitud",
        "municipio_norm", "departamento_norm", "cod_dane_mpio_asignado", "cod_dane_dpto_asignado",
        "metodo_asignacion", "asignacion_ambigua", "n_unidades_candidatas", "codigos_candidatos",
        "distancia_unidad_mas_cercana_m", "coincide_municipio_texto", "coincide_departamento_texto",
    ]
    df_audit_asignacion = df_assigned.loc[mask_auditar, cols_auditoria].drop_duplicates(subset=["sitio_monitoreo_id"])
    df_audit_asignacion.to_csv(AUDIT_ASIGNACION_PATH, index=False, encoding="utf-8")
    print(f"  {AUDIT_ASIGNACION_PATH.name}: {len(df_audit_asignacion)} filas (sitios distintos con algo que auditar)")

    print("\n[J/M] Indicadores territoriales (1.122 unidades)...")
    df_ind_territorial = build_territorial_water_indicators(df_vigente, df_assigned, df_audit_asignacion, catalogo)
    if len(df_ind_territorial) != 1122:
        print(f"ERROR: la tabla de indicadores tiene {len(df_ind_territorial)} filas, se esperaban 1122. Proceso detenido.")
        return 1
    df_ind_territorial.to_csv(IND_TERRITORIAL_PATH, index=False, encoding="utf-8")
    print(f"  {IND_TERRITORIAL_PATH.name}: {len(df_ind_territorial)} filas")
    print(f"  Unidades con monitoreo: {int(df_ind_territorial['tiene_monitoreo_agua'].sum())} / 1122")

    print("\n[K] Evaluación de parámetros candidatos a indicadores específicos...")
    df_candidatos = evaluate_parameter_candidates(catalogo, df_assigned)
    print(df_candidatos[["nombre_normalizado", "n_observaciones_total", "n_municipios_con_dato", "idoneo_para_agregacion"]].to_string())

    print("\n[L] Tendencias temporales...")
    df_tendencias = build_trends_table(df_assigned)
    df_tendencias.to_csv(TENDENCIAS_PATH, index=False, encoding="utf-8")
    n_calculables = int(df_tendencias["tendencia_calculable"].sum())
    print(f"  {TENDENCIAS_PATH.name}: {len(df_tendencias)} combinaciones unidad+parámetro, {n_calculables} con tendencia calculable")

    print("\n[O] Escribiendo metadata...")
    fuentes_comunes = [
        f"{FUENTE_IDEAM}, descargado {FECHA_DESCARGA_IDEAM}",
        "data/processed/territorio/base_geometrica_divipola_mgn2025/*.geojson (Fase 3D.2)",
        "data/processed/territorio/universo_territorial_divipola.csv (Fase 3D.1)",
    ]

    def escribir_metadata(path: Path, *, n_filas: int, tamano_bytes: int, descripcion: str, extra: dict | None = None) -> None:
        meta = {
            "fuente": "Fase 4B - integración hídrica territorial",
            "fuentes_integradas": fuentes_comunes,
            "base_geometrica": "DANE Marco Geoestadístico Nacional 2025 (MGN2025)",
            "crs_entrada": CRS_ORIGEN,
            "crs_calculo": CRS_METRICO,
            "rango_temporal_fuente": [int(df_agua_raw["anio"].min()), int(df_agua_raw["anio"].max())],
            "regla_asignacion_espacial": "covers() como regla principal; proximidad si no hay cobertura directa",
            "umbral_proximidad_m": UMBRAL_PROXIMIDAD_M_DEFAULT,
            "tratamiento_censura": "valores <X y >X conservados como texto original; limite_deteccion y operador_resultado documentados; NO se reemplazan por 0 ni por X/2 en las columnas oficiales",
            "total_registros": len(df_agua_raw),
            "registros_asignados_directo": n_directo,
            "registros_asignados_desambiguados_texto": n_desamb,
            "registros_asignados_proximidad": n_proximidad,
            "registros_ambiguos": n_ambigua,
            "registros_sin_asignacion": n_sin_asignacion,
            "n_parametros": int(catalogo["propiedad_observada_norm"].nunique()),
            "n_combinaciones_parametro_unidad": len(catalogo),
            "fecha_procesamiento": utc_now_iso(),
            "n_filas_salida": n_filas,
            "tamano_bytes": tamano_bytes,
            "descripcion": descripcion,
            "limitaciones": [
                "No se afirma contaminación ni se atribuye causalidad a minería.",
                "No se aplican límites legales/normativos.",
                "La ausencia de monitoreo no implica buena calidad del agua (ver banderas sin_monitoreo/monitoreo_escaso/monitoreo_desactualizado/cobertura_temporal_limitada).",
            ],
        }
        if extra:
            meta.update(extra)
        write_json(path.with_suffix(path.suffix + ".metadata.json"), meta)

    escribir_metadata(GEOREF_PATH, n_filas=len(df_assigned), tamano_bytes=georef_size, descripcion="Una fila por observación original, sin agregación.")
    escribir_metadata(SITE_PARAM_YEAR_PATH, n_filas=len(df_site_param_year), tamano_bytes=file_size_bytes(SITE_PARAM_YEAR_PATH), descripcion="Una fila por sitio+parámetro+unidad+año.")
    escribir_metadata(IND_TERRITORIAL_PATH, n_filas=len(df_ind_territorial), tamano_bytes=file_size_bytes(IND_TERRITORIAL_PATH), descripcion="1.122 filas, indicadores de disponibilidad/intensidad de monitoreo, no de condición ambiental.")
    escribir_metadata(TENDENCIAS_PATH, n_filas=len(df_tendencias), tamano_bytes=file_size_bytes(TENDENCIAS_PATH), descripcion="Pendiente Theil-Sen solo cuando hay evidencia suficiente (>=5 años, >=10 obs, periodo >=4 años).")
    escribir_metadata(CATALOGO_PATH, n_filas=len(catalogo), tamano_bytes=file_size_bytes(CATALOGO_PATH), descripcion="Una fila por combinación propiedad_observada_norm + unidad_norm observada.")
    escribir_metadata(AUDIT_ASIGNACION_PATH, n_filas=len(df_audit_asignacion), tamano_bytes=file_size_bytes(AUDIT_ASIGNACION_PATH), descripcion="Sitios con discrepancia texto/geometría, asignación ambigua, por proximidad o sin asignar.")

    tiempo_total = time.perf_counter() - t0

    resultados_finales = {
        "censura": censura,
        "n_sitios": n_sitios,
        "df_asignacion_sitios": df_asignacion_sitios,
        "anomalias": anomalias,
        "n_directo": n_directo, "n_desamb": n_desamb, "n_proximidad": n_proximidad,
        "n_ambigua": n_ambigua, "n_sin_asignacion": n_sin_asignacion,
        "catalogo": catalogo,
        "df_candidatos": df_candidatos,
        "df_ind_territorial": df_ind_territorial,
        "df_tendencias": df_tendencias,
        "df_audit_asignacion": df_audit_asignacion,
        "georef_size": georef_size,
        "n_registros_total": len(df_agua_raw),
        "anio_min": int(df_agua_raw["anio"].min()), "anio_max": int(df_agua_raw["anio"].max()),
        "tiempo_total_s": tiempo_total,
        "tiempo_asignacion_s": t_asig,
    }
    import pickle
    with open(DATA_INTERIM / "fase4b_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 4B")
    print("=" * 70)
    print(f"Registros procesados: {len(df_agua_raw)}")
    print(f"Sitios de monitoreo: {n_sitios}")
    print(f"Periodo: {df_agua_raw['anio'].min()}-{df_agua_raw['anio'].max()}")
    print(f"Parámetros: {catalogo['propiedad_observada_norm'].nunique()} | combinaciones parámetro+unidad: {len(catalogo)}")
    print(f"Numéricos: {censura['n_numericos']} | censurados inferior: {censura['n_censurados_inferior']} | censurados superior: {censura['n_censurados_superior']}")
    print(f"Asignación: directa={n_directo}, desambiguada={n_desamb}, proximidad={n_proximidad}, ambigua={n_ambigua}, sin_asignar={n_sin_asignacion}")
    print(f"Unidades con monitoreo: {int(df_ind_territorial['tiene_monitoreo_agua'].sum())}/1122")
    print(f"Parámetros aprobados para indicadores específicos: {int(df_candidatos['idoneo_para_agregacion'].sum())}/{len(df_candidatos)}")
    print(f"Tendencias calculables: {n_calculables}/{len(df_tendencias)}")
    print(f"Tiempo total: {tiempo_total:.2f} s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
