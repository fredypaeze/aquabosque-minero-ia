# -*- coding: utf-8 -*-
"""Zoom Bogotá V1 — Índice territorial DESCRIPTIVO (Opción A, CRS-safe).

Reemplaza los scores POT afín-CRS-inválidos por la DENSIDAD HISTÓRICA OBSERVADA de
emergencias, geocodificada por IDIGER en la propia Bitácora (campo Localidad/UPZ).
→ Espacialmente correcto por construcción (sin transformación de coordenadas).

Naturaleza del dato: OBSERVED (histórico), DESCRIPTIVO — NO es una probabilidad predictiva
ni una susceptibilidad física. Útil para PRIORIZACIÓN. Limitación: sesgo de reporte
(zonas más pobladas/monitoreadas reportan más).

Salidas:
  data/processed/bogota_territorial_v1.csv       (20 localidades)
  data/processed/bogota_upz_territorial_v1.csv   (UPZ)
  outputs/rc_v1/territorial_index_validation.json
"""
import json, re, unicodedata, hashlib
from pathlib import Path
import numpy as np, pandas as pd, yaml

ROOT = Path(__file__).resolve().parents[2]
CFG = yaml.safe_load((ROOT / "config" / "release_zoom_bogota_v1.yaml").read_text(encoding="utf-8"))
OUT = ROOT / "outputs" / "rc_v1"; OUT.mkdir(parents=True, exist_ok=True)
BIT = ROOT / CFG["data"]["bronze"]["bitacora"]

def norm(s):
    s = str(s).strip().upper()
    return re.sub(r"\s+", " ", "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"))

# ---- BRONZE (con hash para trazabilidad) ----
raw = BIT.read_bytes()
BIT_HASH = hashlib.sha256(raw).hexdigest()
bit = pd.read_csv(BIT, sep=";", encoding="latin-1", skiprows=2, low_memory=False)
bit.columns = [c.strip() for c in bit.columns]
bit["fecha"] = pd.to_datetime(bit["Fecha reporte"], format="%d/%m/%Y", errors="coerce")
bit = bit.dropna(subset=["fecha"])
bit["cod"] = bit["Localidad"].astype(str).str.extract(r"^\s*(\d+)")
bit["upz_cod"] = bit["Upz"].astype(str).str.extract(r"^\s*(\d+)")
t = bit["Tipo de afectación"].astype(str)
bit["remocion"] = t.str.contains("emoci|eslizam|talud|ladera", case=False, regex=True)
bit["inundacion"] = t.str.contains("nundaci|ncharca|negaci|venida|creciente", case=False, regex=True)

FECHA_MIN, FECHA_MAX = bit["fecha"].min(), bit["fecha"].max()

def agg(df, key):
    d = df.dropna(subset=[key])
    g = d.groupby(key).agg(
        eventos_remocion=("remocion", "sum"),
        eventos_inundacion=("inundacion", "sum"),
        eventos_total=("remocion", "size"),
        dias_remocion=("fecha", lambda s: d.loc[s.index][d.loc[s.index]["remocion"]]["fecha"].nunique()),
    ).reset_index()
    return g

def indexer(s):
    """Índice descriptivo [0,1] por percentil (prioridad relativa). Documentado."""
    s = s.astype(float)
    return s.rank(pct=True).round(3)

# ---- LOCALIDAD ----
susc = pd.read_csv(ROOT / CFG["data"]["bronze"]["susceptibilidad"], dtype={"codigo": str})
susc["cod"] = susc["codigo"].str.zfill(2)
loc = agg(bit.assign(cod=bit["cod"].str.zfill(2)).dropna(subset=["cod"]), "cod")
loc = susc[["cod", "localidad"]].merge(loc, on="cod", how="left").fillna(0)
loc["idx_remocion_obs"] = indexer(loc["eventos_remocion"])
loc["idx_inundacion_obs"] = indexer(loc["eventos_inundacion"])
loc["idx_territorial_obs"] = indexer(loc["eventos_remocion"] + loc["eventos_inundacion"])
loc["fuente"] = "IDIGER Bitácora (geocodificación oficial por localidad)"
loc["naturaleza"] = "OBSERVED_DESCRIPTIVE"
loc = loc.sort_values("idx_territorial_obs", ascending=False)
loc.to_csv(ROOT / "data" / "processed" / "bogota_territorial_v1.csv", index=False, encoding="utf-8")

# ---- UPZ ----
upz = agg(bit, "upz_cod")
upz["codigo"] = "UPZ" + upz["upz_cod"].astype(str)
upz["idx_remocion_obs"] = indexer(upz["eventos_remocion"])
upz["idx_inundacion_obs"] = indexer(upz["eventos_inundacion"])
upz["idx_territorial_obs"] = indexer(upz["eventos_remocion"] + upz["eventos_inundacion"])
upz["naturaleza"] = "OBSERVED_DESCRIPTIVE"
upz.to_csv(ROOT / "data" / "processed" / "bogota_upz_territorial_v1.csv", index=False, encoding="utf-8")

# ---- VALIDACIÓN ----
val = {
    "fuente": "IDIGER Bitácora de Emergencias", "bronze_sha256": BIT_HASH[:16],
    "naturaleza": "OBSERVED historical emergency density (DESCRIPTIVO, no predictivo)",
    "geocodificacion": "campo Localidad/UPZ asignado por IDIGER (sin transformación CRS)",
    "periodo": [str(FECHA_MIN.date()), str(FECHA_MAX.date())],
    "eventos_remocion_total": int(bit["remocion"].sum()), "eventos_inundacion_total": int(bit["inundacion"].sum()),
    "cobertura_upz_pct": round(bit["upz_cod"].notna().mean() * 100, 1),
    "top5_remocion": loc.nlargest(5, "eventos_remocion")[["localidad", "eventos_remocion"]].values.tolist(),
    "top5_inundacion": loc.nlargest(5, "eventos_inundacion")[["localidad", "eventos_inundacion"]].values.tolist(),
    "sanidad_fisica": "remoción debe concentrarse en cerros (Ciudad Bolívar/Usme/San Cristóbal/Rafael Uribe/Chapinero)",
    "limitacion": "sesgo de reporte (exposición/monitoreo); refleja lo ocurrido/reportado, no susceptibilidad física ni pronóstico",
    "error_crs": "0 (geocodificación oficial; sin el afín de 57 km del método POT anterior)",
}
(OUT / "territorial_index_validation.json").write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding="utf-8")

print("== ÍNDICE TERRITORIAL DESCRIPTIVO (IDIGER, CRS-safe) ==")
print(f"Período: {val['periodo'][0]} → {val['periodo'][1]}  | remoción {val['eventos_remocion_total']} · inundación {val['eventos_inundacion_total']}")
print(f"Cobertura UPZ: {val['cobertura_upz_pct']}%  | UPZ con eventos: {len(upz)}")
print("\nTop localidades por remoción (debe ser cerros):")
print(loc.nlargest(6, "eventos_remocion")[["localidad", "eventos_remocion", "eventos_inundacion", "idx_territorial_obs"]].to_string(index=False))
print("\nTop UPZ por remoción:")
print(upz.nlargest(6, "eventos_remocion")[["codigo", "eventos_remocion", "eventos_inundacion"]].to_string(index=False))
print("\nSalidas: data/processed/bogota_territorial_v1.csv + bogota_upz_territorial_v1.csv + validation json")
