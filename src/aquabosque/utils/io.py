"""Utilidades de entrada/salida para descargas y metadata de AquaBosque Minero IA."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    """Crea el directorio (y padres) si no existe. Devuelve el mismo path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_now_iso() -> str:
    """Fecha y hora actual en UTC, formato ISO 8601."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, data: Any, *, compact: bool = False, default: Any = None) -> int:
    """Escribe un objeto como JSON (UTF-8) y devuelve el tamaño en bytes.

    compact=False (por defecto) usa indent=2, legible para archivos pequeños
    como metadata. compact=True usa separadores sin espacios, para no inflar
    el tamaño de payloads de datos grandes por encima de los límites de
    descarga controlada. `default`, si se pasa, se reenvía a json.dumps para
    serializar tipos no nativos (p. ej. numpy.int64) sin tener que
    convertirlos a mano antes de llamar a esta función.
    """
    ensure_dir(path.parent)
    kwargs: dict[str, Any] = {"ensure_ascii": False}
    if default is not None:
        kwargs["default"] = default
    if compact:
        kwargs["separators"] = (",", ":")
    else:
        kwargs["indent"] = 2
    text = json.dumps(data, **kwargs)
    path.write_text(text, encoding="utf-8")
    return path.stat().st_size


def write_bytes(path: Path, content: bytes) -> int:
    """Escribe bytes crudos a un archivo y devuelve el tamaño en bytes."""
    ensure_dir(path.parent)
    path.write_bytes(content)
    return path.stat().st_size


def file_size_bytes(path: Path) -> int:
    """Tamaño en bytes de un archivo existente; 0 si no existe."""
    return path.stat().st_size if path.exists() else 0


def format_bytes(num_bytes: int) -> str:
    """Formatea un tamaño en bytes a una cadena legible (KB/MB)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def write_metadata(
    metadata_path: Path,
    *,
    fuente: str,
    url: str,
    formato: str,
    estado: str,
    tamano_bytes: int,
    filas_descargadas: int | None = None,
    observaciones: str = "",
) -> None:
    """Escribe el archivo de metadata JSON asociado a una descarga."""
    metadata = {
        "fuente": fuente,
        "url": url,
        "fecha_descarga": utc_now_iso(),
        "formato": formato,
        "filas_descargadas": filas_descargadas,
        "tamano_bytes": tamano_bytes,
        "estado": estado,
        "observaciones": observaciones,
    }
    write_json(metadata_path, metadata)
