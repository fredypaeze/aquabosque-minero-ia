"""Descarga y normaliza la geometria oficial de localidades de Bogota.

Genera `data/processed/bogota_localidades.geojson` a partir de la capa publicada
en Datos Abiertos Bogota. La conversion simplifica geometria ESRI JSON a
GeoJSON suficiente para visualizacion cartografica en Streamlit/Plotly.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen


URL = (
    "https://datosabiertos.bogota.gov.co/dataset/"
    "856cb657-8ca3-4ee8-857f-37211173b1f8/resource/"
    "497b8756-0927-4aee-8da9-ca4e32ca3a8a/download/loca.json"
)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "bogota_localidades.geojson"


def signed_area(ring: list[list[float]]) -> float:
    area = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        area += (x1 * y2) - (x2 * y1)
    return area / 2.0


def esri_to_geojson(data: dict) -> dict:
    features = []
    for feat in data["features"]:
        attrs = feat["attributes"]
        rings = feat["geometry"]["rings"]
        outers = []
        for ring in rings:
            if ring[0] != ring[-1]:
                ring = ring + [ring[0]]
            if signed_area(ring) < 0:
                outers.append(ring)
        if not outers:
            outers = rings[:1]

        geometry = (
            {"type": "Polygon", "coordinates": [outers[0]]}
            if len(outers) == 1
            else {"type": "MultiPolygon", "coordinates": [[ring] for ring in outers]}
        )
        features.append(
            {
                "type": "Feature",
                "id": attrs["LocCodigo"],
                "properties": {
                    "codigo": attrs["LocCodigo"],
                    "localidad": attrs["LocNombre"].title(),
                    "localidad_upper": attrs["LocNombre"],
                    "area_m2": attrs["LocArea"],
                    "acto_administrativo": attrs["LocAAdmini"],
                },
                "geometry": geometry,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    with urlopen(URL, timeout=60) as resp:
        data = json.load(resp)
    geojson = esri_to_geojson(data)
    OUT.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"Escribi {OUT} con {len(geojson['features'])} localidades.")


if __name__ == "__main__":
    main()
