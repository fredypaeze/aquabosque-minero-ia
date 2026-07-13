"""Grilla nacional fija y reproducible para la adquisición de productos
ráster forestales del IDEAM (Fase 2D.3, secciones B-D).

La grilla se define UNA sola vez, de forma independiente de los límites
municipales — los tiles se generan por aritmética pura sobre el extent
nacional declarado por el propio servicio WCS, y las geometrías MGN2025 se
usan solo para *marcar* qué tiles son candidatos a descargar, nunca para
modificar sus bounds (Fase 2D.3, sección D: "no crear tiles a partir del
bbox individual de cada municipio").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

M2_PER_HA = 10_000.0


def _tag_values(xml_text: str, tag: str) -> list[str]:
    return re.findall(rf"<{tag}[^>]*>([^<]*)</{tag}>", xml_text)


def parse_wcs_describe_coverage(xml_text: str, coverage_id: str) -> dict[str, Any]:
    """Sección B: extrae del XML real de `DescribeCoverage` los campos
    pedidos por el encargo. No asume que 30 m equivale a una resolución
    angular fija exacta — la resolución se lee de los `offsetVector`
    declarados, no de un valor asumido."""
    crs_match = re.search(r'srsName="([^"]+)"', xml_text)
    crs = crs_match.group(1) if crs_match else None

    lower = _tag_values(xml_text, "gml:lowerCorner")
    upper = _tag_values(xml_text, "gml:upperCorner")
    extent = None
    if lower and upper:
        lo = [float(v) for v in lower[0].split()]
        up = [float(v) for v in upper[0].split()]
        # boundedBy declara (lat, lon) en EPSG:4326 con axisLabels "y x"
        extent = {"ymin": lo[0], "xmin": lo[1], "ymax": up[0], "xmax": up[1]}

    grid_low = _tag_values(xml_text, "gml:low")
    grid_high = _tag_values(xml_text, "gml:high")
    low = [int(v) for v in grid_low[0].split()] if grid_low else None
    high = [int(v) for v in grid_high[0].split()] if grid_high else None

    origin_pos = _tag_values(xml_text, "gml:pos")
    origin = [float(v) for v in origin_pos[0].split()] if origin_pos else None

    offset_vectors_raw = re.findall(r"<gml:offsetVector[^>]*>([^<]+)</gml:offsetVector>", xml_text)
    offset_vectors = [[float(v) for v in ov.split()] for ov in offset_vectors_raw]

    resolucion_x_declarada = abs(offset_vectors[0][0]) if len(offset_vectors) >= 1 else None
    resolucion_y_declarada = abs(offset_vectors[1][1]) if len(offset_vectors) >= 2 else None
    # Aproximación en metros SOLO para referencia (no para calcular área
    # oficial): 1 grado de longitud ≈ 111.320 m × cos(latitud); se evalúa en
    # el origen de la grilla, documentado como aproximación, nunca como
    # valor exacto.
    import math
    lat_origen = origin[0] if origin else 0.0
    resolucion_x_m_aprox = round(resolucion_x_declarada * 111_320 * math.cos(math.radians(lat_origen)), 3) if resolucion_x_declarada else None
    resolucion_y_m_aprox = round(resolucion_y_declarada * 110_574, 3) if resolucion_y_declarada else None

    n_bandas = len(re.findall(r"<swe:field\s", xml_text))

    width = (high[0] - low[0] + 1) if (high and low) else None
    height = (high[1] - low[1] + 1) if (high and low) else None

    return {
        "coverage_id": coverage_id,
        "crs": crs,
        "extent_xmin": extent["xmin"] if extent else None,
        "extent_ymin": extent["ymin"] if extent else None,
        "extent_xmax": extent["xmax"] if extent else None,
        "extent_ymax": extent["ymax"] if extent else None,
        "grid_low_x": low[0] if low else None,
        "grid_low_y": low[1] if low else None,
        "grid_high_x": high[0] if high else None,
        "grid_high_y": high[1] if high else None,
        "ancho_original_px": width,
        "alto_original_px": height,
        "origen_x": origin[1] if origin else None,
        "origen_y": origin[0] if origin else None,
        "offset_vector_x": offset_vectors[0] if len(offset_vectors) >= 1 else None,
        "offset_vector_y": offset_vectors[1] if len(offset_vectors) >= 2 else None,
        "resolucion_x_declarada_grados": resolucion_x_declarada,
        "resolucion_y_declarada_grados": resolucion_y_declarada,
        "resolucion_x_aprox_m": resolucion_x_m_aprox,
        "resolucion_y_aprox_m": resolucion_y_m_aprox,
        "n_bandas": n_bandas,
        "formato": "image/tiff (RGB renderizado, ver forest_layer_colormaps.csv)",
    }


# ---------------------------------------------------------------------------
# C. Grilla nacional canónica
# ---------------------------------------------------------------------------


@dataclass
class NationalGridSpec:
    crs_descarga: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    resolucion_x: float
    resolucion_y: float
    origen_x: float
    origen_y: float
    tile_size_px: int
    buffer_grados: float
    nodata_tecnico: int
    remuestreo: str
    tolerancia_clase_desconocida_pct: float
    politica_borde: str = "recortar_al_extent_nacional_declarado"

    @property
    def ancho_total_px(self) -> int:
        return int(round((self.xmax - self.xmin) / self.resolucion_x))

    @property
    def alto_total_px(self) -> int:
        return int(round((self.ymax - self.ymin) / self.resolucion_y))

    @property
    def n_filas_tiles(self) -> int:
        import math
        return math.ceil(self.alto_total_px / self.tile_size_px)

    @property
    def n_columnas_tiles(self) -> int:
        import math
        return math.ceil(self.ancho_total_px / self.tile_size_px)

    def to_dict(self) -> dict[str, Any]:
        return {
            "crs_descarga": self.crs_descarga, "xmin": self.xmin, "ymin": self.ymin,
            "xmax": self.xmax, "ymax": self.ymax, "resolucion_x": self.resolucion_x,
            "resolucion_y": self.resolucion_y, "origen_x": self.origen_x, "origen_y": self.origen_y,
            "ancho_total_px": self.ancho_total_px, "alto_total_px": self.alto_total_px,
            "tile_size_px": self.tile_size_px, "n_filas_tiles": self.n_filas_tiles,
            "n_columnas_tiles": self.n_columnas_tiles,
            "nomenclatura_tiles": "tile_r{fila:04d}_c{columna:04d}",
            "buffer_grados": self.buffer_grados, "politica_borde": self.politica_borde,
            "nodata_tecnico": self.nodata_tecnico, "remuestreo": self.remuestreo,
            "tolerancia_clase_desconocida_pct": self.tolerancia_clase_desconocida_pct,
        }


def build_national_grid_spec(grid_definitions: list[dict[str, Any]], *, tile_size_px: int = 2048) -> NationalGridSpec:
    """Sección C: construye la especificación de grilla nacional, alineada
    al origen y offsetVector declarados por el WCS cuando la metadata lo
    permite (se usa la definición de `Superficie_Bosque`, que cubre el
    extent nacional completo de forma continua)."""
    referencia = grid_definitions[0]
    xmin = min(g["extent_xmin"] for g in grid_definitions if g["extent_xmin"] is not None)
    ymin = min(g["extent_ymin"] for g in grid_definitions if g["extent_ymin"] is not None)
    xmax = max(g["extent_xmax"] for g in grid_definitions if g["extent_xmax"] is not None)
    ymax = max(g["extent_ymax"] for g in grid_definitions if g["extent_ymax"] is not None)

    return NationalGridSpec(
        crs_descarga="EPSG:4326",
        xmin=referencia["origen_x"] if referencia.get("origen_x") is not None else xmin,
        ymin=ymin,
        xmax=xmax,
        ymax=referencia["origen_y"] if referencia.get("origen_y") is not None else ymax,
        resolucion_x=referencia["resolucion_x_declarada_grados"],
        resolucion_y=referencia["resolucion_y_declarada_grados"],
        origen_x=referencia.get("origen_x") if referencia.get("origen_x") is not None else xmin,
        origen_y=referencia.get("origen_y") if referencia.get("origen_y") is not None else ymax,
        tile_size_px=tile_size_px,
        buffer_grados=0.0,
        nodata_tecnico=253,
        remuestreo="nearest",
        tolerancia_clase_desconocida_pct=0.0,
    )


# ---------------------------------------------------------------------------
# D. Esquema de teselas
# ---------------------------------------------------------------------------


@dataclass
class Tile:
    tile_id: str
    fila: int
    columna: int
    xmin: float
    ymin: float
    xmax: float
    ymax: float
    width_px: int
    height_px: int
    es_candidato_nacional: bool = False
    pct_area_colombia_aprox: float = 0.0
    estado_descarga: str = "no_descargado"


def generate_tile_index(spec: NationalGridSpec) -> list[Tile]:
    """Genera el índice completo de tiles por aritmética pura sobre la
    grilla nacional — nunca a partir del bbox de un municipio individual."""
    tiles: list[Tile] = []
    tile_w_deg = spec.tile_size_px * spec.resolucion_x
    tile_h_deg = spec.tile_size_px * spec.resolucion_y
    for fila in range(spec.n_filas_tiles):
        for col in range(spec.n_columnas_tiles):
            txmin = spec.xmin + col * tile_w_deg
            tymax = spec.ymax - fila * tile_h_deg
            txmax = min(txmin + tile_w_deg, spec.xmax)
            tymin = max(tymax - tile_h_deg, spec.ymin)
            width_px = int(round((txmax - txmin) / spec.resolucion_x))
            height_px = int(round((tymax - tymin) / spec.resolucion_y))
            tiles.append(Tile(
                tile_id=f"tile_r{fila:04d}_c{col:04d}", fila=fila, columna=col,
                xmin=txmin, ymin=tymin, xmax=txmax, ymax=tymax,
                width_px=width_px, height_px=height_px,
            ))
    return tiles


def mark_candidate_tiles(tiles: list[Tile], mgn_union_geom) -> None:
    """Marca (in-place) qué tiles intersectan la unión de las 1.122
    geometrías MGN2025 — solo para filtrar cuáles descargar, nunca para
    recortar o mover los bounds del tile (sección D)."""
    from shapely.geometry import box

    for tile in tiles:
        tile_box = box(tile.xmin, tile.ymin, tile.xmax, tile.ymax)
        if not tile_box.intersects(mgn_union_geom):
            tile.es_candidato_nacional = False
            tile.pct_area_colombia_aprox = 0.0
            continue
        inter = tile_box.intersection(mgn_union_geom)
        tile.es_candidato_nacional = True
        tile.pct_area_colombia_aprox = round(inter.area / tile_box.area * 100, 2) if tile_box.area else 0.0
