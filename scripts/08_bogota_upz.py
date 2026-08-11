# -*- coding: utf-8 -*-
"""AquaBosque · Zoom Bogotá — capa UPZ (Unidades de Planeamiento Zonal).

Baja la geometría oficial de las UPZ de Bogotá (waserver Secretaría de Gobierno,
capa UPZ del Mapa_Base — trae LOCNOMBRE/LOCCODIGO por UPZ), la une al perfil de
amenaza real de cada localidad (bogota_zoom.csv) y produce una capa a resolución
UPZ (~112) para el simulador de alerta temprana orientado a IDIGER.

Diferenciación intra-localidad: modulación por gradiente oriente–occidente
(Cerros Orientales ↔ río Bogotá / humedales), geografía válida de la ciudad.
El cruce fino con las capas IDIGER de amenaza por UPZ (IDECA gestionriesgos) queda
identificado como siguiente paso.

Salidas:
  data/processed/bogota_upz.geojson   (id = codigo UPZ; geometría simplificada)
  data/processed/bogota_upz.csv       (perfil por UPZ para el tablero)
"""
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
ZOOM = PROC / "bogota_zoom.csv"

WASERVER = ("https://mapas.gobiernobogota.gov.co/waserver/rest/services/"
            "Mapa_Base/MapServer/8/query")


def norm(s):
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def fetch_upz():
    params = {"where": "1=1", "outFields": "UPLCODIGO,UPLNOMBRE,LOCNOMBRE,LOCCODIGO,UPLTIPO",
              "outSR": "4326", "returnGeometry": "true", "f": "geojson"}
    url = WASERVER + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def round_coords(obj, nd=4):
    """Redondea coordenadas (reduce tamaño) sin dependencias geoespaciales."""
    if isinstance(obj, (int, float)):
        return round(obj, nd)
    if isinstance(obj, list):
        return [round_coords(x, nd) for x in obj]
    return obj


def iter_points(geom):
    """Genera todos los (lon,lat) de un Polygon/MultiPolygon para el centroide."""
    t = geom["type"]
    coords = geom["coordinates"]
    if t == "Polygon":
        rings = coords
    elif t == "MultiPolygon":
        rings = [ring for poly in coords for ring in poly]
    else:
        rings = []
    for ring in rings:
        for pt in ring:
            yield pt[0], pt[1]


def centroid(geom):
    xs, ys = [], []
    for x, y in iter_points(geom):
        xs.append(x); ys.append(y)
    return (sum(xs) / len(xs), sum(ys) / len(ys)) if xs else (None, None)


def clamp01(v):
    return max(0.0, min(1.0, v))


def upz_eventos():
    """Amenaza OBSERVADA por UPZ = registro real de emergencias IDIGER (Bitácora).
    Cruce fino UPZ↔amenaza: usa un CSV curado pequeño si existe; si no, lo calcula del
    crudo (78 MB, se descarga desde la fuente oficial si falta) y lo guarda."""
    cache = PROC / "bogota_upz_eventos.csv"
    if cache.exists():
        ev = pd.read_csv(cache, dtype={"cod_num": str})
    else:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import _bogota_sources
        raw = _bogota_sources.fetch_all(ROOT / "data" / "raw" / "bogota")
        b = pd.read_csv(raw / "bitacora_emergencias.csv", sep=";", encoding="latin-1",
                        skiprows=2, low_memory=False)
        b.columns = [c.strip() for c in b.columns]
        b["cod_num"] = b["Upz"].astype(str).str.extract(r"^\s*(\d+)")
        t = b["Tipo de afectación"].astype(str)
        b["rem"] = t.str.contains("emoci|eslizam|talud|ladera", case=False, regex=True)
        b["inu"] = t.str.contains("nundaci|ncharca|negaci", case=False, regex=True)
        ev = (b.dropna(subset=["cod_num"]).groupby("cod_num")
              .agg(eventos_remocion=("rem", "sum"), eventos_inundacion=("inu", "sum")).reset_index())
        ev.to_csv(cache, index=False, encoding="utf-8")
    d = {r.cod_num: (int(r.eventos_remocion), int(r.eventos_inundacion)) for r in ev.itertuples()}
    p90r = max(1.0, np.percentile([v[0] for v in d.values() if v[0] > 0] or [1], 90))
    p90i = max(1.0, np.percentile([v[1] for v in d.values() if v[1] > 0] or [1], 90))
    return d, p90r, p90i


def main():
    zoom = pd.read_csv(ZOOM, dtype={"codigo": str})
    zoom["loc_n"] = zoom["localidad"].map(norm)
    by_loc = {r["loc_n"]: r for _, r in zoom.iterrows()}

    gj = fetch_upz()
    feats = gj.get("features", [])
    print(f"UPZ descargadas: {len(feats)}")

    ev_upz, p90_rem, p90_inu = upz_eventos()
    print(f"Amenaza observada IDIGER: {len(ev_upz)} UPZ con eventos "
          f"(p90 remoción {p90_rem:.0f}, inundación {p90_inu:.0f})")

    out_feats, rows = [], []
    sin_match = []
    for f in feats:
        p = f["properties"]
        cod = p.get("UPLCODIGO")
        nombre = str(p.get("UPLNOMBRE", "")).title()
        loc_n = norm(p.get("LOCNOMBRE", ""))
        loc_n = {"CANDELARIA": "LA CANDELARIA"}.get(loc_n, loc_n)
        base = by_loc.get(loc_n)
        if base is None:
            sin_match.append(p.get("LOCNOMBRE"))
            continue

        base_rem = float(base["score_remocion"])
        base_agu = float(base["score_agua"])
        base_fue = float(base["score_fuego_estructural"])
        base_ope = float(base["score_operativo"])

        # CRUCE FINO UPZ ↔ amenaza IDIGER: la susceptibilidad de la UPZ mezcla el perfil
        # físico de su localidad (POT) con la amenaza OBSERVADA — nº real de emergencias de
        # remoción/inundación en esa UPZ (Bitácora IDIGER), normalizado al p90 de la ciudad.
        cod_num = str(cod).replace("UPZ", "")
        n_rem, n_inu = ev_upz.get(cod_num, (0, 0))   # sin registro ⇒ 0 eventos observados
        o_rem = min(n_rem / p90_rem, 1.0)
        o_inu = min(n_inu / p90_inu, 1.0)
        # susceptibilidad = mitad físico de la localidad (POT) + mitad amenaza observada (IDIGER)
        rem = clamp01(0.5 * base_rem + 0.5 * o_rem)
        agu = clamp01(0.5 * base_agu + 0.5 * o_inu)
        fue = base_fue
        ope = base_ope

        indice = round(0.40 * rem + 0.30 * agu + 0.20 * fue + 0.10 * ope, 3)
        nivel = ("Crítico" if indice >= 0.66 else "Alto" if indice >= 0.45
                 else "Medio" if indice >= 0.25 else "Bajo")

        f["geometry"]["coordinates"] = round_coords(f["geometry"]["coordinates"], 4)
        f["id"] = cod
        f["properties"] = {"codigo": cod, "upz": nombre, "localidad": base["localidad"]}
        f.pop("_cx", None)
        out_feats.append(f)

        rows.append({
            "codigo": cod, "upz": nombre, "localidad": base["localidad"],
            "localidad_codigo": base["codigo"],
            "score_remocion": round(rem, 3), "score_agua": round(agu, 3),
            "score_fuego_estructural": round(fue, 3), "score_operativo": round(ope, 3),
            "indice_presion_ecoterritorial_bogota": indice, "nivel": nivel,
            "lluvia_72h_mm": int(base["lluvia_72h_mm"]),
            "incidentes_7d": int(base["incidentes_7d"]),
            "eventos_remocion": int(n_rem or 0), "eventos_inundacion": int(n_inu or 0),
        })

    gj_out = {"type": "FeatureCollection", "features": out_feats}
    (PROC / "bogota_upz.geojson").write_text(
        json.dumps(gj_out, ensure_ascii=False), encoding="utf-8")
    df = pd.DataFrame(rows).sort_values("indice_presion_ecoterritorial_bogota", ascending=False)
    df.to_csv(PROC / "bogota_upz.csv", index=False, encoding="utf-8")

    print(f"UPZ con match de localidad: {len(rows)}  |  sin match: {len(sin_match)} {set(sin_match)}")
    print(f"UPZ por localidad (top): ")
    print(df.groupby('localidad').size().sort_values(ascending=False).head(8).to_string())
    print(f"\nGeoJSON: {(PROC/'bogota_upz.geojson').stat().st_size//1024} KB  |  CSV filas: {len(df)}")
    print("\nTop 8 UPZ por índice:")
    print(df.head(8)[["upz", "localidad", "indice_presion_ecoterritorial_bogota", "nivel"]].to_string(index=False))


if __name__ == "__main__":
    main()
