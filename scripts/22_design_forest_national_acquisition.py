"""Fase 2D.3: diseño y validación de la arquitectura nacional reproducible
de adquisición forestal.

Define una grilla nacional fija (independiente de límites municipales),
valida la estabilidad de clases entre años y establece las llaves correctas
para los registros DTD. No descarga la serie nacional completa. No calcula
indicadores para las 1.122 unidades. No integra minería ni agua. No
construye índice de riesgo. No entrena modelos. No crea dashboard.
"""

from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
import requests
from shapely.geometry import shape as shapely_shape
from shapely.ops import unary_union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
for p in (SRC_DIR, SCRIPTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

mod20 = importlib.import_module("20_validate_forest_data_pilot")

from aquabosque.features.dtd import (  # noqa: E402
    add_registro_id, audit_duplicate_semantics, build_dtd_registro_id, summarize_dtd_metrics,
)
from aquabosque.forest.colormap import (  # noqa: E402
    CLASE_DESCONOCIDA, COLORMAP_BOSQUE_NO_BOSQUE, COLORMAP_CAMBIO_BOSQUE,
    decode_ideam_rgb_classes, hash_colormap,
)
from aquabosque.forest.grid import (  # noqa: E402
    Tile, build_national_grid_spec, generate_tile_index, mark_candidate_tiles, parse_wcs_describe_coverage,
)
from aquabosque.forest.tiles import audit_tile_boundary, download_tile_wcs, mosaic_2x2, read_tile_rgb  # noqa: E402
from aquabosque.utils.io import ensure_dir, utc_now_iso, write_json  # noqa: E402

DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REFERENCE_DIR = DATA_PROCESSED / "reference"
AUDIT_DIR = DATA_PROCESSED / "audit"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "forest_sources"
CONFIG_DIR = PROJECT_ROOT / "config"
FOREST_TILES_DIR = DATA_RAW / "forest_pilot" / "national_grid_pilot"
METADATA_WCS_DIR = DATA_RAW / "metadata" / "forest_sources" / "wcs"

GRID_DEFINITION_PATH = REFERENCE_DIR / "forest_wcs_grid_definition.csv"
NATIONAL_GRID_JSON_PATH = CONFIG_DIR / "forest_national_grid.json"
TILE_INDEX_PATH = REFERENCE_DIR / "forest_national_tile_index.csv"
TILE_BOUNDARY_AUDIT_PATH = AUDIT_DIR / "forest_tile_boundary_audit.csv"
MULTIYEAR_COLORMAP_AUDIT_PATH = AUDIT_DIR / "forest_multiyear_colormap_audit.csv"
LAYER_COLORMAPS_PATH = REFERENCE_DIR / "forest_layer_colormaps.csv"
TILE_MOSAIC_PILOT_PATH = AUDIT_DIR / "forest_tile_mosaic_pilot.csv"
DTD_DUPLICATE_SEMANTICS_PATH = AUDIT_DIR / "dtd_duplicate_semantics_audit.csv"
MANIFEST_SCHEMA_PATH = DATA_RAW / "forest" / "manifest.json"

TILE_SIZE_PX = 2048


def get_xml(url: str, params: dict) -> tuple[str | None, int | None]:
    return mod20.get_xml(url, params)


# ---------------------------------------------------------------------------
# B. Grilla original declarada
# ---------------------------------------------------------------------------


def find_layer_id_by_year(mapserver_rest_url: str, year_tokens: str) -> tuple[int, str]:
    """Busca una capa cuyo nombre contenga todos los años en `year_tokens`
    (separados por espacio, p. ej. "2012 2013"). El separador real entre
    años varía por capa en `Dinamica_Cambio_Cobertura_Bosque` (guion para
    periodos hasta 2017-2018, guion bajo desde 2018_2019 en adelante) — no
    se asume un separador fijo, se buscan los años como subcadenas
    independientes."""
    tokens = year_tokens.split()
    data, _ = mod20.get_json(mapserver_rest_url, {"f": "json"})
    for layer in data.get("layers", []):
        nombre = layer.get("name", "")
        if all(tok in nombre for tok in tokens):
            return layer["id"], nombre
    raise ValueError(f"No se encontró capa con años '{year_tokens}' en {mapserver_rest_url}")


# ---------------------------------------------------------------------------
# L. Estimación de descarga nacional
# ---------------------------------------------------------------------------


def estimate_national_download(spec, tiles_candidatos: list[Tile], tamano_medio_bytes: float, tamano_maximo_bytes: float, tiempo_medio_s: float) -> dict[str, Any]:
    n_tiles = len(tiles_candidatos)
    volumen_por_capa_bytes = n_tiles * tamano_medio_bytes
    anios_bosque_mvp = ["2013", "2018", "2020", "2022", "2024"]
    periodos_cambio_todos = 16  # confirmado real en Fase 2D/2D.1 (16 capas de cambio)

    alt1_n_capas = 17  # todos los cortes anuales de bosque (Fase 2D: 17 capas reales)
    alt2_n_capas = len(anios_bosque_mvp) + periodos_cambio_todos

    return {
        "n_tiles_candidatos_nacional": n_tiles,
        "tamano_medio_por_tile_bytes": round(tamano_medio_bytes, 0),
        "tamano_maximo_observado_bytes": round(tamano_maximo_bytes, 0),
        "volumen_por_capa_gb": round(volumen_por_capa_bytes / 1e9, 2),
        "n_peticiones_por_capa": n_tiles,
        "tiempo_estimado_por_capa_horas": round(n_tiles * tiempo_medio_s / 3600, 2),
        "alternativa_1_todos_los_cortes_bosque": {
            "n_capas": alt1_n_capas,
            "volumen_total_gb": round(alt1_n_capas * volumen_por_capa_bytes / 1e9, 2),
            "n_peticiones_total": alt1_n_capas * n_tiles,
            "tiempo_total_horas": round(alt1_n_capas * n_tiles * tiempo_medio_s / 3600, 2),
        },
        "alternativa_2_cortes_seleccionados_mas_cambios": {
            "n_capas": alt2_n_capas,
            "volumen_total_gb": round(alt2_n_capas * volumen_por_capa_bytes / 1e9, 2),
            "n_peticiones_total": alt2_n_capas * n_tiles,
            "tiempo_total_horas": round(alt2_n_capas * n_tiles * tiempo_medio_s / 3600, 2),
        },
        "recomendacion": (
            f"Alternativa 2 (cortes seleccionados de bosque {anios_bosque_mvp} + los {periodos_cambio_todos} "
            "cambios anuales completos): reduce el número de capas de bosque de 17 a 5 sin perder capacidad "
            "analítica de cambio (el producto de cambio ya captura la dinámica año a año; los cortes de bosque "
            "seleccionados bastan para verificar consistencia y para el estado remanente en años clave de "
            "política pública), reduciendo el volumen total frente a descargar las 17 capas de bosque completas."
        ),
    }


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 2D.3: diseño y validación de la arquitectura nacional de adquisición forestal")
    print("=" * 70)
    for d in (REFERENCE_DIR, AUDIT_DIR, REPORTS_DIR, CONFIG_DIR, FOREST_TILES_DIR, METADATA_WCS_DIR, MANIFEST_SCHEMA_PATH.parent):
        ensure_dir(d)

    resultados: dict[str, Any] = {}

    # -------------------------------------------------------------------
    # B. Grilla original declarada (DescribeCoverage real de ambos servicios)
    # -------------------------------------------------------------------
    print("\n[B] Extrayendo grilla original declarada (DescribeCoverage real)...")
    svc_bosque = mod20.SUPERFICIE_BOSQUE_URL.replace("/rest/services", "/services")
    svc_cambio = mod20.DINAMICA_CAMBIO_URL.replace("/rest/services", "/services")

    xml_bosque, _ = get_xml(f"{svc_bosque}/WCSServer", {"SERVICE": "WCS", "REQUEST": "DescribeCoverage", "VERSION": "2.0.1", "COVERAGEID": mod20.COVERAGE_ID_BOSQUE_2024})
    xml_cambio, _ = get_xml(f"{svc_cambio}/WCSServer", {"SERVICE": "WCS", "REQUEST": "DescribeCoverage", "VERSION": "2.0.1", "COVERAGEID": mod20.COVERAGE_ID_CAMBIO_2324})
    (METADATA_WCS_DIR / "superficie_bosque_describecoverage_grid.xml").write_text(xml_bosque or "", encoding="utf-8")
    (METADATA_WCS_DIR / "dinamica_cambio_describecoverage_grid.xml").write_text(xml_cambio or "", encoding="utf-8")

    grid_bosque = parse_wcs_describe_coverage(xml_bosque, mod20.COVERAGE_ID_BOSQUE_2024)
    grid_cambio = parse_wcs_describe_coverage(xml_cambio, mod20.COVERAGE_ID_CAMBIO_2324)
    grid_bosque["producto"] = "Superficie_Bosque"
    grid_cambio["producto"] = "Dinamica_Cambio_Cobertura_Bosque"
    grid_bosque["resolucion_descarga_piloto_x_grados"] = 0.00027335447197155777  # confirmado Fase 2D.1/2D.2 (Puerto Rico)
    grid_cambio["resolucion_descarga_piloto_x_grados"] = 0.0002733625916123628

    df_grid = pd.DataFrame([grid_bosque, grid_cambio])
    df_grid.to_csv(GRID_DEFINITION_PATH, index=False, encoding="utf-8")
    print(f"  {GRID_DEFINITION_PATH.name}: {len(df_grid)} filas")
    print(f"  Superficie_Bosque: extent=({grid_bosque['extent_xmin']},{grid_bosque['extent_ymin']},{grid_bosque['extent_xmax']},{grid_bosque['extent_ymax']}), grid={grid_bosque['ancho_original_px']}x{grid_bosque['alto_original_px']}")
    print(f"  Resolución declarada (grados): bosque={grid_bosque['resolucion_x_declarada_grados']}, cambio={grid_cambio['resolucion_x_declarada_grados']}")

    # -------------------------------------------------------------------
    # C. Grilla nacional canónica
    # -------------------------------------------------------------------
    print("\n[C] Construyendo especificación de grilla nacional canónica...")
    spec = build_national_grid_spec([grid_bosque, grid_cambio], tile_size_px=TILE_SIZE_PX)
    write_json(NATIONAL_GRID_JSON_PATH, spec.to_dict())
    print(f"  {NATIONAL_GRID_JSON_PATH}: {spec.ancho_total_px}x{spec.alto_total_px} px totales, {spec.n_filas_tiles}x{spec.n_columnas_tiles} tiles de {TILE_SIZE_PX}px")

    # -------------------------------------------------------------------
    # D. Esquema de teselas (independiente de municipios)
    # -------------------------------------------------------------------
    print("\n[D] Generando índice de teselas nacional (aritmética pura, sin depender de municipios)...")
    tiles = generate_tile_index(spec)
    mgn_features = mod20.load_mgn2025_geometries()
    geoms_4326 = [shapely_shape(f["geometry"]) for f in mgn_features]
    mgn_union = unary_union(geoms_4326)
    mark_candidate_tiles(tiles, mgn_union)
    n_candidatos = sum(1 for t in tiles if t.es_candidato_nacional)
    print(f"  {len(tiles)} tiles totales generados | {n_candidatos} candidatos (intersectan territorio nacional MGN2025)")

    df_tiles = pd.DataFrame([{
        "tile_id": t.tile_id, "fila": t.fila, "columna": t.columna, "xmin": t.xmin, "ymin": t.ymin,
        "xmax": t.xmax, "ymax": t.ymax, "width_px": t.width_px, "height_px": t.height_px,
        "es_candidato_nacional": t.es_candidato_nacional, "pct_area_colombia_aprox": t.pct_area_colombia_aprox,
        "estado_descarga": t.estado_descarga,
    } for t in tiles])
    df_tiles.to_csv(TILE_INDEX_PATH, index=False, encoding="utf-8")
    print(f"  {TILE_INDEX_PATH.name}: {len(df_tiles)} filas")

    # -------------------------------------------------------------------
    # G. Colormaps versionados (antes de E/F para tener el hash disponible)
    # -------------------------------------------------------------------
    hash_bosque = hash_colormap(COLORMAP_BOSQUE_NO_BOSQUE)
    hash_cambio = hash_colormap(COLORMAP_CAMBIO_BOSQUE)
    # Fecha real en que estos colores se confirmaron con `identify()` (Fase
    # 2D.1) — un valor fijo, no `utc_now_iso()`, para que este archivo de
    # referencia sea idempotente entre corridas (no se re-confirman por
    # identify() en cada ejecución de este script, son constantes ya
    # validadas).
    FECHA_CONFIRMACION_COLORMAP_BASE = "2026-07-12"
    filas_colormap = []
    for rgb, meta in COLORMAP_BOSQUE_NO_BOSQUE.items():
        filas_colormap.append({"producto": "Superficie_Bosque", "coverage_id": mod20.COVERAGE_ID_BOSQUE_2024, "layer_id": mod20.LAYER_ID_BOSQUE_2024, "periodo": "2024", "rgb_r": rgb[0], "rgb_g": rgb[1], "rgb_b": rgb[2], "codigo_clase": meta["codigo"], "nombre_clase": meta["clase"], "fuente_leyenda": "MapServer identify() + /legend", "fecha_consulta": FECHA_CONFIRMACION_COLORMAP_BASE, "hash_leyenda": hash_bosque, "validado_con_identify": True, "observaciones": "Confirmado Fase 2D.1"})
    for rgb, meta in COLORMAP_CAMBIO_BOSQUE.items():
        filas_colormap.append({"producto": "Dinamica_Cambio_Cobertura_Bosque", "coverage_id": mod20.COVERAGE_ID_CAMBIO_2324, "layer_id": mod20.LAYER_ID_CAMBIO_2324, "periodo": "2023-2024", "rgb_r": rgb[0], "rgb_g": rgb[1], "rgb_b": rgb[2], "codigo_clase": meta["codigo"], "nombre_clase": meta["clase"], "fuente_leyenda": "MapServer identify() + /legend", "fecha_consulta": FECHA_CONFIRMACION_COLORMAP_BASE, "hash_leyenda": hash_cambio, "validado_con_identify": True, "observaciones": "Confirmado Fase 2D.1/2D.2"})

    # -------------------------------------------------------------------
    # E. Continuidad entre tiles (2 tiles candidatos contiguos reales)
    # -------------------------------------------------------------------
    print("\n[E] Probando continuidad entre 2 tiles contiguos (descarga real)...")
    candidatos = [t for t in tiles if t.es_candidato_nacional]
    tile_a = None
    tile_b = None
    for t in candidatos:
        vecino = next((c for c in candidatos if c.fila == t.fila and c.columna == t.columna + 1), None)
        if vecino is not None:
            tile_a, tile_b = t, vecino
            break
    boundary_result = None
    if tile_a is not None:
        dl_a = download_tile_wcs(svc_bosque, mod20.COVERAGE_ID_BOSQUE_2024, tile_a, FOREST_TILES_DIR / f"{tile_a.tile_id}_bosque2024.tif")
        dl_b = download_tile_wcs(svc_bosque, mod20.COVERAGE_ID_BOSQUE_2024, tile_b, FOREST_TILES_DIR / f"{tile_b.tile_id}_bosque2024.tif")
        print(f"  Descarga {tile_a.tile_id}: exito={dl_a.get('exito')} | {tile_b.tile_id}: exito={dl_b.get('exito')}")
        if dl_a.get("exito") and dl_b.get("exito"):
            boundary_result = audit_tile_boundary(FOREST_TILES_DIR / f"{tile_a.tile_id}_bosque2024.tif", FOREST_TILES_DIR / f"{tile_b.tile_id}_bosque2024.tif", COLORMAP_BOSQUE_NO_BOSQUE, eje="columna")
            print(f"  Continuidad: {boundary_result}")
    df_boundary = pd.DataFrame([boundary_result]) if boundary_result else pd.DataFrame()
    df_boundary.to_csv(TILE_BOUNDARY_AUDIT_PATH, index=False, encoding="utf-8")

    # -------------------------------------------------------------------
    # N. Mosaico 2x2 (reusa tile_a/tile_b + sus vecinos de fila siguiente)
    # -------------------------------------------------------------------
    print("\n[N] Probando mosaico 2x2 de tiles contiguos...")
    mosaic_result = None
    if tile_a is not None:
        tile_c = next((c for c in candidatos if c.fila == tile_a.fila + 1 and c.columna == tile_a.columna), None)
        tile_d = next((c for c in candidatos if c.fila == tile_a.fila + 1 and c.columna == tile_b.columna), None)
        if tile_c is not None and tile_d is not None:
            dl_c = download_tile_wcs(svc_bosque, mod20.COVERAGE_ID_BOSQUE_2024, tile_c, FOREST_TILES_DIR / f"{tile_c.tile_id}_bosque2024.tif")
            dl_d = download_tile_wcs(svc_bosque, mod20.COVERAGE_ID_BOSQUE_2024, tile_d, FOREST_TILES_DIR / f"{tile_d.tile_id}_bosque2024.tif")
            if dl_c.get("exito") and dl_d.get("exito"):
                mosaic_result = mosaic_2x2({
                    (0, 0): FOREST_TILES_DIR / f"{tile_a.tile_id}_bosque2024.tif", (0, 1): FOREST_TILES_DIR / f"{tile_b.tile_id}_bosque2024.tif",
                    (1, 0): FOREST_TILES_DIR / f"{tile_c.tile_id}_bosque2024.tif", (1, 1): FOREST_TILES_DIR / f"{tile_d.tile_id}_bosque2024.tif",
                }, COLORMAP_BOSQUE_NO_BOSQUE)
                print(f"  Mosaico: dimensiones correctas={mosaic_result['dimensiones_correctas']}, áreas coinciden={mosaic_result['areas_coinciden']}")
    df_mosaic = pd.DataFrame([mosaic_result]) if mosaic_result else pd.DataFrame()
    df_mosaic.to_csv(TILE_MOSAIC_PILOT_PATH, index=False, encoding="utf-8")

    # -------------------------------------------------------------------
    # F. Prueba multitemporal (colormap por año/periodo, mismo tile piloto)
    # -------------------------------------------------------------------
    print("\n[F] Auditando colormap multitemporal (Bosque 2013/2018/2024, Cambio 2012-13/2017-18/2023-24)...")
    tile_multiyear = tile_a if tile_a is not None else (candidatos[0] if candidatos else None)
    filas_multiyear = []
    if tile_multiyear is not None:
        anios_bosque = ["2013", "2018", "2024"]
        for anio in anios_bosque:
            layer_id, layer_name = find_layer_id_by_year(mod20.SUPERFICIE_BOSQUE_URL, anio)
            coverage_id = f"Coverage{layer_id + 1}"
            legend_xml, _ = mod20.get_json(f"{mod20.SUPERFICIE_BOSQUE_URL}/legend", {"f": "json"})
            leyenda_labels = _legend_for_layer(legend_xml, layer_id)
            dest = FOREST_TILES_DIR / f"multiyear_bosque_{anio}.tif"
            dl = download_tile_wcs(svc_bosque, coverage_id, tile_multiyear, dest)
            fila = _audit_one_layer("Superficie_Bosque", coverage_id, layer_id, anio, dl, dest, COLORMAP_BOSQUE_NO_BOSQUE, leyenda_labels)
            filas_multiyear.append(fila)
            print(f"  Bosque {anio} (layer {layer_id}, {coverage_id}): {fila['estado']}")

        periodos_cambio = [("2012-2013", "2012 2013"), ("2017-2018", "2017 2018"), ("2023-2024", "2023 2024")]
        for periodo_label, periodo_tokens in periodos_cambio:
            layer_id, layer_name = find_layer_id_by_year(mod20.DINAMICA_CAMBIO_URL, periodo_tokens)
            coverage_id = f"Coverage{layer_id + 1}"
            legend_data, _ = mod20.get_json(f"{mod20.DINAMICA_CAMBIO_URL}/legend", {"f": "json"})
            leyenda_labels = _legend_for_layer(legend_data, layer_id)
            dest = FOREST_TILES_DIR / f"multiyear_cambio_{periodo_tokens.replace(' ', '_')}.tif"
            dl = download_tile_wcs(svc_cambio, coverage_id, tile_multiyear, dest)
            fila = _audit_one_layer("Dinamica_Cambio_Cobertura_Bosque", coverage_id, layer_id, periodo_label, dl, dest, COLORMAP_CAMBIO_BOSQUE, leyenda_labels)
            filas_multiyear.append(fila)
            print(f"  Cambio {periodo_label} (layer {layer_id}, {coverage_id}): {fila['estado']}")

    df_multiyear = pd.DataFrame(filas_multiyear)
    df_multiyear.to_csv(MULTIYEAR_COLORMAP_AUDIT_PATH, index=False, encoding="utf-8")

    # Añadir filas de colormap por año/periodo cuya decodificación con el
    # colormap base dejó píxeles sin decodificar (sección G): la etiqueta de
    # leyenda ("Bosque", "No Bosque"...) es idéntica entre años, así que un
    # hash del TEXTO de la leyenda nunca detecta el drift real de RGB — el
    # indicador correcto es `pct_clase_desconocida` calculado al decodificar
    # de verdad (sección F), no el hash de las etiquetas.
    for fila in filas_multiyear:
        if fila.get("pct_clase_desconocida") not in (None, 0.0):
            filas_colormap.append({
                "producto": fila["producto"], "coverage_id": fila["coverage_id"], "layer_id": fila["layer_id"], "periodo": fila["periodo"],
                "rgb_r": None, "rgb_g": None, "rgb_b": None, "codigo_clase": None, "nombre_clase": "colormap_base_no_coincide_ver_multiyear_audit",
                "fuente_leyenda": "/legend + decodificación real", "fecha_consulta": FECHA_CONFIRMACION_COLORMAP_BASE, "hash_leyenda": fila.get("hash_leyenda_actual"),
                "validado_con_identify": False,
                "observaciones": f"{fila['pct_clase_desconocida']}% de píxeles no coinciden con el RGB exacto del colormap base 2024 — requiere confirmar colormap propio de este año/periodo con identify() antes de decodificar en producción (ver forest_multiyear_colormap_audit.csv).",
            })
    df_colormaps = pd.DataFrame(filas_colormap)
    df_colormaps.to_csv(LAYER_COLORMAPS_PATH, index=False, encoding="utf-8")
    print(f"  {LAYER_COLORMAPS_PATH.name}: {len(df_colormaps)} filas")

    # -------------------------------------------------------------------
    # I/J. Identificador canónico DTD y semántica de duplicados
    # -------------------------------------------------------------------
    print("\n[I/J] Construyendo dtd_registro_id y auditando semántica de duplicados (histórico completo)...")
    mod21 = importlib.import_module("21_forest_dtd_and_colormap_robustness")
    df_dtd_all = mod21.fetch_all_dtd_attributes()
    df_dtd_all = add_registro_id(df_dtd_all)
    metricas = summarize_dtd_metrics(df_dtd_all)
    print(f"  Métricas (NUNCA equivalentes entre sí): {metricas}")
    df_dup = audit_duplicate_semantics(df_dtd_all)
    df_dup.to_csv(DTD_DUPLICATE_SEMANTICS_PATH, index=False, encoding="utf-8")
    print(f"  {DTD_DUPLICATE_SEMANTICS_PATH.name}: {len(df_dup)} filas")
    print("  Clasificación (por_cod_dtd):", df_dup[df_dup["tipo_analisis"] == "por_cod_dtd"]["clasificacion"].value_counts().to_dict())

    # K. Metodología de asignación territorial: se valida el MÉTODO sobre una
    # muestra pequeña (no se construye la tabla final de 1.122 unidades).
    print("\n[K] Validando la metodología de asignación territorial DTD sobre una muestra de 20 puntos...")
    from aquabosque.features.dtd import assign_dtd_points_to_mgn2025
    from aquabosque.geo.intersection import build_transformer as _build_transformer
    from aquabosque.geo.point_assignment import assign_point as _assign_point
    from aquabosque.geo.point_assignment import build_territorial_point_index as _build_index
    from aquabosque.utils.spatial_cache import load_cache_if_valid

    mgn_geoms_4326_shapely = [(f["properties"]["cod_dane_mpio"], shapely_shape(f["geometry"])) for f in mgn_features]
    with open(DATA_PROCESSED / "territorio" / "base_geometrica_divipola_mgn2025" / "manifest.json", encoding="utf-8") as fh:
        mgn_manifest = json.load(fh)
    mgn_source_paths = [DATA_PROCESSED / "territorio" / "base_geometrica_divipola_mgn2025" / a["archivo"] for a in mgn_manifest["archivos_y_tamanos"]]
    mgn_geoms_proj = load_cache_if_valid(DATA_INTERIM / "spatial_cache", cache_name="territorial_units_mgn2025_epsg9377", source_paths=mgn_source_paths, crs="EPSG:9377")
    transformer_k = _build_transformer("EPSG:4326", "EPSG:9377")
    territorial_index = _build_index(mgn_geoms_4326_shapely, mgn_geoms_proj, transformer_k)

    muestra_k = df_dtd_all.sample(n=min(20, len(df_dtd_all)), random_state=42)
    df_k_demo = assign_dtd_points_to_mgn2025(muestra_k, territorial_index, lambda x, y, idx: _assign_point(x, y, idx))
    n_coincide = int(df_k_demo["coincide_municipio_fuente_vs_espacial"].sum(skipna=True))
    print(f"  Muestra de {len(df_k_demo)} puntos asignados con covers() sobre MGN2025 | coinciden con cod_mpio de la fuente: {n_coincide}/{len(df_k_demo)}")
    resultados_k_demo = {"n_muestra": len(df_k_demo), "n_coincide_municipio_fuente": n_coincide, "metodo": "covers() sobre MGN2025, mismo patrón que Fase 4B; código de la fuente nunca sobrescribe la asignación espacial"}

    # -------------------------------------------------------------------
    # L. Estimación de descarga nacional
    # -------------------------------------------------------------------
    print("\n[L] Estimando volumen y costo de la adquisición nacional...")
    tamanos = [f.get("tamano_bytes") for f in [dl_a if tile_a else {}, dl_b if tile_a else {}] if f and f.get("tamano_bytes")]
    tamano_medio = float(np.mean(tamanos)) if tamanos else 20_000_000.0
    tamano_max = float(np.max(tamanos)) if tamanos else tamano_medio
    tiempos = [f.get("tiempo_s") for f in [dl_a if tile_a else {}, dl_b if tile_a else {}] if f and f.get("tiempo_s")]
    tiempo_medio = float(np.mean(tiempos)) if tiempos else 2.0
    estimacion = estimate_national_download(spec, candidatos, tamano_medio, tamano_max, tiempo_medio)
    print(f"  {estimacion}")

    # -------------------------------------------------------------------
    # M. Esquema del manifiesto de adquisición
    # -------------------------------------------------------------------
    print("\n[M] Escribiendo esquema del manifiesto de adquisición...")
    manifest_schema = {
        "version_esquema": "1.0", "fecha_diseno": utc_now_iso(),
        "descripcion": "Esquema (no poblado con datos reales) del manifiesto que registrará cada tile descargado en una futura fase de adquisición nacional.",
        "campos_por_tile": [
            "producto", "periodo", "coverage_id", "layer_id", "tile_id", "bounds", "width", "height",
            "resolucion", "crs", "url_o_parametros_wcs", "fecha_descarga", "http_status", "intentos",
            "tamano_bytes", "sha256", "hash_colormap", "colores_observados", "porcentaje_desconocido",
            "estado", "error", "version_script",
        ],
        "valores_estado_permitidos": ["pendiente", "descargado_valido", "descargado_invalido", "fallido", "omitido_ya_valido"],
        "politica_reanudacion": "Si un tile ya tiene estado='descargado_valido' y su SHA-256/hash_colormap coincide con la grilla y colormap vigentes, se omite. Si la grilla o el colormap cambian de hash, el tile se invalida y se vuelve a descargar.",
        "ejemplo_ilustrativo_no_real": {
            "producto": "Superficie_Bosque", "periodo": "2024", "coverage_id": "Coverage17", "layer_id": 16,
            "tile_id": "tile_r0000_c0000", "bounds": [-79.1, 12.0, -78.5, 12.5], "width": 2048, "height": 2048,
            "resolucion": 0.00027335447197155777, "crs": "EPSG:4326", "url_o_parametros_wcs": "(omitido en el ejemplo)",
            "fecha_descarga": None, "http_status": None, "intentos": 0, "tamano_bytes": None, "sha256": None,
            "hash_colormap": hash_bosque, "colores_observados": [], "porcentaje_desconocido": None,
            "estado": "pendiente", "error": None, "version_script": "scripts/22_design_forest_national_acquisition.py",
        },
        "tiles": [],
    }
    write_json(MANIFEST_SCHEMA_PATH, manifest_schema)
    print(f"  {MANIFEST_SCHEMA_PATH}: esquema escrito (0 tiles reales — no se descargó la serie nacional)")

    # -------------------------------------------------------------------
    # Metadata + pickle
    # -------------------------------------------------------------------
    for path, n_filas, desc in [
        (GRID_DEFINITION_PATH, len(df_grid), "Definición real de grilla WCS (DescribeCoverage) de los 2 servicios forestales, Fase 2D.3."),
        (TILE_INDEX_PATH, len(df_tiles), "Índice de teselas de la grilla nacional canónica, independiente de límites municipales, Fase 2D.3."),
        (TILE_BOUNDARY_AUDIT_PATH, len(df_boundary), "Auditoría de continuidad entre 2 tiles contiguos reales, Fase 2D.3."),
        (MULTIYEAR_COLORMAP_AUDIT_PATH, len(df_multiyear), "Auditoría de colormap en múltiples años/periodos sobre el mismo tile piloto, Fase 2D.3."),
        (LAYER_COLORMAPS_PATH, len(df_colormaps), "Colormaps versionados con hash de leyenda por producto/periodo, Fase 2D.3."),
        (TILE_MOSAIC_PILOT_PATH, len(df_mosaic), "Prueba de mosaico 2x2 de tiles contiguos, Fase 2D.3."),
        (DTD_DUPLICATE_SEMANTICS_PATH, len(df_dup), "Semántica de duplicados DTD sobre el histórico completo, Fase 2D.3."),
    ]:
        write_json(path.with_suffix(path.suffix + ".metadata.json"), {"fuente": "Fase 2D.3 - arquitectura nacional de adquisición forestal", "fecha_procesamiento": utc_now_iso(), "n_filas": n_filas, "descripcion": desc})

    tiempo_total = time.perf_counter() - t0
    resultados_finales = {
        "grid_bosque": grid_bosque, "grid_cambio": grid_cambio, "spec": spec.to_dict(),
        "n_tiles_total": len(tiles), "n_candidatos": n_candidatos, "boundary_result": boundary_result,
        "mosaic_result": mosaic_result, "df_multiyear": df_multiyear, "df_colormaps": df_colormaps,
        "metricas_dtd": metricas, "df_dup": df_dup, "estimacion": estimacion,
        "hash_bosque": hash_bosque, "hash_cambio": hash_cambio, "resultados_k_demo": resultados_k_demo,
        "tiempo_total_s": tiempo_total,
    }
    import pickle
    with open(DATA_INTERIM / "fase2d3_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 2D.3")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s")
    print(f"Grilla nacional: {spec.ancho_total_px}x{spec.alto_total_px} px, {len(tiles)} tiles ({n_candidatos} candidatos)")
    print(f"Continuidad entre tiles: {boundary_result.get('recomponible_deterministicamente') if boundary_result else 'no evaluado'}")
    print(f"Mosaico 2x2: {mosaic_result.get('areas_coinciden') if mosaic_result else 'no evaluado'}")
    print(f"Métricas DTD: {metricas}")

    return 0


def _legend_for_layer(legend_response: dict | None, layer_id: int) -> list[str]:
    """El endpoint `/legend` devuelve la leyenda de TODAS las capas del
    MapServer en una sola respuesta — se debe filtrar por `layerId`, nunca
    asumir que la primera entrada corresponde a la capa consultada."""
    if not legend_response:
        return []
    for layer in legend_response.get("layers", []):
        if layer.get("layerId") == layer_id:
            return [leg["label"] for leg in layer.get("legend", [])]
    return []


def _audit_one_layer(producto: str, coverage_id: str, layer_id: int, periodo: str, dl: dict, dest: Path, colormap: dict, leyenda_labels: list[str]) -> dict[str, Any]:
    if not dl.get("exito"):
        return {"producto": producto, "coverage_id": coverage_id, "layer_id": layer_id, "periodo": periodo, "estado": f"fallo_descarga_HTTP{dl.get('http_status')}", "hash_leyenda_actual": None}
    rgb, transform, crs = read_tile_rgb(dest)
    with rasterio.open(dest) as src:
        n_bandas = src.count
    decoded = decode_ideam_rgb_classes(rgb, colormap, tolerancia_pct=100.0, detener_si_excede=False)
    hash_leyenda_actual = "n/a_sin_leyenda" if not leyenda_labels else __import__("hashlib").sha256(repr(sorted(leyenda_labels)).encode()).hexdigest()[:16]
    return {
        "producto": producto, "coverage_id": coverage_id, "layer_id": layer_id, "periodo": periodo,
        "n_bandas": n_bandas, "leyenda_real": "; ".join(leyenda_labels), "hash_leyenda_actual": hash_leyenda_actual,
        "colores_rgb_observados": str(sorted({tuple(int(v) for v in row) for row in rgb.reshape(-1, 3)[::5000]})),
        "pct_clase_desconocida": decoded.pct_clase_desconocida, "rgb_desconocidos": str(decoded.rgb_desconocidos),
        "codigos_clase_presentes": str(decoded.codigos_clase_presentes),
        "clases_esperadas_ausentes": str(sorted(set(m["codigo"] for m in colormap.values()) - set(decoded.codigos_clase_presentes))),
        "estado": "ok_0_desconocido" if decoded.n_clase_desconocida == 0 else f"ADVERTENCIA_{decoded.pct_clase_desconocida}pct_desconocido",
    }


if __name__ == "__main__":
    raise SystemExit(main())
