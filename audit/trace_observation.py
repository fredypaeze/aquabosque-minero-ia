# -*- coding: utf-8 -*-
"""Comando de TRAZABILIDAD puntual (Sec 41/64/82) — reconstruye la genealogía completa.

Todo valor visible debe recorrer: valor → transformación → registros fuente → SOURCE_ID → URL/fecha.

Uso:
  # traza el índice territorial descriptivo de una localidad
  ./venv/bin/python audit/trace_observation.py --territorial "Ciudad Bolívar"
  # traza el vector de features de lluvia de una localidad-día
  ./venv/bin/python audit/trace_observation.py --feature --cod 19 --fecha 2024-05-10
"""
import argparse, hashlib, json, re, sys, unicodedata
from pathlib import Path
import numpy as np, pandas as pd, yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config" / "release_zoom_bogota_v1.yaml").read_text(encoding="utf-8"))
REG = json.loads((ROOT / "metadata" / "source_registry.json").read_text(encoding="utf-8")) if (ROOT / "metadata" / "source_registry.json").exists() else {"sources": []}

def norm(s):
    s = str(s).strip().upper()
    return re.sub(r"\s+", " ", "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"))
def src(sid): return next((s for s in REG["sources"] if s["SOURCE_ID"] == sid), {})

def trace_territorial(nombre):
    bit = ROOT / CFG["data"]["bronze"]["bitacora"]
    df = pd.read_csv(bit, sep=";", encoding="latin-1", skiprows=2, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df["fecha"] = pd.to_datetime(df["Fecha reporte"], format="%d/%m/%Y", errors="coerce")
    df["loc_n"] = df["Localidad"].astype(str).str.replace(r"^\s*\d+\s*", "", regex=True).map(norm)
    d = df[df["loc_n"] == norm(nombre)].copy()
    rx = CFG["target"]["event_types_included_regex"]
    d["incluido"] = d["Tipo de afectación"].astype(str).str.contains(rx, case=False, regex=True)
    ter = pd.read_csv(ROOT / "data" / "processed" / "bogota_territorial_v1.csv")
    row = ter[ter["localidad"].map(norm) == norm(nombre)]
    print(f"== TRAZA · índice territorial · {nombre} ==")
    if len(row):
        r = row.iloc[0]
        print(f"VALOR: idx_territorial_obs={r['idx_territorial_obs']}  (eventos remoción={int(r['eventos_remocion'])}, inundación={int(r['eventos_inundacion'])})")
    print("FÓRMULA: idx = percentil(eventos_remoción+inundación entre las 20 localidades)  [scripts/rc/build_territorial_index.py]")
    print(f"REGISTROS FUENTE: {int(d['incluido'].sum())} emergencias incluidas (de {len(d)} de la localidad)")
    print("  muestra (fecha · tipo):")
    for _, e in d[d["incluido"]].head(6).iterrows():
        print(f"    {e['fecha'].date() if pd.notna(e['fecha']) else '?'} · {str(e['Tipo de afectación'])[:48]}")
    s = src("IDIGER_BITACORA_V202608")
    print(f"SOURCE_ID: IDIGER_BITACORA_V202608 · {s.get('entidad')} · {s.get('url')}")
    print(f"  bronze hash: {s.get('file_hash')} · geocodificación: IDIGER (localidad) · CRS: N/A (error 0)")
    print("NATURALEZA: OBSERVED_DESCRIPTIVO (no probabilidad, no pronóstico).")

def trace_feature(cod, fecha):
    cod = str(cod).zfill(2); f = pd.Timestamp(fecha)
    # estaciones de la localidad
    est = pd.read_csv(ROOT / CFG["data"]["bronze"]["sab_estaciones"], sep=";", encoding="latin-1", skiprows=2, low_memory=False)
    est.columns = [c.strip() for c in est.columns]
    susc = pd.read_csv(ROOT / CFG["data"]["bronze"]["susceptibilidad"], dtype={"codigo": str})
    name2cod = {norm(r.localidad): str(r.codigo).zfill(2) for r in susc.itertuples()}
    est["cod"] = est["Localidad"].map(lambda x: name2cod.get(norm(x)))
    est_loc = est[est["cod"] == cod]["Estación"].map(lambda s: re.sub(r"(?i)^estaci[oó]n\s+", "", str(s)).strip()).tolist()
    rain = pd.read_csv(ROOT / CFG["data"]["bronze"]["sab_lluvia"], sep=";", encoding="latin-1", skiprows=2, low_memory=False)
    rain = rain.rename(columns={rain.columns[0]: "fecha"}); rain["fecha"] = pd.to_datetime(rain["fecha"], errors="coerce")
    def val(x):
        try:
            s = str(x); return float(s.replace(".", "").replace(",", ".")) if s.count(",") else float(s.replace(",", "."))
        except Exception: return np.nan
    cols_est = [c for c in rain.columns if norm(c) in {norm(e) for e in est_loc}]
    win = rain[(rain["fecha"] <= f) & (rain["fecha"] > f - pd.Timedelta(days=15))].copy()
    for c in cols_est: win[c] = win[c].map(val)
    daily = win[["fecha"] + cols_est].set_index("fecha")[cols_est].mean(axis=1)  # media localidad por día
    p = lambda k: round(float(daily.tail(k).sum()), 2)
    print(f"== TRAZA · features de lluvia · localidad {cod} · {f.date()} (cierre de t) ==")
    print(f"ESTACIONES de la localidad: {est_loc}  (usadas: {cols_est or 'ninguna → respaldo media-ciudad'})")
    print("FEATURES (ventanas hacia atrás, ≤ t):")
    print(f"  p1={p(1)}  p3={p(3)}  p7={p(7)}  p15={p(15)}  (mm; suma de la media diaria por localidad)")
    print("  código: scripts/rc/build_and_validate.py (rolling backward) · rc_lib.py")
    s = src("IDIGER_SAB_LLUVIA_V202608")
    print(f"SOURCE_ID: IDIGER_SAB_LLUVIA_V202608 · {s.get('entidad')} · bronze hash {s.get('file_hash')}")
    print("REGLA TEMPORAL: features con fecha ≤ t; target sería [t+1,t+3] (no incluido aquí).")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--territorial"); ap.add_argument("--feature", action="store_true")
    ap.add_argument("--cod"); ap.add_argument("--fecha")
    a = ap.parse_args()
    if a.territorial:
        trace_territorial(a.territorial)
    elif a.feature and a.cod and a.fecha:
        trace_feature(a.cod, a.fecha)
    else:
        print("uso: --territorial <localidad>  |  --feature --cod <NN> --fecha <YYYY-MM-DD>"); sys.exit(1)
