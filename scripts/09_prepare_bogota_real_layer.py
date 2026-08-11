"""Construye la primera capa real del Zoom Bogota.

Integra dos fuentes oficiales de Datos Abiertos Bogota:

- Cuerpo de agua (GeoJSON)
- Cobertura vegetal en humedales (GeoJSON)

La salida es `data/processed/bogota_zoom.csv`, que parte del dataset demo de
drivers y sustituye `score_agua` por un score calculado con datos reales por
localidad.
"""

from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path
from urllib.request import urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
LOCALIDADES = ROOT / "data" / "processed" / "bogota_localidades.geojson"
BASE = ROOT / "data" / "processed" / "bogota_zoom_demo.csv"
OUT = ROOT / "data" / "processed" / "bogota_zoom.csv"

URL_CUERPOS_AGUA = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "81e8c8ce-90dd-44b0-8abd-8a7a4a998bc7/resource/"
    "3f11fac6-4cb3-4e60-89a7-26b2b04c75a4/download/cuerpoagua.geojson"
)
URL_HUMEDALES = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "48cfbc10-a003-4402-a13c-463a6dcbeaac/resource/"
    "31b941a6-aec5-4e7b-845c-35223dbe23b2/download/cober_vege_humedales.geojson"
)


def normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().split())


def polygon_area(ring: list[list[float]]) -> float:
    area = 0.0
    for i in range(len(ring)):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % len(ring)]
        area += (x1 * y2) - (x2 * y1)
    return area / 2.0


def polygon_centroid(ring: list[list[float]]) -> tuple[float, float]:
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]
    area = polygon_area(ring)
    if abs(area) < 1e-12:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return sum(xs) / len(xs), sum(ys) / len(ys)

    cx = 0.0
    cy = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        cross = (x1 * y2) - (x2 * y1)
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    cx /= (6.0 * area)
    cy /= (6.0 * area)
    return cx, cy


def point_in_ring(point: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        intersects = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1)
        if intersects:
            inside = not inside
    return inside


def feature_rings(geometry: dict) -> list[list[list[float]]]:
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        rings = []
        for polygon in geometry["coordinates"]:
            rings.extend(polygon)
        return rings
    return []


def load_localidades() -> list[dict]:
    data = json.loads(LOCALIDADES.read_text(encoding="utf-8"))
    rows = []
    for feat in data["features"]:
        rings = feature_rings(feat["geometry"])
        xs = [p[0] for ring in rings for p in ring]
        ys = [p[1] for ring in rings for p in ring]
        rows.append(
            {
                "codigo": str(feat["id"]).zfill(2),
                "localidad": feat["properties"]["localidad"],
                "localidad_norm": normalize_name(feat["properties"]["localidad"]),
                "rings": rings,
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
            }
        )
    return rows


def download_geojson(url: str) -> dict:
    with urlopen(url, timeout=120) as resp:
        return json.load(resp)


def locality_for_point(point: tuple[float, float], localidades: list[dict]) -> str | None:
    x, y = point
    for loc in localidades:
        minx, miny, maxx, maxy = loc["bbox"]
        if not (minx <= x <= maxx and miny <= y <= maxy):
            continue
        if any(point_in_ring(point, ring) for ring in loc["rings"]):
            return loc["codigo"]
    return None


def score_series(values: pd.Series) -> pd.Series:
    logged = values.fillna(0).astype(float).map(lambda x: math.log1p(max(x, 0.0)))
    lo = float(logged.min())
    hi = float(logged.max())
    if hi - lo < 1e-12:
        return pd.Series([0.0] * len(logged), index=values.index)
    return (logged - lo) / (hi - lo)


def classify_level(score: float) -> str:
    if score >= 0.67:
        return "Crítico"
    if score >= 0.56:
        return "Alto"
    if score >= 0.43:
        return "Medio"
    return "Bajo"


def main() -> None:
    localidades = load_localidades()
    agua = download_geojson(URL_CUERPOS_AGUA)["features"]
    hum = download_geojson(URL_HUMEDALES)["features"]

    water_rows: list[dict] = []
    for feat in agua:
        props = feat["properties"]
        ring = feature_rings(feat["geometry"])[0]
        point = polygon_centroid(ring)
        codigo = locality_for_point(point, localidades)
        if not codigo:
            continue
        water_rows.append(
            {
                "codigo": codigo,
                "water_area": float(props.get("AREA") or 0.0),
                "water_feature_count": 1,
                "water_rio_bogota": 1 if normalize_name(props.get("CUENCA", "")) == "rio bogota" else 0,
                "water_nombre": props.get("NOMBRE", ""),
            }
        )

    hum_rows: list[dict] = []
    for feat in hum:
        props = feat["properties"]
        ring = feature_rings(feat["geometry"])[0]
        point = polygon_centroid(ring)
        codigo = locality_for_point(point, localidades)
        if not codigo:
            continue
        hum_rows.append(
            {
                "codigo": codigo,
                "humedal_area_proxy": abs(float(props.get("Shape_Area") or 0.0)),
                "humedal_feature_count": 1,
                "humedal_nombre": props.get("nombre", ""),
            }
        )

    agua_df = pd.DataFrame(water_rows)
    hum_df = pd.DataFrame(hum_rows)

    agua_agg = agua_df.groupby("codigo", as_index=False).agg(
        water_area=("water_area", "sum"),
        water_feature_count=("water_feature_count", "sum"),
        water_rio_bogota=("water_rio_bogota", "sum"),
    )
    hum_agg = hum_df.groupby("codigo", as_index=False).agg(
        humedal_area_proxy=("humedal_area_proxy", "sum"),
        humedal_feature_count=("humedal_feature_count", "sum"),
    )

    base = pd.read_csv(BASE, dtype={"codigo": str})
    merged = base.merge(agua_agg, on="codigo", how="left").merge(hum_agg, on="codigo", how="left")
    for col in [
        "water_area",
        "water_feature_count",
        "water_rio_bogota",
        "humedal_area_proxy",
        "humedal_feature_count",
    ]:
        merged[col] = merged[col].fillna(0.0)

    merged["score_agua_real"] = (
        0.45 * score_series(merged["water_area"])
        + 0.25 * score_series(merged["water_feature_count"])
        + 0.20 * score_series(merged["humedal_area_proxy"])
        + 0.10 * score_series(merged["humedal_feature_count"] + merged["water_rio_bogota"])
    ).round(3)

    merged["score_agua_demo"] = merged["score_agua"]
    merged["score_agua"] = merged["score_agua_real"]
    merged["indice_bogota_base"] = (
        0.35 * merged["score_fuego_estructural"]
        + 0.30 * merged["score_agua"]
        + 0.35 * merged["score_remocion"]
    ).round(3)
    merged["indice_bogota_dinamico"] = merged["score_operativo"].round(3)
    merged["indice_presion_ecoterritorial_bogota"] = (
        0.65 * merged["indice_bogota_base"] + 0.35 * merged["indice_bogota_dinamico"]
    ).round(3)
    merged["nivel"] = merged["indice_presion_ecoterritorial_bogota"].map(classify_level)
    merged["fuente_agua_real"] = "Datos Abiertos Bogota: cuerpo de agua + humedales"

    merged = merged.sort_values("indice_presion_ecoterritorial_bogota", ascending=False)
    merged.to_csv(OUT, index=False)

    print(f"Escribi {OUT}")
    print(
        merged[
            [
                "localidad",
                "score_agua_demo",
                "score_agua_real",
                "indice_presion_ecoterritorial_bogota",
                "nivel",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()
