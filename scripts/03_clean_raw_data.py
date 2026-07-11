"""Fase 3B / 3C: limpieza y estandarización de las fuentes MVP.

Lee los datos crudos ya descargados (Fase 2A/2A.1/2B) y perfilados (Fase 3A/3C) y
genera una versión limpia por fuente en data/processed/. Cada fuente se
limpia por separado: este script NO cruza las fuentes entre sí ni construye
ningún dataset maestro. No descarga nada nuevo, no entrena modelo, no crea
dashboard.

Salidas:
  data/processed/territorio/divipola_municipios_clean.csv (+ .metadata.json)
  data/processed/mineria/anm_anotaciones_rmn_clean.csv (+ .metadata.json)
  data/processed/agua/ideam_calidad_agua_clean.csv (+ .metadata.json)
  data/processed/mineria/catastro_minero_anm_clean.geojson (+ .metadata.json)
  outputs/reports/cleaning/cleaning_summary.md
  outputs/reports/cleaning/catastro_minero_anm_cleaning.md
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
        "# Reporte de limpieza de datos crudos (Fase 3B)",
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
    print("=== AquaBosque Minero IA — Fase 3B/3C: limpieza de datos crudos ===\n")
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

    summary = build_cleaning_summary(results)
    summary_path = REPORTS_DIR / "cleaning_summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"Reporte de limpieza -> {summary_path.relative_to(PROJECT_ROOT)}")

    catastro_result = results["Catastro Minero ANM - Títulos Vigentes (WFS)"]
    catastro_report = build_catastro_minero_cleaning_report(catastro_result)
    catastro_report_path = REPORTS_DIR / "catastro_minero_anm_cleaning.md"
    catastro_report_path.write_text(catastro_report, encoding="utf-8")
    print(f"Reporte de limpieza (catastro minero) -> {catastro_report_path.relative_to(PROJECT_ROOT)}")

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
