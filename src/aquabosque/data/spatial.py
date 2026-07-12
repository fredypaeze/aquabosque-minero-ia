"""Utilidades espaciales reutilizables (Fase 3D.1 y futura Fase 4A).

Funciones puras para reproyectar geometrías GeoJSON y construir/consultar un
índice espacial (`STRtree`) antes de ejecutar intersecciones reales. El
objetivo es evitar el producto cartesiano completo (todos los títulos mineros
contra todas las unidades territoriales) en la futura intersección nacional:
en vez de ~6.294 × 1.122 ≈ 7,06 millones de pares, se consultan solo
candidatas por bounding box antes de calcular la intersección real.
"""

from __future__ import annotations

import time
import tracemalloc
from typing import Any

from pyproj import Transformer
from shapely.geometry import shape as shapely_shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from shapely.strtree import STRtree


def build_transformer(crs_origen: str, crs_destino: str) -> Transformer:
    """Construye un `pyproj.Transformer` reutilizable (always_xy=True, es
    decir, orden x=longitud/este, y=latitud/norte en ambos extremos)."""
    return Transformer.from_crs(crs_origen, crs_destino, always_xy=True)


def reproject_geometry(geom: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    """Reproyecta una geometría shapely con un `Transformer` ya construido."""
    return shapely_transform(transformer.transform, geom)


def run_strtree_performance_test(
    title_geometries: list[tuple[str, dict]],
    territorial_geometries: list[tuple[str, dict]],
    *,
    crs_origen: str = "EPSG:4326",
    crs_metrico: str = "EPSG:9377",
) -> dict[str, Any]:
    """Prueba de rendimiento antes de la intersección nacional completa.

    1. Reproyecta títulos mineros y unidades territoriales a `crs_metrico`.
    2. Construye un `STRtree` sobre las unidades territoriales reproyectadas.
    3. Para cada título, consulta candidatas por bounding box (`tree.query`).
    4. Ejecuta la intersección geométrica real SOLO sobre esas candidatas.

    `title_geometries` / `territorial_geometries`: listas de tuplas
    `(id, geometria_geojson)`. Devuelve un dict con tiempos, memoria pico
    (vía `tracemalloc`) y conteo de pares candidatos vs. intersecciones
    reales, para decidir si el índice espacial es viable en la Fase 4A.
    """
    transformer = build_transformer(crs_origen, crs_metrico)

    tracemalloc.start()
    t0 = time.perf_counter()

    terr_ids: list[str] = []
    terr_geoms_proj: list[BaseGeometry] = []
    for tid, geom_dict in territorial_geometries:
        g = shapely_shape(geom_dict)
        terr_ids.append(tid)
        terr_geoms_proj.append(reproject_geometry(g, transformer))

    tree = STRtree(terr_geoms_proj)
    t_index_built = time.perf_counter()

    n_pares_candidatos = 0
    n_intersecciones_reales = 0
    pares_detalle: list[dict[str, str]] = []

    for title_id, geom_dict in title_geometries:
        g = shapely_shape(geom_dict)
        g_proj = reproject_geometry(g, transformer)
        candidate_idx = tree.query(g_proj)
        n_pares_candidatos += len(candidate_idx)
        for idx in candidate_idx:
            terr_geom = terr_geoms_proj[int(idx)]
            if g_proj.intersects(terr_geom):
                n_intersecciones_reales += 1
                pares_detalle.append({"titulo_id": title_id, "unidad_territorial_id": terr_ids[int(idx)]})

    t1 = time.perf_counter()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    n_titulos = len(title_geometries)
    n_unidades = len(territorial_geometries)
    n_pares_fuerza_bruta = n_titulos * n_unidades

    return {
        "n_titulos_muestra": n_titulos,
        "n_unidades_territoriales_indexadas": n_unidades,
        "crs_metrico_usado": crs_metrico,
        "tiempo_construccion_indice_s": round(t_index_built - t0, 4),
        "tiempo_consulta_e_interseccion_s": round(t1 - t_index_built, 4),
        "tiempo_total_s": round(t1 - t0, 4),
        "memoria_pico_mb": round(peak / (1024 * 1024), 2),
        "n_pares_candidatos_bbox": n_pares_candidatos,
        "n_intersecciones_reales": n_intersecciones_reales,
        "n_pares_fuerza_bruta_evitados": n_pares_fuerza_bruta - n_pares_candidatos,
        "pares_interseccion_detalle": pares_detalle[:50],
    }
