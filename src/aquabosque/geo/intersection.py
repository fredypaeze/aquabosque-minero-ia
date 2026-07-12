"""Motor de intersección espacial reutilizable (Fase 4A).

Construye un índice `STRtree` UNA SOLA VEZ sobre las unidades territoriales
reproyectadas y lo usa para consultar candidatas por bounding box antes de
calcular intersecciones geométricas reales — evita el producto cartesiano
completo (6.294 títulos × 1.122 unidades ≈ 7,06 millones de pares).

Reglas geométricas aplicadas (Fase 4A, sección E):

- Solo cuenta como asignación territorial una intersección con área positiva.
- Un contacto de solo línea/punto (touches, sin superficie) se registra con
  `solo_toca_limite=True` y área 0; no se excluye en silencio, queda en los
  registros para auditoría, pero no aporta área a los indicadores.
- Si la intersección produce una `GeometryCollection` mixta, se conservan
  solo los componentes `Polygon`/`MultiPolygon` (unidos); los componentes no
  poligonales se cuentan y se listan, nunca se descartan en silencio.
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any, Callable

from pyproj import Transformer
from shapely.geometry import shape as shapely_shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shapely_transform
from shapely.ops import unary_union
from shapely.strtree import STRtree

M2_PER_HA = 10_000.0


def build_transformer(crs_origen: str, crs_destino: str) -> Transformer:
    """`always_xy=True`: orden x=longitud/este, y=latitud/norte en ambos extremos."""
    return Transformer.from_crs(crs_origen, crs_destino, always_xy=True)


def reproject_geometry(geom: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    return shapely_transform(transformer.transform, geom)


def extract_polygonal(geom: BaseGeometry) -> tuple[BaseGeometry | None, list[str]]:
    """De una geometría de intersección, conserva solo el componente
    poligonal (Polygon/MultiPolygon, unidos si hay varios). Devuelve
    (geometría poligonal o None si no hay ninguna, lista de tipos de
    componentes no poligonales encontrados — nunca descartados en silencio)."""
    if geom.is_empty:
        return None, []
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom, []
    if geom.geom_type == "GeometryCollection":
        poligonales = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon") and not g.is_empty]
        descartados = [g.geom_type for g in geom.geoms if g.geom_type not in ("Polygon", "MultiPolygon")]
        if not poligonales:
            return None, descartados
        return unary_union(poligonales), descartados
    # LineString, Point, MultiLineString, MultiPoint, etc.: sin área.
    return None, [geom.geom_type]


@dataclass
class IntersectionRecord:
    title_id: str
    territorial_id: str
    area_interseccion_m2: float
    solo_toca_limite: bool
    componentes_no_poligonales: list[str] = field(default_factory=list)
    geometria_interseccion: BaseGeometry | None = field(default=None, repr=False)


@dataclass
class IntersectionRunStats:
    n_titulos: int
    n_unidades: int
    tiempo_reproyeccion_s: float = 0.0
    tiempo_construccion_indice_s: float = 0.0
    tiempo_consulta_s: float = 0.0
    tiempo_interseccion_s: float = 0.0
    tiempo_total_s: float = 0.0
    memoria_pico_mb: float = 0.0
    n_pares_candidatos: int = 0
    n_intersecciones_area_positiva: int = 0
    n_contactos_sin_area: int = 0
    n_titulos_sin_interseccion: int = 0


@dataclass
class NationalIntersectionResult:
    records: list[IntersectionRecord]
    territorial_ids: list[str]
    territorial_geoms_proj: list[BaseGeometry]
    title_areas_m2: dict[str, float]
    stats: IntersectionRunStats


def run_national_intersection(
    title_geoms: list[tuple[str, dict]],
    territorial_geoms_proj: list[tuple[str, BaseGeometry]],
    *,
    crs_origen: str = "EPSG:4326",
    crs_metrico: str = "EPSG:9377",
    progress_every: int = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> NationalIntersectionResult:
    """Ejecuta la intersección nacional completa con índice espacial.

    `territorial_geoms_proj` ya debe venir reproyectado (para poder
    reutilizar un caché externo y no reproyectar en cada corrida, ver
    `src/aquabosque/utils/spatial_cache.py`). `title_geoms` viene en
    `crs_origen` (EPSG:4326) y se reproyecta aquí, una vez por título.
    """
    tracemalloc.start()
    t_start = time.perf_counter()

    transformer = build_transformer(crs_origen, crs_metrico)

    terr_ids = [tid for tid, _ in territorial_geoms_proj]
    terr_geoms = [g for _, g in territorial_geoms_proj]

    t0 = time.perf_counter()
    tree = STRtree(terr_geoms)
    t_index = time.perf_counter() - t0

    records: list[IntersectionRecord] = []
    title_areas_m2: dict[str, float] = {}

    n_pares_candidatos = 0
    n_area_positiva = 0
    n_contactos_sin_area = 0
    n_sin_interseccion = 0

    tiempo_reproyeccion = 0.0
    tiempo_consulta = 0.0
    tiempo_interseccion = 0.0

    n_total = len(title_geoms)
    for i, (title_id, geom_dict) in enumerate(title_geoms):
        t0 = time.perf_counter()
        g = shapely_shape(geom_dict)
        g_proj = reproject_geometry(g, transformer)
        tiempo_reproyeccion += time.perf_counter() - t0
        title_areas_m2[title_id] = g_proj.area

        t0 = time.perf_counter()
        candidate_idx = tree.query(g_proj)
        tiempo_consulta += time.perf_counter() - t0
        n_pares_candidatos += len(candidate_idx)

        tuvo_area_positiva = False
        t0 = time.perf_counter()
        for idx in candidate_idx:
            terr_geom = terr_geoms[int(idx)]
            inter = g_proj.intersection(terr_geom)
            if inter.is_empty:
                continue

            poligonal, descartados = extract_polygonal(inter)
            if poligonal is None or poligonal.is_empty or poligonal.area <= 0:
                n_contactos_sin_area += 1
                records.append(
                    IntersectionRecord(
                        title_id=title_id,
                        territorial_id=terr_ids[int(idx)],
                        area_interseccion_m2=0.0,
                        solo_toca_limite=True,
                        componentes_no_poligonales=descartados,
                    )
                )
                continue

            n_area_positiva += 1
            tuvo_area_positiva = True
            records.append(
                IntersectionRecord(
                    title_id=title_id,
                    territorial_id=terr_ids[int(idx)],
                    area_interseccion_m2=poligonal.area,
                    solo_toca_limite=False,
                    componentes_no_poligonales=descartados,
                    geometria_interseccion=poligonal,
                )
            )
        tiempo_interseccion += time.perf_counter() - t0

        if not tuvo_area_positiva:
            n_sin_interseccion += 1

        if progress_every and (i + 1) % progress_every == 0:
            if on_progress:
                on_progress(i + 1, n_total)

    t_total = time.perf_counter() - t_start
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    stats = IntersectionRunStats(
        n_titulos=n_total,
        n_unidades=len(territorial_geoms_proj),
        tiempo_reproyeccion_s=round(tiempo_reproyeccion, 4),
        tiempo_construccion_indice_s=round(t_index, 4),
        tiempo_consulta_s=round(tiempo_consulta, 4),
        tiempo_interseccion_s=round(tiempo_interseccion, 4),
        tiempo_total_s=round(t_total, 4),
        memoria_pico_mb=round(peak / (1024 * 1024), 2),
        n_pares_candidatos=n_pares_candidatos,
        n_intersecciones_area_positiva=n_area_positiva,
        n_contactos_sin_area=n_contactos_sin_area,
        n_titulos_sin_interseccion=n_sin_interseccion,
    )

    return NationalIntersectionResult(
        records=records,
        territorial_ids=terr_ids,
        territorial_geoms_proj=terr_geoms,
        title_areas_m2=title_areas_m2,
        stats=stats,
    )
