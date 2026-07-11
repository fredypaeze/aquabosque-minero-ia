"""Funciones de descarga liviana para fuentes MVP de AquaBosque Minero IA.

Fase 2A: solo cubre descarga directa de archivos pequeños (p. ej. XLSX) y
descarga paginada de datasets Socrata (API SODA de datos.gov.co). No procesa
ni limpia los datos descargados.

Todas las funciones respetan un límite duro de tamaño (`max_bytes`, por
defecto 20 MB) para no descargar archivos pesados sin autorización explícita:
si una fuente excede el límite, la descarga se detiene y queda registrada con
estado "truncado_por_tamano" u "omitido_por_tamano" en vez de completarse.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import requests

from ..utils.io import ensure_dir, file_size_bytes, utc_now_iso, write_json

MAX_BYTES_DEFAULT = 20 * 1024 * 1024  # 20 MB
DEFAULT_TIMEOUT = 30
DEFAULT_PAGE_SIZE = 1000
USER_AGENT = "AquaBosqueMineroIA/0.1 (uso academico/institucional, descarga controlada)"


@dataclass
class DownloadResult:
    fuente: str
    url: str
    dest_path: Path
    formato: str
    estado: str
    tamano_bytes: int
    filas_descargadas: int | None = None
    observaciones: str = ""


def download_direct_file(
    fuente: str,
    url: str,
    dest_path: Path,
    *,
    max_bytes: int = MAX_BYTES_DEFAULT,
    timeout: int = DEFAULT_TIMEOUT,
    formato: str = "binario",
) -> DownloadResult:
    """Descarga un archivo directo (p. ej. XLSX) con límite de tamaño.

    Antes de descargar, hace un HEAD para verificar Content-Length cuando esté
    disponible. Si se conoce y supera max_bytes, no descarga.
    """
    headers = {"User-Agent": USER_AGENT}

    try:
        head = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
        content_length = head.headers.get("Content-Length")
        if content_length is not None and int(content_length) > max_bytes:
            return DownloadResult(
                fuente=fuente,
                url=url,
                dest_path=dest_path,
                formato=formato,
                estado="omitido_por_tamano",
                tamano_bytes=int(content_length),
                observaciones=(
                    f"Content-Length ({int(content_length)} bytes) supera el límite "
                    f"de {max_bytes} bytes; se requiere autorización antes de descargar."
                ),
            )
    except requests.RequestException as exc:
        return DownloadResult(
            fuente=fuente,
            url=url,
            dest_path=dest_path,
            formato=formato,
            estado="error",
            tamano_bytes=0,
            observaciones=f"Fallo en HEAD request: {exc}",
        )

    try:
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        ensure_dir(dest_path.parent)
        downloaded = 0
        with open(dest_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > max_bytes:
                    fh.close()
                    dest_path.unlink(missing_ok=True)
                    return DownloadResult(
                        fuente=fuente,
                        url=url,
                        dest_path=dest_path,
                        formato=formato,
                        estado="omitido_por_tamano",
                        tamano_bytes=downloaded,
                        observaciones=(
                            f"Descarga cancelada: superó {max_bytes} bytes sin que "
                            "Content-Length lo advirtiera de antemano."
                        ),
                    )
                fh.write(chunk)
    except requests.RequestException as exc:
        return DownloadResult(
            fuente=fuente,
            url=url,
            dest_path=dest_path,
            formato=formato,
            estado="error",
            tamano_bytes=0,
            observaciones=f"Fallo en GET request: {exc}",
        )

    size = file_size_bytes(dest_path)
    if size == 0:
        return DownloadResult(
            fuente=fuente,
            url=url,
            dest_path=dest_path,
            formato=formato,
            estado="error",
            tamano_bytes=0,
            observaciones="El archivo descargado quedó vacío (0 bytes).",
        )

    return DownloadResult(
        fuente=fuente,
        url=url,
        dest_path=dest_path,
        formato=formato,
        estado="completo",
        tamano_bytes=size,
        observaciones="Descarga directa completa.",
    )


def download_socrata_json(
    fuente: str,
    resource_url: str,
    dest_path: Path,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_bytes: int = MAX_BYTES_DEFAULT,
    timeout: int = DEFAULT_TIMEOUT,
    extra_params: dict | None = None,
) -> DownloadResult:
    """Descarga paginada (`$limit`/`$offset`) de un recurso Socrata como JSON.

    Se detiene apenas el tamaño acumulado estimado supera max_bytes, dejando
    un archivo parcial (las páginas completas ya obtenidas) y marcando el
    estado como "truncado_por_tamano" en vez de continuar sin autorización.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    all_rows: list[dict] = []
    offset = 0
    accumulated_bytes = 0
    truncated = False

    while True:
        params = {"$limit": page_size, "$offset": offset}
        if extra_params:
            params.update(extra_params)

        try:
            response = requests.get(resource_url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            if all_rows:
                # Ya hay datos parciales válidos: se guarda lo obtenido hasta el error.
                break
            return DownloadResult(
                fuente=fuente,
                url=resource_url,
                dest_path=dest_path,
                formato="json (API Socrata)",
                estado="error",
                tamano_bytes=0,
                observaciones=f"Fallo en petición paginada (offset={offset}): {exc}",
            )

        page_bytes = len(response.content)
        page_rows = response.json()

        if not page_rows:
            break

        if accumulated_bytes + page_bytes > max_bytes:
            truncated = True
            break

        all_rows.extend(page_rows)
        accumulated_bytes += page_bytes
        offset += len(page_rows)

        if len(page_rows) < page_size:
            break

    if not all_rows:
        return DownloadResult(
            fuente=fuente,
            url=resource_url,
            dest_path=dest_path,
            formato="json (API Socrata)",
            estado="error",
            tamano_bytes=0,
            observaciones="No se obtuvo ninguna fila desde la API.",
        )

    size = write_json(dest_path, all_rows, compact=True)

    # Verificación dura final: el tamaño real del archivo escrito nunca puede
    # superar max_bytes, sin importar qué tan preciso fue el conteo por página.
    while size > max_bytes and all_rows:
        truncated = True
        remove_n = max(1, int(len(all_rows) * 0.05))
        all_rows = all_rows[:-remove_n]
        size = write_json(dest_path, all_rows, compact=True)

    if not all_rows:
        return DownloadResult(
            fuente=fuente,
            url=resource_url,
            dest_path=dest_path,
            formato="json (API Socrata)",
            estado="error",
            tamano_bytes=0,
            observaciones="Ni siquiera una fila cupo dentro del límite de tamaño.",
        )

    estado = "truncado_por_tamano" if truncated else "completo"
    if truncated:
        detalle = (
            "Se detuvo antes del límite de tamaño; hay más filas disponibles en el "
            "origen y se requiere autorización para continuar."
        )
    else:
        detalle = "Se recuperaron todas las filas disponibles."
    observaciones = f"Descarga paginada ({page_size} filas/página). {detalle}"

    return DownloadResult(
        fuente=fuente,
        url=resource_url,
        dest_path=dest_path,
        formato="json (API Socrata)",
        estado=estado,
        tamano_bytes=size,
        filas_descargadas=len(all_rows),
        observaciones=observaciones,
    )


@dataclass
class BatchPart:
    part_num: int
    path: Path
    offset_inicio: int
    offset_fin: int
    filas: int
    tamano_bytes: int


@dataclass
class BatchDownloadResult:
    fuente: str
    url: str
    dest_dir: Path
    total_filas_origen: int | None
    total_filas_descargadas: int
    numero_partes: int
    tamano_total_bytes: int
    parts: list[BatchPart] = field(default_factory=list)
    estado: str = "completo"
    observaciones: str = ""


def get_socrata_row_count(resource_url: str, *, timeout: int = DEFAULT_TIMEOUT) -> int | None:
    """Consulta el total de filas de un recurso Socrata vía `$select=count(*)`."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        response = requests.get(
            resource_url,
            headers=headers,
            params={"$select": "count(*)"},
            timeout=timeout,
        )
        response.raise_for_status()
        rows = response.json()
        if rows and "count" in rows[0]:
            return int(rows[0]["count"])
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None
    return None


def _json_bytes_len(rows: list[dict]) -> int:
    return len(json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def download_socrata_batched(
    fuente: str,
    resource_url: str,
    dest_dir: Path,
    *,
    filename_prefix: str,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_bytes_per_part: int = MAX_BYTES_DEFAULT,
    timeout: int = DEFAULT_TIMEOUT,
) -> BatchDownloadResult:
    """Descarga completa y paginada de un recurso Socrata, partida en varios
    archivos para que ninguno supere `max_bytes_per_part`.

    Cada parte agrupa una o más páginas consecutivas de `$limit`/`$offset`
    Socrata; se cierra (se escribe a disco) apenas agregar la siguiente página
    haría que el archivo superase el límite de tamaño. Los offsets usados por
    cada parte quedan registrados para poder auditar que no falten rangos ni
    haya offsets duplicados.
    """
    ensure_dir(dest_dir)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    total_origin = get_socrata_row_count(resource_url, timeout=timeout)

    parts: list[BatchPart] = []
    part_rows: list[dict] = []
    part_start_offset = 0
    part_num = 0
    offset = 0
    total_rows = 0
    error_msg: str | None = None

    def flush_part(rows: list[dict], start_offset: int, end_offset: int) -> None:
        nonlocal part_num
        part_num += 1
        part_path = dest_dir / f"{filename_prefix}_part_{part_num:04d}.json"
        size = write_json(part_path, rows, compact=True)
        parts.append(
            BatchPart(
                part_num=part_num,
                path=part_path,
                offset_inicio=start_offset,
                offset_fin=end_offset,
                filas=len(rows),
                tamano_bytes=size,
            )
        )

    while True:
        params = {"$limit": page_size, "$offset": offset}
        try:
            response = requests.get(resource_url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            page_rows = response.json()
        except (requests.RequestException, ValueError) as exc:
            error_msg = f"Fallo en petición paginada (offset={offset}): {exc}"
            break

        if not page_rows:
            break

        candidate_rows = part_rows + page_rows
        candidate_size = _json_bytes_len(candidate_rows)

        if candidate_size > max_bytes_per_part and part_rows:
            # La página actual no cabe en la parte en curso: se cierra la
            # parte con lo acumulado hasta ahora (sin esta página) y se abre
            # una nueva parte que empieza con esta página.
            flush_part(part_rows, part_start_offset, offset)
            part_rows = list(page_rows)
            part_start_offset = offset
        elif candidate_size > max_bytes_per_part and not part_rows:
            # Una sola página ya supera el límite (caso extremo): se recorta
            # fila por fila hasta que quepa, sin perder la garantía de tamaño.
            trimmed = list(page_rows)
            while trimmed and _json_bytes_len(trimmed) > max_bytes_per_part:
                trimmed = trimmed[:-1]
            if trimmed:
                flush_part(trimmed, offset, offset + len(trimmed))
            part_rows = []
            part_start_offset = offset + len(trimmed)
        else:
            part_rows = candidate_rows

        total_rows += len(page_rows)
        offset += len(page_rows)

        if len(page_rows) < page_size:
            break

    if part_rows:
        flush_part(part_rows, part_start_offset, offset)

    total_size = sum(p.tamano_bytes for p in parts)
    total_rows_written = sum(p.filas for p in parts)

    if error_msg and not parts:
        estado = "error"
        observaciones = error_msg
    elif error_msg:
        estado = "incompleto_por_error"
        observaciones = (
            f"Se descargaron {total_rows_written} filas en {len(parts)} partes antes de un "
            f"error de red; hay que reintentar para completar. {error_msg}"
        )
    elif total_origin is not None and total_rows_written < total_origin:
        estado = "incompleto"
        observaciones = (
            f"Se esperaban {total_origin} filas según el conteo de origen, pero solo se "
            f"descargaron {total_rows_written}."
        )
    else:
        estado = "completo"
        observaciones = (
            f"Descarga por lotes completa: {total_rows_written} filas en {len(parts)} "
            f"partes, ninguna mayor a {max_bytes_per_part} bytes."
        )

    return BatchDownloadResult(
        fuente=fuente,
        url=resource_url,
        dest_dir=dest_dir,
        total_filas_origen=total_origin,
        total_filas_descargadas=total_rows_written,
        numero_partes=len(parts),
        tamano_total_bytes=total_size,
        parts=parts,
        estado=estado,
        observaciones=observaciones,
    )


def write_batch_manifest(manifest_path: Path, result: BatchDownloadResult) -> None:
    """Escribe el manifest.json que resume una descarga por lotes."""
    manifest = {
        "fuente": result.fuente,
        "url": result.url,
        "fecha_descarga": utc_now_iso(),
        "total_filas_origen": result.total_filas_origen,
        "total_filas_descargadas": result.total_filas_descargadas,
        "numero_partes": result.numero_partes,
        "tamano_total_bytes": result.tamano_total_bytes,
        "tamano_por_parte": [
            {
                "parte": p.part_num,
                "archivo": p.path.name,
                "filas": p.filas,
                "tamano_bytes": p.tamano_bytes,
            }
            for p in result.parts
        ],
        "offsets_usados": [
            {
                "parte": p.part_num,
                "offset_inicio": p.offset_inicio,
                "offset_fin": p.offset_fin,
            }
            for p in result.parts
        ],
        "estado_final": result.estado,
        "observaciones": result.observaciones,
    }
    write_json(manifest_path, manifest)
