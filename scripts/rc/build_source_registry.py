# -*- coding: utf-8 -*-
"""Genera metadata/source_registry.json (Sec 6/7) — registro maestro de fuentes con hashes.
Autoridad = archivo real; este registro es una VISTA reproducible (Sec 66)."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "metadata"; META.mkdir(exist_ok=True)

def h(p):
    p = ROOT / p
    if not p.exists():
        return {"file_hash": None, "file_size": None, "present": False}
    b = p.read_bytes()
    return {"file_hash": "sha256:" + hashlib.sha256(b).hexdigest(), "file_size": len(b), "present": True}

SOURCES = [
    {"SOURCE_ID": "IDIGER_BITACORA_V202608", "nombre": "Bitácora de Emergencias IDIGER",
     "entidad": "IDIGER / SIRE", "portal": "Datos Abiertos Bogotá", "licencia": "CC-BY 4.0",
     "url": "https://datosabiertos.bogota.gov.co/dataset/bitacora-de-emergencias",
     "cobertura_temporal": "2017-01..2025-06", "cobertura_espacial": "Bogotá D.C.", "frecuencia": "evento",
     "formato": "CSV", "crs": "N/A (geocodificado a localidad/UPZ por IDIGER)", "unidad": "evento",
     "archivo": "data/raw/bogota/bitacora_emergencias.csv", "campos_usados": ["Fecha reporte","Localidad","Upz","Tipo de afectación"],
     "script_ingesta": "scripts/_bogota_sources.py", **h("data/raw/bogota/bitacora_emergencias.csv")},
    {"SOURCE_ID": "IDIGER_SAB_LLUVIA_V202608", "nombre": "SAB Lluvia diaria",
     "entidad": "IDIGER — Sistema de Alerta de Bogotá", "portal": "Datos Abiertos Bogotá", "licencia": "CC-BY 4.0",
     "url": "https://datosabiertos.bogota.gov.co/dataset/sab-sistema-de-alerta-de-bogota-idiger-bogota-d-c-15-10-2021",
     "cobertura_temporal": "2021-09..2024-12", "cobertura_espacial": "70 estaciones Bogotá", "frecuencia": "diaria",
     "formato": "CSV", "crs": "N/A (matriz fecha×estación)", "unidad": "mm/día",
     "archivo": "data/raw/bogota/sab_lluvia_diaria.csv", "campos_usados": ["FECHALECTURA","<estaciones>"],
     "script_ingesta": "scripts/_bogota_sources.py", **h("data/raw/bogota/sab_lluvia_diaria.csv")},
    {"SOURCE_ID": "IDIGER_SAB_ESTACIONES_V202608", "nombre": "Catálogo estaciones SAB",
     "entidad": "IDIGER — SAB", "portal": "Datos Abiertos Bogotá", "licencia": "CC-BY 4.0",
     "url": "https://datosabiertos.bogota.gov.co/dataset/sab-sistema-de-alerta-de-bogota-idiger-bogota-d-c-15-10-2021",
     "cobertura_temporal": "vigente", "cobertura_espacial": "77 estaciones", "frecuencia": "catálogo",
     "formato": "CSV", "crs": "lat/lon (crudo con punto de miles → /1e5)", "unidad": "estación",
     "archivo": "data/raw/bogota/sab_estaciones.csv", "campos_usados": ["Estación","Latitud","Longitud","Localidad"],
     "script_ingesta": "scripts/_bogota_sources.py", **h("data/raw/bogota/sab_estaciones.csv")},
    {"SOURCE_ID": "IDECA_POT_AMENAZA_MM_URB_2021", "nombre": "Amenaza mov. en masa urbano (POT)",
     "entidad": "IDECA / SDP", "portal": "Datos Abiertos Bogotá", "licencia": "CC-BY 4.0",
     "url": "https://datosabiertos.bogota.gov.co/dataset/areas-amenaza-movimientos-en-masa...",
     "cobertura_temporal": "POT 2021 (escala 1:5000, 2016)", "cobertura_espacial": "Bogotá urbano", "frecuencia": "estático",
     "formato": "GeoJSON", "crs": "SISTEMA LOCAL BOGOTÁ (Observatorio) sin etiquetar — REQUIERE CRS autoritativo IDECA",
     "unidad": "polígono", "archivo": "data/raw/bogota/pot/amenaza_mm_urbano.geojson",
     "campos_usados": ["geometry","CATEGORIZA","SHAPE_Area"], "script_ingesta": "scripts/11_prepare_bogota_remocion.py (DEPRECADO: afín 57km)",
     "estado": "NO USAR sin reproyección geodésica; reemplazado en V1 por índice IDIGER", **h("data/raw/bogota/pot/amenaza_mm_urbano.geojson")},
]

reg = {"generated_by": "scripts/rc/build_source_registry.py",
       "note": "SOURCE_ID obligatorio; ningún dataset sin él (Sec 6). Autoridad = archivo + hash.",
       "sources": SOURCES}
(META / "source_registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"source_registry.json: {len(SOURCES)} fuentes")
for s in SOURCES:
    print(f"  {s['SOURCE_ID']:34s} {'OK' if s['present'] else 'FALTA':5s} {str(s['file_hash'])[:23]}")
