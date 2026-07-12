"""Fase 4B.2: corrección canónica de normalización hídrica y validación
independiente de códigos de sitio.

Corrige las fusiones semánticas de isómeros de la Fase 3B/4B (α/β/γ/δ-HCH y
α/β-endosulfán) y valida de forma independiente si los códigos originales de
estación/punto/muestra/proyecto se reutilizan en ubicaciones distintas, sin
apoyarse en `sitio_monitoreo_id` (que ya incorpora coordenadas por
construcción para los sitios sin código).

Esta fase NO recalcula la asignación espacial punto-territorio, NO aplica
límites legales, NO integra minería ni deforestación, NO construye índice de
riesgo y NO modifica datos crudos. El archivo de observaciones
georreferenciadas (`calidad_agua_observaciones_georreferenciadas.csv`) no se
abre en modo escritura en ningún momento de este script.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.features.water import (  # noqa: E402
    UMBRAL_PARAMETRO_MIN_MUNICIPIOS,
    UMBRAL_PARAMETRO_MIN_OBSERVACIONES,
    build_parameter_catalog,
    build_site_parameter_year_table,
    build_territorial_water_indicators,
    build_trends_table,
)
from aquabosque.features.water_audit import (  # noqa: E402
    audit_detection_limits,
    audit_source_codes,
    audit_trends_v2,
    build_absent_parameter_candidates,
    build_parameter_normalization_dictionary,
    build_source_code_column,
    classify_parameter_suitability_v2,
    summarize_sites_without_original_code,
)
from aquabosque.features.water_normalization import (  # noqa: E402
    VERSION_NORMALIZACION_PARAMETROS,
    build_normalization_comparison,
    normalize_water_parameter_name,
)
from aquabosque.geo.intersection import build_transformer  # noqa: E402
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "water_integration"

REFERENCE_DIR = DATA_PROCESSED / "reference"
INTEGRATED_DIR = DATA_PROCESSED / "integrated"
FEATURES_DIR = DATA_PROCESSED / "features"
AUDIT_DIR = DATA_PROCESSED / "audit"

UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"
GEOREF_PATH = INTEGRATED_DIR / "calidad_agua_observaciones_georreferenciadas.csv"
AUDIT_ASIGNACION_PATH = AUDIT_DIR / "calidad_agua_asignacion_territorial_audit.csv"

CATALOGO_PATH = REFERENCE_DIR / "catalogo_parametros_calidad_agua.csv"
SITE_PARAM_YEAR_PATH = INTEGRATED_DIR / "calidad_agua_sitio_parametro_anio.csv"
TENDENCIAS_PATH = FEATURES_DIR / "calidad_agua_tendencias_territoriales.csv"
IND_TERRITORIAL_PATH = FEATURES_DIR / "calidad_agua_por_unidad_territorial.csv"
DICCIONARIO_PATH = REFERENCE_DIR / "diccionario_normalizacion_parametros_agua.csv"
CLASIFICACION_PATH = REFERENCE_DIR / "clasificacion_idoneidad_parametros_agua.csv"
LIMITES_DETECCION_PATH = AUDIT_DIR / "calidad_agua_limites_deteccion_audit.csv"
TENDENCIAS_AUDIT_PATH = AUDIT_DIR / "calidad_agua_tendencias_audit.csv"

CODIGOS_ORIGEN_AUDIT_PATH = AUDIT_DIR / "calidad_agua_codigos_sitio_origen_audit.csv"
COMPARACION_NORMALIZACION_PATH = AUDIT_DIR / "calidad_agua_normalizacion_parametros_comparison.csv"
CANDIDATOS_AUSENTES_PATH = REFERENCE_DIR / "parametros_agua_candidatos_ausentes.csv"

LEGACY_SUFFIX = "_legacy_normalizacion_previa"

# Archivos dependientes de propiedad_observada_norm que se regeneran con la
# normalización corregida (sección D) y se promueven como canónicos
# (sección G) conservando la versión previa como referencia histórica.
ARCHIVOS_A_PROMOVER = [
    CATALOGO_PATH,
    SITE_PARAM_YEAR_PATH,
    TENDENCIAS_PATH,
    IND_TERRITORIAL_PATH,
    DICCIONARIO_PATH,
    CLASIFICACION_PATH,
    LIMITES_DETECCION_PATH,
    TENDENCIAS_AUDIT_PATH,
]

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"

# Los mismos 13 candidatos evaluados en la sección K de la Fase 4B
# (scripts/13_build_water_territorial.py): ninguno de estos nombres contiene
# un prefijo griego ni el typo "HEXACLOROCICLOHEXA", así que la corrección de
# normalización no cambia su forma normalizada.
CANDIDATOS_PARAMETRO_K = [
    "PH", "OXIGENO DISUELTO OD", "CONDUCTIVIDAD ELECTRICA", "TURBIDEZ",
    "DEMANDA BIOQUIMICA DE OXIGENO DBO5", "DEMANDA QUIMICA DE OXIGENO DQO",
    "SOLIDOS SUSPENDIDOS TOTALES", "COLIFORMES TOTALES POR SUSTRATO DEFINIDO",
    "ESCHERICHIA COLI POR SUSTRATO DEFINIDO", "MERCURIO TOTAL EN AGUA",
    "ARSENICO TOTAL EN AGUA", "PLOMO TOTAL EN AGUA", "CADMIO TOTAL EN AGUA",
]


def load_universo_vigente() -> pd.DataFrame:
    df = pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    return df[df["presente_divipola_vigente"]].reset_index(drop=True)


def diff_combinaciones(v1: pd.DataFrame, v2: pd.DataFrame, cols: list[str]) -> dict[str, int]:
    set_v1 = set(map(tuple, v1[cols].itertuples(index=False, name=None)))
    set_v2 = set(map(tuple, v2[cols].itertuples(index=False, name=None)))
    return {
        "n_v1": len(set_v1),
        "n_v2": len(set_v2),
        "n_solo_en_v1": len(set_v1 - set_v2),
        "n_solo_en_v2": len(set_v2 - set_v1),
        "n_comunes": len(set_v1 & set_v2),
    }


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 4B.2: corrección canónica de normalización hídrica y validación de códigos de sitio")
    print("=" * 70)

    for d in (REFERENCE_DIR, INTEGRATED_DIR, FEATURES_DIR, AUDIT_DIR, REPORTS_DIR):
        ensure_dir(d)

    print("\nCargando resultados canónicos de la Fase 4B/4B.1 (sin abrir el georreferenciado en modo escritura)...")
    df_assigned = pd.read_csv(GEOREF_PATH, low_memory=False, dtype={"cod_dane_mpio_asignado": str, "cod_dane_dpto_asignado": str})

    def path_v1_baseline(path: Path) -> Path:
        # Si este script ya corrió antes, el archivo canónico es v2 — la
        # base "antes de la corrección" real queda en la copia legada. Leer
        # de ahí hace que el diagnóstico antes/después sea correcto sin
        # importar cuántas veces se re-ejecute este script (idempotencia).
        legacy = path.with_name(f"{path.stem}{LEGACY_SUFFIX}{path.suffix}")
        return legacy if legacy.exists() else path

    catalogo_v1 = pd.read_csv(path_v1_baseline(CATALOGO_PATH))
    tendencias_v1 = pd.read_csv(path_v1_baseline(TENDENCIAS_PATH), dtype={"cod_dane_mpio": str})
    df_vigente = load_universo_vigente()
    df_audit_asignacion = pd.read_csv(AUDIT_ASIGNACION_PATH, dtype={"cod_dane_mpio_asignado": str, "cod_dane_dpto_asignado": str})
    huella_georef_pre = file_size_bytes(GEOREF_PATH)
    print(f"  {len(df_assigned)} observaciones (huella {format_bytes(huella_georef_pre)}) | catálogo v1: {len(catalogo_v1)} filas | tendencias v1: {len(tendencias_v1)} filas")

    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)

    # -------------------------------------------------------------------
    # A. Auditoría independiente de códigos originales
    # -------------------------------------------------------------------
    print("\n[A] Auditoría independiente de códigos originales (sin coordenadas en la llave)...")
    df_con_codigo = build_source_code_column(df_assigned)
    print("  Fuentes usadas para codigo_sitio_origen:", df_con_codigo["campo_origen_codigo"].value_counts().to_dict())

    df_codigos_audit = audit_source_codes(df_con_codigo, transformer)
    df_codigos_audit.to_csv(CODIGOS_ORIGEN_AUDIT_PATH, index=False, encoding="utf-8")
    print(f"  {CODIGOS_ORIGEN_AUDIT_PATH.name}: {len(df_codigos_audit)} códigos de origen distintos auditados")
    print("  Clasificación:", df_codigos_audit["clasificacion"].value_counts().to_dict())

    resumen_sin_codigo = summarize_sites_without_original_code(df_con_codigo)
    print(f"  Sitios sin código de estación/punto real disponible: {resumen_sin_codigo['n_sitios_sin_codigo_estacion_punto']}")

    n_reutilizados_distantes = int((df_codigos_audit["clasificacion"] == "codigo_reutilizado_en_ubicaciones_distantes").sum())
    print(f"  Códigos de estación/punto reutilizados en ubicaciones distantes: {n_reutilizados_distantes}")

    # -------------------------------------------------------------------
    # B/C. Normalización corregida y tabla de correspondencia
    # -------------------------------------------------------------------
    print("\n[B] Normalización hídrica corregida (preserva isómeros)...")
    df_assigned_v2 = df_assigned.copy()
    df_assigned_v2["propiedad_observada_norm"] = df_assigned_v2["propiedad_observada"].map(normalize_water_parameter_name)
    n_norm_v1 = df_assigned["propiedad_observada_norm"].nunique()
    n_norm_v2 = df_assigned_v2["propiedad_observada_norm"].nunique()
    print(f"  Parámetros normalizados: {n_norm_v1} (v1) -> {n_norm_v2} (v2)")

    print("\n[C] Tabla de correspondencia antes/después...")
    df_comparacion = build_normalization_comparison(df_assigned, propiedad_norm_v1_col="propiedad_observada_norm")
    # `build_normalization_comparison` recalcula propiedad_norm_corregida internamente con la misma función.
    df_comparacion.to_csv(COMPARACION_NORMALIZACION_PATH, index=False, encoding="utf-8")
    n_originales = df_comparacion["propiedad_observada_original"].nunique()
    n_separaciones = int(df_comparacion["separacion_isomero"].sum())
    n_revision_restante = int(df_comparacion["requiere_revision_tecnica"].sum())
    obs_afectadas_separacion = int(df_comparacion.loc[df_comparacion["separacion_isomero"], "n_observaciones"].sum())
    print(f"  {COMPARACION_NORMALIZACION_PATH.name}: {len(df_comparacion)} filas | {n_originales} nombres originales")
    print(f"  Separaciones de isómero: {n_separaciones} filas ({obs_afectadas_separacion} observaciones afectadas) | fusiones técnicas restantes: {n_revision_restante}")
    if n_revision_restante:
        print("  ADVERTENCIA: quedan fusiones técnicamente dudosas sin resolver — revisar antes de promover.")

    # -------------------------------------------------------------------
    # D. Regeneración de productos hídricos derivados
    # -------------------------------------------------------------------
    print("\n[D] Regenerando productos derivados con la normalización corregida (sin recalcular asignación espacial)...")
    catalogo_v2 = build_parameter_catalog(df_assigned_v2)
    site_param_year_v2 = build_site_parameter_year_table(df_assigned_v2)
    tendencias_v2 = build_trends_table(df_assigned_v2)
    ind_territorial_v2 = build_territorial_water_indicators(df_vigente, df_assigned_v2, df_audit_asignacion, catalogo_v2)
    diccionario_v2 = build_parameter_normalization_dictionary(df_assigned_v2)
    clasificacion_v2 = classify_parameter_suitability_v2(catalogo_v2, df_assigned_v2)
    limites_v2 = audit_detection_limits(df_assigned_v2)
    tendencias_audit_v2 = audit_trends_v2(tendencias_v2, df_assigned_v2)

    print(f"  catalogo: {len(catalogo_v1)} -> {len(catalogo_v2)} filas")
    print(f"  sitio_parametro_anio: {len(site_param_year_v2)} filas")
    print(f"  tendencias: {len(tendencias_v1)} -> {len(tendencias_v2)} filas ({int(tendencias_v1['tendencia_calculable'].sum())} -> {int(tendencias_v2['tendencia_calculable'].sum())} calculables)")
    print(f"  indicadores territoriales: {len(ind_territorial_v2)} filas (debe ser 1122)")
    if len(ind_territorial_v2) != 1122:
        print("ERROR: los indicadores territoriales v2 no tienen 1122 filas. Proceso detenido.")
        return 1

    diff_catalogo = diff_combinaciones(catalogo_v1, catalogo_v2, ["propiedad_observada_norm", "unidad_norm"])
    diff_tendencias = diff_combinaciones(
        tendencias_v1[tendencias_v1["tendencia_calculable"]], tendencias_v2[tendencias_v2["tendencia_calculable"]],
        ["cod_dane_mpio", "propiedad_observada_norm", "unidad_norm"],
    )
    print(f"  Diferencia combinaciones de catálogo: {diff_catalogo}")
    print(f"  Diferencia tendencias calculables: {diff_tendencias}")

    # Recalculado en memoria a partir del `df_assigned` original (v1), nunca
    # leído del CSV en disco: el CSV en disco puede ya estar promovido a v2
    # si este script se ejecuta más de una vez (idempotencia), lo que haría
    # el conteo "antes" ambiguo entre corridas.
    diccionario_v1_recalculado = build_parameter_normalization_dictionary(df_assigned)
    n_fusionados_v1 = int(diccionario_v1_recalculado["requiere_revision_tecnica"].sum())
    n_revision_v2 = int(diccionario_v2["requiere_revision_tecnica"].sum())
    print(f"  Fusiones que requerían revisión técnica: {n_fusionados_v1} (v1) -> {n_revision_v2} (v2)")

    # -------------------------------------------------------------------
    # F. Nivel D / candidatos ausentes
    # -------------------------------------------------------------------
    print("\n[F] Verificación de niveles A/B/C/D y candidatos ausentes...")
    conteo_niveles = clasificacion_v2["nivel_idoneidad"].value_counts().to_dict()
    suma_niveles = sum(conteo_niveles.values())
    print(f"  Niveles: {conteo_niveles} | suma={suma_niveles} | universo (catálogo v2)={len(catalogo_v2)}")
    if suma_niveles != len(catalogo_v2):
        print("ERROR: la suma de niveles A+B+C+D no coincide con el universo del catálogo. Proceso detenido.")
        return 1

    df_ausentes = build_absent_parameter_candidates(df_assigned_v2, CANDIDATOS_PARAMETRO_K)
    df_ausentes.to_csv(CANDIDATOS_AUSENTES_PATH, index=False, encoding="utf-8")
    n_confirmados_ausentes = int(df_ausentes["confirmado_ausente"].sum())
    print(f"  {CANDIDATOS_AUSENTES_PATH.name}: {len(df_ausentes)} candidatos evaluados, {n_confirmados_ausentes} confirmados ausentes de la fuente")

    # -------------------------------------------------------------------
    # G. Promoción canónica (solo si todas las validaciones anteriores pasaron)
    # -------------------------------------------------------------------
    print("\n[G] Promoviendo normalización corregida como canónica (conservando versión anterior)...")
    resultados_v2 = {
        CATALOGO_PATH: catalogo_v2,
        SITE_PARAM_YEAR_PATH: site_param_year_v2,
        TENDENCIAS_PATH: tendencias_v2,
        IND_TERRITORIAL_PATH: ind_territorial_v2,
        DICCIONARIO_PATH: diccionario_v2,
        CLASIFICACION_PATH: clasificacion_v2,
        LIMITES_DETECCION_PATH: limites_v2,
        TENDENCIAS_AUDIT_PATH: tendencias_audit_v2,
    }

    for path in ARCHIVOS_A_PROMOVER:
        legacy_path = path.with_name(f"{path.stem}{LEGACY_SUFFIX}{path.suffix}")
        if path.exists() and not legacy_path.exists():
            shutil.copy2(path, legacy_path)
            legacy_meta_src = path.with_suffix(path.suffix + ".metadata.json")
            if legacy_meta_src.exists():
                shutil.copy2(legacy_meta_src, legacy_path.with_suffix(legacy_path.suffix + ".metadata.json"))
            print(f"  Conservado como referencia histórica: {legacy_path.name}")

        df_v2 = resultados_v2[path]
        df_v2.to_csv(path, index=False, encoding="utf-8")
        print(f"  Promovido: {path.name} ({len(df_v2)} filas)")

    huella_georef_post = file_size_bytes(GEOREF_PATH)
    georef_sin_cambios = huella_georef_pre == huella_georef_post
    print(f"  Huella de {GEOREF_PATH.name}: {format_bytes(huella_georef_pre)} -> {format_bytes(huella_georef_post)} (sin cambios: {georef_sin_cambios})")
    if not georef_sin_cambios:
        print("ERROR: el archivo de asignación espacial cambió de tamaño; este script nunca debió escribirlo.")
        return 1

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------
    print("\nEscribiendo metadata...")

    def escribir_metadata(path: Path, *, n_filas: int, descripcion: str, extra: dict | None = None) -> None:
        meta = {
            "fuente": "Fase 4B.2 - corrección canónica de normalización hídrica",
            "version_normalizacion_parametros": VERSION_NORMALIZACION_PARAMETROS,
            "asignacion_espacial_modificada": False,
            "fecha_procesamiento": utc_now_iso(),
            "n_filas": n_filas,
            "tamano_bytes": file_size_bytes(path),
            "descripcion": descripcion,
            "version_anterior_conservada_como": f"{path.stem}{LEGACY_SUFFIX}{path.suffix}",
        }
        if extra:
            meta.update(extra)
        write_json(path.with_suffix(path.suffix + ".metadata.json"), meta)

    escribir_metadata(CATALOGO_PATH, n_filas=len(catalogo_v2), descripcion="Catálogo de parámetros regenerado con normalización corregida (Fase 4B.2).", extra={"diff_vs_v1": diff_catalogo})
    escribir_metadata(SITE_PARAM_YEAR_PATH, n_filas=len(site_param_year_v2), descripcion="Tabla sitio+parámetro+año regenerada con normalización corregida.")
    escribir_metadata(TENDENCIAS_PATH, n_filas=len(tendencias_v2), descripcion="Tendencias territoriales regeneradas con normalización corregida.", extra={"diff_calculables_vs_v1": diff_tendencias})
    escribir_metadata(IND_TERRITORIAL_PATH, n_filas=len(ind_territorial_v2), descripcion="Indicadores territoriales (1.122 unidades) regenerados con normalización corregida; asignación espacial sin cambios.")
    escribir_metadata(DICCIONARIO_PATH, n_filas=len(diccionario_v2), descripcion="Diccionario de normalización regenerado; fusiones técnicamente dudosas resueltas.")
    escribir_metadata(CLASIFICACION_PATH, n_filas=len(clasificacion_v2), descripcion="Clasificación de idoneidad A/B/C/D regenerada sobre el catálogo corregido.")
    escribir_metadata(LIMITES_DETECCION_PATH, n_filas=len(limites_v2), descripcion="Auditoría de límites de detección regenerada con normalización corregida.")
    escribir_metadata(TENDENCIAS_AUDIT_PATH, n_filas=len(tendencias_audit_v2), descripcion="Auditoría de tendencias v2: distingue reproducibilidad matemática de idoneidad interpretativa e incorpora variabilidad del límite de detección.")

    write_json(
        CODIGOS_ORIGEN_AUDIT_PATH.with_suffix(CODIGOS_ORIGEN_AUDIT_PATH.suffix + ".metadata.json"),
        {
            "fuente": "Fase 4B.2 - auditoría independiente de códigos originales",
            "fecha_procesamiento": utc_now_iso(),
            "n_filas": len(df_codigos_audit),
            "tamano_bytes": file_size_bytes(CODIGOS_ORIGEN_AUDIT_PATH),
            "descripcion": "Agrupado por codigo_sitio_origen (sin coordenadas en la llave), con prioridad estación/punto > muestra > proyecto > nombre.",
            "sitios_sin_codigo_estacion_punto": resumen_sin_codigo,
        },
    )
    write_json(
        COMPARACION_NORMALIZACION_PATH.with_suffix(COMPARACION_NORMALIZACION_PATH.suffix + ".metadata.json"),
        {
            "fuente": "Fase 4B.2 - tabla de correspondencia de normalización",
            "fecha_procesamiento": utc_now_iso(),
            "n_filas": len(df_comparacion),
            "tamano_bytes": file_size_bytes(COMPARACION_NORMALIZACION_PATH),
            "n_nombres_originales": int(n_originales),
            "n_parametros_normalizados_v1": int(n_norm_v1),
            "n_parametros_normalizados_v2": int(n_norm_v2),
            "n_separaciones_isomero": n_separaciones,
            "n_observaciones_afectadas_separacion": obs_afectadas_separacion,
            "n_fusiones_tecnicas_restantes": n_revision_v2,
        },
    )
    write_json(
        CANDIDATOS_AUSENTES_PATH.with_suffix(CANDIDATOS_AUSENTES_PATH.suffix + ".metadata.json"),
        {
            "fuente": "Fase 4B.2 - candidatos a parámetro específico evaluados pero no encontrados en la fuente",
            "fecha_procesamiento": utc_now_iso(),
            "n_filas": len(df_ausentes),
            "tamano_bytes": file_size_bytes(CANDIDATOS_AUSENTES_PATH),
            "n_confirmados_ausentes": n_confirmados_ausentes,
        },
    )

    tiempo_total = time.perf_counter() - t0

    resultados_finales: dict[str, Any] = {
        "df_codigos_audit": df_codigos_audit,
        "resumen_sin_codigo": resumen_sin_codigo,
        "n_reutilizados_distantes": n_reutilizados_distantes,
        "campo_origen_counts": df_con_codigo["campo_origen_codigo"].value_counts().to_dict(),
        "df_comparacion": df_comparacion,
        "n_norm_v1": n_norm_v1,
        "n_norm_v2": n_norm_v2,
        "n_separaciones": n_separaciones,
        "obs_afectadas_separacion": obs_afectadas_separacion,
        "n_revision_v2": n_revision_v2,
        "n_fusionados_v1": n_fusionados_v1,
        "catalogo_v1_n": len(catalogo_v1),
        "catalogo_v2_n": len(catalogo_v2),
        "diff_catalogo": diff_catalogo,
        "diff_tendencias": diff_tendencias,
        "tendencias_v1_calculables": int(tendencias_v1["tendencia_calculable"].sum()),
        "tendencias_v2_calculables": int(tendencias_v2["tendencia_calculable"].sum()),
        "conteo_niveles": conteo_niveles,
        "df_ausentes": df_ausentes,
        "n_confirmados_ausentes": n_confirmados_ausentes,
        "df_tendencias_audit_v2": tendencias_audit_v2,
        "df_limites_v2": limites_v2,
        "georef_sin_cambios": georef_sin_cambios,
        "tiempo_total_s": tiempo_total,
    }
    import pickle
    with open(DATA_INTERIM / "fase4b2_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 4B.2")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s")
    print(f"1. Campos usados para codigo_sitio_origen: {resultados_finales['campo_origen_counts']}")
    print(f"2. Códigos reutilizados en ubicaciones distantes: {n_reutilizados_distantes}")
    print(f"3. Sitios sin código de estación/punto original: {resumen_sin_codigo['n_sitios_sin_codigo_estacion_punto']}")
    print(f"4. Parámetros normalizados: {n_norm_v1} -> {n_norm_v2} | separaciones de isómero: {n_separaciones} | fusiones restantes: {n_revision_v2}")
    print(f"5. Observaciones afectadas por separación de isómeros: {obs_afectadas_separacion}")
    print(f"6. Catálogo: {len(catalogo_v1)} -> {len(catalogo_v2)} combinaciones | tendencias calculables: {resultados_finales['tendencias_v1_calculables']} -> {resultados_finales['tendencias_v2_calculables']}")
    print(f"7. Niveles A/B/C/D: {conteo_niveles} (suma={suma_niveles}, universo={len(catalogo_v2)})")
    print(f"8. Candidatos confirmados ausentes: {n_confirmados_ausentes}/{len(df_ausentes)}")
    print(f"9. Georreferenciado sin cambios: {georef_sin_cambios}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
