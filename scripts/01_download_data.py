"""Fase 2A / 2A.1: descarga controlada de las fuentes MVP aprobadas y livianas.

Descarga únicamente:
  1. DIVIPOLA - Códigos de municipios (DANE), XLSX directo.
  2. ANM Títulos Mineros - Anotaciones RMN (API Socrata, paginada, archivo único).
  3. IDEAM - Data Histórica de Calidad de Agua (API Socrata, paginada, POR LOTES:
     el dataset completo no cabe en un solo archivo de <20 MB, así que se parte
     en varios archivos, cada uno bajo el límite, más un manifest.json).

No descarga RUNAP, SMByC, el catastro minero WFS completo, el MGN completo,
Global Forest Watch, MapBiomas, Sentinel ni Landsat: esas fuentes quedan para
fases posteriores, según lo acordado en la Fase 1.5.

No procesa ni limpia los datos: solo guarda el archivo crudo y su metadata en
data/raw/. Ningún archivo individual supera 20 MB (ver
src/aquabosque/data/download.py); si una fuente de archivo único lo supera,
la descarga se detiene y queda marcada como incompleta en la metadata en vez
de continuar sin autorización.

Reejecutable: cada corrida vuelve a descargar y sobrescribe los archivos de
salida, sus metadata y (para la fuente por lotes) todas las partes y el
manifest, sin fallar si ya existían de una corrida anterior.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.data.download import (  # noqa: E402
    BatchDownloadResult,
    DownloadResult,
    download_direct_file,
    download_socrata_batched,
    download_socrata_json,
    write_batch_manifest,
)
from aquabosque.utils.io import file_size_bytes, format_bytes, write_metadata  # noqa: E402

DATA_RAW = PROJECT_ROOT / "data" / "raw"
MAX_BYTES = 20 * 1024 * 1024  # 20 MB, límite duro para cualquier archivo individual

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
]

BATCH_SOURCE = {
    "id": "ideam_calidad_agua_historica",
    "fuente": "IDEAM - Data Histórica de Calidad de Agua",
    "url": "https://www.datos.gov.co/resource/62gv-3857.json",
    "dest_dir": DATA_RAW / "agua" / "ideam_calidad_agua_historica",
    "filename_prefix": "ideam_calidad_agua_historica",
}


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
            max_bytes=MAX_BYTES,
        )
    elif source["kind"] == "socrata":
        result = download_socrata_json(
            fuente=source["fuente"],
            resource_url=source["url"],
            dest_path=dest,
            max_bytes=MAX_BYTES,
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


def run_batch_source(source: dict) -> BatchDownloadResult:
    result = download_socrata_batched(
        fuente=source["fuente"],
        resource_url=source["url"],
        dest_dir=source["dest_dir"],
        filename_prefix=source["filename_prefix"],
        max_bytes_per_part=MAX_BYTES,
    )

    # Metadata individual por cada parte, igual que las demás fuentes.
    for part in result.parts:
        write_metadata(
            metadata_path_for(part.path),
            fuente=f"{result.fuente} (parte {part.part_num})",
            url=result.url,
            formato="json (API Socrata, parte de lote)",
            estado="completo",
            tamano_bytes=part.tamano_bytes,
            filas_descargadas=part.filas,
            observaciones=(
                f"Parte {part.part_num} de {result.numero_partes}. "
                f"Offsets Socrata [{part.offset_inicio}, {part.offset_fin})."
            ),
        )

    manifest_path = source["dest_dir"] / "manifest.json"
    write_batch_manifest(manifest_path, result)
    return result


def validate_batch_result(result: BatchDownloadResult) -> list[str]:
    """Valida la descarga por lotes según los criterios de la Fase 2A.1.

    Devuelve una lista de problemas encontrados (vacía si todo está bien).
    """
    problems: list[str] = []

    if result.estado not in ("completo",):
        problems.append(f"estado final no es 'completo' (es '{result.estado}')")

    if not result.parts:
        problems.append("no se generó ninguna parte")
        return problems

    # Ningún archivo individual debe superar el límite de tamaño.
    for part in result.parts:
        if part.tamano_bytes > MAX_BYTES:
            problems.append(
                f"parte {part.part_num} ({part.path.name}) pesa {part.tamano_bytes} "
                f"bytes, supera el límite de {MAX_BYTES} bytes"
            )
        if not part.path.exists() or file_size_bytes(part.path) == 0:
            problems.append(f"parte {part.part_num} no existe o está vacía")

    # Todos los JSON deben ser parseables (se relee cada archivo desde disco).
    for part in result.parts:
        try:
            with open(part.path, encoding="utf-8") as fh:
                data = json.load(fh)
            if len(data) != part.filas:
                problems.append(
                    f"parte {part.part_num}: filas en disco ({len(data)}) no coincide "
                    f"con lo reportado ({part.filas})"
                )
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"parte {part.part_num} no es JSON válido: {exc}")

    # No debe haber offsets duplicados ni huecos entre partes consecutivas.
    ordered = sorted(result.parts, key=lambda p: p.offset_inicio)
    expected_next = ordered[0].offset_inicio
    seen_ranges = set()
    for part in ordered:
        range_key = (part.offset_inicio, part.offset_fin)
        if range_key in seen_ranges:
            problems.append(f"offset duplicado en parte {part.part_num}: {range_key}")
        seen_ranges.add(range_key)
        if part.offset_inicio != expected_next:
            problems.append(
                f"hueco o solape de offsets antes de la parte {part.part_num}: "
                f"se esperaba offset_inicio={expected_next}, llegó {part.offset_inicio}"
            )
        expected_next = part.offset_fin

    # La suma de filas descargadas debe coincidir con el total de filas de origen.
    if result.total_filas_origen is not None:
        if result.total_filas_descargadas != result.total_filas_origen:
            problems.append(
                f"total de filas descargadas ({result.total_filas_descargadas}) no "
                f"coincide con el total de origen reportado por Socrata "
                f"({result.total_filas_origen})"
            )
    else:
        problems.append(
            "no se pudo confirmar el total de filas de origen vía Socrata "
            "(count(*) falló); no se puede verificar completitud con certeza"
        )

    return problems


def main() -> int:
    print("=== AquaBosque Minero IA — Fase 2A / 2A.1: descarga controlada ===\n")

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

    print(f"-> Descargando por lotes: {BATCH_SOURCE['fuente']} ...")
    batch_result = run_batch_source(BATCH_SOURCE)
    batch_problems = validate_batch_result(batch_result)
    print(
        f"   estado: {batch_result.estado} | partes: {batch_result.numero_partes} "
        f"| tamaño total: {format_bytes(batch_result.tamano_total_bytes)}"
    )
    print(
        f"   filas descargadas: {batch_result.total_filas_descargadas} "
        f"(origen reportado: {batch_result.total_filas_origen})"
    )
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

    marca_batch = "OK" if not batch_problems else "REVISAR"
    if batch_problems:
        con_problemas += 1
    else:
        ok += 1
    print(
        f"[{marca_batch}] {BATCH_SOURCE['fuente']} (por lotes)\n"
        f"        ruta: {batch_result.dest_dir.relative_to(PROJECT_ROOT)}/\n"
        f"        estado: {batch_result.estado} | partes: {batch_result.numero_partes} "
        f"| tamaño total: {format_bytes(batch_result.tamano_total_bytes)} "
        f"| filas: {batch_result.total_filas_descargadas}"
    )
    for part in batch_result.parts:
        print(
            f"          - {part.path.name}: {part.filas} filas, "
            f"{format_bytes(part.tamano_bytes)}, offsets [{part.offset_inicio}, {part.offset_fin})"
        )
    if batch_problems:
        for p in batch_problems:
            print(f"        observación: {p}")

    total_sources = len(SOURCES) + 1
    print(f"\nFuentes OK: {ok}/{total_sources} | Con problemas: {con_problemas}/{total_sources}")

    if con_problemas:
        print(
            "\nAtención: hay fuentes con problemas (ver detalle arriba). No se "
            "procesó ni limpió ningún dato en esta fase; revisar antes de avanzar."
        )
        return 1

    print("\nTodas las fuentes MVP aprobadas se descargaron correctamente y completas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
