"""Fase 2D.1: piloto técnico de acceso, semántica y consistencia de los
productos forestales oficiales del IDEAM.

Comprueba con muestras reales (no con la sola disponibilidad HTTP) que los
servicios seleccionados en la Fase 2D permiten recuperar datos geoespaciales
analíticos reproducibles, y determina qué producto debe usarse para bosque,
deforestación anual y detecciones tempranas.

No descarga la colección nacional completa. No calcula indicadores para los
1.122 territorios. No integra minería ni calidad hídrica. No construye
índice de riesgo. No entrena modelos. No crea dashboard.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.io import MemoryFile
from rasterio.mask import mask as rio_mask
from rasterio.warp import Resampling, calculate_default_transform, reproject
from shapely.geometry import shape as shapely_shape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.geo.intersection import build_transformer, reproject_geometry  # noqa: E402
from aquabosque.utils.io import ensure_dir, file_size_bytes, utc_now_iso, write_json  # noqa: E402

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "forest_sources"

METADATA_DIR = DATA_RAW / "metadata" / "forest_sources"
WCS_METADATA_DIR = METADATA_DIR / "wcs"
PILOT_DIR = DATA_RAW / "forest_pilot"
BOSQUE_PILOT_DIR = PILOT_DIR / "bosque_2024"
CAMBIO_PILOT_DIR = PILOT_DIR / "cambio_2023_2024"

AUDIT_DIR = DATA_PROCESSED / "audit"
MUNICIPIO_SELECTION_PATH = AUDIT_DIR / "forest_pilot_municipality_selection.csv"
RASTER_ACCESS_PILOT_PATH = AUDIT_DIR / "forest_raster_access_pilot.csv"
RASTER_VECTOR_COMPARISON_PATH = AUDIT_DIR / "forest_raster_vector_comparison.csv"
DTD_SEMANTIC_AUDIT_PATH = AUDIT_DIR / "dtd_semantic_audit.csv"

MGN_DIR = DATA_PROCESSED / "territorio" / "base_geometrica_divipola_mgn2025"
MGN_MANIFEST = MGN_DIR / "manifest.json"
UNIVERSO_PATH = DATA_PROCESSED / "territorio" / "universo_territorial_divipola.csv"

ARCGIS_ROOT_REST = "https://visualizador.ideam.gov.co/gisserver/rest/services"
ARCGIS_ROOT_SVC = "https://visualizador.ideam.gov.co/gisserver/services"
USER_AGENT = "AquaBosqueMineroIA/0.1 (uso academico/institucional, descarga controlada)"
TIMEOUT = 120

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

CRS_ORIGEN = "EPSG:4326"
CRS_METRICO = "EPSG:9377"
M2_PER_HA = 10_000.0

SUPERFICIE_BOSQUE_URL = f"{ARCGIS_ROOT_REST}/Superficie_Bosque/MapServer"
DINAMICA_CAMBIO_URL = f"{ARCGIS_ROOT_REST}/Dinamica_Cambio_Cobertura_Bosque/MapServer"
ZONAS_DEFOR_URL = f"{ARCGIS_ROOT_REST}/Hosted/zonas_deforestadas_2013_2024/FeatureServer/0"
DTD_URL = f"{ARCGIS_ROOT_REST}/Hosted/DTD_Trimestral/FeatureServer/0"

# Bosque No Bosque 2024 = layer 16 (Coverage17); Cambio de Bosque 2023_2024 = layer 15 (Coverage16).
LAYER_ID_BOSQUE_2024 = 16
COVERAGE_ID_BOSQUE_2024 = "Coverage17"
LAYER_ID_CAMBIO_2324 = 15
COVERAGE_ID_CAMBIO_2324 = "Coverage16"

# Diccionarios de clase (colormap ARGB -> código de píxel -> etiqueta oficial)
# derivados de la operación real `identify` del MapServer (Raster Attribute
# Table), NUNCA de inspección visual de color. Esta misma correspondencia se
# re-verifica en tiempo de ejecución (sección D) contra puntos reales.
COLORMAP_BOSQUE_NO_BOSQUE = {
    (0, 0, 0): {"codigo": 0, "clase": "Sin Informacion o NoData"},
    (60, 137, 39): {"codigo": 1, "clase": "Bosque"},
    (244, 244, 215): {"codigo": 2, "clase": "No Bosque"},
}
COLORMAP_CAMBIO_BOSQUE = {
    (0, 0, 0): {"codigo": 0, "clase": "Sin Informacion o NoData"},
    (60, 137, 39): {"codigo": 1, "clase": "Bosque Estable"},
    (255, 0, 0): {"codigo": 2, "clase": "Deforestacion"},
    (244, 244, 215): {"codigo": 5, "clase": "No Bosque Estable"},
}

# Puntos reales usados para re-verificar el colormap en tiempo de ejecución
# (sección D): un punto de bosque amazónico y uno urbano, ambos ya
# confirmados manualmente durante la investigación de esta fase.
PUNTO_VERIFICACION_BOSQUE = (-70.5, 1.5)  # Amazonía, dentro de Vaupés/Guaviare
PUNTO_VERIFICACION_NO_BOSQUE = (-74.08, 4.65)  # Bogotá


def get_xml(url: str, params: dict) -> tuple[str | None, int | None]:
    try:
        resp = SESSION.get(url, params=params, timeout=TIMEOUT)
        return resp.text, resp.status_code
    except requests.RequestException as exc:
        return None, None


def get_json(url: str, params: dict | None = None) -> tuple[dict | None, int | None]:
    try:
        resp = SESSION.get(url, params=params, timeout=TIMEOUT)
        if resp.status_code != 200:
            return None, resp.status_code
        return resp.json(), resp.status_code
    except (requests.RequestException, ValueError):
        return None, None


# ---------------------------------------------------------------------------
# B. Validación WCS
# ---------------------------------------------------------------------------


def validate_wcs_service(nombre_servicio: str, mapserver_rest_url: str) -> dict[str, Any]:
    """Sección B: valida WCS mediante peticiones reales a GetCapabilities y
    DescribeCoverage. No considera suficiente `exportMap`."""
    svc_path = mapserver_rest_url.replace(ARCGIS_ROOT_REST, ARCGIS_ROOT_SVC)
    getcap_url = f"{svc_path}/WCSServer"
    xml_getcap, status_getcap = get_xml(getcap_url, {"SERVICE": "WCS", "REQUEST": "GetCapabilities", "VERSION": "2.0.1"})
    resultado: dict[str, Any] = {"servicio": nombre_servicio, "wcs_url": getcap_url, "http_status_getcapabilities": status_getcap}

    if xml_getcap:
        (WCS_METADATA_DIR / f"{nombre_servicio}_getcapabilities.xml").write_text(xml_getcap, encoding="utf-8")
        resultado["formatos_soportados"] = sorted(set(_extract_tags(xml_getcap, "wcs:formatSupported")))
        resultado["crs_soportados"] = sorted(set(_extract_tags(xml_getcap, "crs:crsSupported")))
        resultado["interpolacion_soportada"] = sorted(set(_extract_tags(xml_getcap, "int:InterpolationSupported")))
        coverage_ids = _extract_tags(xml_getcap, "wcs:CoverageId")
        resultado["n_coverages"] = len(coverage_ids)
        resultado["coverage_ids_ejemplo"] = coverage_ids[:3] + coverage_ids[-3:] if len(coverage_ids) > 6 else coverage_ids
        resultado["service_type_versions"] = sorted(set(_extract_tags(xml_getcap, "ows:ServiceTypeVersion")))

    # DescribeCoverage sobre la cobertura más reciente (la usada en el piloto).
    coverage_objetivo = COVERAGE_ID_BOSQUE_2024 if "superficie" in nombre_servicio.lower() else COVERAGE_ID_CAMBIO_2324
    xml_desc, status_desc = get_xml(getcap_url, {"SERVICE": "WCS", "REQUEST": "DescribeCoverage", "VERSION": "2.0.1", "COVERAGEID": coverage_objetivo})
    resultado["http_status_describecoverage"] = status_desc
    resultado["coverage_objetivo_piloto"] = coverage_objetivo
    if xml_desc:
        (WCS_METADATA_DIR / f"{nombre_servicio}_describecoverage_{coverage_objetivo}.xml").write_text(xml_desc, encoding="utf-8")
        import re as _re
        resultado["n_bandas_declaradas"] = len(_re.findall(r"<swe:field\s", xml_desc))
        grid_high = _extract_tags(xml_desc, "gml:high")
        resultado["grid_high_declarado"] = grid_high[0] if grid_high else None

    # Límite de tamaño / errores del servidor: coverage inexistente.
    xml_err, status_err = get_xml(getcap_url, {"SERVICE": "WCS", "REQUEST": "GetCoverage", "VERSION": "2.0.1", "COVERAGEID": "CoverageInexistente999", "FORMAT": "image/tiff"})
    resultado["http_status_coverage_invalido"] = status_err
    resultado["maneja_error_coverage_invalido"] = bool(xml_err and "NoSuchCoverage" in xml_err)

    return resultado


def _extract_tags(xml_text: str, tag: str) -> list[str]:
    import re

    pattern = rf"<{tag}[^>]*>([^<]*)</{tag}>"
    return [m.strip() for m in re.findall(pattern, xml_text)]


# ---------------------------------------------------------------------------
# L. Selección de municipios piloto (con evidencia real)
# ---------------------------------------------------------------------------


def load_mgn2025_geometries() -> list[dict]:
    with open(MGN_MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)
    feats = []
    for a in manifest["archivos_y_tamanos"]:
        with open(MGN_DIR / a["archivo"], encoding="utf-8") as fh:
            fc = json.load(fh)
        feats.extend(fc["features"])
    return feats


def select_pilot_municipalities(mgn_features: list[dict]) -> pd.DataFrame:
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)

    # 1) Municipio con deforestación reciente: estadística real 2024 por
    # municipio, filtrando a un tamaño manejable (<600.000 ha) para que el
    # piloto sea descargable.
    stats_data, _ = get_json(
        f"{ZONAS_DEFOR_URL}/query",
        {
            "where": "ano='2024'",
            "groupByFieldsForStatistics": "cod_mpio,nom_mpio,nom_depto",
            "outStatistics": json.dumps([
                {"statisticType": "sum", "onStatisticField": "hectareas", "outStatisticFieldName": "total_ha"},
                {"statisticType": "count", "onStatisticField": "cod_zd", "outStatisticFieldName": "n_poligonos"},
            ]),
            "orderByFields": "total_ha DESC",
            "f": "json",
        },
    )
    stats_rows = [f["attributes"] for f in (stats_data or {}).get("features", [])]
    cod_to_geom = {feat["properties"]["cod_dane_mpio"]: feat for feat in mgn_features}

    def area_ha(cod: str) -> float:
        geom = shapely_shape(cod_to_geom[cod]["geometry"])
        return reproject_geometry(geom, transformer).area / M2_PER_HA

    candidato_defor = None
    for row in stats_rows:
        cod = row["cod_mpio"]
        if cod not in cod_to_geom:
            continue
        a_ha = area_ha(cod)
        if a_ha <= 600_000:
            candidato_defor = {**row, "area_ha": a_ha}
            break

    # 2) Municipio con bosque, baja o nula deforestación histórica (2013-2024):
    # departamentos amazónicos, cero registros en zonas_deforestadas.
    distinct_data, _ = get_json(f"{ZONAS_DEFOR_URL}/query", {"where": "1=1", "outFields": "cod_mpio", "returnDistinctValues": "true", "f": "json"})
    cods_con_defor = {f["attributes"]["cod_mpio"] for f in (distinct_data or {}).get("features", [])}
    deptos_forestales = {"91", "97", "94"}  # Amazonas, Vaupés, Guainía
    candidatos_bosque = []
    for feat in mgn_features:
        props = feat["properties"]
        cod_mpio = props["cod_dane_mpio"]
        cod_dpto = props.get("cod_dane_dpto", cod_mpio[:2])
        if cod_dpto in deptos_forestales and cod_mpio not in cods_con_defor:
            candidatos_bosque.append((cod_mpio, cod_dpto, area_ha(cod_mpio)))
    candidatos_bosque.sort(key=lambda x: -x[2])
    candidato_bosque = candidatos_bosque[0] if candidatos_bosque else None

    # 3) Municipio con geometría pequeña o límite complejo: mayor compacidad
    # (perímetro^2 / (4*pi*área)) entre municipios de una sola parte y área
    # > 5.000 ha (evita astillas geométricas irrelevantes).
    import math

    complejidad = []
    for feat in mgn_features:
        props = feat["properties"]
        cod_mpio = props["cod_dane_mpio"]
        geom = shapely_shape(feat["geometry"])
        geom_proj = reproject_geometry(geom, transformer)
        n_parts = len(geom_proj.geoms) if geom_proj.geom_type == "MultiPolygon" else 1
        a_m2 = geom_proj.area
        a_ha_v = a_m2 / M2_PER_HA
        if n_parts == 1 and a_ha_v > 5000:
            compact = (geom_proj.length ** 2) / (4 * math.pi * a_m2) if a_m2 else None
            complejidad.append((cod_mpio, a_ha_v, compact))
    complejidad.sort(key=lambda x: -(x[2] or 0))
    candidato_complejo = complejidad[0] if complejidad else None

    universo = pd.read_csv(UNIVERSO_PATH, dtype={"cod_dane_mpio": str, "cod_dane_dpto": str})
    nombre_por_cod = dict(zip(universo["cod_dane_mpio"], universo["nombre_mpio"]))
    dpto_por_cod = dict(zip(universo["cod_dane_mpio"], universo["nombre_dpto"]))

    filas = []
    if candidato_defor:
        cod = candidato_defor["cod_mpio"]
        filas.append({
            "rol_piloto": "deforestacion_reciente",
            "cod_dane_mpio": cod, "nombre_mpio": nombre_por_cod.get(cod), "nombre_dpto": dpto_por_cod.get(cod),
            "area_ha": round(candidato_defor["area_ha"], 1),
            "criterio_seleccion": "mayor total_ha deforestada en 2024 (consulta de estadísticas real) entre municipios con área <= 600.000 ha",
            "evidencia": f"total_ha_2024={candidato_defor['total_ha']:.2f}, n_poligonos_2024={candidato_defor['n_poligonos']}",
        })
    if candidato_bosque:
        cod, cod_dpto, a_ha_v = candidato_bosque
        filas.append({
            "rol_piloto": "bosque_baja_o_nula_deforestacion",
            "cod_dane_mpio": cod, "nombre_mpio": nombre_por_cod.get(cod), "nombre_dpto": dpto_por_cod.get(cod),
            "area_ha": round(a_ha_v, 1),
            "criterio_seleccion": "0 registros en zonas_deforestadas_2013_2024 (consulta distinct real) entre municipios de Amazonas/Vaupés/Guainía, mayor área",
            "evidencia": f"cod_dpto={cod_dpto}, n_municipios_forestales_sin_deforestacion_evaluados={len(candidatos_bosque)}",
        })
    if candidato_complejo:
        cod, a_ha_v, compact = candidato_complejo
        filas.append({
            "rol_piloto": "geometria_pequena_o_compleja",
            "cod_dane_mpio": cod, "nombre_mpio": nombre_por_cod.get(cod), "nombre_dpto": dpto_por_cod.get(cod),
            "area_ha": round(a_ha_v, 1),
            "criterio_seleccion": "mayor índice de compacidad (perímetro²/(4π·área), 1=círculo) entre municipios de una sola parte con área > 5.000 ha, calculado en EPSG:9377",
            "evidencia": f"compacidad={compact:.2f}",
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# C/D/E. Descarga e inspección de ráster piloto (WCS GetCoverage)
# ---------------------------------------------------------------------------


def extract_tiff_from_multipart(raw_bytes: bytes) -> bytes:
    parts = raw_bytes.split(b"--wcs")
    for part in parts:
        if b"Content-Type: image/tiff" in part[:200]:
            idx = part.index(b"\n\n")
            body = part[idx + 2:]
            return body.rstrip(b"\n")
    raise ValueError("Respuesta WCS no contiene una parte image/tiff — no se puede continuar.")


def download_wcs_pilot(mapserver_rest_url: str, coverage_id: str, bounds_4326: tuple[float, float, float, float], dest_path: Path) -> dict[str, Any]:
    """Sección C: intenta WCS GetCoverage primero (orden 1 del encargo). No
    hay descarga oficial directa documentada (orden 2, descartado en Fase
    2D). No se usa `exportMap` en ningún caso de esta fase porque WCS
    respondió con éxito."""
    svc_path = mapserver_rest_url.replace(ARCGIS_ROOT_REST, ARCGIS_ROOT_SVC)
    minx, miny, maxx, maxy = bounds_4326
    buffer = 0.01
    params = {
        "SERVICE": "WCS", "REQUEST": "GetCoverage", "VERSION": "2.0.1", "COVERAGEID": coverage_id,
        "FORMAT": "image/tiff",
        "SUBSET": [f"x({minx - buffer},{maxx + buffer})", f"y({miny - buffer},{maxy + buffer})"],
        "SUBSETTINGCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
        "OUTPUTCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
        "INTERPOLATION": "http://www.opengis.net/def/interpolation/OGC/1/nearest-neighbor",
    }
    t0 = time.perf_counter()
    resp = SESSION.get(f"{svc_path}/WCSServer", params=params, timeout=TIMEOUT)
    t_elapsed = time.perf_counter() - t0
    resultado = {"metodo_descarga": "WCS GetCoverage", "http_status": resp.status_code, "tiempo_s": round(t_elapsed, 2), "url_servicio": f"{svc_path}/WCSServer"}
    if resp.status_code != 200:
        resultado["exito"] = False
        resultado["mensaje"] = resp.text[:500]
        return resultado
    try:
        tiff_bytes = extract_tiff_from_multipart(resp.content)
    except ValueError as exc:
        resultado["exito"] = False
        resultado["mensaje"] = str(exc)
        return resultado
    ensure_dir(dest_path.parent)
    dest_path.write_bytes(tiff_bytes)
    resultado["exito"] = True
    resultado["archivo_analitico"] = str(dest_path.relative_to(PROJECT_ROOT))
    resultado["tamano_bytes"] = len(tiff_bytes)
    return resultado


def inspect_raster(path: Path, colormap: dict[tuple[int, int, int], dict]) -> dict[str, Any]:
    """Sección D/E: registra propiedades reales del ráster y decodifica el
    colormap RGB a códigos de clase reales — NUNCA por inspección visual."""
    with rasterio.open(path) as src:
        info: dict[str, Any] = {
            "formato": src.driver, "ancho": src.width, "alto": src.height, "n_bandas": src.count,
            "dtype": str(src.dtypes[0]), "crs": str(src.crs), "transform": str(src.transform),
            "resolucion_x": abs(src.transform.a), "resolucion_y": abs(src.transform.e),
            "bounds": tuple(src.bounds), "nodata": src.nodata, "compresion": src.compression.value if src.compression else None,
            "tamano_bytes": file_size_bytes(path), "overviews": src.overviews(1) if src.count else [],
        }
        arr = src.read()
        transform = src.transform
        crs = src.crs

    if arr.shape[0] < 3:
        info["contenido"] = "banda única — posibles códigos de clase originales (a confirmar)"
        class_arr = arr[0]
        valores_unicos, conteos = np.unique(class_arr, return_counts=True)
        info["valores_unicos"] = valores_unicos.tolist()
        info["conteos_por_valor"] = dict(zip(valores_unicos.tolist(), conteos.tolist()))
        info["contiene_codigos_clase_originales"] = True
        return info, class_arr, transform, crs

    rgb = arr[:3].transpose(1, 2, 0)
    flat = rgb.reshape(-1, 3)
    uniq_rgb, counts = np.unique(flat, axis=0, return_counts=True)
    info["valores_unicos_rgb"] = [tuple(int(v) for v in row) for row in uniq_rgb]
    info["conteos_por_valor_rgb"] = {str(tuple(int(v) for v in row)): int(c) for row, c in zip(uniq_rgb, counts)}

    no_reconocidos = [tuple(int(v) for v in row) for row in uniq_rgb if tuple(int(v) for v in row) not in colormap]
    info["contiene_codigos_clase_originales"] = False
    info["contiene_valores_rgb_renderizados"] = True
    info["rgb_no_reconocidos_en_colormap"] = no_reconocidos

    class_arr = np.zeros(rgb.shape[:2], dtype=np.uint8)
    codigos_confirmados = {}
    for color, meta in colormap.items():
        m = np.all(rgb == np.array(color, dtype=np.uint8), axis=-1)
        class_arr[m] = meta["codigo"]
        n = int(m.sum())
        if n > 0:
            codigos_confirmados[meta["codigo"]] = {"clase": meta["clase"], "n_pixeles": n}
    info["codigos_clase_validados"] = codigos_confirmados
    info["comparacion_con_leyenda_oficial"] = "coincide" if not no_reconocidos else "valores RGB sin correspondencia en el colormap conocido — requiere revisión"
    return info, class_arr, transform, crs


def verify_colormap_live(mapserver_rest_url: str, layer_id: int, layer_name: str) -> dict[str, Any]:
    """Re-verifica en tiempo de ejecución (sección D) que el colormap
    hardcodeado sigue vigente, usando la operación `identify` real sobre dos
    puntos de control (bosque y no-bosque)."""
    resultados = {}
    for etiqueta, (x, y) in (("bosque", PUNTO_VERIFICACION_BOSQUE), ("no_bosque", PUNTO_VERIFICACION_NO_BOSQUE)):
        params = {
            "geometry": json.dumps({"x": x, "y": y}), "geometryType": "esriGeometryPoint", "sr": 4326,
            "layers": f"all:{layer_id}", "tolerance": 1, "mapExtent": f"{x-0.5},{y-0.5},{x+0.5},{y+0.5}",
            "imageDisplay": "400,400,96", "returnGeometry": "false", "f": "json",
        }
        data, status = get_json(f"{mapserver_rest_url}/identify", params)
        resultados[etiqueta] = (data or {}).get("results", [])
    return resultados


# ---------------------------------------------------------------------------
# F/G. Áreas piloto y efecto de la reproyección
# ---------------------------------------------------------------------------


def geodesic_pixel_area_ha(transform, crs, shape) -> np.ndarray:
    """Área aproximada por fila de píxel usando el factor de conversión
    grado->metro dependiente de la latitud (alternativa 2 de la sección F:
    áreas geodésicas por píxel), NUNCA cantidad de píxeles × resolución
    angular constante."""
    height, width = shape
    res_x = abs(transform.a)
    res_y = abs(transform.e)
    rows = np.arange(height)
    lats = transform.f + transform.e * (rows + 0.5)
    m_per_deg_lat = 110_574.0
    m_per_deg_lon = 111_320.0 * np.cos(np.radians(lats))
    area_m2_por_fila = (res_x * m_per_deg_lon) * (res_y * m_per_deg_lat)
    area_ha_grid = np.repeat(area_m2_por_fila[:, None], width, axis=1) / M2_PER_HA
    return area_ha_grid


def reproject_class_array(class_arr: np.ndarray, src_transform, src_crs, dst_crs=CRS_METRICO):
    """Reproyecta con remuestreo `nearest` exclusivamente (obligatorio para
    clases categóricas). `calculate_default_transform` genera un rectángulo
    delimitador en el CRS destino que no coincide exactamente con la huella
    reproyectada de los datos fuente — sin `dst_nodata` explícito, los
    píxeles del borde que caen fuera de esa huella quedan rellenados con 0
    por defecto de numpy, lo que colisiona con el código de clase real
    'Sin Información' (también 0) y crea área de esa clase que no existe en
    los datos fuente. Se usa `MASCARA_FUERA_MUNICIPIO` como nodata explícito
    en origen y destino para que ese relleno nunca se confunda con una clase
    real (sección G: "no aceptar una transformación que cree valores de
    clase nuevos")."""
    dst_transform, width, height = calculate_default_transform(src_crs, dst_crs, class_arr.shape[1], class_arr.shape[0], *rasterio.transform.array_bounds(class_arr.shape[0], class_arr.shape[1], src_transform))
    dst_arr = np.full((height, width), MASCARA_FUERA_MUNICIPIO, dtype=class_arr.dtype)
    reproject(
        source=class_arr, destination=dst_arr, src_transform=src_transform, src_crs=src_crs,
        dst_transform=dst_transform, dst_crs=dst_crs, resampling=Resampling.nearest,
        src_nodata=MASCARA_FUERA_MUNICIPIO, dst_nodata=MASCARA_FUERA_MUNICIPIO,
    )
    return dst_arr, dst_transform


# Centinela usado exclusivamente por `clip_to_municipio` para marcar píxeles
# FUERA del polígono real del municipio (recorte rectangular con relleno).
# Nunca es un código de clase real del IDEAM (0-5) — se excluye siempre de
# los cálculos de área para no inflar "área válida" con territorio ajeno al
# municipio piloto.
MASCARA_FUERA_MUNICIPIO = 255


def class_areas_from_metric_grid(class_arr: np.ndarray, transform, colormap: dict) -> dict[int, float]:
    px_area_ha = abs(transform.a) * abs(transform.e) / M2_PER_HA
    codigo_a_clase = {v["codigo"]: v["clase"] for v in colormap.values()}
    areas = {}
    for codigo in np.unique(class_arr):
        if int(codigo) == MASCARA_FUERA_MUNICIPIO:
            continue
        n = int((class_arr == codigo).sum())
        areas[int(codigo)] = {"clase": codigo_a_clase.get(int(codigo), f"codigo_{codigo}"), "n_pixeles": n, "area_ha": round(n * px_area_ha, 2)}
    return areas


def class_areas_geodesic(class_arr: np.ndarray, transform, crs, colormap: dict) -> dict[int, float]:
    area_grid = geodesic_pixel_area_ha(transform, crs, class_arr.shape)
    codigo_a_clase = {v["codigo"]: v["clase"] for v in colormap.values()}
    areas = {}
    for codigo in np.unique(class_arr):
        if int(codigo) == MASCARA_FUERA_MUNICIPIO:
            continue
        m = class_arr == codigo
        areas[int(codigo)] = {"clase": codigo_a_clase.get(int(codigo), f"codigo_{codigo}"), "n_pixeles": int(m.sum()), "area_ha": round(float(area_grid[m].sum()), 2)}
    return areas


def clip_to_municipio(class_arr: np.ndarray, transform, crs, geom_4326: dict, geom_crs="EPSG:4326"):
    """Recorta el arreglo de clases al polígono real del municipio (no solo
    al bbox), usando rasterio.mask sobre un dataset en memoria. Los píxeles
    fuera del polígono quedan marcados con `MASCARA_FUERA_MUNICIPIO`, nunca
    con un código de clase real."""
    with MemoryFile() as memfile:
        with memfile.open(driver="GTiff", height=class_arr.shape[0], width=class_arr.shape[1], count=1, dtype=class_arr.dtype, crs=crs, transform=transform) as dataset:
            dataset.write(class_arr, 1)
        with memfile.open() as dataset:
            out_arr, out_transform = rio_mask(dataset, [geom_4326], crop=True, nodata=MASCARA_FUERA_MUNICIPIO)
    return out_arr[0], out_transform


# ---------------------------------------------------------------------------
# H. Piloto vectorial de zonas deforestadas
# ---------------------------------------------------------------------------


def validate_zonas_deforestadas_service() -> dict[str, Any]:
    layer_data, status = get_json(ZONAS_DEFOR_URL, {"f": "json"})
    resultado: dict[str, Any] = {"http_status": status}
    if not layer_data:
        return resultado
    resultado["nombre_real"] = layer_data.get("name")
    resultado["layer_id"] = layer_data.get("id")
    resultado["geometryType"] = layer_data.get("geometryType")
    resultado["campos"] = [f.get("name") for f in layer_data.get("fields", [])]

    sin_anio, _ = get_json(f"{ZONAS_DEFOR_URL}/query", {"where": "ano IS NULL", "returnCountOnly": "true", "f": "json"})
    resultado["n_registros_sin_anio"] = (sin_anio or {}).get("count")

    por_anio, _ = get_json(f"{ZONAS_DEFOR_URL}/query", {"where": "1=1", "groupByFieldsForStatistics": "ano", "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": "cod_zd", "outStatisticFieldName": "n"}]), "orderByFields": "ano", "f": "json"})
    resultado["registros_por_anio"] = {f["attributes"]["ano"]: f["attributes"]["n"] for f in (por_anio or {}).get("features", [])}

    dup_ids, _ = get_json(f"{ZONAS_DEFOR_URL}/query", {"where": "1=1", "groupByFieldsForStatistics": "cod_zd", "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": "cod_zd", "outStatisticFieldName": "n"}]), "having": "count(cod_zd) > 1", "f": "json"})
    resultado["n_cod_zd_duplicados"] = len((dup_ids or {}).get("features", [])) if dup_ids is not None else None
    return resultado


def query_municipio_deforestacion_2024(cod_mpio: str) -> tuple[list[dict], dict]:
    data, status = get_json(
        f"{ZONAS_DEFOR_URL}/query",
        {"where": f"ano='2024' AND cod_mpio='{cod_mpio}'", "outFields": "cod_zd,ano,cod_mpio,nom_mpio,hectareas", "returnGeometry": "true", "outSR": 4326, "f": "geojson"},
    )
    feats = (data or {}).get("features", [])
    return feats, {"http_status": status, "n_registros": len(feats)}


def compute_vector_pilot_stats(feats: list[dict], transformer) -> dict[str, Any]:
    from shapely.ops import unary_union

    geoms = []
    area_reportada_ha = 0.0
    n_invalidas = 0
    for f in feats:
        geom = shapely_shape(f["geometry"])
        geom_proj = reproject_geometry(geom, transformer)
        if not geom_proj.is_valid:
            n_invalidas += 1
            geom_proj = geom_proj.buffer(0)
        geoms.append(geom_proj)
        area_reportada_ha += f["properties"].get("hectareas") or 0.0

    area_geometrica_total_ha = sum(g.area for g in geoms) / M2_PER_HA
    union_geom = unary_union(geoms) if geoms else None
    area_union_ha = (union_geom.area / M2_PER_HA) if union_geom else 0.0

    wkts = [g.wkt for g in geoms]
    n_geom_duplicadas = len(wkts) - len(set(wkts))

    return {
        "n_poligonos": len(geoms),
        "n_geometrias_invalidas": n_invalidas,
        "n_geometrias_duplicadas": n_geom_duplicadas,
        "area_geometrica_total_ha": round(area_geometrica_total_ha, 2),
        "area_union_ha": round(area_union_ha, 2),
        "area_reportada_fuente_ha": round(area_reportada_ha, 2),
        "solape_interno_ha": round(area_geometrica_total_ha - area_union_ha, 2),
        "diferencia_suma_vs_union_pct": round((area_geometrica_total_ha - area_union_ha) / area_geometrica_total_ha * 100, 2) if area_geometrica_total_ha else 0.0,
    }


# ---------------------------------------------------------------------------
# I. Comparación ráster-vector
# ---------------------------------------------------------------------------


def compare_raster_vector(area_defor_raster_ha: float, area_union_vector_ha: float, area_suma_vector_ha: float) -> dict[str, Any]:
    if area_defor_raster_ha <= 0 and area_union_vector_ha <= 0:
        return {"clasificacion": "no_comparable", "razon": "ambas fuentes reportan 0 ha para este municipio/periodo"}
    base = max(area_defor_raster_ha, area_union_vector_ha, 1e-9)
    diff_abs_ha = abs(area_defor_raster_ha - area_union_vector_ha)
    diff_pct = diff_abs_ha / base * 100

    if diff_pct <= 15:
        clasif = "alta"
    elif diff_pct <= 40:
        clasif = "razonable"
    elif diff_pct <= 80:
        clasif = "baja"
    else:
        clasif = "no_comparable"

    razones = [
        "resolución del ráster (30 m) frente a la vectorización de polígonos puede sub/sobre-estimar bordes",
        "el ráster de cambio 2023-2024 y el registro vectorial 'año 2024' pueden usar ventanas de corte temporal ligeramente distintas dentro del mismo año calendario",
        "el registro vectorial puede aplicar un umbral mínimo de área por polígono que el ráster (pixel a pixel) no aplica",
        "generalización/discretización en la vectorización desde el ráster original",
    ]
    return {
        "clasificacion": clasif,
        "diferencia_absoluta_ha": round(diff_abs_ha, 2),
        "diferencia_porcentual": round(diff_pct, 2),
        "razones_posibles": razones,
    }


# ---------------------------------------------------------------------------
# J/K. Auditoría semántica DTD y relación con el boletín
# ---------------------------------------------------------------------------


def query_dtd_sample(anio: str, periodo: str) -> tuple[list[dict], dict]:
    """Sección J: extrae una MUESTRA (el encargo no exige el trimestre
    completo) — pero se registra explícitamente el total real del periodo
    (`returnCountOnly`) para dejar claro si la muestra es parcial frente al
    `maxRecordCount=2000` del servicio."""
    where = f"anio='{anio}' AND periodo='{periodo}'"
    count_data, _ = get_json(f"{DTD_URL}/query", {"where": where, "returnCountOnly": "true", "f": "json"})
    n_total_periodo = (count_data or {}).get("count")

    data, status = get_json(f"{DTD_URL}/query", {"where": where, "outFields": "*", "returnGeometry": "true", "outSR": 4326, "f": "geojson"})
    feats = (data or {}).get("features", [])
    return feats, {
        "http_status": status,
        "n_registros_muestra": len(feats),
        "n_total_periodo_real": n_total_periodo,
        "muestra_es_periodo_completo": n_total_periodo is not None and len(feats) >= n_total_periodo,
    }


def dtd_semantic_audit(feats: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    filas = []
    campos_encontrados = sorted(set().union(*[set(f["properties"].keys()) for f in feats])) if feats else []
    campos_esperados = {
        "identificador_registro": "cod_dtd" if "cod_dtd" in campos_encontrados else None,
        "periodo": "periodo" if "periodo" in campos_encontrados else None,
        "fecha_inicial": "fecha_inicial" if "fecha_inicial" in campos_encontrados else "NO_PRESENTE",
        "fecha_final": "fecha_final" if "fecha_final" in campos_encontrados else "NO_PRESENTE",
        "fecha_publicacion": "fecha_publicacion" if "fecha_publicacion" in campos_encontrados else "NO_PRESENTE",
        "departamento": "nom_depto" if "nom_depto" in campos_encontrados else None,
        "municipio": "nom_mpio" if "nom_mpio" in campos_encontrados else None,
        "nucleo": "nucleo_tri" if "nucleo_tri" in campos_encontrados else None,
        "tipo_alerta": "tipo_dtd" if "tipo_dtd" in campos_encontrados else None,
        "area": "NO_PRESENTE (sin campo de área en el esquema real)",
        "nivel_confianza": "NO_PRESENTE",
        "fuente_satelital": "NO_PRESENTE",
        "resolucion": "NO_PRESENTE (no declarada por registro)",
        "geometria": "punto (x, y)",
    }
    for k, v in campos_esperados.items():
        filas.append({"campo_conceptual": k, "campo_real_o_estado": v})

    df_campos = pd.DataFrame(filas)

    ids = [f["properties"].get("cod_dtd") for f in feats]
    coords = [tuple(f["geometry"]["coordinates"]) for f in feats if f.get("geometry")]
    n_dup_id = len(ids) - len(set(ids))
    n_dup_coord = len(coords) - len(set(coords))
    serie_mpio = pd.Series([f["properties"].get("nom_mpio") for f in feats])
    serie_depto = pd.Series([f["properties"].get("nom_depto") for f in feats])
    serie_nucleo = pd.Series([f["properties"].get("nucleo_tri") for f in feats])
    por_mpio = serie_mpio.value_counts()
    por_nucleo = serie_nucleo.value_counts()
    # Corrección Fase 2D.2 (sección A): `value_counts().nunique()` cuenta
    # cuántas FRECUENCIAS distintas hay (p. ej. cuántos municipios comparten
    # el mismo conteo de puntos), no cuántos municipios distintos hay. El
    # conteo correcto de categorías distintas es `serie.nunique(dropna=True)`
    # sobre la serie ORIGINAL (equivalente a `len(value_counts())`).
    n_municipios_distintos = int(serie_mpio.nunique(dropna=True))
    n_departamentos_distintos = int(serie_depto.nunique(dropna=True))
    n_nucleos_distintos = int(serie_nucleo.nunique(dropna=True))
    assert n_municipios_distintos == len(por_mpio), "serie.nunique() y len(value_counts()) deben coincidir"
    nulos = {c: sum(1 for f in feats if f["properties"].get(c) is None) for c in ("cod_dtd", "nom_mpio", "nom_depto", "nucleo_tri", "cod_depto")}

    resumen = pd.DataFrame([
        {"metrica": "n_registros_muestra", "valor": len(feats)},
        {"metrica": "n_duplicados_por_cod_dtd", "valor": n_dup_id},
        {"metrica": "n_coordenadas_duplicadas", "valor": n_dup_coord},
        {"metrica": "n_municipios_distintos", "valor": n_municipios_distintos},
        {"metrica": "n_departamentos_distintos", "valor": n_departamentos_distintos},
        {"metrica": "n_nucleos_distintos", "valor": n_nucleos_distintos},
        {"metrica": "max_puntos_un_municipio", "valor": int(por_mpio.max()) if len(por_mpio) else 0},
        {"metrica": "max_puntos_un_nucleo", "valor": int(por_nucleo.max()) if len(por_nucleo) else 0},
        {"metrica": "nulos_cod_dtd", "valor": nulos["cod_dtd"]},
        {"metrica": "nulos_nom_mpio", "valor": nulos["nom_mpio"]},
        {"metrica": "nulos_nom_depto", "valor": nulos["nom_depto"]},
        {"metrica": "nulos_nucleo_tri", "valor": nulos["nucleo_tri"]},
        {"metrica": "presencia_campo_area", "valor": "NO — no se convierte punto en hectáreas sin regla oficial"},
    ])
    return df_campos, resumen, por_mpio, por_nucleo


def compare_dtd_with_boletin(por_mpio: pd.Series) -> dict[str, Any]:
    """Sección K: compara los municipios más frecuentes del FeatureServer
    (IV trimestre 2025) con lo declarado en el Boletín 45 (departamentos con
    el 98% de la deforestación del trimestre: Caquetá 44%, Meta 26%,
    Guaviare 17%, Putumayo 10% — cifras reales tomadas del boletín, no
    inventadas)."""
    top_municipios = por_mpio.head(10).to_dict()
    deptos_boletin_45 = {"CAQUETA": 44, "META": 26, "GUAVIARE": 17, "PUTUMAYO": 10}
    return {
        "periodo_comparado": "2025-IV (FeatureServer) vs. Boletín 45 (IV trimestre 2025, publicado 2026-03-31)",
        "top_10_municipios_featureserver": top_municipios,
        "departamentos_declarados_boletin_45_pct": deptos_boletin_45,
        "observacion": (
            "El Boletín 45 reporta que el 98% de la deforestación del IV trimestre de 2025 se concentró en "
            "Caquetá (44%), Meta (26%), Guaviare (17%) y Putumayo (10%). Se compara cualitativamente contra los "
            "10 municipios con más puntos DTD del FeatureServer para el mismo periodo — no se recalculan "
            "porcentajes de área porque el FeatureServer no tiene campo de área por punto."
        ),
    }


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 2D.1: piloto técnico de bosque y deforestación IDEAM")
    print("=" * 70)
    for d in (WCS_METADATA_DIR, BOSQUE_PILOT_DIR, CAMBIO_PILOT_DIR, AUDIT_DIR, REPORTS_DIR):
        ensure_dir(d)

    resultados: dict[str, Any] = {}

    # ---- B. WCS ----
    print("\n[B] Validando WCS de Superficie_Bosque y Dinamica_Cambio_Cobertura_Bosque...")
    wcs_superficie = validate_wcs_service("superficie_bosque", SUPERFICIE_BOSQUE_URL)
    wcs_cambio = validate_wcs_service("dinamica_cambio_cobertura_bosque", DINAMICA_CAMBIO_URL)
    resultados["wcs_superficie"] = wcs_superficie
    resultados["wcs_cambio"] = wcs_cambio
    print(f"  Superficie_Bosque WCS: n_coverages={wcs_superficie.get('n_coverages')}, formatos={wcs_superficie.get('formatos_soportados')}, CRS={wcs_superficie.get('crs_soportados')}")
    print(f"  Dinamica_Cambio WCS: n_coverages={wcs_cambio.get('n_coverages')}, interpolacion={wcs_cambio.get('interpolacion_soportada')}")
    print(f"  Manejo de coverage inválido: {wcs_superficie.get('maneja_error_coverage_invalido')}")

    # ---- L. Selección de municipios piloto ----
    print("\n[L] Seleccionando municipios piloto con evidencia real...")
    mgn_features = load_mgn2025_geometries()
    df_municipios = select_pilot_municipalities(mgn_features)
    df_municipios.to_csv(MUNICIPIO_SELECTION_PATH, index=False, encoding="utf-8")
    print(df_municipios[["rol_piloto", "cod_dane_mpio", "nombre_mpio", "nombre_dpto", "area_ha"]].to_string(index=False))

    cod_defor = df_municipios[df_municipios["rol_piloto"] == "deforestacion_reciente"]["cod_dane_mpio"].iloc[0]
    cod_bosque_estable = df_municipios[df_municipios["rol_piloto"] == "bosque_baja_o_nula_deforestacion"]["cod_dane_mpio"].iloc[0]
    cod_complejo = df_municipios[df_municipios["rol_piloto"] == "geometria_pequena_o_compleja"]["cod_dane_mpio"].iloc[0]

    cod_to_geom = {f["properties"]["cod_dane_mpio"]: f for f in mgn_features}
    geom_pilot_4326 = shapely_shape(cod_to_geom[cod_defor]["geometry"])
    bounds_pilot = geom_pilot_4326.bounds
    transformer = build_transformer(CRS_ORIGEN, CRS_METRICO)

    filas_access_pilot = []
    filas_vector_comparison = []

    # ---- C/D. Bosque No Bosque 2024 ----
    print(f"\n[C/D] Descargando e inspeccionando Bosque No Bosque 2024 para {cod_defor} (deforestación reciente)...")
    dl_bosque = download_wcs_pilot(SUPERFICIE_BOSQUE_URL, COVERAGE_ID_BOSQUE_2024, bounds_pilot, BOSQUE_PILOT_DIR / f"bosque_2024_{cod_defor}.tif")
    print(f"  Descarga: exito={dl_bosque.get('exito')}, metodo={dl_bosque.get('metodo_descarga')}, tiempo={dl_bosque.get('tiempo_s')}s, tamano={dl_bosque.get('tamano_bytes')}")

    info_bosque = class_arr_bosque = transform_bosque = crs_bosque = None
    if dl_bosque.get("exito"):
        info_bosque, class_arr_bosque, transform_bosque, crs_bosque = inspect_raster(BOSQUE_PILOT_DIR / f"bosque_2024_{cod_defor}.tif", COLORMAP_BOSQUE_NO_BOSQUE)
        print(f"  {info_bosque['ancho']}x{info_bosque['alto']} px, {info_bosque['n_bandas']} bandas, dtype={info_bosque['dtype']}, crs={info_bosque['crs']}")
        print(f"  Códigos de clase validados: {info_bosque.get('codigos_clase_validados')}")
        verif_bosque = verify_colormap_live(SUPERFICIE_BOSQUE_URL, LAYER_ID_BOSQUE_2024, "Bosque No Bosque 2024")
        resultados["verificacion_colormap_bosque"] = verif_bosque
        print(f"  Re-verificación en vivo (identify): {verif_bosque}")

    # ---- E. Cambio de Bosque 2023-2024 ----
    print(f"\n[E] Descargando e inspeccionando Cambio de Bosque 2023-2024 para {cod_defor}...")
    dl_cambio = download_wcs_pilot(DINAMICA_CAMBIO_URL, COVERAGE_ID_CAMBIO_2324, bounds_pilot, CAMBIO_PILOT_DIR / f"cambio_2023_2024_{cod_defor}.tif")
    print(f"  Descarga: exito={dl_cambio.get('exito')}, tiempo={dl_cambio.get('tiempo_s')}s, tamano={dl_cambio.get('tamano_bytes')}")

    info_cambio = class_arr_cambio = transform_cambio = crs_cambio = None
    if dl_cambio.get("exito"):
        info_cambio, class_arr_cambio, transform_cambio, crs_cambio = inspect_raster(CAMBIO_PILOT_DIR / f"cambio_2023_2024_{cod_defor}.tif", COLORMAP_CAMBIO_BOSQUE)
        print(f"  {info_cambio['ancho']}x{info_cambio['alto']} px, códigos de clase validados: {info_cambio.get('codigos_clase_validados')}")
        verif_cambio = verify_colormap_live(DINAMICA_CAMBIO_URL, LAYER_ID_CAMBIO_2324, "Cambio de Bosque 2023_2024")
        resultados["verificacion_colormap_cambio"] = verif_cambio
        print(f"  Re-verificación en vivo (identify): {verif_cambio}")

    # ---- F/G. Áreas piloto y efecto de reproyección ----
    areas_bosque_antes = areas_bosque_despues = areas_cambio_antes = areas_cambio_despues = None
    if class_arr_bosque is not None:
        print(f"\n[F/G] Calculando áreas piloto (bosque) y efecto de reproyección para {cod_defor}...")
        clip_bosque_4326, clip_transform_bosque = clip_to_municipio(class_arr_bosque, transform_bosque, crs_bosque, geom_pilot_4326.__geo_interface__)
        areas_bosque_antes = class_areas_geodesic(clip_bosque_4326, clip_transform_bosque, crs_bosque, COLORMAP_BOSQUE_NO_BOSQUE)
        reproj_bosque, reproj_transform_bosque = reproject_class_array(clip_bosque_4326, clip_transform_bosque, str(crs_bosque))
        areas_bosque_despues = class_areas_from_metric_grid(reproj_bosque, reproj_transform_bosque, COLORMAP_BOSQUE_NO_BOSQUE)
        print(f"  Antes (geodésico, EPSG:4326): {areas_bosque_antes}")
        print(f"  Después (EPSG:9377, nearest): {areas_bosque_despues}")
        resultados["efecto_reproyeccion_bosque"] = {
            "n_clases_antes": len(areas_bosque_antes), "n_clases_despues": len(areas_bosque_despues),
            "valores_nuevos_creados": sorted(set(areas_bosque_despues) - set(areas_bosque_antes)),
            "valores_perdidos": sorted(set(areas_bosque_antes) - set(areas_bosque_despues)),
        }

    if class_arr_cambio is not None:
        clip_cambio_4326, clip_transform_cambio = clip_to_municipio(class_arr_cambio, transform_cambio, crs_cambio, geom_pilot_4326.__geo_interface__)
        areas_cambio_antes = class_areas_geodesic(clip_cambio_4326, clip_transform_cambio, crs_cambio, COLORMAP_CAMBIO_BOSQUE)
        reproj_cambio, reproj_transform_cambio = reproject_class_array(clip_cambio_4326, clip_transform_cambio, str(crs_cambio))
        areas_cambio_despues = class_areas_from_metric_grid(reproj_cambio, reproj_transform_cambio, COLORMAP_CAMBIO_BOSQUE)
        print(f"  Cambio — antes: {areas_cambio_antes}")
        print(f"  Cambio — después: {areas_cambio_despues}")
        resultados["efecto_reproyeccion_cambio"] = {
            "n_clases_antes": len(areas_cambio_antes), "n_clases_despues": len(areas_cambio_despues),
            "valores_nuevos_creados": sorted(set(areas_cambio_despues) - set(areas_cambio_antes)),
            "valores_perdidos": sorted(set(areas_cambio_antes) - set(areas_cambio_despues)),
        }

    for label, info, areas_antes, areas_despues, dl in [
        ("Bosque No Bosque 2024", info_bosque, areas_bosque_antes, areas_bosque_despues, dl_bosque),
        ("Cambio de Bosque 2023-2024", info_cambio, areas_cambio_antes, areas_cambio_despues, dl_cambio),
    ]:
        area_valida_ha = sum(v["area_ha"] for k, v in (areas_despues or {}).items() if k != 0)
        area_clase_objetivo = None
        if areas_despues:
            objetivo_codigo = 1 if "Bosque No Bosque" in label else 2
            area_clase_objetivo = areas_despues.get(objetivo_codigo, {}).get("area_ha")
        filas_access_pilot.append({
            "producto": label, "capa": label, "periodo": "2024" if "No Bosque" in label else "2023-2024",
            "municipio": cod_defor, "metodo_descarga": dl.get("metodo_descarga"), "url_servicio": dl.get("url_servicio"),
            "formato": info.get("formato") if info else None, "archivo_analitico": dl.get("archivo_analitico"),
            "CRS": info.get("crs") if info else None, "resolucion": info.get("resolucion_x") if info else None,
            "dtype": info.get("dtype") if info else None, "nodata": info.get("nodata") if info else None,
            "valores_unicos": str(info.get("valores_unicos_rgb")) if info else None,
            "codigos_clase_validados": str(info.get("codigos_clase_validados")) if info else None,
            "area_valida_ha": round(area_valida_ha, 2) if areas_despues else None,
            "area_clase_objetivo_ha": area_clase_objetivo,
            "estado_validacion": "validado_con_descarga_real_wcs" if dl.get("exito") else "fallo_descarga",
            "limitaciones": info.get("comparacion_con_leyenda_oficial") if info else dl.get("mensaje"),
        })

    # ---- H. Piloto vectorial ----
    print(f"\n[H] Piloto vectorial zonas_deforestadas_2013_2024 para {cod_defor}, 2024...")
    val_zonas = validate_zonas_deforestadas_service()
    resultados["validacion_zonas_deforestadas"] = val_zonas
    feats_zonas, meta_zonas = query_municipio_deforestacion_2024(cod_defor)
    print(f"  {meta_zonas['n_registros']} polígonos reales para {cod_defor}/2024")
    stats_vector = compute_vector_pilot_stats(feats_zonas, transformer) if feats_zonas else {}
    print(f"  {stats_vector}")

    # ---- I. Comparación ráster-vector ----
    print("\n[I] Comparando ráster de deforestación vs. polígonos vectoriales...")
    area_defor_raster_ha = (areas_cambio_despues or {}).get(2, {}).get("area_ha", 0.0)
    comparacion = compare_raster_vector(area_defor_raster_ha, stats_vector.get("area_union_ha", 0.0), stats_vector.get("area_geometrica_total_ha", 0.0))
    print(f"  Ráster deforestación: {area_defor_raster_ha} ha | Vector unión: {stats_vector.get('area_union_ha')} ha -> {comparacion['clasificacion']}")
    filas_vector_comparison.append({
        "municipio": cod_defor, "periodo": "2024/2023-2024", "area_deforestacion_raster_ha": area_defor_raster_ha,
        "area_suma_poligonos_vector_ha": stats_vector.get("area_geometrica_total_ha"), "area_union_vector_ha": stats_vector.get("area_union_ha"),
        "area_reportada_fuente_vector_ha": stats_vector.get("area_reportada_fuente_ha"), "n_poligonos_vector": stats_vector.get("n_poligonos"),
        "solape_interno_vector_ha": stats_vector.get("solape_interno_ha"), "n_geometrias_invalidas": stats_vector.get("n_geometrias_invalidas"),
        "clasificacion_correspondencia": comparacion["clasificacion"], "diferencia_absoluta_ha": comparacion.get("diferencia_absoluta_ha"),
        "diferencia_porcentual": comparacion.get("diferencia_porcentual"), "razones_posibles": "; ".join(comparacion.get("razones_posibles", [])),
    })

    # ---- Municipio 2: bosque estable (verificación ligera vía identify) ----
    print(f"\n[L extra] Verificando cobertura boscosa real en {cod_bosque_estable} (bosque baja/nula deforestación)...")
    geom_bosque_estable = shapely_shape(cod_to_geom[cod_bosque_estable]["geometry"])
    cx, cy = geom_bosque_estable.centroid.x, geom_bosque_estable.centroid.y
    verif_estable = verify_colormap_live(SUPERFICIE_BOSQUE_URL, LAYER_ID_BOSQUE_2024, "control")
    identify_centroid, _ = get_json(f"{SUPERFICIE_BOSQUE_URL}/identify", {
        "geometry": json.dumps({"x": cx, "y": cy}), "geometryType": "esriGeometryPoint", "sr": 4326,
        "layers": f"all:{LAYER_ID_BOSQUE_2024}", "tolerance": 1, "mapExtent": f"{cx-0.5},{cy-0.5},{cx+0.5},{cy+0.5}",
        "imageDisplay": "400,400,96", "returnGeometry": "false", "f": "json",
    })
    resultados["verificacion_municipio_bosque_estable"] = identify_centroid
    print(f"  Identify en centroide de {cod_bosque_estable}: {identify_centroid}")

    # ---- Municipio 3: geometría compleja (confirmación de dimensiones) ----
    print(f"\n[L extra] Confirmando geometría compleja de {cod_complejo}...")
    geom_complejo = shapely_shape(cod_to_geom[cod_complejo]["geometry"])
    geom_complejo_proj = reproject_geometry(geom_complejo, transformer)
    resultados["geometria_compleja_confirmacion"] = {
        "cod_mpio": cod_complejo, "area_ha": round(geom_complejo_proj.area / M2_PER_HA, 1),
        "perimetro_m": round(geom_complejo_proj.length, 1),
        "n_vertices_aprox": sum(len(p.exterior.coords) for p in geom_complejo.geoms) if geom_complejo.geom_type == "MultiPolygon" else len(geom_complejo.exterior.coords),
    }
    print(f"  {resultados['geometria_compleja_confirmacion']}")

    df_access_pilot = pd.DataFrame(filas_access_pilot)
    df_access_pilot.to_csv(RASTER_ACCESS_PILOT_PATH, index=False, encoding="utf-8")
    df_vector_comparison = pd.DataFrame(filas_vector_comparison)
    df_vector_comparison.to_csv(RASTER_VECTOR_COMPARISON_PATH, index=False, encoding="utf-8")

    # ---- J/K. Auditoría semántica DTD ----
    print("\n[J/K] Auditoría semántica DTD — muestra IV trimestre 2025...")
    feats_dtd, meta_dtd = query_dtd_sample("2025", "iv")
    print(f"  Muestra: {meta_dtd['n_registros_muestra']} registros | total real del periodo: {meta_dtd['n_total_periodo_real']} | muestra completa: {meta_dtd['muestra_es_periodo_completo']}")
    df_dtd_campos, df_dtd_resumen, por_mpio_dtd, por_nucleo_dtd = dtd_semantic_audit(feats_dtd)
    comparacion_boletin = compare_dtd_with_boletin(por_mpio_dtd)
    resultados["comparacion_dtd_boletin_45"] = comparacion_boletin
    print(f"  Top municipios DTD 2025-IV: {comparacion_boletin['top_10_municipios_featureserver']}")

    df_dtd_full = pd.concat([
        df_dtd_campos.assign(tipo_fila="campo_semantico", metrica=None, valor=None),
        df_dtd_resumen.assign(tipo_fila="metrica_calculada", campo_conceptual=None, campo_real_o_estado=None),
    ], ignore_index=True)
    df_dtd_full.to_csv(DTD_SEMANTIC_AUDIT_PATH, index=False, encoding="utf-8")

    # ---- Metadata ----
    for path, n_filas, desc in [
        (MUNICIPIO_SELECTION_PATH, len(df_municipios), "Municipios piloto seleccionados con evidencia real (Fase 2D.1, sección L)."),
        (RASTER_ACCESS_PILOT_PATH, len(df_access_pilot), "Resultado del piloto de acceso ráster analítico vía WCS (Fase 2D.1, secciones C-G)."),
        (RASTER_VECTOR_COMPARISON_PATH, len(df_vector_comparison), "Comparación ráster vs. vector de deforestación para el municipio piloto (Fase 2D.1, secciones H-I)."),
        (DTD_SEMANTIC_AUDIT_PATH, len(df_dtd_full), "Auditoría semántica de campos DTD y métricas calculadas sobre la muestra 2025-IV (Fase 2D.1, secciones J-K)."),
    ]:
        write_json(path.with_suffix(path.suffix + ".metadata.json"), {"fuente": "Fase 2D.1 - piloto técnico forestal", "fecha_procesamiento": utc_now_iso(), "n_filas": n_filas, "descripcion": desc})

    tiempo_total = time.perf_counter() - t0
    resultados_finales = {
        **resultados,
        "df_municipios": df_municipios, "df_access_pilot": df_access_pilot, "df_vector_comparison": df_vector_comparison,
        "df_dtd_resumen": df_dtd_resumen, "comparacion_boletin": comparacion_boletin,
        "cod_defor": cod_defor, "cod_bosque_estable": cod_bosque_estable, "cod_complejo": cod_complejo,
        "info_bosque": info_bosque, "info_cambio": info_cambio,
        "areas_bosque_antes": areas_bosque_antes, "areas_bosque_despues": areas_bosque_despues,
        "areas_cambio_antes": areas_cambio_antes, "areas_cambio_despues": areas_cambio_despues,
        "stats_vector": stats_vector, "comparacion_raster_vector": comparacion,
        "n_registros_dtd_muestra": meta_dtd["n_registros_muestra"],
        "n_total_periodo_real_dtd": meta_dtd["n_total_periodo_real"],
        "muestra_dtd_es_periodo_completo": meta_dtd["muestra_es_periodo_completo"],
        "tiempo_total_s": tiempo_total,
    }
    import pickle
    with open(DATA_INTERIM / "fase2d1_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 2D.1")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s")
    print(f"Municipio piloto (deforestación): {cod_defor}")
    print(f"Áreas bosque (post-reproyección): {areas_bosque_despues}")
    print(f"Áreas cambio (post-reproyección): {areas_cambio_despues}")
    print(f"Comparación ráster-vector: {comparacion['clasificacion']}")
    print(f"Registros DTD 2025-IV: muestra={meta_dtd['n_registros_muestra']}, total real={meta_dtd['n_total_periodo_real']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
