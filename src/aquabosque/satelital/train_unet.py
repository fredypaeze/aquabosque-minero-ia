"""U-Net (PyTorch) — segmentación bosque/no-bosque sobre Sentinel-2, en GPU L40S.

Entrena un U-Net compacto con las bandas Sentinel-2 (rojo, verde, NIR, SWIR) como
entrada y ESA WorldCover (clase 10 = árbol) como etiqueta débil. La etiqueta se
reproyecta al grid exacto de Sentinel-2. Corre en la GPU del Ministerio (soberano).

Honestidad: es el motor de deep learning de la capa satelital, entrenado sobre una
AOI como prueba de capacidad; un detector de deforestación de producción requiere
más AOIs y validación externa (Hansen / AT-D IDEAM).

Uso: python -m aquabosque.satelital.train_unet --sentinel data/raw/sentinel2/t1 \
        --worldcover data/raw/worldcover_aoi.tif --epochs 15 --out models/unet_bosque.pt
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import torch
from torch import nn


# ---------------- U-Net compacto ----------------
class DoubleConv(nn.Module):
    def __init__(self, ci, co):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(ci, co, 3, padding=1), nn.BatchNorm2d(co), nn.ReLU(inplace=True),
            nn.Conv2d(co, co, 3, padding=1), nn.BatchNorm2d(co), nn.ReLU(inplace=True))

    def forward(self, x):
        return self.net(x)


class UNet(nn.Module):
    def __init__(self, ci=4, base=32):
        super().__init__()
        self.d1 = DoubleConv(ci, base)
        self.d2 = DoubleConv(base, base * 2)
        self.d3 = DoubleConv(base * 2, base * 4)
        self.pool = nn.MaxPool2d(2)
        self.bott = DoubleConv(base * 4, base * 8)
        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.u3 = DoubleConv(base * 8, base * 4)
        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.u2 = DoubleConv(base * 4, base * 2)
        self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.u1 = DoubleConv(base * 2, base)
        self.out = nn.Conv2d(base, 1, 1)

    def forward(self, x):
        c1 = self.d1(x)
        c2 = self.d2(self.pool(c1))
        c3 = self.d3(self.pool(c2))
        b = self.bott(self.pool(c3))
        x = self.u3(torch.cat([self.up3(b), c3], 1))
        x = self.u2(torch.cat([self.up2(x), c2], 1))
        x = self.u1(torch.cat([self.up1(x), c1], 1))
        return self.out(x)


# ---------------- Datos ----------------
def cargar_datos(sentinel: Path, worldcover: Path):
    bandas = ["red", "green", "nir"]  # 10 m (SWIR es 20 m nativo, no alinea)
    arrs, prof = [], None
    for b in bandas:
        with rasterio.open(sentinel / f"{b}.tif") as s:
            arrs.append(s.read(1).astype("float32"))
            if prof is None:
                prof = s.profile.copy()
    X = np.stack(arrs) / 10000.0  # reflectancia aprox 0-1
    X = np.clip(X, 0, 1)
    # etiqueta WorldCover reproyectada al grid de Sentinel-2
    with rasterio.open(worldcover) as w:
        wc = np.zeros((prof["height"], prof["width"]), dtype="uint8")
        reproject(source=rasterio.band(w, 1), destination=wc,
                  src_transform=w.transform, src_crs=w.crs,
                  dst_transform=prof["transform"], dst_crs=prof["crs"],
                  resampling=Resampling.nearest)
    y = (wc == 10).astype("float32")  # clase 10 = árbol
    return X, y


def parches(X, y, size=256, stride=256):
    _, H, W = X.shape
    px, py = [], []
    for i in range(0, H - size + 1, stride):
        for j in range(0, W - size + 1, stride):
            xp = X[:, i:i + size, j:j + size]
            if (xp.sum(0) > 0).mean() < 0.6:   # descarta parches con mucho nodata
                continue
            px.append(xp)
            py.append(y[i:i + size, j:j + size][None])
    return np.asarray(px), np.asarray(py)


def iou(logits, target):
    p = (torch.sigmoid(logits) > 0.5).float()
    inter = (p * target).sum()
    union = ((p + target) >= 1).float().sum()
    return (inter / (union + 1e-6)).item()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sentinel", type=Path, required=True)
    ap.add_argument("--worldcover", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--out", type=Path, default=Path("models/unet_bosque.pt"))
    a = ap.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Dispositivo: {dev} · {torch.cuda.get_device_name(0) if dev=='cuda' else ''}")
    X, y = cargar_datos(a.sentinel, a.worldcover)
    px, py = parches(X, y, size=128, stride=128)
    print(f"Parches: {px.shape} · bosque medio {py.mean():.2f}")
    n = len(px)
    idx = np.random.RandomState(42).permutation(n)
    ntr = int(n * 0.8)
    tr, va = idx[:ntr], idx[ntr:]
    Xtr = torch.tensor(px[tr]); ytr = torch.tensor(py[tr])
    Xva = torch.tensor(px[va]).to(dev); yva = torch.tensor(py[va]).to(dev)

    # pos_weight = no-bosque/bosque (contrarresta el desbalance de clases)
    pos = float(ytr.mean()); pw = torch.tensor([(1 - pos) / max(pos, 1e-3)]).to(dev)
    model = UNet(ci=3).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pw)
    scaler = torch.cuda.amp.GradScaler(enabled=(dev == "cuda"))

    best = 0.0
    for ep in range(a.epochs):
        model.train()
        perm = torch.randperm(len(Xtr))
        tot = 0.0
        for k in range(0, len(Xtr), a.batch):
            b = perm[k:k + a.batch]
            xb = Xtr[b].to(dev); yb = ytr[b].to(dev)
            opt.zero_grad()
            with torch.cuda.amp.autocast(enabled=(dev == "cuda")):
                out = model(xb); loss = lossf(out, yb)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            tot += float(loss) * len(b)
        model.eval()
        with torch.no_grad():
            vio = iou(model(Xva), yva)
            tio = iou(model(Xtr[:16].to(dev)), ytr[:16].to(dev))
        best = max(best, vio)
        print(f"  época {ep+1:2d}/{a.epochs} · loss {tot/len(Xtr):.4f} · IoU train {tio:.3f} · IoU val {vio:.3f}")
    vio = best

    a.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "bandas": ["red", "green", "nir"]}, a.out)
    print(f"OK: pesos guardados en {a.out} · IoU val final {vio:.3f}")


if __name__ == "__main__":
    main()
