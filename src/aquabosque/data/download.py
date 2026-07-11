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

from dataclasses import dataclass
from pathlib import Path

import requests

from ..utils.io import ensure_dir, file_size_bytes, write_json

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
