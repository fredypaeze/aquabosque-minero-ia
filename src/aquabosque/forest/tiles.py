"""Descarga, continuidad y mosaico de tiles de la grilla nacional forestal
(Fase 2D.3, secciones E y N).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile

from .colormap import decode_ideam_rgb_classes
from .grid import Tile

USER_AGENT = "AquaBosqueMineroIA/0.1 (uso academico/institucional, descarga controlada)"
TIMEOUT_DEFAULT = 120

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def extract_tiff_from_multipart(raw_bytes: bytes) -> bytes:
    parts = raw_bytes.split(b"--wcs")
    for part in parts:
        if b"Content-Type: image/tiff" in part[:200]:
            idx = part.index(b"\n\n")
            return part[idx + 2:].rstrip(b"\n")
    raise ValueError("Respuesta WCS no contiene una parte image/tiff.")


def download_tile_wcs(
    mapserver_services_url: str,
    coverage_id: str,
    tile: Tile,
    dest_path: Path,
    *,
    timeout: int = TIMEOUT_DEFAULT,
    forzar_resolucion_canonica: bool = True,
) -> dict[str, Any]:
    """Descarga un tile exacto (sus bounds, sin buffer adicional) vía WCS
    GetCoverage con interpolación `nearest-neighbor` fija — la misma
    interpolación para todos los tiles, requisito de reproducibilidad de la
    sección F.

    Hallazgo real de la Fase 2D.4 (sección H): sin forzar el tamaño de
    salida, el servidor WCS devuelve cada coverage en SU PROPIA resolución
    nativa para el mismo bbox solicitado (confirmado: la misma tesela de
    prueba produjo 2048x2048 px para `Superficie_Bosque` 2024 pero 2063x2063
    px para `Dinamica_Cambio_Cobertura_Bosque` 2023-2024, y 2033x2063 px para
    `Superficie_Bosque` 2013/2018) — el parámetro `INTERPOLATION` por sí solo
    NO fuerza el remuestreo a la grilla canónica. `forzar_resolucion_canonica`
    (por defecto `True`) añade la extensión WCS `SCALESIZE` (confirmada como
    soportada por el servicio vía `GetCapabilities` ->
    `WCS_service-extension_scaling`) para que la tesela descargada tenga
    exactamente `tile.width_px` x `tile.height_px`, alineada a la grilla
    nacional. Se puede desactivar explícitamente (`False`) únicamente para
    auditar la resolución nativa real de un producto/año (sección H)."""
    params = {
        "SERVICE": "WCS", "REQUEST": "GetCoverage", "VERSION": "2.0.1", "COVERAGEID": coverage_id,
        "FORMAT": "image/tiff",
        "SUBSET": [f"x({tile.xmin},{tile.xmax})", f"y({tile.ymin},{tile.ymax})"],
        "SUBSETTINGCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
        "OUTPUTCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
        "INTERPOLATION": "http://www.opengis.net/def/interpolation/OGC/1/nearest-neighbor",
    }
    if forzar_resolucion_canonica:
        params["SCALESIZE"] = f"x({tile.width_px}),y({tile.height_px})"
    t0 = time.perf_counter()
    resp = SESSION.get(f"{mapserver_services_url}/WCSServer", params=params, timeout=timeout)
    tiempo_s = round(time.perf_counter() - t0, 2)
    resultado: dict[str, Any] = {
        "tile_id": tile.tile_id, "http_status": resp.status_code, "tiempo_s": tiempo_s,
        "resolucion_canonica_forzada": forzar_resolucion_canonica,
    }
    if resp.status_code != 200:
        resultado["exito"] = False
        resultado["mensaje"] = resp.text[:300]
        return resultado
    try:
        tiff_bytes = extract_tiff_from_multipart(resp.content)
    except ValueError as exc:
        resultado["exito"] = False
        resultado["mensaje"] = str(exc)
        return resultado
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(tiff_bytes)
    resultado["exito"] = True
    resultado["tamano_bytes"] = len(tiff_bytes)
    return resultado


def read_tile_rgb(path: Path) -> tuple[np.ndarray, Any, Any]:
    with rasterio.open(path) as src:
        arr = src.read()
        transform = src.transform
        crs = src.crs
    rgb = arr[:3].transpose(1, 2, 0)
    return rgb, transform, crs


# ---------------------------------------------------------------------------
# E. Continuidad entre tiles
# ---------------------------------------------------------------------------


def audit_tile_boundary(path_a: Path, path_b: Path, colormap: dict, *, eje: str) -> dict[str, Any]:
    """Sección E: audita el límite compartido entre dos tiles contiguos
    (`eje="columna"` para tiles lado a lado, `eje="fila"` para tiles uno
    sobre otro). Nunca aprueba la grilla si no hay continuidad
    determinística."""
    rgb_a, transform_a, crs_a = read_tile_rgb(path_a)
    rgb_b, transform_b, crs_b = read_tile_rgb(path_b)

    res_a = (abs(transform_a.a), abs(transform_a.e))
    res_b = (abs(transform_b.a), abs(transform_b.e))
    misma_resolucion = bool(np.allclose(res_a, res_b, rtol=1e-6))

    decoded_a = decode_ideam_rgb_classes(rgb_a, colormap, tolerancia_pct=100.0, detener_si_excede=False)
    decoded_b = decode_ideam_rgb_classes(rgb_b, colormap, tolerancia_pct=100.0, detener_si_excede=False)

    if eje == "columna":
        borde_a = decoded_a.class_array[:, -1]
        borde_b = decoded_b.class_array[:, 0]
        gap_x = round((transform_b.c - transform_a.c) / abs(transform_a.a) - rgb_a.shape[1], 3)
        gap_y = 0.0
    else:
        borde_a = decoded_a.class_array[-1, :]
        borde_b = decoded_b.class_array[0, :]
        gap_y = round((transform_a.f - transform_b.f) / abs(transform_a.e) - rgb_a.shape[0], 3)
        gap_x = 0.0

    n_comparados = min(len(borde_a), len(borde_b))
    coincidencia_borde = float(np.mean(borde_a[:n_comparados] == borde_b[:n_comparados])) if n_comparados else None

    hay_hueco = abs(gap_x) > 1e-6 or abs(gap_y) > 1e-6
    hay_hueco_positivo = gap_x > 1e-6 or gap_y > 1e-6
    hay_superposicion = gap_x < -1e-6 or gap_y < -1e-6

    return {
        "tile_a": path_a.name, "tile_b": path_b.name, "eje": eje,
        "misma_resolucion": misma_resolucion, "resolucion_a": res_a, "resolucion_b": res_b,
        "gap_px_x": gap_x, "gap_px_y": gap_y, "hay_hueco": hay_hueco_positivo, "hay_superposicion": hay_superposicion,
        "n_pixeles_borde_comparados": n_comparados, "pct_coincidencia_clases_borde": round(coincidencia_borde * 100, 2) if coincidencia_borde is not None else None,
        "recomponible_deterministicamente": bool(misma_resolucion and not hay_hueco and not hay_superposicion),
    }


# ---------------------------------------------------------------------------
# N. Mosaico 2x2
# ---------------------------------------------------------------------------


def mosaic_2x2(paths_by_position: dict[tuple[int, int], Path], colormap: dict) -> dict[str, Any]:
    """Reconstruye un mosaico determinístico a partir de 4 tiles
    (fila, columna) in {0,1}x{0,1} y calcula área por clase antes/después."""
    arrays = {}
    transforms = {}
    for (fila, col), path in paths_by_position.items():
        rgb, transform, crs = read_tile_rgb(path)
        decoded = decode_ideam_rgb_classes(rgb, colormap, tolerancia_pct=100.0, detener_si_excede=False)
        arrays[(fila, col)] = decoded.class_array
        transforms[(fila, col)] = transform

    h0 = arrays[(0, 0)].shape[0]
    w0 = arrays[(0, 0)].shape[1]
    top = np.concatenate([arrays[(0, 0)], arrays[(0, 1)]], axis=1)
    bottom = np.concatenate([arrays[(1, 0)], arrays[(1, 1)]], axis=1)
    mosaico = np.concatenate([top, bottom], axis=0)

    area_por_clase_antes = {}
    for pos, arr in arrays.items():
        for v in np.unique(arr):
            area_por_clase_antes[int(v)] = area_por_clase_antes.get(int(v), 0) + int((arr == v).sum())
    area_por_clase_despues = {int(v): int((mosaico == v).sum()) for v in np.unique(mosaico)}

    dims_esperadas = (arrays[(0, 0)].shape[0] + arrays[(1, 0)].shape[0], arrays[(0, 0)].shape[1] + arrays[(0, 1)].shape[1])
    dims_ok = mosaico.shape == dims_esperadas

    import hashlib
    hash_mosaico = hashlib.sha256(mosaico.tobytes()).hexdigest()[:16]

    return {
        "dimensiones_esperadas": dims_esperadas, "dimensiones_obtenidas": mosaico.shape, "dimensiones_correctas": dims_ok,
        "area_por_clase_antes_px": area_por_clase_antes, "area_por_clase_despues_px": area_por_clase_despues,
        "areas_coinciden": area_por_clase_antes == area_por_clase_despues,
        "hash_mosaico": hash_mosaico, "valores_unicos_mosaico": sorted(int(v) for v in np.unique(mosaico)),
    }
