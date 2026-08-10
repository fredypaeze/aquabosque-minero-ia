"""Integra el cuarto eje real: ladera / remocion en masa.

Usa capas POT de movimiento en masa publicadas por Datos Abiertos Bogota:

- Amenaza por movimiento en masa en suelo urbano y de expansion
- Amenaza por movimiento en masa en suelo rural
- Areas en condicion de riesgo por movimiento en masa en suelo urbano y expansion

Las capas vienen en coordenadas proyectadas sin CRS explicito en el GeoJSON
publicado. Para poder agregarlas por localidad sin dependencias geoespaciales
pesadas, se usa una normalizacion espacial affine sobre la extension completa
de Bogota y luego una asignacion por punto-en-poligono sobre localidades.
Es un proxy reproducible suficiente para esta fase de producto.
"""

from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path
from urllib.request import urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "data" / "processed" / "bogota_zoom.csv"
LOCALIDADES = ROOT / "data" / "processed" / "bogota_localidades.geojson"

URL_MM_URB = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "e4012cd7-e178-4868-a0f0-b857d243cd92/resource/"
    "8904ce1f-a4a4-4648-a684-bb62fd9182b8/download/amenaza_mm_urbano.geojson"
)
URL_MM_RUR = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "bfc4c1ca-7747-4147-a5ad-4b522f3fabda/resource/"
    "21d376b4-f126-4a5c-93ad-c4ac025d5f7a/download/amenaza_mm_rural.geojson"
)
URL_MM_RISK_URB = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "60d773e2-41a3-4343-abe6-c802eaf0568d/resource/"
    "7c859764-81d3-47d2-af89-06ef9b7df785/download/area_cr_mm_urbano.geojson"
)


def normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    return " ".join(text.lower().split())


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


def download_json(url: str) -> dict:
    with urlopen(url, timeout=180) as resp:
        return json.load(resp)


def feature_rings(geometry: dict) -> list[list[list[float]]]:
    if geometry["type"] == "Polygon":
        return geometry["coordinates"]
    if geometry["type"] == "MultiPolygon":
        rings = []
        for polygon in geometry["coordinates"]:
            rings.extend(polygon)
        return rings
    return []


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


def load_localidades() -> tuple[list[dict], tuple[float, float, float, float]]:
    data = json.loads(LOCALIDADES.read_text(encoding="utf-8"))
    rows = []
    xs_all = []
    ys_all = []
    for feat in data["features"]:
        rings = feature_rings(feat["geometry"])
        xs = [p[0] for ring in rings for p in ring]
        ys = [p[1] for ring in rings for p in ring]
        xs_all.extend(xs)
        ys_all.extend(ys)
        rows.append(
            {
                "codigo": str(feat["id"]).zfill(2),
                "localidad": feat["properties"]["localidad"],
                "localidad_norm": normalize_name(feat["properties"]["localidad"]),
                "rings": rings,
                "bbox": (min(xs), min(ys), max(xs), max(ys)),
            }
        )
    return rows, (min(xs_all), min(ys_all), max(xs_all), max(ys_all))


def projected_bbox(feature_sets: list[dict]) -> tuple[float, float, float, float]:
    xs = []
    ys = []
    for data in feature_sets:
        for feat in data["features"]:
            for ring in feature_rings(feat["geometry"]):
                for x, y in ring:
                    xs.append(x)
                    ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def approx_projected_to_lonlat(
    point: tuple[float, float],
    src_bbox: tuple[float, float, float, float],
    dst_bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    x, y = point
    src_minx, src_miny, src_maxx, src_maxy = src_bbox
    dst_minx, dst_miny, dst_maxx, dst_maxy = dst_bbox
    lon = dst_minx + ((x - src_minx) / ((src_maxx - src_minx) or 1e-12)) * (dst_maxx - dst_minx)
    lat = dst_miny + ((y - src_miny) / ((src_maxy - src_miny) or 1e-12)) * (dst_maxy - dst_miny)
    return lon, lat


def locality_for_point(point: tuple[float, float], localidades: list[dict]) -> str | None:
    x, y = point
    for loc in localidades:
        minx, miny, maxx, maxy = loc["bbox"]
        if not (minx <= x <= maxx and miny <= y <= maxy):
            continue
        if any(point_in_ring(point, ring) for ring in loc["rings"]):
            return loc["codigo"]
    return None


def build_remocion(localidades: list[dict], dst_bbox: tuple[float, float, float, float]) -> pd.DataFrame:
    sources = [
        ("amenaza_urbana", download_json(URL_MM_URB)),
        ("amenaza_rural", download_json(URL_MM_RUR)),
        ("riesgo_urbano", download_json(URL_MM_RISK_URB)),
    ]
    src_bbox = projected_bbox([data for _, data in sources])
    rows: list[dict] = []
    for source_name, data in sources:
        for feat in data["features"]:
            rings = feature_rings(feat["geometry"])
            if not rings:
                continue
            centroid_proj = polygon_centroid(rings[0])
            centroid_ll = approx_projected_to_lonlat(centroid_proj, src_bbox, dst_bbox)
            codigo = locality_for_point(centroid_ll, localidades)
            if not codigo:
                continue
            props = feat["properties"]
            area_val = props.get("SHAPE_Area") or props.get("Shape_Area") or 0.0
            try:
                area_val = abs(float(area_val))
            except Exception:
                area_val = abs(polygon_area(rings[0]))
            rows.append(
                {
                    "codigo": codigo,
                    "mm_area_proxy": area_val,
                    "mm_feature_count": 1,
                    "mm_riesgo_count": 1 if source_name == "riesgo_urbano" else 0,
                    "mm_amenaza_urb_count": 1 if source_name == "amenaza_urbana" else 0,
                    "mm_amenaza_rur_count": 1 if source_name == "amenaza_rural" else 0,
                }
            )
    mm_df = pd.DataFrame(rows)
    if mm_df.empty:
        return pd.DataFrame(columns=["codigo"])
    return mm_df.groupby("codigo", as_index=False).agg(
        mm_area_proxy=("mm_area_proxy", "sum"),
        mm_feature_count=("mm_feature_count", "sum"),
        mm_riesgo_count=("mm_riesgo_count", "sum"),
        mm_amenaza_urb_count=("mm_amenaza_urb_count", "sum"),
        mm_amenaza_rur_count=("mm_amenaza_rur_count", "sum"),
    )


def main() -> None:
    base = pd.read_csv(IN_CSV, dtype={"codigo": str})
    localidades, bbox_ll = load_localidades()
    mm = build_remocion(localidades, bbox_ll)
    df = base.merge(mm, on="codigo", how="left")
    for col in [
        "mm_area_proxy",
        "mm_feature_count",
        "mm_riesgo_count",
        "mm_amenaza_urb_count",
        "mm_amenaza_rur_count",
    ]:
        df[col] = df[col].fillna(0.0)

    df["score_remocion_demo"] = df["score_remocion"]
    df["score_remocion_real"] = (
        0.40 * score_series(df["mm_area_proxy"])
        + 0.25 * score_series(df["mm_feature_count"])
        + 0.25 * score_series(df["mm_riesgo_count"])
        + 0.10 * score_series(df["mm_amenaza_urb_count"] + df["mm_amenaza_rur_count"])
    ).round(3)

    df["score_remocion"] = df["score_remocion_real"]
    df["indice_bogota_base"] = (
        0.35 * df["score_fuego_estructural"]
        + 0.30 * df["score_agua"]
        + 0.35 * df["score_remocion"]
    ).round(3)
    df["indice_bogota_dinamico"] = df["score_operativo"].round(3)
    df["indice_presion_ecoterritorial_bogota"] = (
        0.65 * df["indice_bogota_base"] + 0.35 * df["indice_bogota_dinamico"]
    ).round(3)
    df["nivel"] = df["indice_presion_ecoterritorial_bogota"].map(classify_level)
    df["fuente_remocion_real"] = (
        "POT Bogota 2021: amenaza por movimiento en masa urbano+rural y areas en condicion de riesgo urbano"
    )

    df = df.sort_values("indice_presion_ecoterritorial_bogota", ascending=False)
    df.to_csv(IN_CSV, index=False)
    print(f"Actualice {IN_CSV}")
    print(
        df[
            [
                "localidad",
                "score_fuego_estructural",
                "score_agua",
                "score_remocion",
                "score_operativo",
                "indice_presion_ecoterritorial_bogota",
                "nivel",
            ]
        ].head(10).to_string(index=False)
    )


if __name__ == "__main__":
    main()
