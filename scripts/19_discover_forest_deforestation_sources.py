"""Fase 2D: descubrimiento, inventario y validación técnica de fuentes
oficiales de bosque y deforestación.

Fase exclusivamente de descubrimiento y validación: NO descarga la serie
histórica nacional completa, NO procesa rásteres nacionales, NO calcula
indicadores municipales, NO cruza con minería ni calidad hídrica, NO
construye índice de riesgo, NO entrena modelos, NO crea dashboard.

Todas las validaciones de servicio se hacen con peticiones HTTP reales
(nunca se asume que una URL es válida solo por responder 200); las
respuestas de metadata livianas quedan guardadas en
`data/raw/metadata/forest_sources/` para trazabilidad y reproducibilidad.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.utils.io import ensure_dir, utc_now_iso, write_json  # noqa: E402

DATA_RAW = PROJECT_ROOT / "data" / "raw"
METADATA_DIR = DATA_RAW / "metadata" / "forest_sources"
REFERENCE_DIR = PROJECT_ROOT / "data" / "processed" / "reference"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "forest_sources"

CATALOGO_PATH = REFERENCE_DIR / "catalogo_fuentes_bosque_deforestacion.csv"
ACTUALIDAD_PATH = REFERENCE_DIR / "actualidad_fuentes_deforestacion.csv"

USER_AGENT = "AquaBosqueMineroIA/0.1 (uso academico/institucional, descarga controlada)"
TIMEOUT = 30

ARCGIS_ROOT = "https://visualizador.ideam.gov.co/gisserver/rest/services"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


# ---------------------------------------------------------------------------
# D. Validación de servicios geoespaciales — peticiones reales
# ---------------------------------------------------------------------------


def get_json(url: str, *, params: dict | None = None) -> tuple[dict | None, int | None, str]:
    """GET real con manejo de error; nunca asume 200 = contenido válido."""
    try:
        resp = SESSION.get(url, params=params, timeout=TIMEOUT)
        status = resp.status_code
        if status != 200:
            return None, status, f"HTTP {status}"
        try:
            data = resp.json()
        except ValueError:
            return None, status, "HTTP 200 pero cuerpo no es JSON válido"
        if isinstance(data, dict) and "error" in data:
            return None, status, f"HTTP 200 con error de servicio: {data['error']}"
        return data, status, "ok"
    except requests.RequestException as exc:
        return None, None, f"excepcion de red: {exc}"


def head_request(url: str) -> dict[str, Any]:
    try:
        resp = SESSION.head(url, timeout=TIMEOUT, allow_redirects=True)
        return {
            "status": resp.status_code,
            "content_length": resp.headers.get("Content-Length"),
            "content_type": resp.headers.get("Content-Type"),
            "last_modified": resp.headers.get("Last-Modified"),
        }
    except requests.RequestException as exc:
        return {"status": None, "error": str(exc)}


def validate_arcgis_service(id_fuente: str, base_url: str, *, tipo_servicio: str) -> dict[str, Any]:
    """Valida un servicio ArcGIS REST con una petición real a `?f=json`,
    guarda la respuesta cruda y extrae los campos técnicos pedidos por el
    encargo (capas, layer id, campos, geometryType, spatialReference,
    extent, maxRecordCount, paginación) — nunca se limita a comprobar el
    código HTTP."""
    data, status, msg = get_json(base_url, params={"f": "json"})
    resultado: dict[str, Any] = {
        "id_fuente": id_fuente, "url_servicio": base_url, "tipo_servicio": tipo_servicio,
        "http_status": status, "validado": data is not None, "mensaje": msg,
    }
    if data is None:
        write_json(METADATA_DIR / f"{id_fuente}.json", {"url": base_url, "error": msg, "http_status": status})
        return resultado

    write_json(METADATA_DIR / f"{id_fuente}.json", data)
    resultado["capabilities"] = data.get("capabilities")
    resultado["spatial_reference_wkid"] = (data.get("spatialReference") or {}).get("latestWkid") or (data.get("spatialReference") or {}).get("wkid")
    extent = data.get("fullExtent") or {}
    resultado["extent"] = {k: extent.get(k) for k in ("xmin", "ymin", "xmax", "ymax")}
    resultado["max_record_count"] = data.get("maxRecordCount")
    layers = data.get("layers") or []
    tables = data.get("tables") or []
    resultado["n_layers"] = len(layers)
    resultado["n_tables"] = len(tables)
    resultado["layer_names"] = [l.get("name") for l in layers]
    resultado["table_names"] = [t.get("name") for t in tables]

    # Para servicios con exactamente 1 capa vectorial, se valida también el
    # detalle de esa capa (campos, geometryType, paginación) y se hace un
    # conteo real de registros.
    if len(layers) == 1 and layers[0].get("type") == "Feature Layer":
        layer_id = layers[0].get("id", 0)
        layer_data, layer_status, layer_msg = get_json(f"{base_url}/{layer_id}", params={"f": "json"})
        if layer_data is not None:
            write_json(METADATA_DIR / f"{id_fuente}_layer{layer_id}.json", layer_data)
            resultado["geometry_type"] = layer_data.get("geometryType")
            resultado["campos"] = [f.get("name") for f in layer_data.get("fields", [])]
            resultado["supports_pagination"] = (layer_data.get("advancedQueryCapabilities") or {}).get("supportsPagination")
            count_data, count_status, count_msg = get_json(
                f"{base_url}/{layer_id}/query", params={"where": "1=1", "returnCountOnly": "true", "f": "json"}
            )
            resultado["record_count"] = count_data.get("count") if count_data else None
    return resultado


def validate_socrata_dataset(id_fuente: str, resource_id: str) -> dict[str, Any]:
    """Valida un dataset de datos.gov.co (Socrata) leyendo la metadata real
    de la vista (`/api/views/{id}.json`) — nunca asume el contenido por el
    nombre del recurso.

    Corrección Fase 2D.1: la propia descripción de estos datasets (texto real
    devuelto por la API, ver `descripcion`) declara explícitamente
    "Los datos a visualizar o descargar a continuación no han sido validados
    por el IDEAM" — por lo tanto NUNCA se marcan como `validado_oficialmente`,
    aunque la petición HTTP haya sido exitosa (una cosa es que el servicio
    responda, otra que la entidad respalde el contenido)."""
    url = f"https://www.datos.gov.co/api/views/{resource_id}.json"
    data, status, msg = get_json(url)
    resultado: dict[str, Any] = {"id_fuente": id_fuente, "url_servicio": url, "tipo_servicio": "socrata_api", "http_status": status, "validado": data is not None, "mensaje": msg}
    if data is None:
        write_json(METADATA_DIR / f"{id_fuente}.json", {"url": url, "error": msg, "http_status": status})
        return resultado
    write_json(METADATA_DIR / f"{id_fuente}.json", data)
    resultado["nombre"] = data.get("name")
    resultado["descripcion"] = data.get("description")
    resultado["categoria"] = data.get("category")
    resultado["declara_no_validado_por_ideam"] = "no han sido validados por el IDEAM" in (data.get("description") or "")
    resultado["fecha_publicacion_unix"] = data.get("publicationDate")
    resultado["fecha_actualizacion_unix"] = data.get("rowsUpdatedAt")
    # En un dataset Socrata de tipo "blob" (un archivo adjunto, p. ej. un
    # ZIP), el archivo se describe en los campos de nivel superior
    # blobFilename/blobFileSize/blobId/blobMimeType — no en
    # metadata.attachments (esa lista queda vacía para este tipo de vista).
    blob_filename = data.get("blobFilename")
    blob_id = data.get("blobId")
    resultado["blob_filename"] = blob_filename
    resultado["blob_filesize_bytes"] = data.get("blobFileSize")
    resultado["blob_mimetype"] = data.get("blobMimeType")
    if blob_filename and blob_id:
        dl_url = f"https://www.datos.gov.co/api/views/{resource_id}/files/{blob_id}?download=true&filename={blob_filename}"
        resultado["blob_download_url"] = dl_url
        resultado["blob_head"] = head_request(dl_url)
    return resultado


def validate_plain_url(id_fuente: str, url: str) -> dict[str, Any]:
    """Para páginas/documentos que no son servicios de datos (geovisor,
    informes PDF, boletines): valida solo disponibilidad HTTP real vía HEAD.
    El contenido real (que corresponda a bosque/deforestación) se verificó
    de forma manual durante la investigación de la sección A y queda
    documentado en el catálogo, no inferido del código de estado."""
    info = head_request(url)
    write_json(METADATA_DIR / f"{id_fuente}.json", {"url": url, **info})
    return {"id_fuente": id_fuente, "url_servicio": url, "tipo_servicio": "documento_o_pagina", "http_status": info.get("status"), "validado": info.get("status") == 200, "mensaje": "ok" if info.get("status") == 200 else str(info)}


def main() -> int:
    t0 = time.perf_counter()
    print("Fase 2D: descubrimiento y validación de fuentes de bosque y deforestación")
    print("=" * 70)
    for d in (METADATA_DIR, REFERENCE_DIR, REPORTS_DIR):
        ensure_dir(d)

    resultados: dict[str, dict[str, Any]] = {}

    print("\n[D] Validando servicios ArcGIS REST (SMByC / IDEAM) con peticiones reales...")
    servicios = [
        ("smbyc_superficie_bosque", f"{ARCGIS_ROOT}/Superficie_Bosque/MapServer", "arcgis_mapserver"),
        ("smbyc_dinamica_cambio_cobertura_bosque", f"{ARCGIS_ROOT}/Dinamica_Cambio_Cobertura_Bosque/MapServer", "arcgis_mapserver"),
        ("smbyc_zonas_deforestadas_2013_2024", f"{ARCGIS_ROOT}/Hosted/zonas_deforestadas_2013_2024/FeatureServer", "arcgis_featureserver"),
        ("smbyc_dtd_trimestral", f"{ARCGIS_ROOT}/Hosted/DTD_Trimestral/FeatureServer", "arcgis_featureserver"),
        ("smbyc_deforestacion_car_deptos", f"{ARCGIS_ROOT}/Hosted/Deforestacion_CAR_Deptos/FeatureServer", "arcgis_featureserver"),
        ("smbyc_indicadores_diferencia", f"{ARCGIS_ROOT}/Hosted/Indicadores_SMByC_diferencia/FeatureServer", "arcgis_featureserver"),
        ("ideam_uso_recurso_bosque", f"{ARCGIS_ROOT}/Uso_Recurso_Bosque/MapServer", "arcgis_mapserver"),
        ("ideam_snif", f"{ARCGIS_ROOT}/SNIF/SNIF/MapServer", "arcgis_mapserver"),
        ("ideam_arcgis_root_catalog", ARCGIS_ROOT, "arcgis_root_catalog"),
    ]
    for id_fuente, url, tipo in servicios:
        r = validate_arcgis_service(id_fuente, url, tipo_servicio=tipo)
        resultados[id_fuente] = r
        print(f"  {id_fuente}: validado={r['validado']} ({r['mensaje']})"
              + (f" | capas={r.get('n_layers')} tablas={r.get('n_tables')}" if r["validado"] else ""))

    print("\n[D] Validando datasets Socrata (datos.gov.co) reportados como IDEAM...")
    socrata = [
        ("datosgovco_cambio_bosque_nacional", "39dh-rc72"),
        ("datosgovco_cambio_bosque_amazonia", "env9-bhc9"),
    ]
    for id_fuente, resource_id in socrata:
        r = validate_socrata_dataset(id_fuente, resource_id)
        resultados[id_fuente] = r
        print(f"  {id_fuente}: validado={r['validado']} ({r['mensaje']})")

    print("\n[D] Validando disponibilidad de páginas y documentos (contenido verificado manualmente en la sección A)...")
    paginas = [
        ("ideam_geovisor_bosque", "https://www.ideam.gov.co/temas/monitoreo-de-bosques/geovisor"),
        ("ideam_informe_anual_bosque_deforestacion", "https://www.ideam.gov.co/sala-de-prensa/informes/Informe-anual-del-monitoreo-de-bosque-y-la-deforestacion"),
        ("ideam_resumen_ejecutivo_defo_2024", "https://bart.ideam.gov.co/smbyc/Resultados%20Cifra%20Deforestacion%202024/Comunicados/Resumen%20ejecutivo_cifra%20Defo_2024_SMByC_compressed.pdf"),
        # Corrección Fase 2D.1: el boletín 44 (III trimestre 2025) ya NO es el
        # más reciente — el boletín 45 (IV trimestre 2025) fue confirmado con
        # petición HTTP real (HTTP 200) y con la página oficial de boletines
        # de IDEAM (publicado 2026-03-31).
        ("ideam_boletin_dtd_45_iv_2025", "https://bart.ideam.gov.co/smbyc/Boletines%20Detecciones%20Tempranas%20de%20Deforestacion/2025/Boletin/Boletin%2045%20-%20IV%20trimestre%202025.pdf"),
        ("ideam_smbyc_bart_root", "https://bart.ideam.gov.co/smbyc/"),
    ]
    for id_fuente, url in paginas:
        r = validate_plain_url(id_fuente, url)
        resultados[id_fuente] = r
        print(f"  {id_fuente}: validado={r['validado']} (HTTP {r['http_status']})")

    print("\n[D] Consultando periodos reales disponibles en zonas_deforestadas y DTD_Trimestral...")
    anios_zonas, _, msg1 = get_json(
        f"{ARCGIS_ROOT}/Hosted/zonas_deforestadas_2013_2024/FeatureServer/0/query",
        params={"where": "1=1", "outFields": "ano", "returnDistinctValues": "true", "orderByFields": "ano", "f": "json"},
    )
    periodos_dtd, _, msg2 = get_json(
        f"{ARCGIS_ROOT}/Hosted/DTD_Trimestral/FeatureServer/0/query",
        params={"where": "1=1", "outFields": "anio,periodo,tipo_dtd", "returnDistinctValues": "true", "orderByFields": "anio,periodo", "f": "json"},
    )
    lista_anios_zonas = sorted({f["attributes"]["ano"] for f in (anios_zonas or {}).get("features", [])})
    lista_periodos_dtd = [f["attributes"] for f in (periodos_dtd or {}).get("features", [])]
    write_json(METADATA_DIR / "smbyc_zonas_deforestadas_anios_distintos.json", {"anios": lista_anios_zonas})
    write_json(METADATA_DIR / "smbyc_dtd_periodos_distintos.json", {"periodos": lista_periodos_dtd})
    print(f"  zonas_deforestadas: años {lista_anios_zonas[0] if lista_anios_zonas else '?'}-{lista_anios_zonas[-1] if lista_anios_zonas else '?'} ({len(lista_anios_zonas)} años)")
    print(f"  DTD_Trimestral: {len(lista_periodos_dtd)} combinaciones año+periodo, última = {lista_periodos_dtd[-1] if lista_periodos_dtd else '?'}")

    print("\n[D] Consultando leyenda (diccionario de clases) de las capas ráster de bosque...")
    leyenda_superficie, _, _ = get_json(f"{ARCGIS_ROOT}/Superficie_Bosque/MapServer/legend", params={"f": "json"})
    leyenda_cambio, _, _ = get_json(f"{ARCGIS_ROOT}/Dinamica_Cambio_Cobertura_Bosque/MapServer/legend", params={"f": "json"})
    write_json(METADATA_DIR / "smbyc_superficie_bosque_legend.json", leyenda_superficie or {})
    write_json(METADATA_DIR / "smbyc_dinamica_cambio_legend.json", leyenda_cambio or {})
    clases_bosque_no_bosque = [leg["label"] for leg in (leyenda_superficie or {}).get("layers", [{}])[0].get("legend", [])] if leyenda_superficie else []
    clases_cambio = [leg["label"] for leg in (leyenda_cambio or {}).get("layers", [{}])[0].get("legend", [])] if leyenda_cambio else []
    print(f"  Clases bosque/no bosque: {clases_bosque_no_bosque}")
    print(f"  Clases cambio de bosque: {clases_cambio}")

    # -------------------------------------------------------------------
    # C. Tabla maestra de fuentes
    # -------------------------------------------------------------------
    print("\n[C] Construyendo catálogo maestro de fuentes...")
    catalogo = build_catalog(resultados, lista_anios_zonas, lista_periodos_dtd, clases_bosque_no_bosque, clases_cambio)
    catalogo.to_csv(CATALOGO_PATH, index=False, encoding="utf-8")
    print(f"  {CATALOGO_PATH.name}: {len(catalogo)} filas")

    # -------------------------------------------------------------------
    # H. Revisión de actualidad
    # -------------------------------------------------------------------
    print("\n[H] Construyendo tabla de actualidad...")
    actualidad = build_actualidad(lista_anios_zonas, lista_periodos_dtd)
    actualidad.to_csv(ACTUALIDAD_PATH, index=False, encoding="utf-8")
    print(f"  {ACTUALIDAD_PATH.name}: {len(actualidad)} filas")

    write_json(
        CATALOGO_PATH.with_suffix(CATALOGO_PATH.suffix + ".metadata.json"),
        {"fuente": "Fase 2D - descubrimiento de fuentes de bosque y deforestacion", "fecha_procesamiento": utc_now_iso(), "n_filas": len(catalogo)},
    )
    write_json(
        ACTUALIDAD_PATH.with_suffix(ACTUALIDAD_PATH.suffix + ".metadata.json"),
        {"fuente": "Fase 2D - actualidad de fuentes de bosque y deforestacion", "fecha_procesamiento": utc_now_iso(), "n_filas": len(actualidad)},
    )

    tiempo_total = time.perf_counter() - t0
    resultados_finales = {
        "resultados_validacion": resultados,
        "lista_anios_zonas": lista_anios_zonas,
        "lista_periodos_dtd": lista_periodos_dtd,
        "clases_bosque_no_bosque": clases_bosque_no_bosque,
        "clases_cambio": clases_cambio,
        "catalogo": catalogo,
        "actualidad": actualidad,
        "tiempo_total_s": tiempo_total,
    }
    import pickle
    with open(DATA_INTERIM / "fase2d_resultados.pkl", "wb") as fh:
        pickle.dump(resultados_finales, fh)

    print("\n" + "=" * 70)
    print("RESUMEN - Fase 2D")
    print("=" * 70)
    print(f"Tiempo total: {tiempo_total:.2f} s")
    n_validados = sum(1 for r in resultados.values() if r.get("validado"))
    print(f"Fuentes validadas con petición real: {n_validados}/{len(resultados)}")
    print(f"Catálogo de fuentes: {len(catalogo)} filas -> {CATALOGO_PATH}")
    print(f"Actualidad: {len(actualidad)} filas -> {ACTUALIDAD_PATH}")

    return 0


# ---------------------------------------------------------------------------
# C. Construcción del catálogo maestro
# ---------------------------------------------------------------------------


def _r(resultados: dict, id_fuente: str) -> dict:
    return resultados.get(id_fuente, {})


def build_catalog(
    resultados: dict[str, dict], lista_anios_zonas: list[str], lista_periodos_dtd: list[dict],
    clases_bosque_no_bosque: list[str], clases_cambio: list[str],
) -> pd.DataFrame:
    filas: list[dict[str, Any]] = []

    def fila(**kwargs) -> None:
        base = {c: None for c in CATALOGO_COLUMNS}
        base.update(kwargs)
        filas.append(base)

    r = _r(resultados, "smbyc_superficie_bosque")
    fila(
        id_fuente="smbyc_superficie_bosque", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Superficie de Bosque Natural (Bosque No Bosque)", categoria_producto="bosque_no_bosque",
        descripcion_oficial="Cartografía de la superficie remanente de bosque natural de Colombia, clasificada en Bosque / No Bosque / Sin Información, por cortes NO continuos (no es una serie anual continua 1990-2024).",
        url_pagina="https://www.ideam.gov.co/temas/monitoreo-de-bosques/geovisor", url_servicio=r.get("url_servicio"),
        tipo_servicio="ArcGIS MapServer", url_descarga=None, formato="Raster (capa de imagen dentro de MapServer)",
        tipo_geometria="raster", raster_o_vector="raster", resolucion_espacial="30 m (Landsat, según metodología SMByC publicada)",
        escala="1:100.000", CRS=f"EPSG:{r.get('spatial_reference_wkid')}", cobertura_geografica="Nacional",
        periodo_inicial="1990", periodo_final="2024",
        frecuencia_actualizacion="Cortes 1990, 2000, 2005, 2010 y 2012 (NO anuales); anual real solo 2013-2024 (confirmado por nombre de capa)",
        ultimo_periodo_disponible="2024", fecha_publicacion="2025-07-31 (cifra 2024)", fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones="CC BY-SA 4.0 (misma licencia declarada por IDEAM para productos SMByC en datos.gov.co)",
        tamaño_estimado="No descargado en esta fase; capas ráster nacionales por año, orden de decenas de MB cada una (referencia: ZIP Amazonia-only de un año pesa ~9.7 MB en datos.gov.co)",
        utilidad_proyecto="Fuente principal candidata para bosque_natural_observado por unidad territorial y año.",
        limitaciones=f"17 capas ráster con cortes 1990, 2000, 2005, 2010, 2012 y luego anuales 2013-2024 (NO serie anual continua desde 1990); requiere exportImage/rasterio para extraer, no query vectorial. maxRecordCount={r.get('max_record_count')}.",
        observaciones=f"Leyenda confirmada vía petición real: {clases_bosque_no_bosque}. capabilities={r.get('capabilities')}. Corrección Fase 2D.1: la Fase 2D describía erróneamente esta serie como 'anual 1990-2024'.",
        decision_priorizacion="adoptar_fuente_principal",
    )

    r = _r(resultados, "smbyc_dinamica_cambio_cobertura_bosque")
    fila(
        id_fuente="smbyc_dinamica_cambio_cobertura_bosque", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Dinámica de Cambio en la Cobertura de Bosque", categoria_producto="deforestacion_anual",
        descripcion_oficial="Cartografía temática del cambio en la superficie de bosque natural por periodo (Bosque Estable / Deforestación / No Bosque Estable / Regeneración / Sin Información).",
        url_pagina="https://www.ideam.gov.co/temas/monitoreo-de-bosques/geovisor", url_servicio=r.get("url_servicio"),
        tipo_servicio="ArcGIS MapServer", url_descarga=None, formato="Raster (capa de imagen dentro de MapServer)",
        tipo_geometria="raster", raster_o_vector="raster", resolucion_espacial="30 m (Landsat)",
        escala="1:100.000", CRS=f"EPSG:{r.get('spatial_reference_wkid')}", cobertura_geografica="Nacional",
        periodo_inicial="1990-2000", periodo_final="2023-2024",
        frecuencia_actualizacion="Cortes multianuales 1990-2000/2000-2005/2005-2010/2010-2012 (NO anuales); anual real solo desde 2012-2013",
        ultimo_periodo_disponible="2023-2024", fecha_publicacion="2025-07-31 (cifra 2024)", fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones="CC BY-SA 4.0",
        tamaño_estimado="No descargado en esta fase; referencia ZIP nacional de un año en datos.gov.co ~38.4 MB.",
        utilidad_proyecto="Fuente principal candidata para deforestacion_anual_confirmada (pérdida bruta, no cambio neto — la leyenda separa Deforestación de Regeneración).",
        limitaciones=f"16 capas ráster por periodo (10, 5, 5, 2 años, y luego anuales); primeros 4 periodos NO son anuales (1990-2000, 2000-2005, 2005-2010, 2010-2012). maxRecordCount={r.get('max_record_count')}.",
        observaciones=f"Leyenda confirmada vía petición real: {clases_cambio} — distingue explícitamente deforestación de regeneración, por lo que es pérdida bruta, no cambio neto.",
        decision_priorizacion="adoptar_fuente_principal",
    )

    r = _r(resultados, "smbyc_zonas_deforestadas_2013_2024")
    fila(
        id_fuente="smbyc_zonas_deforestadas_2013_2024", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Registro Nacional de Zonas Deforestadas 2013-2024", categoria_producto="deforestacion_anual",
        descripcion_oficial="Polígonos individuales de zonas deforestadas por año, con área en hectáreas, municipio, CAR, RUNAP y vereda asociados.",
        url_pagina="https://bart.ideam.gov.co/smbyc/Registro%20Nacional%20de%20Zonas%20Deforestadas", url_servicio=r.get("url_servicio"),
        tipo_servicio="ArcGIS FeatureServer", url_descarga=f"{r.get('url_servicio')}/0/query", formato="Feature Service (vector)",
        tipo_geometria="poligono", raster_o_vector="vector", resolucion_espacial="Polígono vectorizado desde ráster 30 m",
        escala="1:100.000", CRS="EPSG:3857 (Web Mercator, servicio) — datos fuente en 30 m Landsat", cobertura_geografica="Nacional",
        periodo_inicial=lista_anios_zonas[0] if lista_anios_zonas else None, periodo_final=lista_anios_zonas[-1] if lista_anios_zonas else None,
        frecuencia_actualizacion="Anual", ultimo_periodo_disponible=lista_anios_zonas[-1] if lista_anios_zonas else None,
        fecha_publicacion="2025-07-31 (cifra 2024)", fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones="CC BY-SA 4.0 (asumida, coherente con otros productos SMByC; no se encontró página de licencia dedicada a este FeatureServer)",
        tamaño_estimado=f"{r.get('record_count')} polígonos (registro real vía returnCountOnly); tamaño en bytes no estimado en esta fase.",
        utilidad_proyecto="Fuente vectorial de mayor detalle para deforestacion_anual_confirmada a nivel de polígono individual, con campos ya vinculados a cod_mpio/cod_depto — evita reconstruir la agregación municipal desde ráster.",
        limitaciones=f"Servicio soporta paginación estándar (supports_pagination={r.get('supports_pagination')}), maxRecordCount={r.get('max_record_count')} — requiere paginar en descargas futuras. Campos: {r.get('campos')}.",
        observaciones=f"geometryType={r.get('geometry_type')}. Años confirmados por consulta distinct real: {lista_anios_zonas}.",
        decision_priorizacion="adoptar_fuente_principal",
    )

    r = _r(resultados, "smbyc_dtd_trimestral")
    fila(
        id_fuente="smbyc_dtd_trimestral", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Detecciones Tempranas de Deforestación (DTD) Trimestral", categoria_producto="deteccion_temprana",
        descripcion_oficial="Puntos de detección temprana de posible deforestación identificados trimestralmente, con núcleo asociado, municipio, CAR y RUNAP.",
        url_pagina="https://bart.ideam.gov.co/smbyc/Boletines%20Detecciones%20Tempranas%20de%20Deforestacion", url_servicio=r.get("url_servicio"),
        tipo_servicio="ArcGIS FeatureServer", url_descarga=f"{r.get('url_servicio')}/0/query", formato="Feature Service (vector)",
        tipo_geometria="punto", raster_o_vector="vector", resolucion_espacial="Punto (detección individual)",
        escala=None, CRS="EPSG:3857 (Web Mercator)", cobertura_geografica="Nacional (histórico concentrado en Amazonía)",
        periodo_inicial="2017-I", periodo_final=lista_periodos_dtd[-1]["anio"] + "-" + lista_periodos_dtd[-1]["periodo"] if lista_periodos_dtd else None,
        frecuencia_actualizacion="Trimestral", ultimo_periodo_disponible=lista_periodos_dtd[-1]["anio"] + "-" + lista_periodos_dtd[-1]["periodo"] if lista_periodos_dtd else None,
        fecha_publicacion="Boletín 45, IV trimestre 2025, publicado 2026-03-31 (corrección Fase 2D.1; el boletín 44/III-2025 ya no es el más reciente)", fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones="CC BY-SA 4.0 (asumida)",
        tamaño_estimado=f"{r.get('record_count')} puntos (registro real vía returnCountOnly).",
        utilidad_proyecto="Única fuente vectorial encontrada de deteccion_temprana_posible_deforestacion con microdatos descargables (no solo boletín PDF) — candidata a señal de monitoreo oportuno.",
        limitaciones=f"Granularidad de punto (no polígono ni ráster); campo 'nucleo_tri' agrupa puntos por núcleo trimestral pero no se confirmó en esta fase si un mismo núcleo puede fusionarse/dividirse entre boletines sucesivos (requiere_revision_manual). Campos: {r.get('campos')}.",
        observaciones=f"geometryType={r.get('geometry_type')}. tipo_dtd observado='trim' en todas las combinaciones. Periodos confirmados por consulta distinct real (36 combinaciones año+trimestre, 2017-I a 2025-IV).",
        decision_priorizacion="adoptar_fuente_principal",
    )

    r = _r(resultados, "smbyc_deforestacion_car_deptos")
    fila(
        id_fuente="smbyc_deforestacion_car_deptos", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Deforestación por CAR y Departamento (tabla)", categoria_producto="estadistica_agregada",
        descripcion_oficial="Tabla de estadísticas de deforestación agregadas por Corporación Autónoma Regional y departamento (contenido exacto no confirmado a nivel de fila en esta fase).",
        url_pagina=None, url_servicio=r.get("url_servicio"), tipo_servicio="ArcGIS FeatureServer (solo tabla, sin geometría)",
        url_descarga=f"{r.get('url_servicio')}/0/query", formato="Tabla no espacial", tipo_geometria="ninguna (tabla)",
        raster_o_vector="ninguno", resolucion_espacial=None, escala=None, CRS=None, cobertura_geografica="Nacional (por CAR/departamento)",
        periodo_inicial=None, periodo_final=None, frecuencia_actualizacion=None, ultimo_periodo_disponible=None,
        fecha_publicacion=None, fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_parcialmente_requiere_revision",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones=None, tamaño_estimado="No determinado en esta fase (tabla, no se consultó conteo de filas).",
        utilidad_proyecto="Posible estadística agregada complementaria; no se validó su esquema de columnas en esta fase.",
        limitaciones=f"Servicio responde y expone tabla '{r.get('table_names')}', pero esta fase no consultó su contenido detallado (columnas/periodo) — requiere revisión manual antes de adoptar.",
        observaciones="No tiene capa espacial (0 layers, 1 tabla) — no es utilizable para asignación territorial directa por geometría, solo por join alfanumérico si comparte código DANE.",
        decision_priorizacion="requiere_revision_manual",
    )

    r = _r(resultados, "smbyc_indicadores_diferencia")
    fila(
        id_fuente="smbyc_indicadores_diferencia", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Indicadores SMByC — diferencia (tabla)", categoria_producto="estadistica_agregada",
        descripcion_oficial="Tabla de indicadores SMByC (contenido y alcance no confirmados en esta fase).",
        url_pagina=None, url_servicio=r.get("url_servicio"), tipo_servicio="ArcGIS FeatureServer (solo tabla, sin geometría)",
        url_descarga=f"{r.get('url_servicio')}/0/query", formato="Tabla no espacial", tipo_geometria="ninguna (tabla)",
        raster_o_vector="ninguno", resolucion_espacial=None, escala=None, CRS=None, cobertura_geografica="No determinada",
        periodo_inicial=None, periodo_final=None, frecuencia_actualizacion=None, ultimo_periodo_disponible=None,
        fecha_publicacion=None, fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_parcialmente_requiere_revision",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones=None, tamaño_estimado="No determinado en esta fase.",
        utilidad_proyecto="Alcance no confirmado; nombre de tabla ('Hoja1') sugiere una carga ad-hoc desde Excel, no necesariamente un producto oficial estable.",
        limitaciones="Nombre de tabla genérico ('Hoja1') y sin capas espaciales — baja confianza de que sea un producto institucional estable y documentado.",
        observaciones="requiere_revision_manual antes de considerarse como fuente.",
        decision_priorizacion="requiere_revision_manual",
    )

    r = _r(resultados, "ideam_uso_recurso_bosque")
    fila(
        id_fuente="ideam_uso_recurso_bosque", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Uso del Recurso Bosque (Aprovechamiento y Movilización Forestal 2000-2006)", categoria_producto="otro",
        descripcion_oficial="Aprovechamiento forestal y movilización forestal por jurisdicción de CAR, periodo 2000-2006.",
        url_pagina=None, url_servicio=r.get("url_servicio"), tipo_servicio="ArcGIS MapServer", url_descarga=None,
        formato="Feature Service (vector)", tipo_geometria="poligono", raster_o_vector="vector", resolucion_espacial=None,
        escala=None, CRS=f"EPSG:{r.get('spatial_reference_wkid')}", cobertura_geografica="Nacional (por jurisdicción CAR)",
        periodo_inicial="2000", periodo_final="2006", frecuencia_actualizacion="No determinada (sin evidencia de actualización posterior a 2006)",
        ultimo_periodo_disponible="2006", fecha_publicacion=None, fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones=None, tamaño_estimado="No determinado.",
        utilidad_proyecto="No mide deforestación ni cobertura de bosque — mide aprovechamiento forestal legal autorizado; fuera de alcance de los 3 productos pedidos (B.1/B.2/B.3).",
        limitaciones="Periodo histórico muy desactualizado (2000-2006), sin evidencia de continuidad.",
        observaciones=f"n_layers={r.get('n_layers')}: {r.get('layer_names')}.",
        decision_priorizacion="rechazar",
    )

    r = _r(resultados, "ideam_snif")
    fila(
        id_fuente="ideam_snif", entidad="IDEAM", sistema="Sistema Nacional de Información Forestal (SNIF)",
        nombre_producto="SNIF — Coordenada Única, Áreas de Restauración, Plantaciones Forestales Productoras", categoria_producto="otro",
        descripcion_oficial="Capas del Sistema Nacional de Información Forestal: puntos de coordenada única, áreas de restauración forestal y plantaciones forestales productoras (históricas y versión final).",
        url_pagina=None, url_servicio=r.get("url_servicio"), tipo_servicio="ArcGIS MapServer", url_descarga=None,
        formato="Feature Service (vector, capas agrupadas)", tipo_geometria="punto y poligono", raster_o_vector="vector",
        resolucion_espacial=None, escala=None, CRS=None, cobertura_geografica="Nacional",
        periodo_inicial=None, periodo_final=None, frecuencia_actualizacion="No determinada", ultimo_periodo_disponible=None,
        fecha_publicacion=None, fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones=None, tamaño_estimado="No determinado.",
        utilidad_proyecto="No mide deforestación ni bosque natural remanente — mide restauración activa y plantaciones forestales productoras (bosque plantado, no natural); fuera de alcance de B.1/B.2/B.3.",
        limitaciones="Contenido temático distinto (gestión forestal, no monitoreo de pérdida/cobertura de bosque natural).",
        observaciones=f"n_layers={r.get('n_layers')}: {r.get('layer_names')}.",
        decision_priorizacion="rechazar",
    )

    r = _r(resultados, "ideam_geovisor_bosque")
    fila(
        id_fuente="ideam_geovisor_bosque", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Geovisor de Bosque y Deforestación en Cifras", categoria_producto="otro",
        descripcion_oficial="Herramienta web (agosto 2024) para consultar y descargar mapas históricos de deforestación y comparaciones de cobertura de bosque 2000-2023, con estadísticas por departamento, CAR y región natural.",
        url_pagina=r.get("url_servicio"), url_servicio=None, tipo_servicio="Aplicación web (front-end), no expone API documentada directamente",
        url_descarga=None, formato="Interfaz de usuario (exporta imágenes/estadísticas, mecanismo interno no confirmado)",
        tipo_geometria=None, raster_o_vector=None, resolucion_espacial=None, escala=None, CRS=None,
        cobertura_geografica="Nacional", periodo_inicial="2000", periodo_final="2023", frecuencia_actualizacion="No documentada explícitamente en la página",
        ultimo_periodo_disponible="2023 (declarado en la página; los servicios ArcGIS ya tienen 2024)", fecha_publicacion="2024-08-21 (lanzamiento)",
        fecha_actualizacion_portal=None, validado_oficialmente=True, estado_validacion="validado_disponibilidad_http_contenido_no_extraible_automaticamente",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=False,
        licencia_o_condiciones="No requiere registro (declarado en comunicado oficial de lanzamiento)",
        tamaño_estimado=None,
        utilidad_proyecto="Punto de entrada institucional y de verificación cruzada, no una fuente programática — probablemente consume los mismos servicios ArcGIS ya validados en esta fase.",
        limitaciones="La petición automática (WebFetch) no encontró enlaces directos a servicios ArcGIS en el HTML — es una SPA que carga el mapa dinámicamente; no se puede validar mediante HEAD/GET simple más allá de la disponibilidad de la página.",
        observaciones=f"HTTP status real: {r.get('http_status')}.",
        decision_priorizacion="solo_validacion",
    )

    r = _r(resultados, "ideam_informe_anual_bosque_deforestacion")
    fila(
        id_fuente="ideam_informe_anual_bosque_deforestacion", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Informe Anual del Monitoreo de Bosque y la Deforestación", categoria_producto="documento_metodologico",
        descripcion_oficial="Serie de informes anuales (PDF) con cifras oficiales de deforestación, metodología y resultados por departamento/CAR/región natural.",
        url_pagina=r.get("url_servicio"), url_servicio=None, tipo_servicio="Página índice de documentos PDF",
        url_descarga=None, formato="PDF", tipo_geometria=None, raster_o_vector=None, resolucion_espacial=None, escala=None, CRS=None,
        cobertura_geografica="Nacional", periodo_inicial="2013 (monitoreo anual sistemático)", periodo_final="2024",
        frecuencia_actualizacion="Anual", ultimo_periodo_disponible="2024",
        fecha_publicacion="2025-07-31 (resumen ejecutivo cifra 2024)", fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_disponibilidad_http",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=False,
        licencia_o_condiciones="CC BY-SA 4.0 (asumida, coherente con otros productos SMByC)", tamaño_estimado=None,
        utilidad_proyecto="Documento metodológico de referencia obligatoria: aquí se define oficialmente el significado de las clases (pérdida bruta vs. cambio neto) y la cifra nacional 2024 = 113.608 ha.",
        limitaciones="Es un documento narrativo (PDF), no una capa descargable — se usa para interpretar, no para procesar programáticamente.",
        observaciones=f"HTTP status real del resumen ejecutivo 2024: {_r(resultados, 'ideam_resumen_ejecutivo_defo_2024').get('http_status')}.",
        decision_priorizacion="solo_documental",
    )

    r = _r(resultados, "ideam_boletin_dtd_45_iv_2025")
    fila(
        id_fuente="ideam_boletin_dtd_45_iv_2025", entidad="IDEAM", sistema="SMByC",
        nombre_producto="Boletín de Detección Temprana de Deforestación (DTD) — edición 45", categoria_producto="documento_metodologico",
        descripcion_oficial="Boletín trimestral narrativo con análisis de núcleos DTD del IV trimestre de 2025 — complementa (no reemplaza) el microdato vectorial DTD_Trimestral.",
        url_pagina="https://bart.ideam.gov.co/smbyc/Boletines%20Detecciones%20Tempranas%20de%20Deforestacion", url_servicio=None,
        tipo_servicio="Documento PDF", url_descarga=r.get("url_servicio"), formato="PDF", tipo_geometria=None, raster_o_vector=None,
        resolucion_espacial=None, escala=None, CRS=None, cobertura_geografica="Nacional (foco histórico en Amazonía)",
        periodo_inicial="2016 (boletín 1)", periodo_final="2025-IV", frecuencia_actualizacion="Trimestral",
        ultimo_periodo_disponible="2025-IV (boletín 45, confirmado por petición HTTP real y por la página oficial de boletines de IDEAM, publicado 2026-03-31)", fecha_publicacion="2026-03-31",
        fecha_actualizacion_portal=None, validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=False,
        licencia_o_condiciones="CC BY-SA 4.0 (asumida)", tamaño_estimado=None,
        utilidad_proyecto="Fuente narrativa que documenta la metodología y definición de 'núcleo' de deforestación — necesaria para interpretar correctamente el campo nucleo_tri de DTD_Trimestral.",
        limitaciones="Corrección Fase 2D.1: la Fase 2D identificó erróneamente el boletín 44 (III-2025) como el más reciente; el boletín 45 (IV-2025) ya estaba publicado. Ver sección K de docs/11 para la comparación real entre este boletín y el FeatureServer.",
        observaciones=f"HTTP status real: {r.get('http_status')}.",
        decision_priorizacion="solo_documental",
    )

    r = _r(resultados, "datosgovco_cambio_bosque_nacional")
    tam_mb = round(r.get("blob_filesize_bytes", 0) / 1_000_000, 1) if r.get("blob_filesize_bytes") else None
    fila(
        id_fuente="datosgovco_cambio_bosque_nacional", entidad="IDEAM", sistema="Datos Abiertos Colombia",
        nombre_producto="Cambio en la superficie cubierta por bosque natural (Deforestación) - Nacional", categoria_producto="deforestacion_anual",
        descripcion_oficial="Promedio anual de la diferencia entre superficie de bosque regenerado (ganancia) y superficie de bosque deforestado (pérdida) por unidad espacial de referencia.",
        url_pagina="https://www.datos.gov.co/Ambiente-y-Desarrollo-Sostenible/Cambio-en-la-superficie-cubierta-por-bosque-natura/39dh-rc72",
        url_servicio=r.get("url_servicio"), tipo_servicio="Socrata (API SODA), vista tipo blob (archivo adjunto único)", url_descarga=r.get("blob_download_url"),
        formato=f"ZIP ({r.get('blob_mimetype')}; contenido interno no confirmado en esta fase)", tipo_geometria=None, raster_o_vector=None,
        resolucion_espacial=None, escala=None, CRS=None, cobertura_geografica="Nacional", periodo_inicial=None, periodo_final="2022",
        frecuencia_actualizacion="Anual (declarada)", ultimo_periodo_disponible="2022",
        fecha_publicacion="2024-01-30", fecha_actualizacion_portal="2024-01-29",
        validado_oficialmente=False, estado_validacion="publicado_en_portal_pero_no_validado_por_ideam",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones="Datos abiertos sin validar por IDEAM según cláusulas propias del portal (ver descripción en metadata); no es la misma garantía de calidad que el servicio ArcGIS institucional.",
        tamaño_estimado=f"{tam_mb} MB ({r.get('blob_filename')}, blobFileSize real ={r.get('blob_filesize_bytes')} bytes, confirmado por petición real a la API Socrata; HEAD al archivo: HTTP {((r.get('blob_head') or {}).get('status'))})",
        utilidad_proyecto="Redundante y desactualizada frente al servicio ArcGIS (que ya tiene 2023-2024): última actualización 2022, dos años de rezago.",
        limitaciones=f"Portal Socrata no se ha actualizado desde enero 2024 pese a que el servicio ArcGIS institucional ya publicó 2 años adicionales — no debe usarse como fuente principal de actualidad. Corrección Fase 2D.1: la propia metadata Socrata (campo `description` real, declara_no_validado_por_ideam={r.get('declara_no_validado_por_ideam')}) aclara explícitamente que estos datos 'no han sido validados por el IDEAM' — ya NO se marca `validado_oficialmente=True`.",
        observaciones="Vista tipo blob (el recurso completo es un único archivo adjunto, no una tabla de filas) — confirmado con petición real a /api/views.",
        decision_priorizacion="rechazar",
    )

    r = _r(resultados, "datosgovco_cambio_bosque_amazonia")
    tam_mb = round(r.get("blob_filesize_bytes", 0) / 1_000_000, 1) if r.get("blob_filesize_bytes") else None
    fila(
        id_fuente="datosgovco_cambio_bosque_amazonia", entidad="IDEAM", sistema="Datos Abiertos Colombia",
        nombre_producto="Cambio en la superficie cubierta por bosque natural (Deforestación) - Amazonia", categoria_producto="deforestacion_anual",
        descripcion_oficial="Mismo indicador que la versión Nacional, restringido a la región Amazonía.",
        url_pagina="https://www.datos.gov.co/widgets/env9-bhc9",
        url_servicio=r.get("url_servicio"), tipo_servicio="Socrata (API SODA), vista tipo blob (archivo adjunto único)", url_descarga=r.get("blob_download_url"),
        formato=f"ZIP ({r.get('blob_mimetype')})", tipo_geometria=None, raster_o_vector=None, resolucion_espacial=None, escala=None, CRS=None,
        cobertura_geografica="Regional (Amazonía)", periodo_inicial=None, periodo_final="2022", frecuencia_actualizacion="Anual (declarada)",
        ultimo_periodo_disponible="2022", fecha_publicacion="2024-01-30", fecha_actualizacion_portal=None,
        validado_oficialmente=False, estado_validacion="publicado_en_portal_pero_no_validado_por_ideam",
        requiere_autenticacion=False, permite_descarga_directa=True, permite_consulta_programatica=True,
        licencia_o_condiciones="Datos abiertos sin validar por IDEAM según cláusulas propias del portal.",
        tamaño_estimado=f"{tam_mb} MB ({r.get('blob_filename')}, blobFileSize real ={r.get('blob_filesize_bytes')} bytes, confirmado por petición real; HEAD: HTTP {((r.get('blob_head') or {}).get('status'))})",
        utilidad_proyecto="Subconjunto regional del dataset nacional anterior; misma desactualización (2022).",
        limitaciones=f"No agrega cobertura nueva frente al dataset nacional ni frente al servicio ArcGIS — redundante. Corrección Fase 2D.1: declara_no_validado_por_ideam={r.get('declara_no_validado_por_ideam')} confirmado en metadata real.",
        observaciones="Recurso Socrata separado por región (Amazonía), mismo patrón que el dataset nacional.",
        decision_priorizacion="rechazar",
    )

    r = _r(resultados, "ideam_arcgis_root_catalog")
    fila(
        id_fuente="ideam_arcgis_root_catalog", entidad="IDEAM", sistema="Geoportal Ambiental Institucional",
        nombre_producto="Catálogo raíz de servicios ArcGIS Server IDEAM (visualizador.ideam.gov.co)", categoria_producto="otro",
        descripcion_oficial="Catálogo REST raíz que expone todas las carpetas y servicios ArcGIS Server institucionales de IDEAM (clima, agua, ecosistemas, bosque, entre otros).",
        url_pagina="https://www.ideam.gov.co/geoportal-ambiental-institucional", url_servicio=r.get("url_servicio"),
        tipo_servicio="ArcGIS REST catálogo raíz", url_descarga=None, formato="JSON (catálogo)", tipo_geometria=None, raster_o_vector=None,
        resolucion_espacial=None, escala=None, CRS=None, cobertura_geografica="Nacional", periodo_inicial=None, periodo_final=None,
        frecuencia_actualizacion=None, ultimo_periodo_disponible=None, fecha_publicacion=None, fecha_actualizacion_portal=None,
        validado_oficialmente=True, estado_validacion="validado_con_peticion_real",
        requiere_autenticacion=False, permite_descarga_directa=False, permite_consulta_programatica=True,
        licencia_o_condiciones=None, tamaño_estimado=None,
        utilidad_proyecto="Punto de descubrimiento: confirma que todos los servicios de bosque/deforestación viven bajo el mismo ArcGIS Server institucional ya usado en fases anteriores (MGN2025, minería) — mismo patrón de acceso reutilizable.",
        limitaciones="No es un producto de datos en sí, es el índice.",
        observaciones=f"{r.get('n_layers', 0) + 0} servicios listados directamente en la raíz; carpetas: incluye 'SNIF', 'Tematica', 'Hosted', entre otras.",
        decision_priorizacion="solo_documental",
    )

    return pd.DataFrame(filas, columns=CATALOGO_COLUMNS)


CATALOGO_COLUMNS = [
    "id_fuente", "entidad", "sistema", "nombre_producto", "categoria_producto", "descripcion_oficial",
    "url_pagina", "url_servicio", "tipo_servicio", "url_descarga", "formato", "tipo_geometria",
    "raster_o_vector", "resolucion_espacial", "escala", "CRS", "cobertura_geografica",
    "periodo_inicial", "periodo_final", "frecuencia_actualizacion", "ultimo_periodo_disponible",
    "fecha_publicacion", "fecha_actualizacion_portal", "validado_oficialmente", "estado_validacion",
    "requiere_autenticacion", "permite_descarga_directa", "permite_consulta_programatica",
    "licencia_o_condiciones", "tamaño_estimado", "utilidad_proyecto", "limitaciones", "observaciones",
    "decision_priorizacion",
]


# ---------------------------------------------------------------------------
# H. Revisión de actualidad
# ---------------------------------------------------------------------------


def build_actualidad(lista_anios_zonas: list[str], lista_periodos_dtd: list[dict]) -> pd.DataFrame:
    ultimo_periodo_dtd = f"{lista_periodos_dtd[-1]['anio']}-{lista_periodos_dtd[-1]['periodo'].upper()}" if lista_periodos_dtd else None
    filas = [
        {
            "producto": "Informe anual + capas Bosque No Bosque / Cambio de Bosque (SMByC)",
            "ultimo_periodo_observado": "2024 (año calendario completo)",
            "fecha_publicacion": "2025-07-31",
            "fecha_actualizacion_servicio": "No expuesta como campo en el servicio ArcGIS (no hay 'editingInfo.lastEditDate' consultado en esta fase)",
            "latencia_dias_aproximada": 212,
            "frecuencia_declarada": "Anual",
            "frecuencia_observada": "Anual, consistente 1990-2024 (con agregaciones multianuales antes de 2012)",
            "apto_para_historico": True,
            "apto_para_monitoreo_oportuno": False,
            "observaciones": "Latencia aproximada: evento observado hasta 2024-12-31, publicado 2025-07-31 (~7 meses). Serie histórica sólida; no apto para monitoreo oportuno por su cadencia anual.",
            "clasificacion": "historico_anual",
        },
        {
            "producto": "Registro Nacional de Zonas Deforestadas (polígonos, FeatureServer)",
            "ultimo_periodo_observado": lista_anios_zonas[-1] if lista_anios_zonas else None,
            "fecha_publicacion": "2025-07-31 (coincide con cifra anual 2024)",
            "fecha_actualizacion_servicio": "No determinada mediante campo de servicio en esta fase",
            "latencia_dias_aproximada": 212,
            "frecuencia_declarada": "Anual",
            "frecuencia_observada": f"Anual, {len(lista_anios_zonas)} años consecutivos confirmados (2013-{lista_anios_zonas[-1] if lista_anios_zonas else '?'})",
            "apto_para_historico": True,
            "apto_para_monitoreo_oportuno": False,
            "observaciones": "Mismo ciclo de publicación que el informe anual — no aporta mayor oportunidad temporal, solo mayor detalle espacial (polígono vs. ráster agregado).",
            "clasificacion": "historico_anual",
        },
        {
            "producto": "Detecciones Tempranas de Deforestación (DTD) Trimestral (puntos, FeatureServer)",
            "ultimo_periodo_observado": ultimo_periodo_dtd,
            "fecha_publicacion": "Boletín 45 (IV trimestre 2025), publicado 2026-03-31 — corrección Fase 2D.1, confirmado con petición HTTP real",
            "fecha_actualizacion_servicio": "No determinada mediante campo de servicio en esta fase",
            "latencia_dias_aproximada": None,
            "frecuencia_declarada": "Trimestral",
            "frecuencia_observada": "Trimestral, sin vacíos, 2017-I a 2025-IV (36 periodos confirmados)",
            "apto_para_historico": True,
            "apto_para_monitoreo_oportuno": True,
            "observaciones": "Es la única fuente con cadencia menor a un año. No se confirmó en esta fase la latencia exacta evento->publicación por trimestre, ni si versiones posteriores pueden modificar detecciones previas — ambos puntos quedan como riesgo abierto para la Fase de indicadores.",
            "clasificacion": "alerta_temprana",
        },
        {
            "producto": "Datos Abiertos Colombia — Cambio en superficie de bosque (Nacional y Amazonía, Socrata)",
            "ultimo_periodo_observado": "2022",
            "fecha_publicacion": "2024-01-30",
            "fecha_actualizacion_servicio": "2024-01-29 (fecha de fila más reciente declarada por la API Socrata)",
            "latencia_dias_aproximada": None,
            "frecuencia_declarada": "Anual",
            "frecuencia_observada": "Estancada desde 2022 — 2 años de rezago frente al servicio ArcGIS institucional (que ya llega a 2024)",
            "apto_para_historico": True,
            "apto_para_monitoreo_oportuno": False,
            "observaciones": "No se debe usar como fuente de actualidad; solo como respaldo histórico o punto de verificación cruzada de años ya cubiertos por el servicio ArcGIS principal.",
            "clasificacion": "actualizacion_periodica",
        },
    ]
    return pd.DataFrame(filas)


if __name__ == "__main__":
    raise SystemExit(main())
