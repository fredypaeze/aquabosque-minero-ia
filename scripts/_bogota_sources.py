# -*- coding: utf-8 -*-
"""Fuentes oficiales (bronze) del módulo Zoom Bogotá — descarga reproducible.

El crudo grande (bitácora, 78 MB) NO se versiona: se descarga desde Datos Abiertos
Bogotá cuando falta, garantizando trazabilidad a la fuente oficial (ver CATALOGO_DATOS.md).
"""
import urllib.request
from pathlib import Path

BASE_BIT = "https://datosabiertos.bogota.gov.co/dataset/e7bc4258-4b77-454b-8e3a-78166e1d946e/resource"
BASE_SAB = "https://datosabiertos.bogota.gov.co/dataset/0ef49022-8997-41f3-8932-93db779b8780/resource"

URLS = {
    "bitacora_emergencias.csv":
        f"{BASE_BIT}/b1507547-184d-4e4c-b6e4-cd1606800269/download/reporte_consulta_bitacora2017-jun2025.csv",
    "sab_lluvia_diaria.csv":
        f"{BASE_SAB}/28d3ab6b-c0dd-478e-ada9-cebdfed1387c/download/reportes_acumuladosseptiembre2021a-dic2024.csv",
    "sab_estaciones.csv":
        f"{BASE_SAB}/196dca9c-36e6-451b-8cb5-64edfe874f84/download/catalogo-estaciones-hidrometeorologicos2.csv",
}


def fetch_all(raw_dir):
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        f = raw / name
        if f.exists() and f.stat().st_size > 0:
            continue
        print(f"  ↓ descargando bronze desde fuente oficial: {name}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=240) as r, open(f, "wb") as out:
            out.write(r.read())
    return raw


if __name__ == "__main__":
    fetch_all(Path(__file__).resolve().parent.parent / "data" / "raw" / "bogota")
    print("Bronze Bogotá listo.")
