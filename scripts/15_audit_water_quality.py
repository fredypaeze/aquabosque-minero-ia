"""Fase 4B.1: auditoría metodológica de sitios, parámetros censurados y
cobertura hídrica.

Cierra la calidad metodológica de la integración hídrica de la Fase 4B SIN
recalcular la asignación espacial ni construir indicadores de contaminación
o riesgo. No descarga fuentes nuevas. No integra minería ni deforestación.
No aplica límites legales. No crea dashboard. No modifica datos crudos.
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

from aquabosque.features.water_audit import (  # noqa: E402
    audit_detection_limits,
    audit_monitoring_sites,
    audit_trends,
    build_parameter_normalization_dictionary,
    classify_discrepancy_cause,
    classify_parameter_suitability_v2,
    propose_composite_key_for_reused_codes,
)
from aquabosque.geo.intersection import build_transformer  # noqa: E402
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402
from aquabosque.utils.spatial_cache import load_cache_if_valid  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "water_integration"
SPATIAL_CACHE_DIR = DATA_INTERIM / "spatial_cache"

BASE_GEOM_DIR = DATA_PROCESSED / "territorio" / "base_geometrica_divipola_mgn2025"
BASE_GEOM_MANIFEST = BASE_GEOM_DIR / "manifest.json"
UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"

GEOREF_PATH = DATA_PROCESSED / "integrated" / "calidad_agua_observaciones_georreferenciadas.csv"
CATALOGO_PATH = DATA_PROCESSED / "reference" / "catalogo_parametros_calidad_agua.csv"
TENDENCIAS_PATH = DATA_PROCESSED / "features" / "calidad_agua_tendencias_territoriales.csv"
IND_TERRITORIAL_PATH = DATA_PROCESSED / "features" / "calidad_agua_por_unidad_territorial.csv"
AUDIT_ASIGNACION_PATH = DATA_PROCESSED / "audit" / "calidad_agua_asignacion_territorial_audit.csv"

AUDIT_DIR = DATA_PROCESSED / "audit"
REFERENCE_DIR = DATA_PROCESSED / "reference"

SITIOS_AUDIT_PATH = AUDIT_DIR / "calidad_agua_sitios_monitoreo_audit.csv"
DICCIONARIO_PATH = REFERENCE_DIR / "diccionario_normalizacion_parametros_agua.csv"
CLASIFICACION_PATH = REFERENCE_DIR / "clasificacion_idoneidad_parametros_agua.csv"
LIMITES_DETECCION_PATH = AUDIT_DIR / "calidad_agua_limites_deteccion_audit.csv"
TENDENCIAS_AUDIT_PATH = AUDIT_DIR / "calidad_agua_tendencias_audit.csv"
DISCREPANCIAS_CAUSA_PATH = AUDIT_DIR / "calidad_agua_discrepancias_causa_audit.csv"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
VENTANA_RECIENTE = list(range(2020, 2025))


def load_universo_vigente() -> pd.DataFrame:
    df = pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    return df[df["presente_divipola_vigente"]].reset_index(drop=True)


def load_mgn2025_geoms_proj() -> dict[str, Any]:
    with open(BASE_GEOM_MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)
    source_paths = [BASE_GEOM_DIR / a["archivo"] for a in manifest["archivos_y_tamanos"]]
    cached = load_cache_if_valid(
        SPATIAL_CACHE_DIR, cache_name="territorial_units_mgn2025_epsg9377", source_paths=source_paths, crs=CRS_METRICO
    )
    if cached is None:
        raise RuntimeError("Caché espacial MGN2025 no disponible; ejecutar Fase 3D.2/4A.2 primero.")
    return dict(cached)


def summarize_coverage(df_ind: pd.DataFrame) -> dict[str, int]:
    sin_hist = df_ind[df_ind["sin_monitoreo"]]
    con_hist = df_ind[df_ind["tiene_monitoreo_agua"]]
    con_reciente = con_hist[~con_hist["monitoreo_desactualizado"]]
    con_hist_desactualizado = con_hist[con_hist["monitoreo_desactualizado"]]
    return {
        "unidades_sin_monitoreo_historico": len(sin_hist),
        "unidades_con_monitoreo_historico": len(con_hist),
        "unidades_con_monitoreo_reciente": len(con_reciente),
        "unidades_con_monitoreo_historico_pero_desactualizado": len(con_hist_desactualizado),
        "total": len(df_ind),
    }


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 4B.1: auditoría metodológica de sitios, censura y cobertura hídrica")
    print("=" * 70)

    for d in (AUDIT_DIR, REFERENCE_DIR, REPORTS_DIR):
        ensure_dir(d)

    print("\nCargando resultados canónicos de la Fase 4B (sin recalcular asignación espacial)...")
    df_assigned = pd.read_csv(GEOREF_PATH, low_memory=False, dtype={"cod_dane_mpio_asignado": str, "cod_dane_dpto_asignado": str})
    catalogo = pd.read_csv(CATALOGO_PATH)
    df_tendencias = pd.read_csv(TENDENCIAS_PATH, dtype={"cod_dane_mpio": str})
    df_ind = pd.read_csv(IND_TERRITORIAL_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    df_audit_asignacion_4b = pd.read_csv(AUDIT_ASIGNACION_PATH, dtype={"cod_dane_mpio_asignado": str, "cod_dane_dpto_asignado": str})
    df_vigente = load_universo_vigente()
    print(f"  {len(df_assigned)} observaciones | {len(catalogo)} combinaciones parámetro+unidad | "
          f"{len(df_tendencias)} tendencias | {len(df_audit_asignacion_4b)} sitios con discrepancia (Fase 4B)")

    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)

    print("\n[A] Auditoría de identificación de sitios (243 sitios)...")
    df_sitios_audit = audit_monitoring_sites(df_assigned, transformer)
    df_sitios_audit.to_csv(SITIOS_AUDIT_PATH, index=False, encoding="utf-8")
    print(f"  {SITIOS_AUDIT_PATH.name}: {len(df_sitios_audit)} filas")
    print("  Clasificación:", df_sitios_audit["clasificacion"].value_counts().to_dict())

    propuestas_llave = propose_composite_key_for_reused_codes(df_sitios_audit)
    print(f"  Códigos en coordenadas distantes que requerirían nueva llave compuesta: {len(propuestas_llave)}")

    print("\n[B] Diccionario de normalización de parámetros...")
    df_diccionario = build_parameter_normalization_dictionary(df_assigned)
    df_diccionario.to_csv(DICCIONARIO_PATH, index=False, encoding="utf-8")
    n_fusionados = int(df_diccionario["fue_fusionado_con_otro_nombre"].sum())
    n_revision_tecnica = int(df_diccionario["requiere_revision_tecnica"].sum())
    print(f"  {DICCIONARIO_PATH.name}: {len(df_diccionario)} filas (propiedad_original x unidad_original)")
    print(f"  Filas de propiedades fusionadas con otro nombre: {n_fusionados} | "
          f"requieren revisión técnica: {n_revision_tecnica}")

    print("\n[C] Clasificación de idoneidad de parámetros (niveles A/B/C/D)...")
    df_clasificacion = classify_parameter_suitability_v2(catalogo, df_assigned)
    df_clasificacion.to_csv(CLASIFICACION_PATH, index=False, encoding="utf-8")
    print(f"  {CLASIFICACION_PATH.name}: {len(df_clasificacion)} filas")
    print("  Niveles:", df_clasificacion["nivel_idoneidad"].value_counts().to_dict())
    plomo_cadmio = df_clasificacion[df_clasificacion["propiedad_observada_norm"].isin(["PLOMO TOTAL EN AGUA", "CADMIO TOTAL EN AGUA"])]
    print(df_clasificacion[df_clasificacion["propiedad_observada_norm"].isin(["PLOMO TOTAL EN AGUA", "CADMIO TOTAL EN AGUA"])][["propiedad_observada_norm", "pct_censurado", "nivel_idoneidad"]].to_string())

    print("\n[D] Auditoría de límites de detección...")
    df_limites = audit_detection_limits(df_assigned)
    df_limites.to_csv(LIMITES_DETECCION_PATH, index=False, encoding="utf-8")
    print(f"  {LIMITES_DETECCION_PATH.name}: {len(df_limites)} combinaciones censuradas")
    print(f"  Con alta variabilidad de límite de detección: {int(df_limites['alta_variabilidad'].sum())}")

    print("\n[E] Auditoría de tendencias...")
    df_tendencias_audit = audit_trends(df_tendencias, df_assigned)
    df_tendencias_audit.to_csv(TENDENCIAS_AUDIT_PATH, index=False, encoding="utf-8")
    print(f"  {TENDENCIAS_AUDIT_PATH.name}: {len(df_tendencias_audit)} filas")
    print(f"  Precaución por censura (20-80%): {int(df_tendencias_audit['requiere_precaucion_por_censura'].sum())}")
    print(f"  No recomendadas (>80% censura): {int(df_tendencias_audit['no_recomendada_para_interpretacion_numerica'].sum())}")
    n_inconsistentes = int((~df_tendencias_audit["tendencia_valida_metodologicamente"]).sum())
    print(f"  Inconsistencias metodológicas encontradas: {n_inconsistentes}")

    print("\n[F] Cobertura territorial separada (sin monitoreo / histórico / reciente / desactualizado)...")
    cobertura = summarize_coverage(df_ind)
    print(f"  {cobertura}")

    print("\n[G] Discrepancias texto-geometría: causa probable...")
    mgn_geoms_proj_by_cod = load_mgn2025_geoms_proj()
    df_discrepancias = classify_discrepancy_cause(df_audit_asignacion_4b, df_vigente, mgn_geoms_proj_by_cod, transformer)

    obs_por_sitio = df_assigned.groupby("sitio_monitoreo_id").size()
    df_discrepancias["n_observaciones_afectadas"] = df_discrepancias["sitio_monitoreo_id"].map(obs_por_sitio).fillna(0).astype(int)
    df_discrepancias.to_csv(DISCREPANCIAS_CAUSA_PATH, index=False, encoding="utf-8")
    print(f"  {DISCREPANCIAS_CAUSA_PATH.name}: {len(df_discrepancias)} filas")
    print("  Causa probable (municipio):", df_discrepancias["causa_probable_municipio"].value_counts().to_dict())
    total_obs_afectadas = int(df_discrepancias["n_observaciones_afectadas"].sum())
    print(f"  Observaciones totales afectadas por alguna discrepancia: {total_obs_afectadas}")

    print("\nEscribiendo metadata...")

    def escribir_metadata(path: Path, *, n_filas: int, descripcion: str) -> None:
        write_json(
            path.with_suffix(path.suffix + ".metadata.json"),
            {
                "fuente": "Fase 4B.1 - auditoría metodológica de la integración hídrica",
                "fecha_procesamiento": utc_now_iso(),
                "n_filas": n_filas,
                "tamano_bytes": file_size_bytes(path),
                "descripcion": descripcion,
                "no_modifica": "No recalcula la asignación espacial ni los indicadores canónicos de la Fase 4B.",
            },
        )

    escribir_metadata(SITIOS_AUDIT_PATH, n_filas=len(df_sitios_audit), descripcion="Una fila por sitio_monitoreo_id (243), con estadísticas y clasificación de estabilidad.")
    escribir_metadata(DICCIONARIO_PATH, n_filas=len(df_diccionario), descripcion="Mapeo completo propiedad_observada original -> normalizado, con marcado de fusiones técnicamente dudosas.")
    escribir_metadata(CLASIFICACION_PATH, n_filas=len(df_clasificacion), descripcion="Clasificación de idoneidad en 4 niveles (A/B/C/D) por combinación parámetro+unidad.")
    escribir_metadata(LIMITES_DETECCION_PATH, n_filas=len(df_limites), descripcion="Variabilidad del límite de detección por combinación parámetro+unidad censurada.")
    escribir_metadata(TENDENCIAS_AUDIT_PATH, n_filas=len(df_tendencias_audit), descripcion="Auditoría de censura de las tendencias calculables de la Fase 4B.")
    escribir_metadata(DISCREPANCIAS_CAUSA_PATH, n_filas=len(df_discrepancias), descripcion="Causa probable de cada discrepancia texto-geometría, con observaciones afectadas.")

    tiempo_total = time.perf_counter() - t0

    resultados_finales = {
        "df_sitios_audit": df_sitios_audit,
        "propuestas_llave": propuestas_llave,
        "df_diccionario": df_diccionario,
        "n_fusionados": n_fusionados,
        "n_revision_tecnica": n_revision_tecnica,
        "df_clasificacion": df_clasificacion,
        "df_limites": df_limites,
        "df_tendencias_audit": df_tendencias_audit,
        "n_inconsistentes": n_inconsistentes,
        "cobertura": cobertura,
        "df_discrepancias": df_discrepancias,
        "total_obs_afectadas": total_obs_afectadas,
        "tiempo_total_s": tiempo_total,
        "n_registros_total": len(df_assigned),
        "n_sitios": df_assigned["sitio_monitoreo_id"].nunique(),
    }
    import pickle
    with open(DATA_INTERIM / "fase4b1_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 4B.1")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s")
    print(f"1. Sitios estables: {(df_sitios_audit['clasificacion']=='sitio_estable').sum()} | "
          f"requieren revisión: {(df_sitios_audit['clasificacion']=='requiere_revision_manual').sum()}")
    print(f"2. Códigos en coordenadas distantes: {len(propuestas_llave)}")
    print(f"3. Mapeo parámetros: {len(df_diccionario)} combinaciones originales -> {df_diccionario['propiedad_observada_norm'].nunique()} normalizados ({n_fusionados} fusionadas, {n_revision_tecnica} requieren revisión técnica)")
    print(f"4. Niveles de idoneidad: {df_clasificacion['nivel_idoneidad'].value_counts().to_dict()}")
    print(f"5. Combinaciones censuradas auditadas: {len(df_limites)}, alta variabilidad: {int(df_limites['alta_variabilidad'].sum())}")
    print(f"6. Tendencias: válidas metodológicamente {int(df_tendencias_audit['tendencia_valida_metodologicamente'].sum())}/{len(df_tendencias_audit)}, "
          f"precaución {int(df_tendencias_audit['requiere_precaucion_por_censura'].sum())}, "
          f"no recomendadas {int(df_tendencias_audit['no_recomendada_para_interpretacion_numerica'].sum())}")
    print(f"7. Cobertura: {cobertura}")
    print(f"8. Observaciones afectadas por discrepancias: {total_obs_afectadas}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
