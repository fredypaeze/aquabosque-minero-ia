"""Fase 3B / 3C / 3D: limpieza y estandarización de las fuentes MVP.

Lee los datos crudos ya descargados (Fase 2A/2A.1/2B/2C) y perfilados (Fase 3A/3C/3D) y
genera una versión limpia por fuente en data/processed/. Cada fuente se
limpia por separado: este script NO cruza las fuentes entre sí ni construye
ningún dataset maestro. No descarga nada nuevo, no entrena modelo, no crea
dashboard.

Salidas:
  data/processed/territorio/divipola_municipios_clean.csv (+ .metadata.json)
  data/processed/mineria/anm_anotaciones_rmn_clean.csv (+ .metadata.json)
  data/processed/agua/ideam_calidad_agua_clean.csv (+ .metadata.json)
  data/processed/mineria/catastro_minero_anm_clean.geojson (+ .metadata.json)
  data/processed/territorio/limites_municipales_dane/*.geojson (+ manifest + metadata)
  outputs/reports/cleaning/cleaning_summary.md
  outputs/reports/cleaning/catastro_minero_anm_cleaning.md
  outputs/reports/cleaning/limites_municipales_dane_cleaning.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.data.clean import (  # noqa: E402
    clean_anm_anotaciones,
    clean_calidad_agua,
    clean_catastro_minero_anm,
    clean_divipola,
    clean_limites_municipales_dane,
    dataframe_to_geojson,
    json_safe_default,
)
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "cleaning"

DIVIPOLA_PATH = DATA_RAW / "territorio" / "dane_divipola_municipios.xlsx"
ANM_PATH = DATA_RAW / "mineria" / "anm_titulos_anotaciones_rmn.json"
AGUA_DIR = DATA_RAW / "agua" / "ideam_calidad_agua_historica"
AGUA_MANIFEST_PATH = AGUA_DIR / "manifest.json"
CATASTRO_DIR = DATA_RAW / "mineria" / "catastro_minero_anm"
CATASTRO_PATH = CATASTRO_DIR / "catastro_minero_anm_titulo_vigente_part_0001.geojson"
CATASTRO_MANIFEST_PATH = CATASTRO_DIR / "manifest.json"
LIMITES_RAW_DIR = DATA_RAW / "territorio" / "limites_municipales_dane"
LIMITES_RAW_MANIFEST_PATH = LIMITES_RAW_DIR / "manifest.json"
LIMITES_OUT_DIR = DATA_PROCESSED / "territorio" / "limites_municipales_dane"
DIVIPOLA_CLEAN_PATH = DATA_PROCESSED / "territorio" / "divipola_municipios_clean.csv"

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO_PROPUESTO = "EPSG:9377"  # MAGNA-SIRGAS 2018 / Origen-Nacional


# --------------------------------------------------------------------------
# Carga de datos crudos (misma lógica de lectura usada en la Fase 3A)
# --------------------------------------------------------------------------


def load_divipola_raw() -> pd.DataFrame:
    df = pd.read_excel(DIVIPOLA_PATH, sheet_name="Municipios", header=[9, 10])
    df.columns = [
        "depto_codigo",
        "depto_nombre",
        "mpio_codigo",
        "mpio_nombre",
        "tipo",
        "longitud",
        "latitud",
        "nota",
    ]
    return df


def load_anm_raw() -> pd.DataFrame:
    return pd.read_json(ANM_PATH, encoding="utf-8")


def load_calidad_agua_raw() -> tuple[pd.DataFrame, dict]:
    with open(AGUA_MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    frames = []
    for parte in manifest["tamano_por_parte"]:
        part_path = AGUA_DIR / parte["archivo"]
        df_parte = pd.read_json(part_path, encoding="utf-8")
        assert len(df_parte) == parte["filas"], (
            f"{parte['archivo']}: filas leídas ({len(df_parte)}) no coincide con manifest ({parte['filas']})"
        )
        frames.append(df_parte)

    df = pd.concat(frames, ignore_index=True)
    return df, manifest


def load_catastro_minero_raw() -> tuple[pd.DataFrame, list[dict | None], dict]:
    with open(CATASTRO_MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)
    with open(CATASTRO_PATH, encoding="utf-8") as fh:
        fc = json.load(fh)

    features = fc["features"]
    assert len(features) == manifest["total_features_descargadas"], (
        f"Features leídas ({len(features)}) no coinciden con el manifest "
        f"({manifest['total_features_descargadas']})"
    )

    props = [f.get("properties", {}) for f in features]
    geometries = [f.get("geometry") for f in features]
    df = pd.DataFrame(props)
    return df, geometries, manifest


def load_limites_municipales_raw_features() -> tuple[list[dict], dict]:
    """Lee todas las partes declaradas en el manifest crudo de límites
    municipales y devuelve la lista completa de Features GeoJSON (sin
    modificar) más el manifest."""
    with open(LIMITES_RAW_MANIFEST_PATH, encoding="utf-8") as fh:
        manifest = json.load(fh)

    partes = sorted(manifest["tamano_por_parte"], key=lambda p: p["parte"])
    all_features: list[dict] = []
    for p in partes:
        with open(LIMITES_RAW_DIR / p["archivo"], encoding="utf-8") as fh:
            fc = json.load(fh)
        assert len(fc["features"]) == p["features"], (
            f"{p['archivo']}: features leídas ({len(fc['features'])}) no coincide con "
            f"manifest ({p['features']})"
        )
        all_features.extend(fc["features"])

    assert len(all_features) == manifest["total_features_descargadas"], (
        f"Total de features leídas ({len(all_features)}) no coincide con el manifest "
        f"({manifest['total_features_descargadas']})"
    )
    return all_features, manifest


# --------------------------------------------------------------------------
# Escritura de salidas
# --------------------------------------------------------------------------


def write_clean_csv(df: pd.DataFrame, path: Path) -> int:
    ensure_dir(path.parent)
    df.to_csv(path, index=False, encoding="utf-8")
    return file_size_bytes(path)


def write_clean_geojson(df: pd.DataFrame, path: Path, *, geometry_col: str = "_geometry") -> int:
    ensure_dir(path.parent)
    fc = dataframe_to_geojson(df, geometry_col=geometry_col)
    return write_json(path, fc, compact=True, default=json_safe_default)


def write_cleaning_metadata(
    path: Path,
    *,
    fuente: str,
    ruta_entrada: str,
    ruta_salida: str,
    tamano_bytes: int,
    report: dict,
) -> None:
    metadata = {
        "fuente": fuente,
        "ruta_entrada": ruta_entrada,
        "ruta_salida": ruta_salida,
        "fecha_limpieza": utc_now_iso(),
        "tamano_bytes": tamano_bytes,
        **report,
    }
    write_json(path, metadata)


def write_rfc7946_geojson(df: pd.DataFrame, path: Path, *, geometry_col: str = "_geometry") -> int:
    """Escribe un FeatureCollection GeoJSON compatible con RFC 7946.

    RFC 7946 fija el CRS a WGS 84 (equivalente a `CRS84`, longitud/latitud en
    ese orden) de forma implícita y **prohíbe** el miembro `crs` a nivel de
    FeatureCollection (obsoleto desde RFC 7946 §4). Por eso esta función NO
    inserta ningún objeto `crs`: el sistema de referencia se documenta en el
    manifest y en la metadata que acompañan al archivo, no dentro del propio
    GeoJSON. Reemplaza a la antigua `write_clean_geojson_with_crs`, que sí
    insertaba ese miembro (convención GeoJSON pre-RFC 7946).
    """
    ensure_dir(path.parent)
    fc = dataframe_to_geojson(df, geometry_col=geometry_col)
    return write_json(path, fc, compact=True, default=json_safe_default)


# --------------------------------------------------------------------------
# Orquestación por fuente
# --------------------------------------------------------------------------


def run_divipola() -> tuple[str, dict]:
    df_raw = load_divipola_raw()
    df_clean, report = clean_divipola(df_raw)

    out_csv = DATA_PROCESSED / "territorio" / "divipola_municipios_clean.csv"
    size = write_clean_csv(df_clean, out_csv)

    out_meta = out_csv.with_suffix(out_csv.suffix + ".metadata.json")
    write_cleaning_metadata(
        out_meta,
        fuente="DIVIPOLA - Códigos de municipios (DANE)",
        ruta_entrada=str(DIVIPOLA_PATH.relative_to(PROJECT_ROOT)),
        ruta_salida=str(out_csv.relative_to(PROJECT_ROOT)),
        tamano_bytes=size,
        report=report,
    )
    return "DIVIPOLA - Códigos de municipios (DANE)", {**report, "ruta_salida": str(out_csv.relative_to(PROJECT_ROOT)), "tamano_bytes": size}


def run_anm() -> tuple[str, dict]:
    df_raw = load_anm_raw()
    df_clean, report = clean_anm_anotaciones(df_raw)

    out_csv = DATA_PROCESSED / "mineria" / "anm_anotaciones_rmn_clean.csv"
    size = write_clean_csv(df_clean, out_csv)

    out_meta = out_csv.with_suffix(out_csv.suffix + ".metadata.json")
    write_cleaning_metadata(
        out_meta,
        fuente="ANM Títulos Mineros - Anotaciones RMN",
        ruta_entrada=str(ANM_PATH.relative_to(PROJECT_ROOT)),
        ruta_salida=str(out_csv.relative_to(PROJECT_ROOT)),
        tamano_bytes=size,
        report=report,
    )
    return "ANM Títulos Mineros - Anotaciones RMN", {**report, "ruta_salida": str(out_csv.relative_to(PROJECT_ROOT)), "tamano_bytes": size}


def run_calidad_agua() -> tuple[str, dict]:
    df_raw, manifest = load_calidad_agua_raw()
    df_clean, report = clean_calidad_agua(df_raw)
    report["filas_origen_socrata"] = manifest["total_filas_origen"]

    out_csv = DATA_PROCESSED / "agua" / "ideam_calidad_agua_clean.csv"
    size = write_clean_csv(df_clean, out_csv)

    out_meta = out_csv.with_suffix(out_csv.suffix + ".metadata.json")
    write_cleaning_metadata(
        out_meta,
        fuente="IDEAM - Data Histórica de Calidad de Agua",
        ruta_entrada=str(AGUA_DIR.relative_to(PROJECT_ROOT)) + "/manifest.json (+ 4 partes)",
        ruta_salida=str(out_csv.relative_to(PROJECT_ROOT)),
        tamano_bytes=size,
        report=report,
    )
    return "IDEAM - Data Histórica de Calidad de Agua", {**report, "ruta_salida": str(out_csv.relative_to(PROJECT_ROOT)), "tamano_bytes": size}


def run_catastro_minero() -> tuple[str, dict]:
    df_raw, geometries, manifest = load_catastro_minero_raw()
    df_clean, report = clean_catastro_minero_anm(df_raw, geometries)
    report["features_origen_wfs"] = manifest["total_features_origen"]

    out_geojson = DATA_PROCESSED / "mineria" / "catastro_minero_anm_clean.geojson"
    size = write_clean_geojson(df_clean, out_geojson, geometry_col="_geometry")

    # "_geometry" es una columna interna para reconstruir el GeoJSON, no una
    # propiedad tabular: se excluye de "columnas_finales" y se documenta aparte.
    report["columnas_finales"] = [c for c in report["columnas_finales"] if c != "_geometry"]
    report["observaciones"].insert(
        0,
        "La geometría (MultiPolygon) se conserva como el campo `geometry` estándar de cada "
        "Feature del GeoJSON de salida, no como una columna tabular más.",
    )

    out_meta = out_geojson.with_suffix(out_geojson.suffix + ".metadata.json")
    write_cleaning_metadata(
        out_meta,
        fuente="Catastro Minero ANM - Títulos Vigentes (WFS)",
        ruta_entrada=str(CATASTRO_PATH.relative_to(PROJECT_ROOT)),
        ruta_salida=str(out_geojson.relative_to(PROJECT_ROOT)),
        tamano_bytes=size,
        report=report,
    )
    return (
        "Catastro Minero ANM - Títulos Vigentes (WFS)",
        {**report, "ruta_salida": str(out_geojson.relative_to(PROJECT_ROOT)), "tamano_bytes": size},
    )


def validate_crs_transform_sample(df: pd.DataFrame, *, sample_size: int = 15) -> dict:
    """Valida que sea posible transformar una muestra de centroides de
    EPSG:4326 a EPSG:9377 con pyproj, SIN reemplazar la geometría almacenada.
    Este CRS métrico es el propuesto para intersecciones/áreas en Fase 4A."""
    from pyproj import Transformer
    from shapely.geometry import shape

    transformer = Transformer.from_crs(CRS_ORIGEN, CRS_METRICO_PROPUESTO, always_xy=True)

    con_geometria = df[df["_geometry"].notna()]
    n_muestra = min(sample_size, len(con_geometria))
    sample = con_geometria.sample(n=n_muestra, random_state=42) if n_muestra else con_geometria

    xs: list[float] = []
    ys: list[float] = []
    n_errores = 0
    detalle = []
    for _, row in sample.iterrows():
        geom = shape(row["_geometry"])
        cx, cy = geom.centroid.x, geom.centroid.y
        try:
            tx, ty = transformer.transform(cx, cy)
            xs.append(tx)
            ys.append(ty)
            detalle.append(
                {
                    "cod_dane_mpio": row["cod_dane_mpio"],
                    "centroide_epsg4326": [round(cx, 6), round(cy, 6)],
                    "centroide_epsg9377_metros": [round(tx, 2), round(ty, 2)],
                }
            )
        except Exception as exc:  # noqa: BLE001
            n_errores += 1
            detalle.append({"cod_dane_mpio": row["cod_dane_mpio"], "error": str(exc)})

    return {
        "muestra_tamano": n_muestra,
        "n_errores_transformacion": n_errores,
        "rango_x_metros": [min(xs), max(xs)] if xs else None,
        "rango_y_metros": [min(ys), max(ys)] if ys else None,
        "detalle_muestra": detalle,
    }


def compute_divipola_correspondence(df_limites: pd.DataFrame) -> dict:
    """Compara COD_MPIO de límites municipales contra cod_dane_mpio de
    DIVIPOLA limpia (Fase 3B), por código, no por nombre."""
    dv = pd.read_csv(DIVIPOLA_CLEAN_PATH, dtype={"cod_dane_mpio": str})
    set_limites = set(df_limites["cod_dane_mpio"].astype(str))
    set_divipola = set(dv["cod_dane_mpio"].astype(str))
    en_ambos = set_limites & set_divipola
    solo_limites = sorted(set_limites - set_divipola)
    solo_divipola = sorted(set_divipola - set_limites)
    union = set_limites | set_divipola
    pct = round(len(en_ambos) / len(union) * 100, 2) if union else 0.0
    return {
        "codigos_en_ambas_fuentes": len(en_ambos),
        "codigos_solo_en_limites": solo_limites,
        "codigos_solo_en_divipola": solo_divipola,
        "porcentaje_correspondencia": pct,
    }


def build_limites_municipales_cleaning_report(
    clean_report: dict,
    crs_validation: dict,
    correspondencia: dict,
    archivos_info: list[dict],
    total_size: int,
) -> str:
    lines = [
        "# Reporte de limpieza — Límites municipales DANE (Fase 3D)",
        "",
        "Generado automáticamente por `scripts/03_clean_raw_data.py`. Preparación espacial de "
        "la capa municipal descargada en la Fase 2C. **No se intersectó todavía con el "
        "Catastro Minero ni se construyó ningún indicador.**",
        "",
        f"- Features: {clean_report['filas_entrada']} -> {clean_report['filas_salida']} "
        "(ninguna se elimina por invalidez de geometría)",
        f"- Partes procesadas: {len(archivos_info)} | Tamaño total: {format_bytes(total_size)}",
        f"- CRS de almacenamiento: `{CRS_ORIGEN}` | CRS métrico propuesto (Fase 4A): `{CRS_METRICO_PROPUESTO}`",
        "",
        "## Calidad de cod_dane_mpio",
        "",
        f"- Vacíos: {clean_report['validaciones']['n_cod_dane_mpio_vacios']} | "
        f"Duplicados: {clean_report['validaciones']['n_cod_dane_mpio_duplicados']} | "
        f"Es único: {clean_report['validaciones']['cod_dane_mpio_es_unico']} | "
        f"Longitud 5 en todas las filas: {clean_report['validaciones']['cod_dane_mpio_longitud_5_para_todas_las_filas']}",
        "",
        "## Calidad de geometrías",
        "",
        f"- Nulas (entrada): {clean_report['validaciones']['n_geometrias_nulas_entrada']}",
        f"- Inválidas ANTES de limpiar: {clean_report['validaciones']['n_geometrias_invalidas_entrada']}",
        f"- Geometrías reparadas (shapely.make_valid): {clean_report['validaciones']['n_geometrias_reparadas']}",
        f"- Inválidas DESPUÉS de limpiar: {clean_report['validaciones']['n_geometrias_invalidas_salida']}",
        f"- Vacías tras reparar (sin componente poligonal recuperable): {clean_report['validaciones']['n_geometrias_vacias_salida']}",
        f"- Tipos geométricos finales: {clean_report['validaciones']['tipos_geometricos_finales']}",
        "",
    ]

    lines.append("## Reparaciones de geometría (detalle)")
    lines.append("")
    if clean_report["reparaciones_detalle"]:
        lines.append("| cod_dane_mpio | motivo | tipo original | tipo make_valid | GeometryCollection? | vacía? | componentes poligonales | descartados |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in clean_report["reparaciones_detalle"]:
            lines.append(
                f"| {r['feature_id']} | {r['motivo_invalidez']} | {r['tipo_original']} | "
                f"{r['tipo_resultante_make_valid']} | {r['paso_a_geometrycollection']} | "
                f"{r['quedo_vacia']} | {r['n_componentes_poligonales_finales']} | "
                f"{r['componentes_no_poligonales_descartados'] or 'ninguno'} |"
            )
    else:
        lines.append("_No hubo geometrías inválidas que reparar en esta corrida (0 detectadas)._")
    lines.append("")

    lines.append("## Validación CRS métrico propuesto (EPSG:9377)")
    lines.append("")
    lines.append(
        f"- Muestra: {crs_validation['muestra_tamano']} centroides transformados de "
        f"{CRS_ORIGEN} a {CRS_METRICO_PROPUESTO} con pyproj."
    )
    lines.append(f"- Errores de transformación: {crs_validation['n_errores_transformacion']}")
    lines.append(f"- Rango X resultante (metros): {crs_validation['rango_x_metros']}")
    lines.append(f"- Rango Y resultante (metros): {crs_validation['rango_y_metros']}")
    lines.append(
        "- **No se reemplazó la geometría almacenada**: la salida sigue en EPSG:4326. Esta "
        "validación solo confirma que la transformación a EPSG:9377 es técnicamente viable "
        "para la Fase 4A (intersecciones y cálculo de áreas), donde si se necesitará "
        "reproyectar para obtener áreas en unidades métricas correctas."
    )
    lines.append("")

    lines.append("## Correspondencia con DIVIPOLA limpia (Fase 3B)")
    lines.append("")
    lines.append(f"- Códigos en ambas fuentes: {correspondencia['codigos_en_ambas_fuentes']}")
    lines.append(f"- Solo en límites municipales: {correspondencia['codigos_solo_en_limites']}")
    lines.append(f"- Solo en DIVIPOLA: {correspondencia['codigos_solo_en_divipola']}")
    lines.append(f"- Porcentaje de correspondencia: {correspondencia['porcentaje_correspondencia']}%")
    lines.append("")

    lines.append("## Archivos y tamaños")
    lines.append("")
    lines.append("| Parte | Archivo | Features | Tamaño |")
    lines.append("|---|---|---|---|")
    for a in archivos_info:
        lines.append(f"| {a['parte']} | {a['archivo']} | {a['features']} | {format_bytes(a['tamano_bytes'])} |")
    lines.append("")

    lines.append("## Observaciones y decisiones de limpieza")
    lines.append("")
    for obs in clean_report["observaciones"]:
        lines.append(f"- {obs}")
    lines.append("")

    lines.append("## Riesgos pendientes para integración (Fase 4+)")
    lines.append("")
    lines.append(
        "- El municipio con código `94663` (Mapiripana, Guainía) está en esta capa pero no en "
        "DIVIPOLA; el municipio `27493` (Nuevo Belén de Bajirá, Chocó) está en DIVIPOLA pero no "
        "en esta capa geométrica. Cualquier cruce por código debe decidir explícitamente cómo "
        "tratar estos dos casos (no se afirma aquí cuál código es 'correcto')."
    )
    lines.append(
        "- La reproyección real a EPSG:9377 y el cálculo de áreas quedan para la Fase 4A; aquí "
        "solo se validó que la transformación es técnicamente posible."
    )
    lines.append(
        "- El dataset es pesado (geometrías sin simplificar); cualquier operación espacial "
        "futura (intersección con catastro minero) deberá considerar el costo computacional."
    )
    lines.append("")

    return "\n".join(lines)


def run_limites_municipales() -> tuple[str, dict]:
    features, raw_manifest = load_limites_municipales_raw_features()
    df_clean, clean_report = clean_limites_municipales_dane(features)

    crs_validation = validate_crs_transform_sample(df_clean)
    correspondencia = compute_divipola_correspondence(df_clean)

    ensure_dir(LIMITES_OUT_DIR)
    partes_origen = sorted(raw_manifest["tamano_por_parte"], key=lambda p: p["parte"])

    archivos_info = []
    idx = 0
    for p in partes_origen:
        n = p["features"]
        chunk = df_clean.iloc[idx : idx + n].reset_index(drop=True)
        idx += n
        assert len(chunk) > 0, f"Parte {p['parte']} quedó vacía al particionar la salida limpia"

        out_path = LIMITES_OUT_DIR / f"limites_municipales_dane_clean_part_{p['parte']:04d}.geojson"
        size = write_rfc7946_geojson(chunk, out_path, geometry_col="_geometry")
        archivos_info.append(
            {"parte": p["parte"], "archivo": out_path.name, "features": len(chunk), "tamano_bytes": size}
        )

        write_cleaning_metadata(
            out_path.with_suffix(out_path.suffix + ".metadata.json"),
            fuente=f"Límites municipales DANE (parte {p['parte']} de {len(partes_origen)})",
            ruta_entrada=str((LIMITES_RAW_DIR / p["archivo"]).relative_to(PROJECT_ROOT)),
            ruta_salida=str(out_path.relative_to(PROJECT_ROOT)),
            tamano_bytes=size,
            report={"filas": len(chunk), "estado": "completo", "crs": CRS_ORIGEN},
        )

    assert idx == len(df_clean), (
        f"Partición incompleta: se repartieron {idx} de {len(df_clean)} features"
    )

    total_size = sum(a["tamano_bytes"] for a in archivos_info)

    manifest_procesado = {
        "fuente": "Límites municipales DANE (DIVIPOLA - capa Municipios, ArcGIS REST)",
        "fecha_procesamiento": utc_now_iso(),
        "crs": CRS_ORIGEN,
        "crs_metrico_propuesto_fase4a": CRS_METRICO_PROPUESTO,
        "total_features_entrada": clean_report["filas_entrada"],
        "total_features_salida": clean_report["filas_salida"],
        "numero_partes": len(archivos_info),
        "codigos_unicos": int(df_clean["cod_dane_mpio"].nunique()),
        "geometrias_nulas": clean_report["validaciones"]["n_geometrias_nulas_entrada"],
        "geometrias_invalidas_antes": clean_report["validaciones"]["n_geometrias_invalidas_entrada"],
        "geometrias_invalidas_despues": clean_report["validaciones"]["n_geometrias_invalidas_salida"],
        "geometrias_reparadas": clean_report["validaciones"]["n_geometrias_reparadas"],
        "tipos_geometricos_finales": clean_report["validaciones"]["tipos_geometricos_finales"],
        "correspondencia_con_divipola": correspondencia,
        "validacion_crs_9377": {
            "muestra_tamano": crs_validation["muestra_tamano"],
            "n_errores_transformacion": crs_validation["n_errores_transformacion"],
            "rango_x_metros": crs_validation["rango_x_metros"],
            "rango_y_metros": crs_validation["rango_y_metros"],
        },
        "archivos_y_tamanos": archivos_info,
        "observaciones": clean_report["observaciones"]
        + [
            f"CRS métrico propuesto para intersecciones/áreas en Fase 4A: {CRS_METRICO_PROPUESTO} "
            f"(MAGNA-SIRGAS 2018 / Origen-Nacional), validado con una muestra de "
            f"{crs_validation['muestra_tamano']} centroides, {crs_validation['n_errores_transformacion']} errores.",
            "No se reemplazó la geometría almacenada por la versión reproyectada; solo se validó "
            "técnicamente que la transformación es posible. No se calcularon áreas definitivas.",
        ],
    }
    write_json(LIMITES_OUT_DIR / "manifest.json", manifest_procesado, default=json_safe_default)

    report_text = build_limites_municipales_cleaning_report(
        clean_report, crs_validation, correspondencia, archivos_info, total_size
    )
    (REPORTS_DIR / "limites_municipales_dane_cleaning.md").write_text(report_text, encoding="utf-8")

    fuente_label = "Límites municipales DANE (DIVIPOLA - capa Municipios, ArcGIS REST)"
    result_for_summary = {
        **clean_report,
        "ruta_salida": str(LIMITES_OUT_DIR.relative_to(PROJECT_ROOT)) + "/",
        "tamano_bytes": total_size,
    }
    return fuente_label, result_for_summary


def validate_limites_municipales_output(result: dict) -> list[str]:
    problems: list[str] = []
    out_dir = PROJECT_ROOT / result["ruta_salida"]
    manifest_path = out_dir / "manifest.json"
    if not manifest_path.exists():
        problems.append("no se generó manifest.json de la salida procesada")
        return problems

    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)

    if manifest["total_features_salida"] == 0:
        problems.append("0 features en la salida limpia")

    total_leidas = 0
    for a in manifest["archivos_y_tamanos"]:
        part_path = out_dir / a["archivo"]
        if not part_path.exists() or file_size_bytes(part_path) == 0:
            problems.append(f"{a['archivo']}: no existe o está vacío")
            continue
        with open(part_path, encoding="utf-8") as fh:
            fc = json.load(fh)
        if fc["type"] != "FeatureCollection" or not fc["features"]:
            problems.append(f"{a['archivo']}: no es un FeatureCollection no vacío")
        total_leidas += len(fc["features"])

    if total_leidas != manifest["total_features_salida"]:
        problems.append(
            f"suma de features en las partes ({total_leidas}) no coincide con "
            f"total_features_salida del manifest ({manifest['total_features_salida']})"
        )

    if manifest["geometrias_invalidas_despues"] > 0:
        problems.append(
            f"{manifest['geometrias_invalidas_despues']} geometrías siguen inválidas después de la reparación"
        )

    return problems


def validate_output(name: str, result: dict) -> list[str]:
    problems = []
    out_path = PROJECT_ROOT / result["ruta_salida"]
    if not out_path.exists() or file_size_bytes(out_path) == 0:
        problems.append(f"{name}: archivo de salida vacío o inexistente ({out_path})")
    if result["filas_salida"] == 0:
        problems.append(f"{name}: 0 filas en la salida limpia")
    return problems


# --------------------------------------------------------------------------
# Reporte de limpieza
# --------------------------------------------------------------------------


def build_cleaning_summary(results: dict[str, dict]) -> str:
    lines = [
        "# Reporte de limpieza de datos crudos (Fase 3B/3C/3D)",
        "",
        "Generado automáticamente por `scripts/03_clean_raw_data.py`. Cada fuente se limpió",
        "por separado; **no se cruzó ninguna fuente ni se construyó dataset maestro**.",
        "",
        "## Tabla comparativa filas antes/después",
        "",
        "| Fuente | Filas entrada | Filas salida | Diferencia | Tamaño CSV |",
        "|---|---|---|---|---|",
    ]
    for fuente, r in results.items():
        diff = r["filas_entrada"] - r["filas_salida"]
        lines.append(
            f"| {fuente} | {r['filas_entrada']} | {r['filas_salida']} | {diff} | {format_bytes(r['tamano_bytes'])} |"
        )
    lines.append("")

    lines.append("## Registros eliminados y motivo")
    lines.append("")
    for fuente, r in results.items():
        lines.append(f"### {fuente}")
        lines.append("")
        for motivo, n in r["registros_eliminados"].items():
            lines.append(f"- `{motivo}`: {n}")
        lines.append("")

    lines.append("## Columnas finales por fuente")
    lines.append("")
    for fuente, r in results.items():
        lines.append(f"### {fuente}")
        lines.append("")
        lines.append(", ".join(f"`{c}`" for c in r["columnas_finales"]))
        lines.append("")

    lines.append("## Validaciones")
    lines.append("")
    for fuente, r in results.items():
        lines.append(f"### {fuente}")
        lines.append("")
        for k, v in r["validaciones"].items():
            lines.append(f"- `{k}`: {v}")
        lines.append("")

    lines.append("## Observaciones y decisiones de limpieza")
    lines.append("")
    for fuente, r in results.items():
        lines.append(f"### {fuente}")
        lines.append("")
        for obs in r["observaciones"]:
            lines.append(f"- {obs}")
        lines.append("")

    lines.append("## Riesgos pendientes para integración (Fase 4+)")
    lines.append("")
    lines.append(
        "- Ninguna fuente comparte hoy una llave territorial 100% directa: DIVIPOLA tiene "
        "`cod_dane_mpio`, ANM Anotaciones RMN no tiene territorio en absoluto, calidad de agua "
        "solo tiene `departamento_norm`/`municipio_norm` de texto (sin código DANE), y el "
        "catastro minero tiene geometría pero `departamentos_norm`/`municipios_norm` también de "
        "texto (a veces con varias unidades territoriales en una sola cadena)."
    )
    lines.append(
        "- El cruce territorial de calidad de agua/catastro minero con DIVIPOLA requerirá "
        "emparejar texto normalizado (no código), con riesgo de nombres compuestos o variantes "
        "no cubiertas por las equivalencias conocidas."
    )
    lines.append(
        "- `codigo_expediente` de ANM Anotaciones RMN sigue siendo una llave 1-a-muchos: cualquier "
        "integración futura debe decidir si se agrega a nivel de expediente antes de cruzar. En "
        "cambio, `codigo_expediente` del catastro minero geoespacial SÍ es único por feature."
    )
    lines.append(
        "- `resultado_numerico` de calidad de agua tiene nulos por censura de límite de detección "
        "(valores tipo '<0.4'); un análisis agregado ingenuo (promedios, etc.) debe decidir cómo "
        "tratar esos casos, no solo ignorarlos."
    )
    lines.append(
        "- El catastro minero tiene 22 geometrías topológicamente inválidas (sin corregir en esta "
        "fase) y valores centinela `FECHA_TERMINACION = 9999-12-31` que no deben tratarse como "
        "fecha real de vencimiento sin confirmarlo antes."
    )
    lines.append("")

    return "\n".join(lines)


def build_catastro_minero_cleaning_report(result: dict) -> str:
    lines = [
        "# Reporte de limpieza — Catastro Minero ANM (Fase 3C)",
        "",
        "Generado automáticamente por `scripts/03_clean_raw_data.py`. Limpieza de la capa "
        "geoespacial de títulos mineros vigentes descargada en la Fase 2B (WFS ANM). "
        "**No se cruzó con DIVIPOLA ni con ninguna otra fuente.**",
        "",
        f"- Ruta de salida: `{result['ruta_salida']}`",
        f"- Tamaño: {format_bytes(result['tamano_bytes'])}",
        f"- Features: {result['filas_entrada']} -> {result['filas_salida']}",
        f"- Features de origen reportadas por el WFS: {result.get('features_origen_wfs')}",
        "",
        "## Registros eliminados",
        "",
    ]
    for motivo, n in result["registros_eliminados"].items():
        lines.append(f"- `{motivo}`: {n}")
    lines.append("")

    lines.append("## Columnas finales (properties del GeoJSON)")
    lines.append("")
    lines.append(", ".join(f"`{c}`" for c in result["columnas_finales"]))
    lines.append("")
    lines.append(
        "La geometría (`MultiPolygon`) se conserva como el campo `geometry` estándar de cada "
        "Feature, no como una columna de `properties`."
    )
    lines.append("")

    lines.append("## Validaciones")
    lines.append("")
    for k, v in result["validaciones"].items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")

    lines.append("## Calidad de CODIGO_EXPEDIENTE")
    lines.append("")
    lines.append(
        f"- Vacíos: {result['validaciones']['n_codigo_expediente_vacio']} | "
        f"Duplicados: {result['validaciones']['n_codigo_expediente_duplicado']} | "
        f"Es único: {result['validaciones']['codigo_expediente_es_unico']}"
    )
    lines.append("")

    lines.append("## Calidad de geometrías")
    lines.append("")
    lines.append(
        f"- Nulas: {result['validaciones']['n_geometrias_nulas']} | "
        f"Inválidas (topológicamente, vía {result['validaciones']['validez_geometrica_verificada_con']}): "
        f"{result['validaciones']['n_geometrias_invalidas']}"
    )
    lines.append(
        "- Las geometrías inválidas NO se corrigieron ni se descartaron en esta fase; quedan "
        "documentadas como riesgo para análisis espacial futuro."
    )
    lines.append("")

    lines.append("## Calidad de fechas")
    lines.append("")
    lines.append(
        f"- FECHA_DE_INSCRIPCION no parseable: {result['validaciones']['n_fecha_inscripcion_no_parseable']} | "
        f"FECHA_TERMINACION no parseable: {result['validaciones']['n_fecha_terminacion_no_parseable']}"
    )
    lines.append("")

    lines.append("## Observaciones y decisiones de limpieza")
    lines.append("")
    for obs in result["observaciones"]:
        lines.append(f"- {obs}")
    lines.append("")

    lines.append("## Riesgos pendientes para integración (Fase 4+)")
    lines.append("")
    lines.append(
        "- DEPARTAMENTOS/MUNICIPIOS son texto libre con posibles valores múltiples por feature "
        "(separados por coma): un cruce por municipio individual requerirá explotar (split) estos "
        "campos antes de integrarlos con DIVIPOLA."
    )
    lines.append(
        f"- {result['validaciones']['n_geometrias_invalidas']} geometrías topológicamente inválidas: "
        "cualquier operación espacial (intersección, área exacta, unión con otras capas) debe "
        "decidir explícitamente si se corrigen (p. ej. buffer(0)) antes de usarlas."
    )
    lines.append(
        "- `FECHA_TERMINACION` en año 9999 es casi con certeza un valor centinela de 'sin "
        "vencimiento', no una fecha real; no debe usarse en cálculos de antigüedad/vigencia sin "
        "tratarlo como caso especial."
    )
    lines.append(
        "- El geoservicio de origen declara última actualización '22/03/2023'; conviene volver a "
        "validar vigencia con la ANM antes de un uso analítico o público de este catastro."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    print("=== AquaBosque Minero IA — Fase 3B/3C/3D: limpieza de datos crudos ===\n")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    runners = [run_divipola, run_anm, run_calidad_agua, run_catastro_minero]
    results: dict[str, dict] = {}
    problems: list[str] = []

    for runner in runners:
        print(f"-> Limpiando: {runner.__name__} ...")
        fuente, result = runner()
        results[fuente] = result
        print(
            f"   filas: {result['filas_entrada']} -> {result['filas_salida']} | "
            f"tamaño: {format_bytes(result['tamano_bytes'])}"
        )
        problems.extend(validate_output(fuente, result))
        print()

    print("-> Limpiando: run_limites_municipales (requiere divipola_municipios_clean.csv ya generado) ...")
    fuente_limites, result_limites = run_limites_municipales()
    results[fuente_limites] = result_limites
    print(
        f"   features: {result_limites['filas_entrada']} -> {result_limites['filas_salida']} | "
        f"tamaño total: {format_bytes(result_limites['tamano_bytes'])}"
    )
    problems.extend(validate_limites_municipales_output(result_limites))
    print()

    summary = build_cleaning_summary(results)
    summary_path = REPORTS_DIR / "cleaning_summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"Reporte de limpieza -> {summary_path.relative_to(PROJECT_ROOT)}")

    catastro_result = results["Catastro Minero ANM - Títulos Vigentes (WFS)"]
    catastro_report = build_catastro_minero_cleaning_report(catastro_result)
    catastro_report_path = REPORTS_DIR / "catastro_minero_anm_cleaning.md"
    catastro_report_path.write_text(catastro_report, encoding="utf-8")
    print(f"Reporte de limpieza (catastro minero) -> {catastro_report_path.relative_to(PROJECT_ROOT)}")
    print(f"Reporte de limpieza (límites municipales) -> {(REPORTS_DIR / 'limites_municipales_dane_cleaning.md').relative_to(PROJECT_ROOT)}")

    print("\n=== Resumen ===")
    for fuente, r in results.items():
        print(f"[OK] {fuente}: {r['filas_entrada']} -> {r['filas_salida']} filas, {r['ruta_salida']}")

    if problems:
        print("\nAtención: problemas detectados:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("\nLimpieza completa. No se cruzó ninguna fuente ni se construyó dataset maestro.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
