"""Fase 2A: descarga controlada de las fuentes MVP aprobadas y livianas.

Descarga únicamente:
  1. DIVIPOLA - Códigos de municipios (DANE), XLSX directo.
  2. ANM Títulos Mineros - Anotaciones RMN (API Socrata, paginada).
  3. IDEAM - Data Histórica de Calidad de Agua (API Socrata, paginada).

No descarga RUNAP, SMByC, el catastro minero WFS completo, el MGN completo,
Global Forest Watch, MapBiomas, Sentinel ni Landsat: esas fuentes quedan para
fases posteriores, según lo acordado en la Fase 1.5.

No procesa ni limpia los datos: solo guarda el archivo crudo y su metadata en
data/raw/. Cada descarga respeta un límite duro de 20 MB (ver
src/aquabosque/data/download.py); si una fuente lo supera, la descarga se
detiene y queda marcada como incompleta en la metadata en vez de continuar
sin autorización.

Reejecutable: cada corrida vuelve a descargar y sobrescribe los archivos de
salida y su metadata, sin fallar si ya existían de una corrida anterior.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.data.download import (  # noqa: E402
    DownloadResult,
    download_direct_file,
    download_socrata_json,
)
from aquabosque.utils.io import file_size_bytes, format_bytes, write_metadata  # noqa: E402

DATA_RAW = PROJECT_ROOT / "data" / "raw"

SOURCES = [
    {
        "id": "dane_divipola_municipios",
        "fuente": "DIVIPOLA - Códigos de municipios (DANE)",
        "url": "https://geoportal.dane.gov.co/descargas/divipola/DIVIPOLA_Municipios.xlsx",
        "dest": DATA_RAW / "territorio" / "dane_divipola_municipios.xlsx",
        "kind": "direct",
        "formato": "xlsx",
    },
    {
        "id": "anm_titulos_anotaciones_rmn",
        "fuente": "ANM Títulos Mineros - Anotaciones RMN",
        "url": "https://www.datos.gov.co/resource/si2v-pbq5.json",
        "dest": DATA_RAW / "mineria" / "anm_titulos_anotaciones_rmn.json",
        "kind": "socrata",
    },
    {
        "id": "ideam_calidad_agua_historica",
        "fuente": "IDEAM - Data Histórica de Calidad de Agua",
        "url": "https://www.datos.gov.co/resource/62gv-3857.json",
        "dest": DATA_RAW / "agua" / "ideam_calidad_agua_historica.json",
        "kind": "socrata",
    },
]


def metadata_path_for(dest: Path) -> Path:
    return dest.with_suffix(dest.suffix + ".metadata.json")


def run_source(source: dict) -> DownloadResult:
    dest: Path = source["dest"]

    if source["kind"] == "direct":
        result = download_direct_file(
            fuente=source["fuente"],
            url=source["url"],
            dest_path=dest,
            formato=source["formato"],
        )
    elif source["kind"] == "socrata":
        result = download_socrata_json(
            fuente=source["fuente"],
            resource_url=source["url"],
            dest_path=dest,
        )
    else:
        raise ValueError(f"Tipo de descarga desconocido: {source['kind']}")

    write_metadata(
        metadata_path_for(dest),
        fuente=result.fuente,
        url=result.url,
        formato=result.formato,
        estado=result.estado,
        tamano_bytes=result.tamano_bytes,
        filas_descargadas=result.filas_descargadas,
        observaciones=result.observaciones,
    )
    return result


def validate_result(result: DownloadResult) -> str | None:
    """Devuelve un mensaje de problema si el archivo no quedó bien, o None si está OK."""
    if result.estado in ("error", "omitido_por_tamano"):
        return f"no se generó un archivo utilizable ({result.estado})"
    if not result.dest_path.exists():
        return "el archivo de salida no existe"
    if file_size_bytes(result.dest_path) == 0:
        return "el archivo de salida está vacío (0 bytes)"
    return None


def main() -> int:
    print("=== AquaBosque Minero IA — Fase 2A: descarga controlada ===\n")

    results: list[tuple[dict, DownloadResult, str | None]] = []
    for source in SOURCES:
        print(f"-> Descargando: {source['fuente']} ...")
        result = run_source(source)
        problem = validate_result(result)
        results.append((source, result, problem))
        estado_txt = result.estado if not problem else f"{result.estado} (PROBLEMA: {problem})"
        print(f"   estado: {estado_txt} | tamaño: {format_bytes(result.tamano_bytes)}")
        if result.filas_descargadas is not None:
            print(f"   filas descargadas: {result.filas_descargadas}")
        print()

    print("=== Resumen de la descarga ===")
    ok = 0
    con_problemas = 0
    for source, result, problem in results:
        marca = "OK" if not problem else "REVISAR"
        if problem:
            con_problemas += 1
        else:
            ok += 1
        filas = f", {result.filas_descargadas} filas" if result.filas_descargadas is not None else ""
        print(
            f"[{marca}] {source['fuente']}\n"
            f"        ruta: {result.dest_path.relative_to(PROJECT_ROOT)}\n"
            f"        estado: {result.estado} | tamaño: {format_bytes(result.tamano_bytes)}{filas}"
        )
        if problem:
            print(f"        observación: {problem} — {result.observaciones}")

    print(f"\nFuentes OK: {ok}/{len(SOURCES)} | Con problemas: {con_problemas}/{len(SOURCES)}")

    if con_problemas:
        print(
            "\nAtención: hay fuentes con problemas (ver detalle arriba). No se "
            "procesó ni limpió ningún dato en esta fase; revisar antes de avanzar."
        )
        return 1

    print("\nTodas las fuentes MVP aprobadas se descargaron correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
