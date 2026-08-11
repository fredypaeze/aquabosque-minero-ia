# -*- coding: utf-8 -*-
"""Deforestación REAL por municipio — cambio NDVI bi-temporal desde Sentinel-2 (sin GPU).

Descarga escenas Sentinel-2 L2A (STAC público Earth Search), calcula NDVI antes/después,
detecta pérdida de bosque y produce imágenes verdaderas + hectáreas REALES + procedencia.
NADA hardcodeado: cada cifra proviene de esta ejecución. La U-Net/IoU es un paso GPU aparte
(terramin) y NO se simula aquí.

Uso:
  python -m aquabosque.satelital.ndvi_change_real --cod 50350   # por código DANE de municipio
  python -m aquabosque.satelital.ndvi_change_real --lista        # corre el set de hotspots
"""
from __future__ import annotations
import argparse, json, datetime
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
GEO = ROOT / "data" / "processed" / "municipios.geojson"
OUT = ROOT / "outputs" / "satelital_ndvi"
STAC = "https://earth-search.aws.element84.com/v1"

# Parámetros (documentados, no mágicos)
WINDOW_KM = 12.0
FOREST_NDVI = 0.60          # umbral de "era bosque" en la fecha inicial
LOSS_DNDVI = -0.25          # caída de NDVI que marca pérdida
CLOUD_MAX = 30              # % nube máximo por escena
SCL_INVALIDOS = {3, 8, 9, 10, 11}   # sombra/nube/cirro/nieve (Scene Classification)
PIX_M = 10.0                # resolución (m)


def centroide_bbox(cod):
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    for f in geo["features"]:
        if str(f["properties"].get("cod")) == str(cod):
            xs = [p[0] for r in [f["geometry"]["coordinates"][0]] for p in r]
            ys = [p[1] for r in [f["geometry"]["coordinates"][0]] for p in r]
            clon, clat = sum(xs) / len(xs), sum(ys) / len(ys)
            nombre = (f["properties"].get("mpio") or f["properties"].get("municipio") or str(cod)).title()
            dkm = WINDOW_KM / 2
            dlat = dkm / 111.0
            dlon = dkm / (111.0 * np.cos(np.radians(clat)))
            return nombre, (clon - dlon, clat - dlat, clon + dlon, clat + dlat)
    raise SystemExit(f"cod {cod} no está en municipios.geojson")


def mejor_escena(client, bbox, t0, t1):
    items = list(client.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{t0}/{t1}",
                 query={"eo:cloud_cover": {"lt": CLOUD_MAX}}, max_items=12).items())
    return min(items, key=lambda i: i.properties.get("eo:cloud_cover", 100)) if items else None


def leer(item, bbox, bandas):
    """Lee cada banda a la MISMA grilla 10 m (la 1ª banda fija la forma; SCL 20m se remuestrea)."""
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds
    out = {}
    target = None
    for b in bandas:
        with rasterio.open(item.assets[b].href) as ds:
            wb = transform_bounds("EPSG:4326", ds.crs, *bbox)
            w = from_bounds(*wb, ds.transform)
            if target is None:
                target = (int(round(w.height)), int(round(w.width)))
            out[b] = ds.read(1, window=w, out_shape=target).astype("float32")
    return out


def stretch_rgb(r, g, b):
    def st(x):
        lo, hi = np.nanpercentile(x, 2), np.nanpercentile(x, 98)
        return np.clip((x - lo) / (hi - lo + 1e-6), 0, 1)
    return (np.dstack([st(r), st(g), st(b)]) * 255).astype("uint8")


def procesar(cod):
    from pystac_client import Client
    from PIL import Image
    nombre, bbox = centroide_bbox(cod)
    c = Client.open(STAC)
    a = mejor_escena(c, bbox, "2023-01-01", "2023-06-30")
    b = mejor_escena(c, bbox, "2025-09-01", "2026-04-30")
    if not (a and b):
        print(f"[{cod}] sin escenas suficientes (nube)"); return None
    da = leer(a, bbox, ["red", "green", "blue", "nir", "scl"])
    db = leer(b, bbox, ["red", "green", "blue", "nir", "scl"])
    H = min(da["red"].shape[0], db["red"].shape[0]); W = min(da["red"].shape[1], db["red"].shape[1])
    crop = lambda d: {k: v[:H, :W] for k, v in d.items()}
    da, db = crop(da), crop(db)
    ndvi = lambda d: (d["nir"] - d["red"]) / (d["nir"] + d["red"] + 1e-6)
    na, nb = ndvi(da), ndvi(db)
    valido = ~np.isin(da["scl"], list(SCL_INVALIDOS)) & ~np.isin(db["scl"], list(SCL_INVALIDOS))
    perdida = (na > FOREST_NDVI) & ((nb - na) < LOSS_DNDVI) & valido
    ha = float(perdida.sum()) * (PIX_M ** 2) / 10000.0
    cobertura_valida = float(valido.mean())

    d = OUT / str(cod); d.mkdir(parents=True, exist_ok=True)
    rgb_a = stretch_rgb(da["red"], da["green"], da["blue"])
    rgb_b = stretch_rgb(db["red"], db["green"], db["blue"])
    Image.fromarray(rgb_a).save(d / "antes.png")
    Image.fromarray(rgb_b).save(d / "despues.png")
    over = rgb_b.copy()
    over[perdida] = [220, 30, 30]   # pérdida en rojo sobre el "después"
    Image.fromarray(over).save(d / "cambio.png")

    res = {
        "cod": str(cod), "municipio": nombre, "ventana_km": WINDOW_KM, "bbox": [round(x, 4) for x in bbox],
        "hectareas_perdida": round(ha, 1),
        "escena_antes": {"id": a.id, "fecha": a.properties["datetime"][:10], "nube_pct": round(a.properties.get("eo:cloud_cover", -1), 1)},
        "escena_despues": {"id": b.id, "fecha": b.properties["datetime"][:10], "nube_pct": round(b.properties.get("eo:cloud_cover", -1), 1)},
        "umbrales": {"forest_ndvi": FOREST_NDVI, "loss_dndvi": LOSS_DNDVI},
        "cobertura_valida_pct": round(cobertura_valida * 100, 1),
        "metodo": "NDVI-change bi-temporal (sin GPU); máscara de nube SCL", "fuente": "Copernicus Sentinel-2 L2A vía Earth Search STAC",
        "computado_en": datetime.datetime.utcnow().isoformat() + "Z", "naturaleza": "OBSERVED_COMPUTED",
    }
    (d / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{cod}] {nombre}: {ha:.0f} ha · antes {res['escena_antes']['fecha']}({res['escena_antes']['nube_pct']}%) "
          f"→ después {res['escena_despues']['fecha']}({res['escena_despues']['nube_pct']}%) · válido {cobertura_valida*100:.0f}%")
    return res


# Municipios frente de deforestación (códigos DANE) — hotspots del trío insignia
HOTSPOTS = {"50350": "La Macarena", "50325": "Mapiripán", "18150": "Cartagena del Chairá",
            "18753": "San Vicente del Caguán", "99773": "Cumaribo"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cod"); ap.add_argument("--lista", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    cods = list(HOTSPOTS) if a.lista else ([a.cod] if a.cod else [])
    if not cods:
        print("uso: --cod <DANE> | --lista"); return
    idx = {}
    for cod in cods:
        try:
            r = procesar(cod)
            if r:
                idx[cod] = {"municipio": r["municipio"], "hectareas_perdida": r["hectareas_perdida"]}
        except Exception as e:
            print(f"[{cod}] ERROR: {e}")
    if idx:
        (OUT / "index.json").write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"index.json actualizado ({len(idx)} municipios).")


if __name__ == "__main__":
    main()
