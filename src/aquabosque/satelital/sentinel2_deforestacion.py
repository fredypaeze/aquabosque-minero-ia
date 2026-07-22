"""Capa 2 satelital — Deforestación desde Sentinel-2 (deep learning, GPU L40S).

Implementación de referencia (soberana local): busca escenas Sentinel-2 L2A en
un STAC público, descarga a disco del Ministerio, y detecta pérdida de bosque por
dos vías: (a) cambio bi-temporal por índices (NDVI/NBR, sin GPU) y (b) segmentación
U-Net bosque/no-bosque (PyTorch, GPU). Agrega la pérdida a municipio para refrescar
`idx_deforestacion` de AquaBosque.

CORRE EN terramin/skymin (con GPU + rasterio/torch), no en tuxilo-server.
Ver docs/RUNBOOK_SATELITAL_L40S.md. Diseño honesto: los resultados solo se
presentan como operativos tras validación (IoU vs Hansen/AT-D IDEAM).

Uso:
    python -m aquabosque.satelital.sentinel2_deforestacion <search|change|train|infer|aggregate> [opts]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GEOJSON = ROOT / "data" / "processed" / "municipios.geojson"
STAC_URL = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"
# Bandas Earth Search v1 (COGs): 10 m salvo SWIR (20 m, se remuestrea).
BANDS = {"red": "red", "nir": "nir", "swir16": "swir16", "green": "green", "scl": "scl"}


# ----------------------------------------------------------------------------
# Utilidades AOI
# ----------------------------------------------------------------------------
def bbox_de_municipios(cods: list[int]) -> tuple[float, float, float, float]:
    """bbox lon/lat que envuelve los municipios pedidos (desde el geojson)."""
    geo = json.loads(GEOJSON.read_text(encoding="utf-8"))
    xs, ys = [], []
    cods_set = set(cods)
    for feat in geo["features"]:
        if int(feat["properties"]["cod"]) in cods_set:
            for lon, lat in feat["geometry"]["coordinates"][0]:
                xs.append(lon); ys.append(lat)
    if not xs:
        raise SystemExit("Ningún municipio del AOI encontrado en el geojson.")
    return (min(xs), min(ys), max(xs), max(ys))


# ----------------------------------------------------------------------------
# 1) Búsqueda + descarga (STAC → COG windowed a AOI)
# ----------------------------------------------------------------------------
def search(cods: list[int], t0: str, t1: str, max_cloud: int, out: Path,
           bbox_override: tuple[float, float, float, float] | None = None) -> None:
    from pystac_client import Client
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds

    bbox = bbox_override if bbox_override else bbox_de_municipios(cods)
    client = Client.open(STAC_URL)
    out.mkdir(parents=True, exist_ok=True)

    for etiqueta, rango in [("t0", t0), ("t1", t1)]:
        srch = client.search(collections=[COLLECTION], bbox=bbox, datetime=rango,
                             query={"eo:cloud_cover": {"lt": max_cloud}}, max_items=3,
                             sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}])
        items = list(srch.items())
        if not items:
            print(f"  {etiqueta}: sin escenas <{max_cloud}% nube en {rango}")
            continue
        item = items[0]
        print(f"  {etiqueta}: {item.id} (nube {item.properties.get('eo:cloud_cover'):.1f}%)")
        dst_dir = out / etiqueta
        dst_dir.mkdir(parents=True, exist_ok=True)
        for nombre, asset_key in BANDS.items():
            href = item.assets[asset_key].href
            with rasterio.open(href) as src:
                l, b, r, t = transform_bounds("EPSG:4326", src.crs, *bbox)
                win = from_bounds(l, b, r, t, src.transform)
                data = src.read(1, window=win)
                prof = src.profile.copy()
                prof.update(height=data.shape[0], width=data.shape[1],
                            transform=src.window_transform(win))
                with rasterio.open(dst_dir / f"{nombre}.tif", "w", **prof) as dstf:
                    dstf.write(data, 1)
        print(f"     bandas guardadas en {dst_dir}")


# ----------------------------------------------------------------------------
# 2) Baseline sin GPU: cambio bi-temporal NDVI → máscara de pérdida
# ----------------------------------------------------------------------------
def _ndvi(dir_: Path):
    import rasterio
    import numpy as np
    with rasterio.open(dir_ / "red.tif") as r, rasterio.open(dir_ / "nir.tif") as n:
        red = r.read(1).astype("float32"); nir = n.read(1).astype("float32")
        prof = r.profile
    ndvi = (nir - red) / (nir + red + 1e-6)
    return ndvi, prof


def change(in_: Path, out: Path, thr_ndvi: float) -> None:
    import rasterio
    import numpy as np
    out.mkdir(parents=True, exist_ok=True)
    ndvi0, prof = _ndvi(in_ / "t0")
    ndvi1, _ = _ndvi(in_ / "t1")
    h = min(ndvi0.shape[0], ndvi1.shape[0]); w = min(ndvi0.shape[1], ndvi1.shape[1])
    ndvi0, ndvi1 = ndvi0[:h, :w], ndvi1[:h, :w]
    # Bosque en t0 (NDVI alto) que cae por debajo del umbral de caída en t1.
    perdida = ((ndvi0 > 0.6) & ((ndvi0 - ndvi1) > thr_ndvi)).astype("uint8")
    prof.update(count=1, dtype="uint8", height=h, width=w)
    with rasterio.open(out / "perdida_ndvi.tif", "w", **prof) as dst:
        dst.write(perdida, 1)
    px_ha = (10 * 10) / 10000.0  # 10 m/px → ha
    print(f"OK change: pérdida ≈ {int(perdida.sum()) * px_ha:.1f} ha ({out/'perdida_ndvi.tif'})")


# ----------------------------------------------------------------------------
# 3) U-Net bosque/no-bosque (GPU). Etiquetas débiles: ESA WorldCover clase 10.
# ----------------------------------------------------------------------------
def _build_unet():
    import segmentation_models_pytorch as smp
    return smp.Unet(encoder_name="resnet34", encoder_weights="imagenet",
                    in_channels=4, classes=1, activation=None)


def train(in_: Path, worldcover: Path, epochs: int, batch: int, device: str, out: Path) -> None:
    import torch
    from torch import nn
    print(f"Entrenando U-Net (device={device}). Encoder resnet34, 4 canales (RGB+NIR).")
    model = _build_unet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    scaler = torch.cuda.amp.GradScaler(enabled=(device == "cuda"))
    # NOTA ingeniería: construir el DataLoader con parches 512×512 de las escenas
    # (in_/t0, in_/t1) y máscara de bosque desde WorldCover (clase 10 == árbol).
    # Se deja el bucle de referencia; enganchar el dataset real del AOI.
    loader = _worldcover_dataloader(in_, worldcover, batch)
    for ep in range(epochs):
        model.train(); tot = 0.0
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            with torch.cuda.amp.autocast(enabled=(device == "cuda")):
                loss = loss_fn(model(x), y)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            tot += float(loss)
        print(f"  época {ep+1}/{epochs} · loss {tot/max(1,len(loader)):.4f}")
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out)
    print(f"OK train: pesos en {out}")


def _worldcover_dataloader(in_: Path, worldcover: Path, batch: int):
    """Referencia: parches (RGB+NIR) → máscara bosque (WorldCover clase 10).
    Ingeniería completa el muestreo de tiles por ventana rasterio."""
    raise NotImplementedError(
        "Enganchar dataset de parches 512x512 desde las escenas del AOI + WorldCover. "
        "Ver docs/RUNBOOK_SATELITAL_L40S.md §3.3.")


def infer(in_: Path, weights: Path, device: str, out: Path) -> None:
    import torch, rasterio, numpy as np
    out.mkdir(parents=True, exist_ok=True)
    model = _build_unet().to(device)
    model.load_state_dict(torch.load(weights, map_location=device)); model.eval()

    def mascara_bosque(dir_: Path):
        import rasterio
        with rasterio.open(dir_/"red.tif") as r, rasterio.open(dir_/"green.tif") as g, \
             rasterio.open(dir_/"nir.tif") as n:
            red, green, nir = r.read(1), g.read(1), n.read(1); prof = r.profile
        # apilar 4 canales (aprox RGB+NIR; azul opcional). Normalizar reflectancia.
        import numpy as np
        x = np.stack([red, green, red, nir]).astype("float32") / 10000.0
        with torch.no_grad():
            t = torch.from_numpy(x)[None].to(device)
            prob = torch.sigmoid(model(t))[0, 0].cpu().numpy()
        return (prob > 0.5).astype("uint8"), prof

    m0, prof = mascara_bosque(in_/"t0")
    m1, _ = mascara_bosque(in_/"t1")
    h = min(m0.shape[0], m1.shape[0]); w = min(m0.shape[1], m1.shape[1])
    perdida = ((m0[:h,:w] == 1) & (m1[:h,:w] == 0)).astype("uint8")
    prof.update(count=1, dtype="uint8", height=h, width=w)
    with rasterio.open(out/"perdida_unet.tif", "w", **prof) as dst:
        dst.write(perdida, 1)
    px_ha = (10*10)/10000.0
    print(f"OK infer: pérdida U-Net ≈ {int(perdida.sum())*px_ha:.1f} ha ({out/'perdida_unet.tif'})")


# ----------------------------------------------------------------------------
# 5) Agregación a municipio (zonal) → CSV para AquaBosque
# ----------------------------------------------------------------------------
def aggregate(in_: Path, out: Path) -> None:
    import rasterio, numpy as np
    import geopandas as gpd
    from rasterio.features import geometry_mask
    tif = next(in_.glob("perdida_*.tif"))
    muni = gpd.read_file(GEOJSON)
    with rasterio.open(tif) as src:
        arr = src.read(1); transform = src.transform; crs = src.crs
    muni = muni.to_crs(crs)
    px_ha = (abs(transform.a) * abs(transform.e)) / 10000.0
    filas = []
    for _, row in muni.iterrows():
        try:
            m = geometry_mask([row.geometry], out_shape=arr.shape, transform=transform, invert=True)
        except Exception:
            continue
        ha = float((arr[m] == 1).sum()) * px_ha
        if ha > 0:
            filas.append({"cod_mpio": int(row["cod"]), "municipio": row.get("mpio", ""),
                          "ha_perdida_s2": round(ha, 2)})
    import csv
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["cod_mpio", "municipio", "ha_perdida_s2"])
        w.writeheader(); w.writerows(sorted(filas, key=lambda r: -r["ha_perdida_s2"]))
    print(f"OK aggregate: {len(filas)} municipios con pérdida → {out}")


# ----------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description="Capa 2 Sentinel-2 deforestación (L40S).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("--cods", default=""); s.add_argument("--t0", required=True)
    s.add_argument("--t1", required=True); s.add_argument("--max-cloud", type=int, default=20)
    s.add_argument("--bbox", default="", help="lon_min,lat_min,lon_max,lat_max (opcional, anula --cods)")
    s.add_argument("--out", type=Path, default=ROOT/"data/raw/sentinel2")
    c = sub.add_parser("change"); c.add_argument("--in", dest="in_", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True); c.add_argument("--thr-ndvi", type=float, default=0.15)
    t = sub.add_parser("train"); t.add_argument("--in", dest="in_", type=Path, required=True)
    t.add_argument("--worldcover", type=Path, required=True); t.add_argument("--epochs", type=int, default=40)
    t.add_argument("--batch", type=int, default=16); t.add_argument("--device", default="cuda")
    t.add_argument("--out", type=Path, default=ROOT/"models/unet_bosque.pt")
    i = sub.add_parser("infer"); i.add_argument("--in", dest="in_", type=Path, required=True)
    i.add_argument("--weights", type=Path, required=True); i.add_argument("--device", default="cuda")
    i.add_argument("--out", type=Path, required=True)
    a = sub.add_parser("aggregate"); a.add_argument("--in", dest="in_", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    if args.cmd == "search":
        bbox = tuple(float(v) for v in args.bbox.split(",")) if args.bbox else None
        cods = [int(x) for x in args.cods.split(",")] if args.cods else []
        search(cods, args.t0, args.t1, args.max_cloud, args.out, bbox_override=bbox)
    elif args.cmd == "change":
        change(args.in_, args.out, args.thr_ndvi)
    elif args.cmd == "train":
        train(args.in_, args.worldcover, args.epochs, args.batch, args.device, args.out)
    elif args.cmd == "infer":
        infer(args.in_, args.weights, args.device, args.out)
    elif args.cmd == "aggregate":
        aggregate(args.in_, args.out)


if __name__ == "__main__":
    main()
