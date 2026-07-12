"""Fase 3D.2, sección A/B: descarga controlada de la capa nacional DANE MGN2025
(Municipio, layer 317) — base geométrica homogénea, una sola versión oficial.

Antes de descargar, valida la metadata real del servicio (no asume nombres de
columnas ni capacidades). El servidor declara
`advancedQueryCapabilities.supportsPagination=false` y rechaza
`resultOffset`/`resultRecordCount` (verificado empíricamente: HTTP 200 con
`{"error":{"code":400,...}}` incluso sin geometría). Por eso la descarga usa
`objectIds` explícitos en vez de offset — ver
`aquabosque.data.download.download_arcgis_geojson_by_objectid_chunks`.

No integra calidad hídrica. No recalcula indicadores mineros. No borra ni
sobrescribe las capas territoriales anteriores (limites_municipales_dane,
dane_mgn2025_nuevo_belen_bajira_27493_clean.geojson).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.data.download import (  # noqa: E402
    download_arcgis_geojson_by_objectid_chunks,
    get_arcgis_all_object_ids,
    get_arcgis_feature_count,
    get_arcgis_layer_metadata,
)
from aquabosque.utils.io import ensure_dir, format_bytes, utc_now_iso, write_json  # noqa: E402

BASE_URL = "https://geoportal.dane.gov.co/mparcgis/rest/services/MGN2025/Serv_CapasMGN_2025/FeatureServer/317"
DEST_DIR = PROJECT_ROOT / "data" / "raw" / "territorio" / "mgn2025_unidades_territoriales_dane"
MANIFEST_PATH = DEST_DIR / "manifest.json"
FILENAME_PREFIX = "mgn2025_municipio"
OUT_SR = 4326
CHUNK_SIZE = 40  # ~40 features / ~7.8 MB observado en pruebas, con margen bajo el tope de 20 MB


def main() -> int:
    print("Fase 3D.2 - sección A: validación de metadata real del servicio")
    print("=" * 70)

    meta = get_arcgis_layer_metadata(BASE_URL)
    if meta is None:
        print("ERROR: no se pudo obtener la metadata del servicio. Proceso detenido.")
        return 1

    campos = [f["name"] for f in meta.get("fields", [])]
    print(f"  name: {meta.get('name')}")
    print(f"  description: {meta.get('description')!r}")
    print(f"  geometryType: {meta.get('geometryType')}")
    print(f"  sourceSpatialReference (CRS nativo): {meta.get('sourceSpatialReference')}")
    print(f"  maxRecordCount: {meta.get('maxRecordCount')}")
    print(f"  capabilities: {meta.get('capabilities')}")
    print(f"  supportedQueryFormats: {meta.get('supportedQueryFormats')}")
    print(f"  advancedQueryCapabilities.supportsPagination: {meta.get('advancedQueryCapabilities', {}).get('supportsPagination')}")
    print(f"  campos ({len(campos)}): {campos}")

    campos_requeridos = {"OBJECTID", "DPTO_CCDGO", "MPIO_CCDGO", "MPIO_CDPMP", "DPTO_CNMBRE", "MPIO_CNMBRE"}
    faltantes = campos_requeridos - set(campos)
    if faltantes:
        print(f"ERROR: faltan campos esperados en la metadata real: {faltantes}. Proceso detenido.")
        return 1
    if "geoJSON" not in (meta.get("supportedQueryFormats") or ""):
        print("ERROR: el servicio no declara soporte de geoJSON en supportedQueryFormats. Proceso detenido.")
        return 1
    print("  OK: campos clave presentes y geoJSON soportado.")

    total_count = get_arcgis_feature_count(BASE_URL)
    print(f"\n  Total de features (returnCountOnly): {total_count}")
    if total_count is None or total_count <= 0:
        print("ERROR: no se pudo determinar el total de features. Proceso detenido.")
        return 1

    print("\n[B] Descargando la capa nacional completa por particiones de objectIds...")
    object_ids = get_arcgis_all_object_ids(BASE_URL)
    if object_ids is None:
        print("ERROR: no se pudieron obtener los objectIds. Proceso detenido.")
        return 1
    print(f"  {len(object_ids)} objectIds obtenidos (rango {min(object_ids)}-{max(object_ids)}).")
    if len(object_ids) != total_count:
        print(f"ERROR: {len(object_ids)} objectIds != {total_count} del conteo. Proceso detenido.")
        return 1

    ensure_dir(DEST_DIR)
    result = download_arcgis_geojson_by_objectid_chunks(
        fuente="DANE - Marco Geoestadistico Nacional 2025 (MGN2025), capa Municipio (layer 317)",
        base_url=BASE_URL,
        dest_dir=DEST_DIR,
        filename_prefix=FILENAME_PREFIX,
        object_ids=object_ids,
        out_sr=OUT_SR,
        chunk_size=CHUNK_SIZE,
    )

    print(f"  Estado: {result.estado}")
    print(f"  Features descargadas: {result.total_filas_descargadas}/{result.total_filas_origen}")
    print(f"  Partes: {result.numero_partes}, tamaño total: {format_bytes(result.tamano_total_bytes)}")
    print(f"  Observaciones: {result.observaciones}")

    if result.estado not in ("completo",):
        print(f"\nADVERTENCIA: la descarga no quedó en estado 'completo' (estado={result.estado}).")

    manifest = {
        "fuente": result.fuente,
        "entidad": "DANE (Departamento Administrativo Nacional de Estadística)",
        "servicio": BASE_URL,
        "layer_id": 317,
        "fecha_descarga": utc_now_iso(),
        "total_features_origen": result.total_filas_origen,
        "total_features_descargadas": result.total_filas_descargadas,
        "numero_partes": result.numero_partes,
        "campos": campos,
        "crs_nativo": meta.get("sourceSpatialReference"),
        "crs_salida": f"EPSG:{OUT_SR}",
        "tamano_total_bytes": result.tamano_total_bytes,
        "metodo_paginacion": (
            "objectIds explícitos en chunks (no resultOffset/resultRecordCount): el servicio declara "
            "advancedQueryCapabilities.supportsPagination=false y rechaza offset-based pagination "
            "(verificado empíricamente antes de descargar, ver docs/08)."
        ),
        "chunk_size_objectids": CHUNK_SIZE,
        "archivos_y_tamanos": [
            {"archivo": p.path.name, "objectid_inicio": p.offset_inicio, "objectid_fin": p.offset_fin, "features": p.filas, "tamano_bytes": p.tamano_bytes}
            for p in result.parts
        ],
        "estado": result.estado,
        "observaciones": result.observaciones,
    }
    write_json(MANIFEST_PATH, manifest)
    print(f"\n  Manifest escrito: {MANIFEST_PATH}")

    for p in result.parts:
        meta_part_path = p.path.with_suffix(p.path.suffix + ".metadata.json")
        write_json(
            meta_part_path,
            {
                "fuente": result.fuente,
                "url": BASE_URL,
                "fecha_descarga": utc_now_iso(),
                "formato": "GeoJSON (objectIds explícitos, outSR=4326)",
                "objectid_inicio": p.offset_inicio,
                "objectid_fin": p.offset_fin,
                "filas_descargadas": p.filas,
                "tamano_bytes": p.tamano_bytes,
                "estado": result.estado,
            },
        )

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Features esperadas: {total_count} | descargadas: {result.total_filas_descargadas}")
    print(f"Partes: {result.numero_partes} | tamaño total: {format_bytes(result.tamano_total_bytes)}")
    print(f"Estado final: {result.estado}")

    return 0 if result.estado == "completo" else 1


if __name__ == "__main__":
    raise SystemExit(main())
