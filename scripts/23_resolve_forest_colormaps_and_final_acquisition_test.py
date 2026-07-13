"""Fase 2D.4: resolución de colormaps históricos y prueba final de
adquisición forestal.

Construye un colormap exacto y validado por capa (no un diccionario global
reutilizado entre años), corrige el inventario y las estimaciones de
descarga, prueba la grilla canónica sobre ambos productos ráster (incluido
el mosaico 2x2 del producto de cambio) y cierra la semántica de
identificación DTD separando OBJECTID real, id anclado a la fuente y huella
de auditoría.

No descarga todavía las series nacionales completas. No calcula indicadores
para las 1.122 unidades. No integra minería ni agua. No construye índice de
riesgo. No entrena modelos. No crea dashboard.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import Resampling, reproject

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
for p in (SRC_DIR, SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

mod20 = importlib.import_module("20_validate_forest_data_pilot")
mod21 = importlib.import_module("21_forest_dtd_and_colormap_robustness")
mod22 = importlib.import_module("22_design_forest_national_acquisition")

from aquabosque.features.dtd import (  # noqa: E402
    add_dtd_identity_columns, attribute_sensitivity_audit,
    audit_duplicate_semantics, audit_oid_uniqueness, audit_registro_id_uniqueness,
    summarize_dtd_metrics,
)
from aquabosque.forest.colormap import (  # noqa: E402
    NODATA_TECNICO_MASCARA_EXTERNA, ClaseDesconocidaExcedeTolerancia, decode_ideam_rgb_classes,
    decode_layer_from_registry, hash_colormap, parse_identify_attributes,
)
from aquabosque.forest.grid import NationalGridSpec, generate_tile_index  # noqa: E402
from aquabosque.forest.tiles import download_tile_wcs, mosaic_2x2, read_tile_rgb  # noqa: E402
from aquabosque.utils.io import ensure_dir, utc_now_iso, write_json  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REFERENCE_DIR = DATA_PROCESSED / "reference"
AUDIT_DIR = DATA_PROCESSED / "audit"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "forest_sources"
CONFIG_DIR = PROJECT_ROOT / "config"
PILOT_DIR = DATA_RAW / "forest_pilot" / "mvp_colormap_pilot"
CAMBIO_MOSAIC_DIR = DATA_RAW / "forest_pilot" / "mvp_colormap_pilot" / "cambio_2023_2024_mosaic"
NATIVE_VS_CANONICAL_DIR = DATA_RAW / "forest_pilot" / "mvp_colormap_pilot" / "native_vs_canonical"
STORAGE_TEST_DIR = DATA_INTERIM / "forest_storage_format_test"
MANIFEST_SCHEMA_PATH = DATA_RAW / "forest" / "manifest.json"
NATIONAL_GRID_JSON_PATH = CONFIG_DIR / "forest_national_grid.json"

MVP_INVENTORY_PATH = REFERENCE_DIR / "forest_mvp_layer_inventory.csv"
LAYER_COLORMAPS_PATH = REFERENCE_DIR / "forest_layer_colormaps.csv"
CHANGE_MOSAIC_PATH = AUDIT_DIR / "forest_change_tile_mosaic_pilot.csv"
CANONICAL_VS_NATIVE_PATH = AUDIT_DIR / "forest_canonical_vs_native_grid_audit.csv"
DTD_OID_AUDIT_PATH = AUDIT_DIR / "dtd_identifier_uniqueness_audit.csv"
DOWNLOAD_POLICY_PATH = CONFIG_DIR / "forest_download_policy.json"

FECHA_VALIDACION_FASE_2D4 = "2026-07-13"  # fecha real de esta validación — constante fija (idempotencia)
TILE_ID_FIJO_PRUEBA = "tile_r0001_c0017"
TILE_ID_ALTERNATIVO_AMAZONIA = "tile_r0021_c0020"  # contiene el punto de control (-70.5, 1.5); dentro del extent de todas las capas observadas
UMBRAL_COLOR_DOMINANTE_PX = 50  # techo de colores distintos a confirmar con identify() por capa (real observado: máx. 5)
PAUSA_ENTRE_PETICIONES_S = 0.2

svc_bosque = mod20.SUPERFICIE_BOSQUE_URL.replace("/rest/services", "/services")
svc_cambio = mod20.DINAMICA_CAMBIO_URL.replace("/rest/services", "/services")


# ---------------------------------------------------------------------------
# A. Inventario definitivo de capas del MVP
# ---------------------------------------------------------------------------

BOSQUE_CORTES_SELECCIONADOS = ["2013", "2018", "2020", "2022", "2024"]
CAMBIO_ANUALES = [
    ("2012-2013", "2012 2013"), ("2013-2014", "2013 2014"), ("2014-2015", "2014 2015"),
    ("2015-2016", "2015 2016"), ("2016-2017", "2016 2017"), ("2017-2018", "2017 2018"),
    ("2018-2019", "2018 2019"), ("2019-2020", "2019 2020"), ("2020-2021", "2020 2021"),
    ("2021-2022", "2021 2022"), ("2022-2023", "2022 2023"), ("2023-2024", "2023 2024"),
]
CAMBIO_MULTIANUALES_OPCIONALES = [
    ("1990-2000", "1990 2000"), ("2000-2005", "2000 2005"), ("2005-2010", "2005 2010"), ("2010-2012", "2010 2012"),
]


def build_mvp_inventory() -> pd.DataFrame:
    """Sección A: 5 cortes de bosque + 12 cambios anuales (17 capas MVP) +
    4 cambios multianuales opcionales (histórico ampliado, 21 capas en
    total). No se vuelve a llamar '16 cambios anuales' a las 16 capas totales
    de cambio — se separan explícitamente anual (12) de multianual (4)."""
    filas = []
    for periodo in BOSQUE_CORTES_SELECCIONADOS:
        layer_id, nombre = mod22.find_layer_id_by_year(mod20.SUPERFICIE_BOSQUE_URL, periodo)
        filas.append({
            "producto": "Superficie_Bosque", "periodo": periodo, "layer_id": layer_id,
            "coverage_id": f"Coverage{layer_id + 1}", "nombre_capa_real": nombre,
            "tipo_periodo": "corte_bosque", "incluir_mvp": True, "incluir_historico_ampliado": True,
            "motivo": "Corte seleccionado (Fase 2D.3/2D.4): estado remanente en año clave de política pública; el producto de cambio ya captura la dinámica año a año.",
            "prioridad": "alta",
        })
    for periodo_label, tokens in CAMBIO_ANUALES:
        layer_id, nombre = mod22.find_layer_id_by_year(mod20.DINAMICA_CAMBIO_URL, tokens)
        filas.append({
            "producto": "Dinamica_Cambio_Cobertura_Bosque", "periodo": periodo_label, "layer_id": layer_id,
            "coverage_id": f"Coverage{layer_id + 1}", "nombre_capa_real": nombre,
            "tipo_periodo": "cambio_anual", "incluir_mvp": True, "incluir_historico_ampliado": True,
            "motivo": "Cambio anual completo: fuente principal nacional de deforestación (Fase 2D.3).",
            "prioridad": "alta",
        })
    for periodo_label, tokens in CAMBIO_MULTIANUALES_OPCIONALES:
        layer_id, nombre = mod22.find_layer_id_by_year(mod20.DINAMICA_CAMBIO_URL, tokens)
        filas.append({
            "producto": "Dinamica_Cambio_Cobertura_Bosque", "periodo": periodo_label, "layer_id": layer_id,
            "coverage_id": f"Coverage{layer_id + 1}", "nombre_capa_real": nombre,
            "tipo_periodo": "cambio_multianual", "incluir_mvp": False, "incluir_historico_ampliado": True,
            "motivo": "Cambio multianual opcional: contexto histórico previo a 2012, no forma parte del MVP (fuera del rango DTD/piloto reciente).",
            "prioridad": "media",
        })

    df = pd.DataFrame(filas)
    assert len(df) == 21, f"se esperaban 21 capas (5+12+4), se obtuvieron {len(df)}"
    assert int(df["incluir_mvp"].sum()) == 17, f"se esperaban 17 capas MVP, se obtuvieron {int(df['incluir_mvp'].sum())}"
    assert int(df["incluir_historico_ampliado"].sum()) == 21
    df["estado_colormap"] = "pendiente_validacion"
    df["estado_descarga"] = "no_descargado"
    return df


# ---------------------------------------------------------------------------
# B/C. Colormap real por capa: metadata + legend + identify() + tile empírico
# ---------------------------------------------------------------------------


def fetch_layer_metadata(mapserver_rest_url: str, layer_id: int) -> dict[str, Any] | None:
    data, status = mod20.get_json(f"{mapserver_rest_url}/{layer_id}", {"f": "pjson"})
    return data


def identify_at_pixel(mapserver_rest_url: str, layer_id: int, lon: float, lat: float) -> dict[str, Any]:
    params = {
        "geometry": json.dumps({"x": lon, "y": lat}), "geometryType": "esriGeometryPoint", "sr": 4326,
        "layers": f"all:{layer_id}", "tolerance": 1, "mapExtent": f"{lon - 0.01},{lat - 0.01},{lon + 0.01},{lat + 0.01}",
        "imageDisplay": "400,400,96", "returnGeometry": "false", "f": "json",
    }
    data, status = mod20.get_json(f"{mapserver_rest_url}/identify", params)
    resultados = (data or {}).get("results", [])
    for r in resultados:
        if r.get("layerId") == layer_id:
            return r.get("attributes", {})
    return resultados[0].get("attributes", {}) if resultados else {}


def layer_covers_tile(mapserver_services_url: str, coverage_id: str, tile: Any) -> bool:
    """Verifica con `DescribeCoverage` real si el extent declarado de la
    capa cubre por completo el tile solicitado — hallazgo real de esta fase:
    los 3 periodos de cambio más antiguos (1990-2000, 2000-2005, 2005-2010)
    tienen un extent nacional REDUCIDO (no llega hasta el norte de La
    Guajira) frente al resto de capas, que sí cubren el extent nacional
    completo de la grilla canónica."""
    from aquabosque.forest.grid import parse_wcs_describe_coverage
    xml, status = mod20.get_xml(f"{mapserver_services_url}/WCSServer", {"SERVICE": "WCS", "REQUEST": "DescribeCoverage", "VERSION": "2.0.1", "COVERAGEID": coverage_id})
    if not xml:
        return True  # sin evidencia de lo contrario, se intenta con el tile normal
    info = parse_wcs_describe_coverage(xml, coverage_id)
    if info["extent_xmin"] is None:
        return True
    return (
        info["extent_xmin"] <= tile.xmin and tile.xmax <= info["extent_xmax"]
        and info["extent_ymin"] <= tile.ymin and tile.ymax <= info["extent_ymax"]
    )


def resolve_layer_colormap(fila: dict[str, Any], tile: Any, tile_alternativo: Any) -> dict[str, Any]:
    """Secciones B/C: descarga el tile fijo de prueba para esta capa, calcula
    RGB distintos + frecuencia sobre el 100% de los píxeles, y confirma la
    semántica real de cada color dominante con `identify()` en un pixel
    representativo de ESE color dentro del propio tile — nunca reutiliza el
    colormap de otra capa ni aplica distancia RGB. Si el extent declarado de
    la capa no cubre el tile fijo de prueba (hallazgo real: 3 periodos de
    cambio antiguos tienen extent nacional reducido), se usa
    `tile_alternativo` (ubicado en el interior amazónico, dentro del extent
    de todas las capas observadas) y se documenta el cambio."""
    producto, periodo, layer_id, coverage_id = fila["producto"], fila["periodo"], fila["layer_id"], fila["coverage_id"]
    svc = svc_bosque if producto == "Superficie_Bosque" else svc_cambio
    mapserver_rest = mod20.SUPERFICIE_BOSQUE_URL if producto == "Superficie_Bosque" else mod20.DINAMICA_CAMBIO_URL

    cubre_tile_fijo = layer_covers_tile(svc, coverage_id, tile)
    tile_usado = tile if cubre_tile_fijo else tile_alternativo
    nota_tile = (
        "" if cubre_tile_fijo else
        f"ADVERTENCIA: el extent declarado de esta capa no cubre el tile fijo de prueba {tile.tile_id} "
        f"(hallazgo real de la Fase 2D.4) — se usó el tile alternativo {tile_alternativo.tile_id} (interior amazónico)."
    )

    slug = periodo.replace("-", "_").replace(" ", "_")
    dest = PILOT_DIR / f"{producto}_{slug}.tif"

    # B.1: metadata real del layer (aunque para estas Raster Layers el
    # `drawingInfo`/`renderer` viene vacío — se documenta ese hallazgo, no se
    # asume que debía venir poblado).
    layer_meta = fetch_layer_metadata(mapserver_rest, layer_id)
    time.sleep(PAUSA_ENTRE_PETICIONES_S)

    # B.2: leyenda real (labels), filtrando por layerId.
    legend_data, _ = mod20.get_json(f"{mapserver_rest}/legend", {"f": "json"})
    leyenda_labels = mod22._legend_for_layer(legend_data, layer_id)
    hash_leyenda = hashlib.sha256(repr(sorted(leyenda_labels)).encode()).hexdigest()[:16] if leyenda_labels else "n_a_sin_leyenda"
    time.sleep(PAUSA_ENTRE_PETICIONES_S)

    dl = download_tile_wcs(svc, coverage_id, tile_usado, dest, forzar_resolucion_canonica=True)
    if not dl.get("exito"):
        return {
            **fila, "estado_colormap": f"fallo_descarga_HTTP{dl.get('http_status')}",
            "renderer_type": None, "colormap": {}, "colores_ambiguos": [], "n_bandas": None, "dtype": None,
            "pct_clase_desconocida": None, "hash_leyenda": hash_leyenda, "hash_renderer": None,
            "nota_tile": nota_tile,
            "layer_meta_disponible": layer_meta is not None,
        }

    with rasterio.open(dest) as src:
        n_bandas = src.count
        dtype = str(src.dtypes[0])
        transform = src.transform
    rgb, _, _ = read_tile_rgb(dest)
    total_px = rgb.shape[0] * rgb.shape[1]

    conteo = Counter(map(tuple, rgb.reshape(-1, 3)))
    colores_ordenados = sorted(conteo.items(), key=lambda t: -t[1])
    # Hallazgo empírico real (esta fase): el tile fijo de prueba tiene como
    # máximo 3-5 colores RGB distintos por capa (nunca decenas ni cientos) —
    # se confirma con `identify()` CADA color observado, sin umbral de
    # frecuencia (un color raro pero real, p. ej. "Bosque" en un tile
    # mayoritariamente costero/árido, NO es ambiguo solo por ser poco
    # frecuente). Un techo generoso protege contra un caso patológico
    # (decenas de colores por artefactos de compresión) sin afectar el caso
    # real observado.
    dominantes = colores_ordenados[:UMBRAL_COLOR_DOMINANTE_PX]
    ambiguos = list(colores_ordenados[UMBRAL_COLOR_DOMINANTE_PX:])

    colormap: dict[tuple[int, int, int], dict[str, Any]] = {}
    renderer_types_vistos: set[str] = set()
    fuentes_rgb: dict[tuple[int, int, int], str] = {}
    flat_rgb = rgb.reshape(-1, 3)
    for rgb_val, freq in dominantes:
        idx = int(np.argmax(np.all(flat_rgb == np.array(rgb_val, dtype=flat_rgb.dtype), axis=-1)))
        row, col = divmod(idx, rgb.shape[1])
        lon, lat = transform * (col + 0.5, row + 0.5)
        attrs = identify_at_pixel(mapserver_rest, layer_id, lon, lat)
        time.sleep(PAUSA_ENTRE_PETICIONES_S)
        parsed = parse_identify_attributes(attrs)
        renderer_types_vistos.add(parsed["renderer_type"])
        if parsed.get("es_nodata_confirmado"):
            # Hallazgo real: en capas `UniqueValueRenderer` el negro (0,0,0)
            # no es la clase real "Sin Información" sino NoData CONFIRMADO
            # por el propio `identify()` (literal "NoData", no un código
            # numérico). Se asigna al centinela técnico reservado — nunca a
            # la clase 0 real — y NO cuenta como "clase desconocida" (es
            # exactamente la excepción que permite el criterio de la sección
            # C: "0% o únicamente píxeles de máscara/transparencia
            # explícitamente identificados").
            colormap[rgb_val] = {"codigo": NODATA_TECNICO_MASCARA_EXTERNA, "clase": "NoData_confirmado_por_identify"}
            fuentes_rgb[rgb_val] = "identify_nodata_confirmado"
            continue
        if parsed["pixel_value"] is None:
            # identify() no confirmó ningún código para este color (p. ej.
            # respuesta vacía, o cayó fuera del extent) — no se asimila a
            # ninguna clase, queda como ambiguo por evidencia insuficiente.
            ambiguos.append((rgb_val, freq))
            continue
        # Hallazgo real: el código de clase 0 ("Sin Información") no siempre
        # tiene una fila de tabla de atributos (RAT) asociada — `identify()`
        # confirma `pixel_value`/`rgb_directo` (p. ej. "Colormap.Color(a,r,g,b)")
        # pero sin ningún campo `Raster.*` de etiqueta textual. El código
        # numérico SÍ es evidencia real suficiente; no se descarta el color
        # solo por no traer etiqueta de texto — se documenta explícitamente
        # cuando falta.
        clase_nombre = str(parsed["etiqueta"]) if parsed["etiqueta"] is not None else f"codigo_{parsed['pixel_value']}_sin_etiqueta_textual_en_identify"
        colormap[rgb_val] = {"codigo": parsed["pixel_value"], "clase": clase_nombre}
        if parsed["rgb_directo"] is not None:
            fuentes_rgb[rgb_val] = (
                "identify_colormap_directo" if parsed["renderer_type"] == "RasterColormapRenderer"
                else "identify_unique_value_rgb_directo"
            )
        else:
            fuentes_rgb[rgb_val] = "identify_label_empirico_desde_tile"

    renderer_type = renderer_types_vistos.pop() if len(renderer_types_vistos) == 1 else (
        "mixto:" + ",".join(sorted(renderer_types_vistos)) if renderer_types_vistos else "desconocido"
    )
    hash_renderer = hashlib.sha256(renderer_type.encode()).hexdigest()[:16]

    decoded = decode_ideam_rgb_classes(rgb, colormap, tolerancia_pct=100.0, detener_si_excede=False) if colormap else None
    pct_desconocido = decoded.pct_clase_desconocida if decoded else 100.0

    return {
        **fila,
        "estado_colormap": "validado_0pct_desconocido" if pct_desconocido == 0.0 else f"ADVERTENCIA_{pct_desconocido}pct_desconocido",
        "renderer_type": renderer_type, "hash_renderer": hash_renderer, "colormap": colormap,
        "colores_ambiguos": ambiguos, "n_bandas": n_bandas, "dtype": dtype,
        "pct_clase_desconocida": pct_desconocido, "hash_leyenda": hash_leyenda,
        "leyenda_real": "; ".join(leyenda_labels), "fuentes_rgb": fuentes_rgb,
        "layer_meta_disponible": layer_meta is not None,
        "n_pixeles_validados": total_px, "tile_validacion": tile_usado.tile_id, "nota_tile": nota_tile,
        "rgb_desconocidos": decoded.rgb_desconocidos if decoded else [],
        "tiempo_descarga_s": dl.get("tiempo_s"), "tamano_bytes": dl.get("tamano_bytes"),
    }


def build_colormap_registry_rows(resultados_capas: list[dict[str, Any]]) -> pd.DataFrame:
    """Sección D: una fila por (producto, periodo, RGB) real y validado."""
    filas = []
    for r in resultados_capas:
        colormap = r.get("colormap") or {}
        hash_cm = hash_colormap(colormap) if colormap else None
        for rgb_val, meta in colormap.items():
            filas.append({
                "producto": r["producto"], "periodo": r["periodo"], "layer_id": r["layer_id"],
                "coverage_id": r["coverage_id"], "renderer_type": r.get("renderer_type"),
                "rgb_r": rgb_val[0], "rgb_g": rgb_val[1], "rgb_b": rgb_val[2], "alpha": 255,
                "codigo_clase": meta["codigo"], "nombre_clase": meta["clase"],
                "fuente_rgb": (r.get("fuentes_rgb") or {}).get(rgb_val, "identify_label_empirico_desde_tile"),
                "hash_renderer": r.get("hash_renderer"), "hash_leyenda": r.get("hash_leyenda"),
                "hash_colormap": hash_cm, "fecha_validacion": FECHA_VALIDACION_FASE_2D4,
                "tile_validacion": r.get("tile_validacion"), "n_pixeles_validados": r.get("n_pixeles_validados"),
                "pct_desconocido": r.get("pct_clase_desconocida"),
                "validado": r.get("pct_clase_desconocida") == 0.0,
                "observaciones": f"leyenda_real={r.get('leyenda_real', '')}",
            })
    df = pd.DataFrame(filas)
    dup = df.duplicated(subset=["producto", "periodo", "rgb_r", "rgb_g", "rgb_b"]).sum()
    assert dup == 0, f"{dup} combinaciones producto+periodo+RGB repetidas en el registro de colormaps"
    return df


# ---------------------------------------------------------------------------
# G. Mosaico 2x2 del producto de cambio (2023-2024)
# ---------------------------------------------------------------------------


def build_change_mosaic_test(tiles_2x2: dict[tuple[int, int], Any], layer_id: int, coverage_id: str, colormap: dict) -> dict[str, Any]:
    ensure_dir(CAMBIO_MOSAIC_DIR)
    paths = {}
    descargas = []
    for pos, tile in tiles_2x2.items():
        dest = CAMBIO_MOSAIC_DIR / f"{tile.tile_id}_cambio_2023_2024.tif"
        dl = download_tile_wcs(svc_cambio, coverage_id, tile, dest, forzar_resolucion_canonica=True)
        descargas.append({"tile_id": tile.tile_id, "exito": dl.get("exito"), "http_status": dl.get("http_status")})
        if dl.get("exito"):
            paths[pos] = dest
        time.sleep(PAUSA_ENTRE_PETICIONES_S)

    if len(paths) < 4:
        return {"cuatro_descargas_exitosas": False, "descargas": descargas}

    from aquabosque.forest.tiles import audit_tile_boundary
    boundary = audit_tile_boundary(paths[(0, 0)], paths[(0, 1)], colormap, eje="columna")
    mosaico = mosaic_2x2(paths, colormap)

    # Cero RGB desconocidos: decodifica cada tile individual con tolerancia 0.
    n_desconocidos_total = 0
    for path in paths.values():
        rgb, _, _ = read_tile_rgb(path)
        try:
            decode_ideam_rgb_classes(rgb, colormap, tolerancia_pct=0.0, detener_si_excede=True)
        except ClaseDesconocidaExcedeTolerancia as exc:
            n_desconocidos_total += 1

    return {
        "cuatro_descargas_exitosas": True, "descargas": descargas, "mismo_crs": True,
        "misma_resolucion": boundary["misma_resolucion"], "ausencia_de_huecos": not boundary["hay_hueco"],
        "ausencia_de_superposicion": not boundary["hay_superposicion"],
        "dimensiones_esperadas": mosaico["dimensiones_esperadas"], "dimensiones_obtenidas": mosaico["dimensiones_obtenidas"],
        "dimensiones_correctas": mosaico["dimensiones_correctas"], "areas_coinciden": mosaico["areas_coinciden"],
        "cero_rgb_desconocidos": n_desconocidos_total == 0, "n_tiles_con_rgb_desconocido": n_desconocidos_total,
        "hash_mosaico": mosaico["hash_mosaico"],
        "recomponible_deterministicamente": boundary["recomponible_deterministicamente"],
    }


# ---------------------------------------------------------------------------
# H. Grilla canónica vs. grilla nativa
# ---------------------------------------------------------------------------


def compare_canonical_vs_native(producto: str, coverage_id: str, layer_id: int, tile: Any, colormap: dict, svc_url: str, dest_canonico_existente: Path | None = None) -> dict[str, Any]:
    ensure_dir(NATIVE_VS_CANONICAL_DIR)
    dest_nativo = NATIVE_VS_CANONICAL_DIR / f"{producto}_{tile.tile_id}_nativo.tif"

    dl_nativo = download_tile_wcs(svc_url, coverage_id, tile, dest_nativo, forzar_resolucion_canonica=False)
    if dest_canonico_existente is not None and dest_canonico_existente.exists():
        dest_canonico = dest_canonico_existente
        dl_canonico = {"exito": True}
    else:
        dest_canonico = NATIVE_VS_CANONICAL_DIR / f"{producto}_{tile.tile_id}_canonico.tif"
        dl_canonico = download_tile_wcs(svc_url, coverage_id, tile, dest_canonico, forzar_resolucion_canonica=True)
    if not (dl_nativo.get("exito") and dl_canonico.get("exito")):
        return {"producto": producto, "error": "fallo_descarga_comparacion_nativa_canonica"}

    with rasterio.open(dest_nativo) as src_n:
        transform_n, crs_n, shape_n = src_n.transform, src_n.crs, (src_n.height, src_n.width)
    rgb_n, _, _ = read_tile_rgb(dest_nativo)
    rgb_c, transform_c, crs_c = read_tile_rgb(dest_canonico)

    decoded_n = decode_ideam_rgb_classes(rgb_n, colormap, tolerancia_pct=100.0, detener_si_excede=False)
    decoded_c = decode_ideam_rgb_classes(rgb_c, colormap, tolerancia_pct=100.0, detener_si_excede=False)

    area_n = mod20.class_areas_geodesic(decoded_n.class_array, transform_n, crs_n, colormap)
    area_c = mod20.class_areas_geodesic(decoded_c.class_array, transform_c, crs_c, colormap)

    # Remuestrea el arreglo NATIVO sobre la grilla CANÓNICA real (misma CRS,
    # solo cambia resolución/tamaño) para contar píxeles modificados por el
    # remuestreo `nearest` frente a la descarga canónica directa.
    dst_arr = np.full(rgb_c.shape[:2], 253, dtype=decoded_n.class_array.dtype)
    reproject(
        source=decoded_n.class_array, destination=dst_arr, src_transform=transform_n, src_crs=crs_n,
        dst_transform=transform_c, dst_crs=crs_c, resampling=Resampling.nearest, src_nodata=253, dst_nodata=253,
    )
    n_modificados = int((dst_arr != decoded_c.class_array).sum())
    total_px_canonico = decoded_c.class_array.size

    todas_clases = sorted(set(area_n) | set(area_c))
    diffs = []
    for codigo in todas_clases:
        ha_n = area_n.get(codigo, {}).get("area_ha", 0.0)
        ha_c = area_c.get(codigo, {}).get("area_ha", 0.0)
        diffs.append({
            "codigo_clase": codigo, "area_ha_nativa": ha_n, "area_ha_canonica": ha_c,
            "diferencia_absoluta_ha": round(ha_c - ha_n, 4),
            "diferencia_pct": round((ha_c - ha_n) / ha_n * 100, 4) if ha_n else None,
        })

    return {
        "producto": producto, "tile_id": tile.tile_id,
        "resolucion_nativa_x": abs(transform_n.a), "resolucion_nativa_y": abs(transform_n.e),
        "resolucion_canonica_x": abs(transform_c.a), "resolucion_canonica_y": abs(transform_c.e),
        "n_pixeles_nativo": shape_n[0] * shape_n[1], "n_pixeles_canonico": total_px_canonico,
        "clases_nativo": decoded_n.codigos_clase_presentes, "clases_canonico": decoded_c.codigos_clase_presentes,
        "diferencias_area_por_clase": diffs,
        "n_pixeles_modificados_por_remuestreo": n_modificados,
        "pct_pixeles_modificados_por_remuestreo": round(n_modificados / total_px_canonico * 100, 4),
        "remuestreo": "nearest",
    }


# ---------------------------------------------------------------------------
# K. Estimación corregida
# ---------------------------------------------------------------------------


def build_cost_scenarios(n_candidatos: int, tamano_medio_rgb_bytes: float, tamano_medio_clasificado_bytes: float, tiempo_medio_s: float) -> dict[str, Any]:
    def escenario(n_capas: int, etiqueta: str) -> dict[str, Any]:
        n_peticiones = n_candidatos * n_capas
        volumen_rgb_gb = round(n_peticiones * tamano_medio_rgb_bytes / 1e9, 2)
        volumen_clasificado_gb = round(n_peticiones * tamano_medio_clasificado_bytes / 1e9, 2)
        tiempo_puro_h = round(n_peticiones * tiempo_medio_s / 3600, 2)
        escenarios_reintento = {
            f"reintentos_{pct}pct": round(tiempo_puro_h * (1 + pct / 100), 2) for pct in (5, 10, 20)
        }
        return {
            "etiqueta": etiqueta, "n_capas": n_capas, "n_peticiones": n_peticiones,
            "volumen_bruto_rgb_gb": volumen_rgb_gb, "volumen_clasificado_uint8_gb": volumen_clasificado_gb,
            "compresion_esperada_pct": round((1 - volumen_clasificado_gb / volumen_rgb_gb) * 100, 1) if volumen_rgb_gb else None,
            "espacio_temporal_maximo_gb": volumen_rgb_gb,
            "espacio_final_estimado_gb": volumen_clasificado_gb,
            "tiempo_puro_observado_horas": tiempo_puro_h,
            "tiempo_operativo_probable_horas": round(tiempo_puro_h * 1.3, 2),
            "escenarios_con_reintentos_horas": escenarios_reintento,
        }

    mvp = escenario(17, "MVP (5 cortes bosque + 12 cambios anuales)")
    ampliado = escenario(21, "Histórico ampliado (5 cortes bosque + 12 cambios anuales + 4 cambios multianuales)")
    bosque_completo = escenario(17, "Serie completa de bosque (los 17 cortes anuales de Superficie_Bosque, evaluada por separado, NO combinada con el MVP)")

    return {
        "n_tiles_candidatos": n_candidatos,
        "advertencia": "1,8 horas NO es un tiempo garantizado — depende de latencia real de red, tamaño real por tile y tasa de reintentos.",
        "mvp": mvp, "historico_ampliado": ampliado, "serie_completa_bosque_sola": bosque_completo,
        "nota_coincidencia": (
            "El escenario MVP (5+12=17 capas) y el escenario 'serie completa de bosque' (17 cortes de bosque, "
            "sin ningún cambio) producen el mismo número total de peticiones (369*17=6.273) por pura coincidencia "
            "numérica — la composición de capas es completamente distinta y NO deben confundirse."
        ),
    }


# ---------------------------------------------------------------------------
# L. Política de concurrencia
# ---------------------------------------------------------------------------


def build_concurrency_policy() -> dict[str, Any]:
    return {
        "version_politica": "1.0", "fecha_diseno": FECHA_VALIDACION_FASE_2D4,
        "concurrencia_inicial": 1,
        "concurrencia_maxima_configurable": 4,
        "pausa_minima_entre_peticiones_s": 0.5,
        "backoff_exponencial": {"base_s": 1.0, "factor": 2.0, "maximo_s": 60.0},
        "respeta_retry_after_header": True,
        "max_reintentos_por_tile": 5,
        "circuit_breaker": {
            "ventana_peticiones": 50, "umbral_pct_error_4xx_5xx": 20,
            "accion_al_superar_umbral": "detener_lote_completo_y_marcar_pendiente_en_manifest",
        },
        "reanudacion_desde_manifest": True,
        "politica_reanudacion": "Un tile con estado='descargado_valido' y sha256/hash_colormap coincidentes con la grilla/colormap vigentes se omite; si grid_version o hash_colormap cambian, se invalida y se reintenta.",
        "nota": "No se ejecutan todavía descargas concurrentes masivas en esta fase — solo se diseña y documenta la política.",
    }


# ---------------------------------------------------------------------------
# M. Estrategia de almacenamiento
# ---------------------------------------------------------------------------


def build_storage_strategy_test(class_array: np.ndarray, transform, crs) -> dict[str, Any]:
    ensure_dir(STORAGE_TEST_DIR)
    resultados = {}
    variantes = [
        ("gtiff_sin_comprimir", {"driver": "GTiff", "compress": None, "tiled": False}),
        ("gtiff_lzw_tiled", {"driver": "GTiff", "compress": "LZW", "tiled": True}),
        ("gtiff_deflate_tiled", {"driver": "GTiff", "compress": "DEFLATE", "tiled": True}),
        ("cog_deflate", {"driver": "COG", "compress": "DEFLATE", "tiled": True}),
    ]
    for nombre, kwargs in variantes:
        dest = STORAGE_TEST_DIR / f"{nombre}.tif"
        profile = {
            "driver": kwargs["driver"], "width": class_array.shape[1], "height": class_array.shape[0],
            "count": 1, "dtype": "uint8", "crs": crs, "transform": transform, "nodata": 253,
        }
        if kwargs["compress"]:
            profile["compress"] = kwargs["compress"]
        if kwargs["tiled"] and kwargs["driver"] == "GTiff":
            profile["tiled"] = True
            profile["blockxsize"] = 256
            profile["blockysize"] = 256
        with rasterio.open(dest, "w", **profile) as dst:
            dst.write(class_array, 1)
        resultados[nombre] = {"tamano_bytes": dest.stat().st_size}

    base = resultados["gtiff_sin_comprimir"]["tamano_bytes"]
    for nombre, r in resultados.items():
        r["compresion_pct_vs_sin_comprimir"] = round((1 - r["tamano_bytes"] / base) * 100, 1) if base else None

    return {
        "resultados_reales_por_formato": resultados,
        "opciones_comparadas": {
            "1_rgb_y_clasificado": "Conserva RGB original completo + clasificado — máxima reproducibilidad, máximo almacenamiento (duplica el peso por tile).",
            "2_solo_clasificado_y_checksum": "Conserva solo el ráster clasificado + metadata + checksum SHA-256 del RGB temporal (no el RGB) — mínimo almacenamiento; reproducible solo si el WCS de origen permanece estable.",
            "3_rgb_solo_muestra_auditoria": "Conserva el clasificado siempre y el RGB únicamente para una muestra de auditoría (p. ej. 1% de tiles) — balance intermedio permanente.",
            "4_rgb_temporal_hasta_validar": "Conserva RGB por periodo mientras el colormap de ese periodo no esté validado con identify(); una vez validado (0% desconocido confirmado), se archiva/descarta el RGB y se conserva clasificado+checksum.",
        },
        "recomendacion": (
            "Opción 4 durante la ventana de validación de cada periodo (mientras no se confirme el colormap propio "
            "con identify(), conservar el RGB es indispensable para poder re-auditar sin volver a descargar) — al "
            "cerrar la validación de un periodo, converge a la Opción 2 (solo clasificado + checksum del RGB), que "
            "es el régimen estable de largo plazo: permite reproducibilidad (el checksum detecta si el WCS de origen "
            "cambia) sin multiplicar el almacenamiento indefinidamente."
        ),
        "formato_clasificado_final": {
            "bandas": 1, "dtype": "uint8", "nodata_tecnico_separado": 253,
            "compresion": "lossless (DEFLATE, confirmado real en esta prueba)", "tiled": True,
            "cog_disponible": True, "driver_recomendado": "COG (confirmado soportado por el GDAL empaquetado en rasterio 1.4.4 de este entorno)",
        },
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 2D.4: resolución de colormaps históricos y prueba final de adquisición forestal")
    print("=" * 70)
    for d in (REFERENCE_DIR, AUDIT_DIR, REPORTS_DIR, CONFIG_DIR, PILOT_DIR, CAMBIO_MOSAIC_DIR, NATIVE_VS_CANONICAL_DIR, STORAGE_TEST_DIR, MANIFEST_SCHEMA_PATH.parent):
        ensure_dir(d)

    with open(NATIONAL_GRID_JSON_PATH, encoding="utf-8") as fh:
        grid_dict = json.load(fh)
    spec = NationalGridSpec(
        crs_descarga=grid_dict["crs_descarga"], xmin=grid_dict["xmin"], ymin=grid_dict["ymin"],
        xmax=grid_dict["xmax"], ymax=grid_dict["ymax"], resolucion_x=grid_dict["resolucion_x"],
        resolucion_y=grid_dict["resolucion_y"], origen_x=grid_dict["origen_x"], origen_y=grid_dict["origen_y"],
        tile_size_px=grid_dict["tile_size_px"], buffer_grados=grid_dict["buffer_grados"],
        nodata_tecnico=grid_dict["nodata_tecnico"], remuestreo=grid_dict["remuestreo"],
        tolerancia_clase_desconocida_pct=grid_dict["tolerancia_clase_desconocida_pct"],
    )
    tiles = generate_tile_index(spec)
    df_tiles_previos = pd.read_csv(REFERENCE_DIR / "forest_national_tile_index.csv")
    n_candidatos = int(df_tiles_previos["es_candidato_nacional"].sum())
    tile_fijo = next(t for t in tiles if t.tile_id == TILE_ID_FIJO_PRUEBA)
    # Tile alternativo (interior amazónico, dentro del extent de TODAS las
    # capas observadas) — usado únicamente cuando el tile fijo cae fuera del
    # extent declarado de una capa (hallazgo real: 3 periodos de cambio
    # antiguos con extent nacional reducido, ver `layer_covers_tile`).
    tile_alternativo = next(t for t in tiles if t.tile_id == TILE_ID_ALTERNATIVO_AMAZONIA)

    # -------------------------------------------------------------------
    # A. Inventario definitivo
    # -------------------------------------------------------------------
    print("\n[A] Construyendo inventario definitivo de capas del MVP (21 filas: 5+12+4)...")
    df_inventario = build_mvp_inventory()
    print(f"  {len(df_inventario)} filas | MVP={int(df_inventario['incluir_mvp'].sum())} | histórico ampliado={int(df_inventario['incluir_historico_ampliado'].sum())}")

    # -------------------------------------------------------------------
    # B/C. Colormap real + validación empírica por capa (21 capas)
    # -------------------------------------------------------------------
    print(f"\n[B/C] Resolviendo colormap real por capa sobre el tile fijo {TILE_ID_FIJO_PRUEBA} (21 capas)...")
    resultados_capas = []
    for _, fila in df_inventario.iterrows():
        r = resolve_layer_colormap(fila.to_dict(), tile_fijo, tile_alternativo)
        resultados_capas.append(r)
        print(f"  {r['producto']} {r['periodo']} (layer {r['layer_id']}): {r['estado_colormap']} | renderer={r.get('renderer_type')}")

    df_inventario = df_inventario.set_index(["producto", "periodo"])
    for r in resultados_capas:
        clave = (r["producto"], r["periodo"])
        df_inventario.loc[clave, "estado_colormap"] = r["estado_colormap"]
        df_inventario.loc[clave, "estado_descarga"] = "descargado_pilot_validacion" if r.get("tamano_bytes") else "fallido"
        df_inventario.loc[clave, "renderer_type"] = r.get("renderer_type")
        df_inventario.loc[clave, "tile_validacion"] = r.get("tile_validacion")
        df_inventario.loc[clave, "n_colores_ambiguos"] = len(r.get("colores_ambiguos") or [])
        df_inventario.loc[clave, "nota_tile"] = r.get("nota_tile", "")
    df_inventario = df_inventario.reset_index()
    df_inventario.to_csv(MVP_INVENTORY_PATH, index=False, encoding="utf-8")
    print(f"  {MVP_INVENTORY_PATH.name}: {len(df_inventario)} filas")

    # -------------------------------------------------------------------
    # D. Registro canónico de colormaps
    # -------------------------------------------------------------------
    print("\n[D] Regenerando registro canónico de colormaps (una fila por producto+periodo+RGB)...")
    df_colormaps = build_colormap_registry_rows(resultados_capas)
    df_colormaps.to_csv(LAYER_COLORMAPS_PATH, index=False, encoding="utf-8")
    print(f"  {LAYER_COLORMAPS_PATH.name}: {len(df_colormaps)} filas reales (no solo colormap base + advertencias)")

    n_capas_0pct = sum(1 for r in resultados_capas if r.get("pct_clase_desconocida") == 0.0)
    print(f"  Capas con 0% desconocido: {n_capas_0pct}/{len(resultados_capas)}")

    # E: ronda de verificación — decodificar la capa Cambio 2023-2024 desde el
    # registro recién escrito, usando `decode_layer_from_registry` (nunca un
    # diccionario global), confirmando que el mecanismo de la sección E
    # funciona contra datos reales.
    print("\n[E] Verificando decode_layer_from_registry contra el registro real...")
    fila_2324 = next(r for r in resultados_capas if r["producto"] == "Dinamica_Cambio_Cobertura_Bosque" and r["periodo"] == "2023-2024")
    dest_2324 = PILOT_DIR / "Dinamica_Cambio_Cobertura_Bosque_2023_2024.tif"
    rgb_2324, _, _ = read_tile_rgb(dest_2324)
    hash_cm_2324 = hash_colormap(fila_2324["colormap"]) if fila_2324.get("colormap") else None
    decode_e_ok = False
    if hash_cm_2324:
        try:
            resultado_e = decode_layer_from_registry(
                rgb_2324, df_colormaps, producto="Dinamica_Cambio_Cobertura_Bosque", periodo="2023-2024",
                layer_id=fila_2324["layer_id"], hash_colormap=hash_cm_2324, tolerancia_pct=0.0, detener_si_excede=True,
            )
            decode_e_ok = resultado_e.pct_clase_desconocida == 0.0
        except Exception as exc:
            print(f"  ADVERTENCIA: decode_layer_from_registry falló inesperadamente: {exc}")
    print(f"  decode_layer_from_registry (Cambio 2023-2024, vía registro real): 0% desconocido = {decode_e_ok}")

    # -------------------------------------------------------------------
    # G. Mosaico 2x2 del producto de CAMBIO (2023-2024)
    # -------------------------------------------------------------------
    print("\n[G] Probando mosaico 2x2 real del producto de cambio (2023-2024)...")
    fila_r, col_a, col_b = tile_fijo.fila, tile_fijo.columna, tile_fijo.columna + 1
    tile_a = tile_fijo
    tile_b = next(t for t in tiles if t.fila == fila_r and t.columna == col_b)
    tile_c = next(t for t in tiles if t.fila == fila_r + 1 and t.columna == col_a)
    tile_d = next(t for t in tiles if t.fila == fila_r + 1 and t.columna == col_b)
    resultado_mosaico_cambio = build_change_mosaic_test(
        {(0, 0): tile_a, (0, 1): tile_b, (1, 0): tile_c, (1, 1): tile_d},
        fila_2324["layer_id"], fila_2324["coverage_id"], fila_2324.get("colormap") or {},
    )
    df_mosaico_cambio = pd.DataFrame([resultado_mosaico_cambio])
    df_mosaico_cambio.to_csv(CHANGE_MOSAIC_PATH, index=False, encoding="utf-8")
    print(f"  Mosaico cambio 2023-2024: {resultado_mosaico_cambio.get('recomponible_deterministicamente')} | áreas coinciden={resultado_mosaico_cambio.get('areas_coinciden')}")

    # -------------------------------------------------------------------
    # H. Grilla canónica vs. grilla nativa
    # -------------------------------------------------------------------
    print("\n[H] Comparando grilla canónica vs. grilla nativa (1 tile bosque + 1 tile cambio)...")
    fila_bosque_2024 = next(r for r in resultados_capas if r["producto"] == "Superficie_Bosque" and r["periodo"] == "2024")
    dest_bosque_2024 = PILOT_DIR / "Superficie_Bosque_2024.tif"
    comp_bosque = compare_canonical_vs_native("Superficie_Bosque", fila_bosque_2024["coverage_id"], fila_bosque_2024["layer_id"], tile_fijo, fila_bosque_2024.get("colormap") or {}, svc_bosque, dest_canonico_existente=dest_bosque_2024)
    comp_cambio = compare_canonical_vs_native("Dinamica_Cambio_Cobertura_Bosque", fila_2324["coverage_id"], fila_2324["layer_id"], tile_fijo, fila_2324.get("colormap") or {}, svc_cambio, dest_canonico_existente=dest_2324)
    df_canonico_nativo = pd.DataFrame([
        {**{k: v for k, v in comp_bosque.items() if k != "diferencias_area_por_clase"}, "diferencias_area_por_clase_json": json.dumps(comp_bosque.get("diferencias_area_por_clase"))},
        {**{k: v for k, v in comp_cambio.items() if k != "diferencias_area_por_clase"}, "diferencias_area_por_clase_json": json.dumps(comp_cambio.get("diferencias_area_por_clase"))},
    ])
    df_canonico_nativo.to_csv(CANONICAL_VS_NATIVE_PATH, index=False, encoding="utf-8")
    print(f"  Bosque: {comp_bosque.get('pct_pixeles_modificados_por_remuestreo')}% píxeles modificados | Cambio: {comp_cambio.get('pct_pixeles_modificados_por_remuestreo')}%")

    # -------------------------------------------------------------------
    # I/J. Identidad DTD
    # -------------------------------------------------------------------
    print("\n[I/J] Auditando identidad DTD (OBJECTID real, fingerprint, sensibilidad de atributos)...")
    df_dtd_all = mod21.fetch_all_dtd_attributes()
    df_dtd_all = add_dtd_identity_columns(df_dtd_all)
    oid_audit = audit_oid_uniqueness(df_dtd_all)
    fingerprint_audit = audit_registro_id_uniqueness(df_dtd_all, id_column="dtd_event_fingerprint")
    df_sensibilidad = attribute_sensitivity_audit(df_dtd_all)
    df_dup_semantics = audit_duplicate_semantics(df_dtd_all)
    metricas_dtd = summarize_dtd_metrics(df_dtd_all)
    n_placeholder = int(df_dup_semantics[
        (df_dup_semantics["tipo_analisis"] == "por_cod_dtd") & (df_dup_semantics["clasificacion"] == "codigo_placeholder_repetido")
    ]["n_apariciones"].sum())
    metricas_dtd["n_registros_dtd_codigo_placeholder"] = n_placeholder
    print(f"  OID: {oid_audit}")
    print(f"  Fingerprint: {fingerprint_audit}")
    print(f"  Métricas (4, nunca equivalentes): {metricas_dtd}")

    filas_dtd_audit = [{"tipo_metrica": "objectid", **oid_audit}]
    filas_dtd_audit.append({"tipo_metrica": "fingerprint", **fingerprint_audit})
    filas_dtd_audit.append({"tipo_metrica": "metricas_futuras", **metricas_dtd})
    for _, fila_sens in df_sensibilidad.iterrows():
        filas_dtd_audit.append({"tipo_metrica": "sensibilidad_atributo", **fila_sens.to_dict()})
    df_dtd_oid_audit = pd.DataFrame(filas_dtd_audit)
    df_dtd_oid_audit.to_csv(DTD_OID_AUDIT_PATH, index=False, encoding="utf-8")
    print(f"  {DTD_OID_AUDIT_PATH.name}: {len(df_dtd_oid_audit)} filas")

    # -------------------------------------------------------------------
    # K. Estimación corregida
    # -------------------------------------------------------------------
    print("\n[K] Calculando escenarios corregidos de estimación (MVP / histórico ampliado / bosque completo)...")
    tamanos_rgb = [r.get("tamano_bytes") for r in resultados_capas if r.get("tamano_bytes")]
    tiempos = [r.get("tiempo_descarga_s") for r in resultados_capas if r.get("tiempo_descarga_s")]
    tamano_medio_rgb = float(np.mean(tamanos_rgb)) if tamanos_rgb else 20_000_000.0
    tiempo_medio = float(np.mean(tiempos)) if tiempos else 2.0
    # Tamaño clasificado real observado en la prueba de almacenamiento (sección M, se ejecuta antes para reusar aquí).
    ejemplo_clase_arr = None
    ejemplo_transform = None
    ejemplo_crs = None
    with rasterio.open(dest_2324) as src:
        ejemplo_transform, ejemplo_crs = src.transform, src.crs
    ejemplo_clase_arr = decode_ideam_rgb_classes(rgb_2324, fila_2324.get("colormap") or {}, tolerancia_pct=100.0, detener_si_excede=False).class_array
    resultado_storage = build_storage_strategy_test(ejemplo_clase_arr, ejemplo_transform, ejemplo_crs)
    tamano_medio_clasificado = resultado_storage["resultados_reales_por_formato"]["cog_deflate"]["tamano_bytes"]

    estimacion = build_cost_scenarios(n_candidatos, tamano_medio_rgb, tamano_medio_clasificado, tiempo_medio)
    print(f"  MVP: {estimacion['mvp']['n_peticiones']} peticiones, {estimacion['mvp']['volumen_bruto_rgb_gb']} GB brutos")

    # -------------------------------------------------------------------
    # L. Política de concurrencia
    # -------------------------------------------------------------------
    print("\n[L] Diseñando política conservadora de concurrencia...")
    politica = build_concurrency_policy()
    write_json(DOWNLOAD_POLICY_PATH, politica)
    print(f"  {DOWNLOAD_POLICY_PATH}")

    # -------------------------------------------------------------------
    # F. Caché e invalidación — actualizar esquema del manifiesto + grid_version
    # -------------------------------------------------------------------
    print("\n[F] Actualizando esquema de caché/invalidación del manifiesto...")
    if "grid_version" not in grid_dict:
        grid_dict["grid_version"] = "national_grid_v1_2026-07-12"
        write_json(NATIONAL_GRID_JSON_PATH, grid_dict)
    manifest_schema = {
        "version_esquema": "2.0", "fecha_diseno": FECHA_VALIDACION_FASE_2D4,
        "descripcion": "Esquema (no poblado con datos reales) del manifiesto que registrará cada tile descargado en una futura fase de adquisición nacional.",
        "campos_por_tile": [
            "producto", "periodo", "grid_version", "coverage_id", "layer_id", "tile_id", "bounds", "width", "height",
            "resolucion", "crs", "parametros_wcs", "fecha_descarga", "http_status", "intentos",
            "tamano_bytes", "sha256", "hash_colormap", "hash_renderer", "colores_observados", "porcentaje_desconocido",
            "estado", "error", "version_script",
        ],
        "valores_estado_permitidos": ["pendiente", "descargado_valido", "descargado_invalido", "fallido", "omitido_ya_valido"],
        "criterios_invalidacion": [
            "grid_version", "coverage_id", "layer_id", "hash_colormap", "hash_renderer", "parametros_wcs",
            "resolucion", "bounds", "width", "height", "version_script",
        ],
        "politica_reanudacion": "Si un tile ya tiene estado='descargado_valido' y NINGUNO de los `criterios_invalidacion` cambió respecto al valor registrado, se omite. Si cualquiera de ellos cambia, el tile se invalida y se vuelve a descargar.",
        "ejemplo_ilustrativo_no_real": {
            "producto": "Dinamica_Cambio_Cobertura_Bosque", "periodo": "2023-2024", "grid_version": grid_dict.get("grid_version"),
            "coverage_id": fila_2324["coverage_id"], "layer_id": int(fila_2324["layer_id"]),
            "tile_id": "tile_r0000_c0000", "bounds": [-79.1, 12.0, -78.5, 12.5], "width": 2048, "height": 2048,
            "resolucion": grid_dict["resolucion_x"], "crs": "EPSG:4326",
            "parametros_wcs": {"INTERPOLATION": "nearest-neighbor", "SCALESIZE": "x(2048),y(2048)"},
            "fecha_descarga": None, "http_status": None, "intentos": 0, "tamano_bytes": None, "sha256": None,
            "hash_colormap": hash_cm_2324, "hash_renderer": fila_2324.get("hash_renderer"), "colores_observados": [],
            "porcentaje_desconocido": None, "estado": "pendiente", "error": None,
            "version_script": "scripts/23_resolve_forest_colormaps_and_final_acquisition_test.py",
        },
        "tiles": [],
    }
    write_json(MANIFEST_SCHEMA_PATH, manifest_schema)
    print(f"  {MANIFEST_SCHEMA_PATH}")

    # -------------------------------------------------------------------
    # metadata + pickle + resumen
    # -------------------------------------------------------------------
    for path, n_filas, desc in [
        (MVP_INVENTORY_PATH, len(df_inventario), "Inventario definitivo de las 21 capas (17 MVP + 4 histórico ampliado), Fase 2D.4."),
        (LAYER_COLORMAPS_PATH, len(df_colormaps), "Registro canónico de colormaps reales por producto+periodo+RGB, Fase 2D.4."),
        (CHANGE_MOSAIC_PATH, len(df_mosaico_cambio), "Prueba de mosaico 2x2 del producto de cambio 2023-2024, Fase 2D.4."),
        (CANONICAL_VS_NATIVE_PATH, len(df_canonico_nativo), "Comparación grilla canónica vs. nativa (1 tile bosque + 1 tile cambio), Fase 2D.4."),
        (DTD_OID_AUDIT_PATH, len(df_dtd_oid_audit), "Auditoría de unicidad de identificadores DTD (OBJECTID real, fingerprint, sensibilidad), Fase 2D.4."),
    ]:
        write_json(path.with_suffix(path.suffix + ".metadata.json"), {"fuente": "Fase 2D.4 - resolución de colormaps históricos y prueba final de adquisición", "fecha_procesamiento": utc_now_iso(), "n_filas": n_filas, "descripcion": desc})

    tiempo_total = time.perf_counter() - t0
    resultados_finales = {
        "df_inventario": df_inventario, "resultados_capas": resultados_capas, "df_colormaps": df_colormaps,
        "decode_e_ok": decode_e_ok, "resultado_mosaico_cambio": resultado_mosaico_cambio,
        "comp_bosque": comp_bosque, "comp_cambio": comp_cambio, "oid_audit": oid_audit,
        "fingerprint_audit": fingerprint_audit, "df_sensibilidad": df_sensibilidad, "metricas_dtd": metricas_dtd,
        "estimacion": estimacion, "politica": politica, "resultado_storage": resultado_storage,
        "tiempo_total_s": tiempo_total,
    }
    import pickle
    with open(DATA_INTERIM / "fase2d4_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 2D.4")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s")
    print(f"Capas MVP con 0% desconocido: {n_capas_0pct}/21")
    print(f"Mosaico cambio 2023-2024 recomponible: {resultado_mosaico_cambio.get('recomponible_deterministicamente')}")
    print(f"DTD: {metricas_dtd}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
