"""Descarga de fuentes abiertas (Socrata / datos.gov.co) para AquaBosque.

Regla: baja lo VERIFICADO, valida columnas, registra fallas y continúa.
Nunca inventa datos; lo no disponible queda documentado en el log.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "AquaBosque-MinEnergia/1.0 (Grupo de Datos Estrategicos)"}


def _socrata(recurso_id: str, limite_pagina: int = 5000) -> list[dict]:
    """Descarga completa paginada de un recurso Socrata (.json)."""
    base = f"https://www.datos.gov.co/resource/{recurso_id}.json"
    filas, offset = [], 0
    while True:
        url = f"{base}?$limit={limite_pagina}&$offset={offset}"
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            lote = json.loads(r.read().decode("utf-8"))
        lote = [x for x in lote if x]  # descartar dicts vacíos
        filas.extend(lote)
        if len(lote) < limite_pagina:
            break
        offset += limite_pagina
        time.sleep(0.3)  # buen ciudadano: no martillar el servidor
    return filas


def _guardar_csv(filas: list[dict], destino: Path) -> int:
    if not filas:
        return 0
    cols = list({k for f in filas for k in f.keys()})
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    return len(filas)


# fuentes VERIFICADAS en Fase 1 (bajan tabular con las columnas esperadas)
FUENTES = [
    {"clave": "rucom", "dim": "mineria", "id": "42ha-fhvj",
     "cols_esperadas": ["codigo_dane", "municipio", "departamento", "mineral"],
     "descripcion": "ANM RUCOM — explotadores mineros autorizados"},
    {"clave": "divipola", "dim": "territorio", "id": "gdxc-w37w",
     "cols_esperadas": ["cod_mpio", "nom_mpio", "dpto", "latitud", "longitud"],
     "descripcion": "DANE DIVIPOLA — municipios con código y centroide"},
    {"clave": "anm_volumen", "dim": "mineria", "id": "r85m-vv6c",
     "cols_esperadas": ["codigo_dane", "volumenes_de_explotacion", "regalias_pagadas", "recurso_natural"],
     "descripcion": "ANM — volumen de explotación y regalías por municipio (producción real)"},
    {"clave": "pdet", "dim": "territorio", "id": "idrk-ba8y",
     "cols_esperadas": ["cod_muni", "nom_muni"],
     "descripcion": "Municipios PDET (sensibilidad social/territorial)"},
]

# fuentes que requieren vía geoespacial (Fase 4) — se registran, no se inventan
PENDIENTES = [
    {"clave": "deforestacion", "dim": "bosque",
     "motivo": "datasets datos.gov.co no exponen tabla tabular vía SODA; usar IDEAM SMByC o capa geoespacial (Fase 4)"},
    {"clave": "calidad_agua", "dim": "agua",
     "motivo": "capa geoespacial de puntos (GeoJSON); cruce espacial con municipios (Fase 4)"},
    {"clave": "runap", "dim": "sensibilidad",
     "motivo": "servicio WFS/GeoJSON oficial de RUNAP; intersección espacial con municipios (Fase 4)"},
]


def run() -> dict:
    now = datetime.now(timezone.utc)
    log = {"generated_at": now.isoformat(), "descargadas": [], "pendientes": [], "fallas": []}
    for f in FUENTES:
        try:
            filas = _socrata(f["id"])
            faltan = [c for c in f["cols_esperadas"] if filas and c not in filas[0]]
            destino = RAW / f["dim"] / f"{f['clave']}.csv"
            n = _guardar_csv(filas, destino)
            estado = "OK" if not faltan else "COLUMNAS_FALTANTES"
            log["descargadas"].append({"fuente": f["clave"], "filas": n, "estado": estado,
                                       "columnas_faltantes": faltan, "archivo": str(destino.relative_to(ROOT)),
                                       "descripcion": f["descripcion"]})
            print(f"[OK]   {f['clave']:14s} {n:>7,} filas → {destino.relative_to(ROOT)}" +
                  (f"  ⚠ faltan {faltan}" if faltan else ""))
        except Exception as e:  # noqa: BLE001
            log["fallas"].append({"fuente": f["clave"], "error": str(e)[:120]})
            print(f"[FALLA] {f['clave']:14s} {str(e)[:80]}")
    for p in PENDIENTES:
        log["pendientes"].append(p)
        print(f"[PEND] {p['clave']:14s} {p['motivo'][:70]}")
    (ROOT / "data" / "raw" / "_download_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nDescarga: {len(log['descargadas'])} OK · {len(log['pendientes'])} pendientes (vía geoespacial) · {len(log['fallas'])} fallas")
    return log


if __name__ == "__main__":
    run()
