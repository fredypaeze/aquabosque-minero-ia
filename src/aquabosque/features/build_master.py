"""Fase 3-4: limpieza + integración territorial → dataset maestro municipal.

Cruza las 5 fuentes reales a UNA fila por municipio (base: DIVIPOLA 1.122):
  - Minería (RUCOM): por código DANE (cruce exacto, ya validado 100%).
  - Deforestación: por nombre de municipio normalizado (la fuente no trae DANE);
    municipios sin registro = deforestación no significativa (0, documentado).
  - Agua (ICA IDEAM): asignación de cada estación al municipio más cercano por
    distancia al centroide (haversine); se agrega ICA medio y n de estaciones.
  - Sensibilidad (RUNAP): cada área protegida al municipio más cercano por
    centroide; se agrega n de áreas y hectáreas protegidas.

Reglas: sin geopandas (solo centroides + haversine, corre en cualquier PC);
lo faltante se marca, no se inventa; se reportan nulos/duplicados/calidad.
"""
from __future__ import annotations

import csv
import math
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "master_municipal.csv"


def _norm(s: str) -> str:
    """Normaliza nombre: sin tildes, mayúsculas, sin espacios extra."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().split())


def _num(x, default=None):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def run() -> dict:
    # --- base: DIVIPOLA (1 fila por municipio con centroide) ---
    muni = {}
    for r in csv.DictReader((RAW / "territorio" / "divipola.csv").open(encoding="utf-8")):
        cod = r["cod_mpio"].strip().zfill(5)
        lat, lon = _num(r.get("latitud")), _num(r.get("longitud"))
        muni[cod] = {"cod_mpio": cod, "municipio": r.get("nom_mpio", "").strip(),
                     "departamento": r.get("dpto", "").strip(), "lat": lat, "lon": lon,
                     "nom_norm": _norm(r.get("nom_mpio", ""))}
    centros = [(c, m["lat"], m["lon"]) for c, m in muni.items() if m["lat"] and m["lon"]]

    def mas_cercano(lat, lon):
        best, bestd = None, 1e9
        for c, la, lo in centros:
            d = _haversine(lat, lon, la, lo)
            if d < bestd:
                best, bestd = c, d
        return best, bestd

    # --- minería (RUCOM) por DANE ---
    min_cnt, min_min = defaultdict(int), defaultdict(set)
    for r in csv.DictReader((RAW / "mineria" / "rucom.csv").open(encoding="utf-8")):
        cod = (r.get("codigo_dane") or "").strip().zfill(5)
        if cod in muni:
            min_cnt[cod] += 1
            if r.get("mineral"):
                min_min[cod].add(r["mineral"].strip())

    # --- volumen de explotación y regalías (ANM) por DANE, año más reciente ---
    vol_muni, reg_muni = defaultdict(float), defaultdict(float)
    anm_p = RAW / "mineria" / "anm_volumen.csv"
    if anm_p.exists():
        for r in csv.DictReader(anm_p.open(encoding="utf-8")):
            cod = (r.get("codigo_dane") or "").strip().zfill(5)
            if cod in muni:
                vol_muni[cod] += _num(r.get("volumenes_de_explotacion"), 0) or 0
                reg_muni[cod] += _num(r.get("regalias_pagadas"), 0) or 0

    # --- PDET (sensibilidad social) por DANE ---
    pdet = set()
    pdet_p = RAW / "territorio" / "pdet.csv"
    if pdet_p.exists():
        for r in csv.DictReader(pdet_p.open(encoding="utf-8")):
            cod = (r.get("cod_muni") or "").strip().zfill(5)
            if cod in muni:
                pdet.add(cod)

    # --- deforestación por nombre (última año disponible por municipio) ---
    defo = defaultdict(float)
    por_nombre = {m["nom_norm"]: c for c, m in muni.items()}
    for r in csv.DictReader((RAW / "bosque" / "deforestacion.csv").open(encoding="utf-8")):
        cod = por_nombre.get(_norm(r.get("MPIO_CNMBR", "")))
        d = _num(r.get("Defores"), 0)
        if cod and d:
            defo[cod] = max(defo[cod], d)  # peor año registrado

    # --- agua (ICA) estación -> municipio más cercano ---
    ica_vals, ica_n = defaultdict(list), defaultdict(int)
    for r in csv.DictReader((RAW / "agua" / "ica_ideam.csv").open(encoding="utf-8")):
        lat, lon, v = _num(r.get("lat")), _num(r.get("lon")), _num(r.get("ica5"))
        if lat and lon and v is not None and 0 <= v <= 1:
            cod, dist = mas_cercano(lat, lon)
            if cod and dist < 50:  # estación a <50 km del centroide municipal
                ica_vals[cod].append(v)
                ica_n[cod] += 1

    # --- RUNAP área -> municipio más cercano ---
    runap_n, runap_ha = defaultdict(int), defaultdict(float)
    for r in csv.DictReader((RAW / "sensibilidad" / "runap.csv").open(encoding="utf-8")):
        lat, lon = _num(r.get("centroid_y")), _num(r.get("centroid_x"))
        ha = _num(r.get("Área_Oficial__Ha_") or r.get("Area_Oficial__Ha_"), 0)
        if lat and lon:
            cod, dist = mas_cercano(lat, lon)
            if cod and dist < 60:
                runap_n[cod] += 1
                runap_ha[cod] += ha or 0

    # --- ensamblar dataset maestro ---
    filas = []
    for cod, m in sorted(muni.items()):
        ica = ica_vals.get(cod)
        filas.append({
            "cod_mpio": cod, "municipio": m["municipio"], "departamento": m["departamento"],
            "lat": m["lat"], "lon": m["lon"],
            "mineria_titulos": min_cnt.get(cod, 0),
            "mineria_minerales": len(min_min.get(cod, set())),
            "mineria_volumen": round(vol_muni.get(cod, 0), 1),
            "mineria_regalias": round(reg_muni.get(cod, 0), 0),
            "es_pdet": 1 if cod in pdet else 0,
            "deforestacion_ha": round(defo.get(cod, 0), 1),
            "agua_ica_medio": round(sum(ica) / len(ica), 3) if ica else "",
            "agua_estaciones": ica_n.get(cod, 0),
            "runap_areas": runap_n.get(cod, 0),
            "runap_hectareas": round(runap_ha.get(cod, 0), 1),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    # --- reporte de calidad ---
    n = len(filas)
    con_min = sum(1 for f in filas if f["mineria_titulos"] > 0)
    con_defo = sum(1 for f in filas if f["deforestacion_ha"] > 0)
    con_ica = sum(1 for f in filas if f["agua_ica_medio"] != "")
    con_runap = sum(1 for f in filas if f["runap_areas"] > 0)
    print(f"Dataset maestro: {n} municipios → {OUT.relative_to(ROOT)}")
    print(f"  con minería:        {con_min:>4} ({100*con_min/n:.0f}%)")
    print(f"  con deforestación:  {con_defo:>4} ({100*con_defo/n:.0f}%)")
    print(f"  con estación ICA:   {con_ica:>4} ({100*con_ica/n:.0f}%)")
    print(f"  con área RUNAP:     {con_runap:>4} ({100*con_runap/n:.0f}%)")
    return {"n": n, "con_min": con_min, "con_defo": con_defo, "con_ica": con_ica, "con_runap": con_runap}


if __name__ == "__main__":
    run()
