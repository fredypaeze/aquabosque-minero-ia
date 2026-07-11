"""Fase 3B: limpieza y estandarización de las 3 fuentes MVP.

Lee los datos crudos ya descargados (Fase 2A/2A.1) y perfilados (Fase 3A) y
genera una versión limpia por fuente en data/processed/. Cada fuente se
limpia por separado: este script NO cruza las fuentes entre sí ni construye
ningún dataset maestro. No descarga nada nuevo, no entrena modelo, no crea
dashboard.

Salidas:
  data/processed/territorio/divipola_municipios_clean.csv (+ .metadata.json)
  data/processed/mineria/anm_anotaciones_rmn_clean.csv (+ .metadata.json)
  data/processed/agua/ideam_calidad_agua_clean.csv (+ .metadata.json)
  outputs/reports/cleaning/cleaning_summary.md
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
    clean_divipola,
)
from aquabosque.utils.io import ensure_dir, file_size_bytes, format_bytes, utc_now_iso, write_json  # noqa: E402

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "cleaning"

DIVIPOLA_PATH = DATA_RAW / "territorio" / "dane_divipola_municipios.xlsx"
ANM_PATH = DATA_RAW / "mineria" / "anm_titulos_anotaciones_rmn.json"
AGUA_DIR = DATA_RAW / "agua" / "ideam_calidad_agua_historica"
AGUA_MANIFEST_PATH = AGUA_DIR / "manifest.json"


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


# --------------------------------------------------------------------------
# Escritura de salidas
# --------------------------------------------------------------------------


def write_clean_csv(df: pd.DataFrame, path: Path) -> int:
    ensure_dir(path.parent)
    df.to_csv(path, index=False, encoding="utf-8")
    return file_size_bytes(path)


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


def validate_output(name: str, result: dict) -> list[str]:
    problems = []
    csv_path = PROJECT_ROOT / result["ruta_salida"]
    if not csv_path.exists() or file_size_bytes(csv_path) == 0:
        problems.append(f"{name}: archivo de salida vacío o inexistente ({csv_path})")
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
        "`cod_dane_mpio`, pero ANM Anotaciones RMN no tiene territorio y calidad de agua solo "
        "tiene `departamento_norm`/`municipio_norm` de texto (sin código DANE)."
    )
    lines.append(
        "- El cruce territorial de calidad de agua con DIVIPOLA requerirá emparejar "
        "`municipio_norm` contra `nombre_mpio_norm` (texto normalizado, no código), con riesgo "
        "de nombres compuestos o variantes no cubiertas por las equivalencias conocidas."
    )
    lines.append(
        "- `codigo_expediente` de ANM sigue siendo una llave 1-a-muchos: cualquier integración "
        "futura debe decidir si se agrega a nivel de expediente antes de cruzar."
    )
    lines.append(
        "- `resultado_numerico` de calidad de agua tiene nulos por censura de límite de detección "
        "(valores tipo '<0.4'); un análisis agregado ingenuo (promedios, etc.) debe decidir cómo "
        "tratar esos casos, no solo ignorarlos."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    print("=== AquaBosque Minero IA — Fase 3B: limpieza de datos crudos ===\n")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    runners = [run_divipola, run_anm, run_calidad_agua]
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
