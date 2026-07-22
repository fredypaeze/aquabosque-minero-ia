"""Mapa coroplético de focos de calor activos (FIRMS 7d) por municipio."""
import json
from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
geo = json.loads((ROOT / "data/processed/municipios.geojson").read_text(encoding="utf-8"))
focos = {}
with (ROOT / "data/processed/fuego_municipal.csv").open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        focos[int(r["cod_mpio"])] = int(r["focos_7d"])

polys, vals = [], []
for feat in geo["features"]:
    ring = feat["geometry"]["coordinates"][0]
    polys.append([(p[0], p[1]) for p in ring])
    vals.append(focos.get(int(feat["properties"]["cod"]), 0))
vals = np.array(vals, dtype=float)

fig, ax = plt.subplots(figsize=(9, 10), dpi=130)
# base gris para municipios sin fuego
base = PolyCollection([p for p, v in zip(polys, vals) if v == 0],
                      facecolors="#EEF2EE", edgecolors="#DCE4DC", linewidths=0.2)
ax.add_collection(base)
# coropleta para municipios con fuego
hot_polys = [p for p, v in zip(polys, vals) if v > 0]
hot_vals = vals[vals > 0]
if len(hot_vals):
    vmax = np.percentile(hot_vals, 97)
    pc = PolyCollection(hot_polys, array=np.clip(hot_vals, 0, vmax),
                        cmap="YlOrRd", edgecolors="#B0453A", linewidths=0.25)
    ax.add_collection(pc)
    cb = fig.colorbar(pc, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Focos de calor activos (7 días)", fontsize=11)

ax.autoscale_view()
ax.set_aspect("equal")
ax.set_xlim(-79.5, -66.5)
ax.set_ylim(-4.6, 13.8)
ax.axis("off")
ax.set_title("Monitoreo satelital NRT — focos de calor activos por municipio\nNASA FIRMS · VIIRS + MODIS · últimos 7 días",
             fontsize=14, fontweight="bold", color="#12261A", loc="left")
fig.text(0.5, 0.02, f"AquaBosque · capa satelital near-real-time · {int((vals>0).sum())} municipios con fuego activo",
         ha="center", fontsize=9, color="#52645A")
out = ROOT / "outputs" / "jurado_2026" / "assets" / "20_mapa_focos_nrt.png"
out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(out, bbox_inches="tight", facecolor="white")
print("OK:", out, f"({int((vals>0).sum())} municipios con fuego)")
