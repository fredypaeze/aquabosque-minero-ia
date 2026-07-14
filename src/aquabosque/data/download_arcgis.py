"""Descarga de Feature Services de ArcGIS (deforestación, RUNAP) para AquaBosque.

Los datos ambientales oficiales viven en servicios ArcGIS REST (no en tablas
SODA). Se consultan por paginación con resultOffset, extrayendo solo atributos
(sin geometría cuando no se necesita). Buen ciudadano: pausa entre páginas.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "AquaBosque-MinEnergia/1.0"}


def descargar_feature_service(base_url: str, capa: int = 0, out_fields: str = "*",
                              return_geometry: bool = False, pagina: int = 1000) -> list[dict]:
    filas, offset = [], 0
    while True:
        params = {"where": "1=1", "outFields": out_fields, "f": "json",
                  "resultOffset": offset, "resultRecordCount": pagina,
                  "returnGeometry": str(return_geometry).lower()}
        url = f"{base_url}/{capa}/query?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=90) as r:
            d = json.loads(r.read().decode("utf-8"))
        feats = d.get("features", [])
        if not feats:
            break
        filas.extend(f["attributes"] for f in feats)
        if len(feats) < pagina or not d.get("exceededTransferLimit"):
            break
        offset += pagina
        time.sleep(0.3)
    return filas


def _guardar(filas, destino: Path) -> int:
    if not filas:
        return 0
    cols = list({k for f in filas for k in f})
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    return len(filas)


SERVICIOS = [
    {"clave": "deforestacion", "dim": "bosque",
     "url": "https://services9.arcgis.com/1TA62AToEccvEPrZ/arcgis/rest/services/Datos/FeatureServer",
     "out_fields": "DPTO_CNMBR,MPIO_CNMBR,Año,Bosque,No_Bosque,MPIO_NAREA,Defores",
     "descripcion": "Deforestación por municipio (bosque/no bosque/deforestado por año)"},
    {"clave": "runap", "dim": "sensibilidad",
     "url": "https://services3.arcgis.com/Fto9oba51JWVX0Qy/arcgis/rest/services/Areas_Protegidas_RUNAP/FeatureServer",
     "out_fields": "nombre,categoria,hectareas_,centroid_x,centroid_y,organizaci",
     "descripcion": "RUNAP — áreas protegidas (nombre, categoría, hectáreas, centroide)"},
]


def run() -> dict:
    log = {"descargadas": [], "fallas": []}
    for s in SERVICIOS:
        try:
            filas = descargar_feature_service(s["url"], out_fields=s["out_fields"])
            destino = RAW / s["dim"] / f"{s['clave']}.csv"
            n = _guardar(filas, destino)
            log["descargadas"].append({"fuente": s["clave"], "filas": n, "archivo": str(destino.relative_to(ROOT))})
            print(f"[OK] {s['clave']:14s} {n:>6,} filas → {destino.relative_to(ROOT)}")
        except Exception as e:  # noqa: BLE001
            log["fallas"].append({"fuente": s["clave"], "error": str(e)[:120]})
            print(f"[FALLA] {s['clave']}: {str(e)[:90]}")
    return log


if __name__ == "__main__":
    run()
