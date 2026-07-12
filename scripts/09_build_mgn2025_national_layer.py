"""Fase 3D.2, secciones C-J: base geométrica nacional homogénea DANE MGN2025.

Compara la capa nacional MGN2025 (descargada en `08_download_mgn2025_national.py`)
contra DIVIPOLA vigente, perfila sus geometrías, audita su topología nacional
(¿desaparece el solape de ~128.926 ha de la zona de Bajirá encontrado en la
Fase 4A.1 al mezclar versiones?), construye la nueva capa analítica de una
sola fuente homogénea, un caché espacial propio y repite la prueba STRtree de
los mismos 40 títulos de la Fase 3D.1 contra la nueva base.

No integra calidad hídrica. No recalcula indicadores mineros nacionales
completos (solo la prueba de 40 títulos, sección J). No construye dataset
maestro. No entrena modelos. No crea dashboard. No borra ni sobrescribe
`limites_municipales_dane` ni `dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from shapely.geometry import shape as shapely_shape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.data.clean import clean_mgn2025_municipios, dataframe_to_geojson, json_safe_default  # noqa: E402
from aquabosque.data.profile import describe_geometries_detailed  # noqa: E402
from aquabosque.features.mining_audit import audit_territorial_topology  # noqa: E402
from aquabosque.geo.intersection import build_transformer, reproject_geometry, run_national_intersection  # noqa: E402
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402
from aquabosque.utils.spatial_cache import save_cache  # noqa: E402

DATA_RAW = PROJECT_ROOT / "data" / "raw" / "territorio" / "mgn2025_unidades_territoriales_dane"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
AUDIT_DIR = DATA_PROCESSED / "audit"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "territorial_geometry"
SPATIAL_CACHE_DIR = DATA_INTERIM / "spatial_cache"

BASE_GEOM_DIR = DATA_PROCESSED / "territorio" / "base_geometrica_divipola_mgn2025"
BASE_GEOM_MANIFEST = BASE_GEOM_DIR / "manifest.json"
UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
FUERA_DIVIPOLA_AUDIT_PATH = AUDIT_DIR / "mgn2025_codigos_fuera_divipola.csv"
CATASTRO_SPATIAL_READY_PATH = DATA_PROCESSED / "mineria" / "catastro_minero_anm_spatial_ready.geojson"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
CODIGO_BAJIRA = "27493"
CODIGO_MAPIRIPANA = "94663"
ZONA_BAJIRA_VECINOS = ["27493", "27615", "05480", "05837", "27150", "05234"]
MAX_BYTES_PER_PART = 20 * 1024 * 1024
SOLAPE_BAJIRA_FASE4A1_HA = 128926.00121382295  # hallazgo de referencia de la Fase 4A.1


def load_raw_features() -> list[dict]:
    feats: list[dict] = []
    for p in sorted(DATA_RAW.glob("mgn2025_municipio_part_*.geojson")):
        with open(p, encoding="utf-8") as fh:
            fc = json.load(fh)
        feats.extend(fc["features"])
    return feats


def load_universo_vigente() -> pd.DataFrame:
    df = pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    return df[df["presente_divipola_vigente"]].reset_index(drop=True)


# --------------------------------------------------------------------------
# C. Comparación con DIVIPOLA vigente
# --------------------------------------------------------------------------


def compare_with_divipola(df_mgn: pd.DataFrame, df_vigente: pd.DataFrame) -> dict[str, Any]:
    mgn_codes = set(df_mgn["cod_dane_mpio"])
    divipola_codes = set(df_vigente["cod_dane_mpio"])

    en_ambas = mgn_codes & divipola_codes
    solo_mgn = sorted(mgn_codes - divipola_codes)
    solo_divipola = sorted(divipola_codes - mgn_codes)
    n_dup_mgn = int(df_mgn["cod_dane_mpio"].duplicated().sum())

    mgn_idx = df_mgn.set_index("cod_dane_mpio")
    div_idx = df_vigente.set_index("cod_dane_mpio")

    disc_nombre = []
    disc_dpto = []
    disc_tipo = []
    for cod in sorted(en_ambas):
        mgn_row = mgn_idx.loc[cod]
        div_row = div_idx.loc[cod]
        if mgn_row["nombre_mpio_norm"] != div_row["nombre_mpio_norm"]:
            disc_nombre.append({"cod_dane_mpio": cod, "divipola": div_row["nombre_mpio_norm"], "mgn2025": mgn_row["nombre_mpio_norm"]})
        if mgn_row["cod_dane_dpto"] != div_row["cod_dane_dpto"]:
            disc_dpto.append({"cod_dane_mpio": cod, "divipola": div_row["cod_dane_dpto"], "mgn2025": mgn_row["cod_dane_dpto"]})

    tipo_map = {"MUNICIPIO": "Municipio", "ÁREA NO MUNICIPALIZADA": "Área no municipalizada", "ISLA": "Isla"}
    for cod in sorted(en_ambas):
        mgn_tipo_mapeado = tipo_map.get(mgn_idx.loc[cod]["mpio_tipo"], mgn_idx.loc[cod]["mpio_tipo"])
        div_tipo = div_idx.loc[cod]["tipo_unidad_territorial"]
        if mgn_tipo_mapeado != div_tipo:
            disc_tipo.append({"cod_dane_mpio": cod, "divipola": div_tipo, "mgn2025_mapeado": mgn_tipo_mapeado, "mgn2025_original": mgn_idx.loc[cod]["mpio_tipo"]})

    normalizacion_5_ok = bool((df_mgn["cod_dane_mpio"].str.len() == 5).all())
    normalizacion_2_ok = bool((df_mgn["cod_dane_dpto"].str.len() == 2).all())

    return {
        "n_mgn": len(mgn_codes),
        "n_divipola_vigente": len(divipola_codes),
        "n_en_ambas": len(en_ambas),
        "solo_mgn2025": solo_mgn,
        "solo_divipola_vigente": solo_divipola,
        "n_duplicados_mgn2025": n_dup_mgn,
        "discrepancias_nombre": disc_nombre,
        "discrepancias_departamento": disc_dpto,
        "discrepancias_tipo_unidad": disc_tipo,
        "presente_27493": CODIGO_BAJIRA in mgn_codes,
        "presente_94663": CODIGO_MAPIRIPANA in mgn_codes,
        "normalizacion_cod_mpio_5_digitos_ok": normalizacion_5_ok,
        "normalizacion_cod_dpto_2_digitos_ok": normalizacion_2_ok,
    }


def validar_o_detener(comparacion: dict[str, Any]) -> list[str]:
    problemas = []
    if comparacion["solo_divipola_vigente"]:
        problemas.append(
            f"{len(comparacion['solo_divipola_vigente'])} código(s) DIVIPOLA vigente NO están en "
            f"MGN2025 sin explicación: {comparacion['solo_divipola_vigente']}"
        )
    if comparacion["n_duplicados_mgn2025"] > 0:
        problemas.append(f"{comparacion['n_duplicados_mgn2025']} código(s) duplicados en MGN2025")
    if not comparacion["normalizacion_cod_mpio_5_digitos_ok"]:
        problemas.append("no todos los cod_dane_mpio de MGN2025 se normalizan a 5 dígitos")
    if not comparacion["normalizacion_cod_dpto_2_digitos_ok"]:
        problemas.append("no todos los cod_dane_dpto de MGN2025 se normalizan a 2 dígitos")
    return problemas


# --------------------------------------------------------------------------
# F. Capa analítica base_geometrica_divipola_mgn2025
# --------------------------------------------------------------------------


def build_analytical_layer(df_mgn: pd.DataFrame, df_vigente: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Una feature por código DANE vigente. Devuelve (df_analitico, codigos_excluidos)."""
    divipola_codes = set(df_vigente["cod_dane_mpio"])
    df_analitico = df_mgn[df_mgn["cod_dane_mpio"].isin(divipola_codes)].copy()
    codigos_excluidos = sorted(set(df_mgn["cod_dane_mpio"]) - divipola_codes)

    df_analitico = df_analitico.merge(
        df_vigente[["cod_dane_mpio", "tipo_unidad_territorial"]], on="cod_dane_mpio", how="left"
    )
    return df_analitico.reset_index(drop=True), codigos_excluidos


def write_analytical_geojson_parts(df_analitico: pd.DataFrame) -> list[dict]:
    ensure_dir(BASE_GEOM_DIR)
    cols_out = [
        "cod_dane_mpio", "cod_dane_dpto", "dpto_cnmbre", "nombre_dpto_norm",
        "mpio_cnmbre", "nombre_mpio_norm", "tipo_unidad_territorial",
        "mpio_tipo", "mpio_narea", "mpio_nano", "_geometry",
    ]
    df = df_analitico[cols_out].reset_index(drop=True)

    parts_info = []
    part_num = 0
    start = 0
    n = len(df)
    chunk = 150
    i = start
    while i < n:
        j = min(i + chunk, n)
        while True:
            fc = dataframe_to_geojson(df.iloc[i:j])
            size = len(json.dumps(fc, ensure_ascii=False, separators=(",", ":"), default=json_safe_default).encode("utf-8"))
            if size <= MAX_BYTES_PER_PART or j - i <= 1:
                break
            j = i + max(1, (j - i) // 2)
        part_num += 1
        part_path = BASE_GEOM_DIR / f"base_geometrica_divipola_mgn2025_part_{part_num:04d}.geojson"
        fc = dataframe_to_geojson(df.iloc[i:j])
        written_size = write_json(part_path, fc, compact=True, default=json_safe_default)
        parts_info.append({"archivo": part_path.name, "features": j - i, "tamano_bytes": written_size})
        i = j

    return parts_info


# --------------------------------------------------------------------------
# J. Prueba espacial con los 40 títulos de la Fase 3D.1
# --------------------------------------------------------------------------


def load_sample_40_titles() -> list[tuple[str, dict]]:
    with open(CATASTRO_SPATIAL_READY_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)
    props = []
    for feat in fc["features"]:
        p = dict(feat["properties"])
        p["_geometry"] = feat.get("geometry")
        props.append(p)
    df = pd.DataFrame(props)
    muestra = df[df["_geometry"].notna()].sample(n=40, random_state=42)
    return [(row["codigo_expediente"], row["_geometry"]) for _, row in muestra.iterrows()]


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 3D.2 - secciones C-J: base geométrica nacional MGN2025")
    print("=" * 70)

    ensure_dir(AUDIT_DIR)
    ensure_dir(REPORTS_DIR)
    ensure_dir(SPATIAL_CACHE_DIR)

    print("\n[C] Cargando features crudas MGN2025 y comparando con DIVIPOLA vigente...")
    raw_features = load_raw_features()
    print(f"  {len(raw_features)} features crudas cargadas de {DATA_RAW.name}/")

    print("\n[D] Perfilamiento geométrico (sobre datos crudos, antes de limpiar)...")
    ids_crudos = [f["properties"].get("MPIO_CDPMP") for f in raw_features]
    geoms_crudos = [f.get("geometry") for f in raw_features]
    perfil = describe_geometries_detailed(geoms_crudos, ids=ids_crudos, top_n_complex=10)
    print(f"  nulas={perfil['n_geometrias_nulas']}, vacías={perfil['n_geometrias_vacias']}, "
          f"inválidas={perfil['n_geometrias_invalidas']}, tipos={perfil['tipos_geometria']}")
    print(f"  bbox nacional: {perfil['bbox_nacional']}")
    print(f"  fuera de rango Colombia: {perfil['n_fuera_de_rango_colombia']}")
    print(f"  vértices min/max/promedio: {perfil['vertices_min']}/{perfil['vertices_max']}/{perfil['vertices_promedio']:.1f}")

    df_mgn, reporte_limpieza = clean_mgn2025_municipios(raw_features)
    print(f"\n  Limpieza: {reporte_limpieza['validaciones']['n_geometrias_reparadas']} geometrías reparadas "
          f"(de {reporte_limpieza['validaciones']['n_geometrias_invalidas_entrada']} inválidas de entrada)")

    df_vigente = load_universo_vigente()
    print(f"  DIVIPOLA vigente: {len(df_vigente)} unidades (debe ser 1122)")
    if len(df_vigente) != 1122:
        print("ERROR: DIVIPOLA vigente no tiene 1122 filas. Proceso detenido.")
        return 1

    comparacion = compare_with_divipola(df_mgn, df_vigente)
    print(f"  en ambas: {comparacion['n_en_ambas']} | solo MGN2025: {len(comparacion['solo_mgn2025'])} | "
          f"solo DIVIPOLA: {len(comparacion['solo_divipola_vigente'])}")
    print(f"  27493 presente: {comparacion['presente_27493']} | 94663 presente: {comparacion['presente_94663']}")
    print(f"  discrepancias de nombre: {len(comparacion['discrepancias_nombre'])} | "
          f"departamento: {len(comparacion['discrepancias_departamento'])} | "
          f"tipo unidad: {len(comparacion['discrepancias_tipo_unidad'])}")

    problemas = validar_o_detener(comparacion)
    if problemas:
        print("\nERROR: se encontraron problemas que detienen el proceso:")
        for p in problemas:
            print(f"  - {p}")
        return 1
    print("  OK: sin problemas que detengan el proceso.")

    print("\n[E] Auditoría topológica nacional (EPSG:9377)...")
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)
    mgn_geoms_proj = [
        (row["cod_dane_mpio"], reproject_geometry(shapely_shape(row["_geometry"]), transformer))
        for _, row in df_mgn.iterrows()
        if row["_geometry"] is not None
    ]
    topo = audit_territorial_topology(mgn_geoms_proj, geom_94663_proj=None)
    print(f"  geometrías inválidas: {topo['n_geometrias_invalidas']} | áreas no positivas: {topo['n_areas_no_positivas']} | "
          f"duplicados: {topo['n_codigos_duplicados']}")
    print(f"  pares con solape: {topo['n_pares_solape']} | área total de solape: {topo['area_total_solapes_ha']:.4f} ha")
    print(f"  contenciones completas: {topo['n_contenciones_completas']} | huecos relevantes: {topo['n_huecos_relevantes']}")

    mgn_proj_idx = dict(mgn_geoms_proj)
    zona_bajira = {}
    for cod in ZONA_BAJIRA_VECINOS:
        g = mgn_proj_idx.get(cod)
        zona_bajira[cod] = {"presente": g is not None, "area_ha": (g.area / 10000.0) if g is not None else None}
    solape_bajira_mgn2025_ha = sum(
        p["area_solape_ha"] for p in topo["pares_solape"] if CODIGO_BAJIRA in (p["cod_dane_mpio_a"], p["cod_dane_mpio_b"])
    )
    print(f"  Solape de la zona Bajirá en MGN2025: {solape_bajira_mgn2025_ha:.4f} ha "
          f"(referencia Fase 4A.1, capa mixta: {SOLAPE_BAJIRA_FASE4A1_HA:,.2f} ha)")

    print("\n[F] Construyendo la capa analítica base_geometrica_divipola_mgn2025...")
    df_analitico, codigos_excluidos = build_analytical_layer(df_mgn, df_vigente)
    print(f"  {len(df_analitico)} features analíticas (debe ser 1122) | {len(codigos_excluidos)} códigos excluidos")
    if len(df_analitico) != 1122:
        print("ERROR: la capa analítica no tiene 1122 features. Proceso detenido.")
        return 1

    parts_info = write_analytical_geojson_parts(df_analitico)
    tamano_total = sum(p["tamano_bytes"] for p in parts_info)
    print(f"  {len(parts_info)} partes escritas, {format_bytes(tamano_total)} en total.")

    write_json(
        BASE_GEOM_MANIFEST,
        {
            "fuente": "DANE - Marco Geoestadistico Nacional 2025 (MGN2025), capa Municipio (layer 317), filtrada a DIVIPOLA vigente",
            "fecha_generacion": utc_now_iso(),
            "crs": "EPSG:4326 (RFC 7946, sin miembro top-level crs)",
            "total_features": len(df_analitico),
            "numero_partes": len(parts_info),
            "tamano_total_bytes": tamano_total,
            "archivos_y_tamanos": parts_info,
            "codigos_excluidos_de_divipola_vigente": codigos_excluidos,
            "geometrias_reparadas": reporte_limpieza["validaciones"]["n_geometrias_reparadas"],
            "observaciones": (
                "Una feature por código DANE vigente (presente_divipola_vigente=True). "
                f"{len(codigos_excluidos)} códigos de MGN2025 quedaron fuera de DIVIPOLA vigente "
                "(ver data/processed/audit/mgn2025_codigos_fuera_divipola.csv), no incorporados a "
                "esta capa analítica."
            ),
        },
    )

    print("\n[G] Auditoría de códigos MGN2025 fuera de DIVIPOLA vigente...")
    df_fuera = df_mgn[df_mgn["cod_dane_mpio"].isin(codigos_excluidos)][
        ["cod_dane_mpio", "cod_dane_dpto", "mpio_cnmbre", "dpto_cnmbre", "mpio_tipo"]
    ]
    df_fuera.to_csv(FUERA_DIVIPOLA_AUDIT_PATH, index=False, encoding="utf-8")
    print(f"  {len(df_fuera)} filas escritas en {FUERA_DIVIPOLA_AUDIT_PATH.name}")

    print("\n[I] Construyendo caché espacial MGN2025 (nombre propio, no reutiliza el caché mixto anterior)...")
    part_paths = [BASE_GEOM_DIR / p["archivo"] for p in parts_info]
    analitico_proj = [(cod, mgn_proj_idx[cod]) for cod in df_analitico["cod_dane_mpio"] if cod in mgn_proj_idx]
    cache_meta = save_cache(
        SPATIAL_CACHE_DIR,
        cache_name="territorial_units_mgn2025_epsg9377",
        data=analitico_proj,
        source_paths=part_paths,
        crs=CRS_METRICO,
    )
    print(f"  Caché escrito: {cache_meta['n_geometrias']} geometrías, {format_bytes(cache_meta['tamano_bytes_pkl'])}")

    print("\n[J] Prueba espacial: mismos 40 títulos de la Fase 3D.1 contra la nueva base...")
    muestra_titulos = load_sample_40_titles()
    resultado_prueba = run_national_intersection(
        muestra_titulos, analitico_proj, crs_origen=CRS_ORIGEN, crs_metrico=CRS_METRICO, progress_every=0
    )
    stats = resultado_prueba.stats
    print(f"  títulos: {stats.n_titulos} | unidades: {stats.n_unidades} | "
          f"pares candidatos: {stats.n_pares_candidatos} | intersecciones positivas: {stats.n_intersecciones_area_positiva} | "
          f"contactos sin área: {stats.n_contactos_sin_area} | sin intersección: {stats.n_titulos_sin_interseccion}")
    print(f"  tiempo total: {stats.tiempo_total_s} s | memoria pico: {stats.memoria_pico_mb} MB")

    from aquabosque.features.mining import build_area_conservation_table

    df_prueba_rel_filas = []
    for rec in resultado_prueba.records:
        if not rec.solo_toca_limite and rec.area_interseccion_m2 > 0:
            df_prueba_rel_filas.append({"codigo_expediente": rec.title_id, "cod_dane_mpio": rec.territorial_id, "area_interseccion_ha": rec.area_interseccion_m2 / 10000.0})
    df_prueba_rel = pd.DataFrame(df_prueba_rel_filas)
    df_prueba_cons = build_area_conservation_table(df_prueba_rel, resultado_prueba.title_areas_m2, tolerancia_area_m2=1.0)
    n_sobreasignados = int(df_prueba_cons["asignacion_superior_100"].sum())
    n_sin_asignar = int(df_prueba_cons["sin_interseccion_territorial"].sum())
    print(f"  De los 40: {n_sobreasignados} sobreasignados (>100%), {n_sin_asignar} sin ninguna asignación")

    titulos_en_bajira = df_prueba_rel[df_prueba_rel["cod_dane_mpio"].isin(ZONA_BAJIRA_VECINOS)]
    print(f"  Títulos de la muestra en la zona Bajirá: {titulos_en_bajira['codigo_expediente'].nunique()}")

    tiempo_total = time.perf_counter() - t0

    resultados_finales = {
        "perfil_geometrico": perfil,
        "reporte_limpieza": reporte_limpieza,
        "comparacion_divipola": comparacion,
        "topologia": topo,
        "zona_bajira": zona_bajira,
        "solape_bajira_mgn2025_ha": solape_bajira_mgn2025_ha,
        "solape_bajira_fase4a1_ha": SOLAPE_BAJIRA_FASE4A1_HA,
        "capa_analitica": {"n_features": len(df_analitico), "n_partes": len(parts_info), "tamano_bytes": tamano_total, "codigos_excluidos": codigos_excluidos},
        "prueba_strtree_40_titulos": {
            "stats": stats,
            "n_sobreasignados": n_sobreasignados,
            "n_sin_asignar": n_sin_asignar,
            "n_titulos_zona_bajira": int(titulos_en_bajira["codigo_expediente"].nunique()),
        },
        "tiempo_total_script_s": tiempo_total,
    }

    import pickle
    with open(DATA_INTERIM / "fase3d2_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - secciones C-J completas")
    print("=" * 70)
    print(f"Tiempo total del script: {tiempo_total:.2f} s")
    print("Resultados intermedios guardados en data/interim/fase3d2_resultados.pkl para la redacción de reportes/docs/08.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
