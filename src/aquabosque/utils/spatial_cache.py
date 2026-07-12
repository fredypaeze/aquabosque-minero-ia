"""Caché espacial regenerable (Fase 4A).

Guarda las geometrías territoriales ya reproyectadas a un CRS métrico para
no repetir el paso más costoso del pipeline minero-territorial (reproyectar
~1.122 polígonos muy detallados tomó ~40 s en la prueba de la Fase 3D.1) en
cada corrida.

El caché es completamente regenerable y se invalida automáticamente si
cambian los archivos de origen (por tamaño + hash SHA-256, no por fecha de
modificación). **No se serializa el índice `STRtree`**: la versión de
shapely usada aquí no garantiza que sea serializable de forma estable entre
procesos/versiones, así que el índice se reconstruye en cada ejecución a
partir de la lista de geometrías cacheada (reconstruir el STRtree en sí es
rápido; lo costoso es la reproyección, que sí se cachea).
"""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any

from shapely.geometry.base import BaseGeometry

from .io import ensure_dir, utc_now_iso, write_json


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_source_fingerprint(source_paths: list[Path]) -> dict[str, dict]:
    """Huella (tamaño + SHA-256) de los archivos de origen, para invalidar el
    caché si cambian los límites territoriales u otra geometría de entrada."""
    return {
        p.name: {"tamano_bytes": p.stat().st_size, "sha256": _hash_file(p)}
        for p in source_paths
    }


def load_cache_if_valid(
    cache_dir: Path,
    *,
    cache_name: str,
    source_paths: list[Path],
    crs: str,
) -> list[tuple[str, BaseGeometry]] | None:
    """Devuelve la lista `(id, geometría reproyectada)` cacheada si el caché
    existe y su huella coincide exactamente con los archivos de origen
    actuales y el CRS solicitado; `None` si hay que regenerarlo."""
    pkl_path = cache_dir / f"{cache_name}.pkl"
    meta_path = cache_dir / f"{cache_name}.metadata.json"
    if not pkl_path.exists() or not meta_path.exists():
        return None

    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)

    if meta.get("crs") != crs:
        return None

    huella_actual = compute_source_fingerprint(source_paths)
    if meta.get("huella_archivos_origen") != huella_actual:
        return None

    with open(pkl_path, "rb") as fh:
        data: list[tuple[str, BaseGeometry]] = pickle.load(fh)
    return data


def save_cache(
    cache_dir: Path,
    *,
    cache_name: str,
    data: list[tuple[str, BaseGeometry]],
    source_paths: list[Path],
    crs: str,
) -> dict[str, Any]:
    """Guarda el caché (pickle de geometrías + metadata JSON) y devuelve la
    metadata escrita."""
    ensure_dir(cache_dir)
    pkl_path = cache_dir / f"{cache_name}.pkl"
    meta_path = cache_dir / f"{cache_name}.metadata.json"

    with open(pkl_path, "wb") as fh:
        pickle.dump(data, fh, protocol=pickle.HIGHEST_PROTOCOL)

    meta = {
        "cache_name": cache_name,
        "crs": crs,
        "fecha_creacion": utc_now_iso(),
        "n_geometrias": len(data),
        "tamano_bytes_pkl": pkl_path.stat().st_size,
        "huella_archivos_origen": compute_source_fingerprint(source_paths),
        "observaciones": (
            "Caché regenerable: contiene solo geometrías ya reproyectadas, no el "
            "índice STRtree (no se serializa: no se garantiza estable entre "
            "versiones de shapely). Se invalida automáticamente si cambia el "
            "tamaño o el hash SHA-256 de cualquiera de los archivos de origen."
        ),
    }
    write_json(meta_path, meta)
    return meta
