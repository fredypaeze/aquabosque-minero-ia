"""Capa satelital NRT — Focos de calor activos (FIRMS) → señal municipal.

Monitoreo de deforestación/quema NEAR-REAL-TIME a partir de sensores satelitales
(VIIRS 375 m y MODIS 1 km, NASA FIRMS). Los focos de calor activos son el proxy
estándar de la frontera de deforestación y quema en Colombia y la Amazonía.

Diseño coherente con AquaBosque: sin GDAL. La asignación de cada foco a su
municipio se hace con point-in-polygon (ray casting) en Python puro, usando
`data/processed/municipios.geojson` (1.122 polígonos DIVIPOLA).

Honestidad: esto NO procesa imagen cruda con una red neuronal (eso es la capa 2,
en GPU). Es una señal satelital térmica NRT, oficial y verificable, presentada
como lo que es: proxy de actividad de fuego/deforestación reciente.

Fuente sin API key: descargas regionales de FIRMS (South America, 7 días).
Con un MAP_KEY gratuito se pueden ampliar rangos y usar el API por área.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GEOJSON = ROOT / "data" / "processed" / "municipios.geojson"
MASTER = ROOT / "data" / "processed" / "master_con_etiqueta.csv"
RAW_DIR = ROOT / "data" / "raw" / "satelital"
OUT_CSV = ROOT / "data" / "processed" / "fuego_municipal.csv"
OUT_SUMMARY = ROOT / "data" / "processed" / "fuego_summary.json"

# Bounding box de Colombia continental + insular (lon_min, lat_min, lon_max, lat_max)
COL_BBOX = (-79.2, -4.4, -66.7, 13.6)

FIRMS_FILES = {
    "VIIRS_SNPP": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_7d.csv",
    "VIIRS_NOAA20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_America_7d.csv",
    "MODIS": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_South_America_7d.csv",
}
UA = {"User-Agent": "AquaBosque-MinEnergia/1.0 (monitoreo ambiental datos abiertos)"}


def _download(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_firms() -> list[dict]:
    """Descarga los 3 productos FIRMS (7 días), filtra a Colombia y unifica."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    lon_min, lat_min, lon_max, lat_max = COL_BBOX
    registros: list[dict] = []
    for sensor, url in FIRMS_FILES.items():
        try:
            text = _download(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  AVISO: {sensor} no descargó ({exc}); se continúa.")
            continue
        (RAW_DIR / f"firms_{sensor}_7d.csv").write_text(text, encoding="utf-8")
        reader = csv.DictReader(io.StringIO(text))
        n = 0
        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except (KeyError, ValueError):
                continue
            if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
                continue
            frp = row.get("frp")
            registros.append({
                "sensor": sensor,
                "lat": lat,
                "lon": lon,
                "acq_date": row.get("acq_date", ""),
                "frp": float(frp) if frp not in (None, "", "nan") else 0.0,
                "confidence": row.get("confidence", ""),
                "daynight": row.get("daynight", ""),
            })
            n += 1
        print(f"  {sensor}: {n} focos en Colombia (7d)")
    return registros


# ---- Point-in-polygon (ray casting) sin dependencias ----

def _point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def _load_municipios() -> list[dict]:
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    munis = []
    for feat in geo["features"]:
        props = feat["properties"]
        geom = feat["geometry"]
        # Polygon: coords[0] = anillo exterior
        ring = geom["coordinates"][0]
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        munis.append({
            "cod": int(props["cod"]),
            "mpio": props.get("mpio", ""),
            "dpto": props.get("dpto", ""),
            "ring": ring,
            "bbox": (min(xs), min(ys), max(xs), max(ys)),
        })
    return munis


def asignar_a_municipios(focos: list[dict], munis: list[dict]) -> dict[int, dict]:
    """Point-in-polygon con pre-filtro por bbox. Devuelve agregados por municipio."""
    agg: dict[int, dict] = {}
    sin_asignar = 0
    for foco in focos:
        lon, lat = foco["lon"], foco["lat"]
        asignado = None
        for m in munis:
            bx0, by0, bx1, by1 = m["bbox"]
            if bx0 <= lon <= bx1 and by0 <= lat <= by1 and _point_in_ring(lon, lat, m["ring"]):
                asignado = m
                break
        if asignado is None:
            sin_asignar += 1
            continue
        cod = asignado["cod"]
        rec = agg.setdefault(cod, {
            "cod_mpio": cod, "municipio": asignado["mpio"], "departamento": asignado["dpto"],
            "focos_7d": 0, "frp_total": 0.0, "ultima_fecha": "",
        })
        rec["focos_7d"] += 1
        rec["frp_total"] += foco["frp"]
        if foco["acq_date"] > rec["ultima_fecha"]:
            rec["ultima_fecha"] = foco["acq_date"]
    print(f"  focos asignados a municipio: {len(focos) - sin_asignar}/{len(focos)} (sin asignar: {sin_asignar})")
    return agg


def construir_senal() -> dict:
    print("Capa satelital NRT — FIRMS focos de calor activos (7 días)")
    focos = fetch_firms()
    munis = _load_municipios()
    agg = asignar_a_municipios(focos, munis)

    filas = list(agg.values())
    # Nombres limpios desde el master (el geojson trae artefactos de codificación).
    try:
        import csv as _csv
        nombres = {}
        with MASTER.open(encoding="utf-8") as fh:
            for row in _csv.DictReader(fh):
                nombres[int(row["cod_mpio"])] = (row["municipio"], row["departamento"])
        for f in filas:
            if f["cod_mpio"] in nombres:
                f["municipio"], f["departamento"] = nombres[f["cod_mpio"]]
    except Exception as exc:  # noqa: BLE001
        print(f"  AVISO: no se pudieron mapear nombres del master ({exc}).")
    # Normalización de la señal de fuego a [0,1] (idx_fuego), escala log para colas largas.
    import math
    max_frp = max((f["frp_total"] for f in filas), default=0.0)
    denom = math.log1p(max_frp) or 1.0
    for f in filas:
        f["idx_fuego"] = round(math.log1p(f["frp_total"]) / denom, 4)
        f["frp_total"] = round(f["frp_total"], 2)
    filas.sort(key=lambda r: r["frp_total"], reverse=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cod_mpio", "municipio", "departamento",
                                           "focos_7d", "frp_total", "idx_fuego", "ultima_fecha"])
        w.writeheader()
        w.writerows(filas)

    resumen = {
        "generado": datetime.now(timezone.utc).isoformat(),
        "ventana": "7 días (NRT)",
        "fuente": "NASA FIRMS · VIIRS (SNPP+NOAA-20) + MODIS · sin API key",
        "total_focos_colombia": len(focos),
        "municipios_con_fuego": len(filas),
        "top10": [{"municipio": r["municipio"], "departamento": r["departamento"],
                   "focos_7d": r["focos_7d"], "frp_total": r["frp_total"]} for r in filas[:10]],
        "nota_honestidad": ("Señal satelital térmica NRT (proxy de deforestación/quema), "
                            "no clasificación de imagen cruda por red neuronal (esa es la capa 2, GPU)."),
    }
    OUT_SUMMARY.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {OUT_CSV.name} ({len(filas)} municipios con fuego) · {OUT_SUMMARY.name}")
    return resumen


if __name__ == "__main__":
    r = construir_senal()
    print("\nTop 5 municipios por FRP (potencia radiativa acumulada 7d):")
    for t in r["top10"][:5]:
        print(f"  {t['municipio']} ({t['departamento']}): {t['focos_7d']} focos · FRP {t['frp_total']}")
