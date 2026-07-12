"""Asignación espacial punto-territorio (Fase 4B).

Asigna observaciones puntuales (p. ej. estaciones de monitoreo de calidad de
agua) a unidades territoriales poligonales. Regla principal: `covers()`, no
`contains()`, para que un punto justo sobre el borde de una unidad sí pueda
asignarse. Si un punto no queda cubierto por ninguna unidad, se calcula su
distancia a la unidad más cercana en un CRS métrico (EPSG:9377) y se asigna
por proximidad solo si esa distancia no supera un umbral configurable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pyproj import Transformer
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

from .intersection import reproject_geometry

UMBRAL_PROXIMIDAD_M_DEFAULT = 100.0

METODO_COVERS_DIRECTO = "covers_directo"
METODO_COVERS_DESAMBIGUADO_TEXTO = "covers_desambiguado_texto"
METODO_PROXIMIDAD = "proximidad_menor_100m"
METODO_SIN_ASIGNACION = "sin_asignacion"
METODO_AMBIGUA = "ambigua"

CALIDAD_ALTA = "alta"
CALIDAD_MEDIA = "media"
CALIDAD_BAJA = "baja"

_CALIDAD_POR_METODO = {
    METODO_COVERS_DIRECTO: CALIDAD_ALTA,
    METODO_COVERS_DESAMBIGUADO_TEXTO: CALIDAD_MEDIA,
    METODO_PROXIMIDAD: CALIDAD_MEDIA,
    METODO_AMBIGUA: CALIDAD_BAJA,
    METODO_SIN_ASIGNACION: CALIDAD_BAJA,
}


@dataclass
class TerritorialPointIndex:
    """Índices reutilizables (construidos una sola vez) para asignar muchos
    puntos: un STRtree en EPSG:4326 (para `covers`, topológico, no depende de
    distancias reales) y uno en el CRS métrico (para distancia real al
    candidato más cercano cuando ningún polígono cubre el punto)."""

    ids: list[str]
    tree_4326: STRtree
    geoms_4326: list[BaseGeometry]
    tree_proj: STRtree
    geoms_proj: list[BaseGeometry]
    transformer_a_metrico: Transformer


def build_territorial_point_index(
    territorial_geoms_4326: list[tuple[str, BaseGeometry]],
    territorial_geoms_proj: list[tuple[str, BaseGeometry]],
    transformer_a_metrico: Transformer,
) -> TerritorialPointIndex:
    """`territorial_geoms_4326` y `territorial_geoms_proj` deben tener
    exactamente el mismo orden de códigos (mismo universo territorial)."""
    ids_4326 = [cod for cod, _ in territorial_geoms_4326]
    ids_proj = [cod for cod, _ in territorial_geoms_proj]
    if ids_4326 != ids_proj:
        raise ValueError("territorial_geoms_4326 y territorial_geoms_proj deben tener el mismo orden de códigos")

    geoms_4326 = [g for _, g in territorial_geoms_4326]
    geoms_proj = [g for _, g in territorial_geoms_proj]
    return TerritorialPointIndex(
        ids=ids_4326,
        tree_4326=STRtree(geoms_4326),
        geoms_4326=geoms_4326,
        tree_proj=STRtree(geoms_proj),
        geoms_proj=geoms_proj,
        transformer_a_metrico=transformer_a_metrico,
    )


@dataclass
class PointAssignmentResult:
    cod_dane_mpio_asignado: str | None
    metodo_asignacion: str
    asignacion_ambigua: bool
    n_unidades_candidatas: int
    distancia_unidad_mas_cercana_m: float | None
    codigos_candidatos: list[str] = field(default_factory=list)
    calidad_asignacion: str = CALIDAD_BAJA

    def __post_init__(self) -> None:
        self.calidad_asignacion = _CALIDAD_POR_METODO[self.metodo_asignacion]


def assign_point(
    lon: float,
    lat: float,
    index: TerritorialPointIndex,
    *,
    codigo_esperado_por_texto: str | None = None,
    umbral_proximidad_m: float = UMBRAL_PROXIMIDAD_M_DEFAULT,
) -> PointAssignmentResult:
    """Asigna un único punto (lon, lat en EPSG:4326) a una unidad
    territorial. `codigo_esperado_por_texto` es el `cod_dane_mpio` que el
    municipio/departamento textual de la fuente resolvería contra DIVIPOLA
    (calculado por el llamador); se usa solo como desempate determinístico
    cuando hay más de un candidato `covers`, nunca para forzar una
    asignación que la geometría no respalda."""
    point = Point(lon, lat)
    cand_idx = index.tree_4326.query(point)
    covers_ids = [index.ids[int(i)] for i in cand_idx if index.geoms_4326[int(i)].covers(point)]

    if len(covers_ids) == 1:
        return PointAssignmentResult(
            cod_dane_mpio_asignado=covers_ids[0],
            metodo_asignacion=METODO_COVERS_DIRECTO,
            asignacion_ambigua=False,
            n_unidades_candidatas=1,
            distancia_unidad_mas_cercana_m=0.0,
            codigos_candidatos=covers_ids,
        )

    if len(covers_ids) > 1:
        if codigo_esperado_por_texto is not None and codigo_esperado_por_texto in covers_ids:
            return PointAssignmentResult(
                cod_dane_mpio_asignado=codigo_esperado_por_texto,
                metodo_asignacion=METODO_COVERS_DESAMBIGUADO_TEXTO,
                asignacion_ambigua=False,
                n_unidades_candidatas=len(covers_ids),
                distancia_unidad_mas_cercana_m=0.0,
                codigos_candidatos=covers_ids,
            )
        return PointAssignmentResult(
            cod_dane_mpio_asignado=None,
            metodo_asignacion=METODO_AMBIGUA,
            asignacion_ambigua=True,
            n_unidades_candidatas=len(covers_ids),
            distancia_unidad_mas_cercana_m=0.0,
            codigos_candidatos=covers_ids,
        )

    # Ningún polígono cubre el punto: buscar la unidad más cercana en el CRS métrico.
    point_proj = reproject_geometry(point, index.transformer_a_metrico)
    nearest_idx = int(index.tree_proj.nearest(point_proj))
    distancia_m = index.geoms_proj[nearest_idx].distance(point_proj)
    cod_cercano = index.ids[nearest_idx]

    if distancia_m <= umbral_proximidad_m:
        return PointAssignmentResult(
            cod_dane_mpio_asignado=cod_cercano,
            metodo_asignacion=METODO_PROXIMIDAD,
            asignacion_ambigua=False,
            n_unidades_candidatas=0,
            distancia_unidad_mas_cercana_m=distancia_m,
            codigos_candidatos=[],
        )

    return PointAssignmentResult(
        cod_dane_mpio_asignado=None,
        metodo_asignacion=METODO_SIN_ASIGNACION,
        asignacion_ambigua=False,
        n_unidades_candidatas=0,
        distancia_unidad_mas_cercana_m=distancia_m,
        codigos_candidatos=[],
    )
