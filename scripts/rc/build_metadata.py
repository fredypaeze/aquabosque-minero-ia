# -*- coding: utf-8 -*-
"""Genera metadata de trazabilidad (Sec 10/51/52): data_lineage, run_manifest, artifact_registry."""
import hashlib, json, subprocess, sys, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; META = ROOT / "metadata"; META.mkdir(exist_ok=True)

def H(p):
    p = ROOT / p
    return ("sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()) if p.exists() else None
def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()

# ---- FIELD-LEVEL LINEAGE (Sec 10) ----
lineage = [
    {"output_field": "eventos_remocion", "transformation": "count(regex remoción) groupby Localidad",
     "input_field": "Tipo de afectación, Localidad", "source_id": "IDIGER_BITACORA_V202608", "script": "scripts/rc/build_territorial_index.py"},
    {"output_field": "idx_territorial_obs", "transformation": "percentil(eventos_remoción+inundación)",
     "input_field": "eventos_remocion, eventos_inundacion", "source_id": "IDIGER_BITACORA_V202608", "script": "scripts/rc/build_territorial_index.py"},
    {"output_field": "p1", "transformation": "media diaria por localidad (t)",
     "input_field": "mm por estación", "source_id": "IDIGER_SAB_LLUVIA_V202608", "script": "scripts/rc/build_and_validate.py"},
    {"output_field": "p3/p7/p15", "transformation": "rolling_sum(window) BACKWARD terminando en t",
     "input_field": "p1", "source_id": "IDIGER_SAB_LLUVIA_V202608", "script": "scripts/rc/build_and_validate.py"},
    {"output_field": "pmax3", "transformation": "rolling_max(3) backward", "input_field": "p1",
     "source_id": "IDIGER_SAB_LLUVIA_V202608", "script": "scripts/rc/build_and_validate.py"},
    {"output_field": "wet7", "transformation": "rolling_count(p1>umbral,7) backward", "input_field": "p1",
     "source_id": "IDIGER_SAB_LLUVIA_V202608", "script": "scripts/rc/build_and_validate.py"},
    {"output_field": "y", "transformation": "fwd_target [t+1,t+3] (estrictamente futuro)", "input_field": "evento(remoción∪inundación)",
     "source_id": "IDIGER_BITACORA_V202608", "script": "scripts/rc/rc_lib.py::fwd_target"},
    {"output_field": "score_remocion (RETIRADO)", "transformation": "afín de bbox (INVÁLIDO, error 57km)",
     "input_field": "POT amenaza mm", "source_id": "IDECA_POT_AMENAZA_MM_URB_2021", "script": "scripts/11_prepare_bogota_remocion.py (DEPRECADO)"},
]
(META / "data_lineage.json").write_text(json.dumps({"note": "trazabilidad a nivel de campo (Sec 10)", "lineage": lineage}, ensure_ascii=False, indent=2), encoding="utf-8")

# ---- ARTIFACT REGISTRY (Sec 52) ----
RUN_ID = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_" + (git("rev-parse", "--short", "HEAD") or "nogit")
arts = {
    "gold_localidad_dia": "outputs/rc_v1/gold_localidad_dia.csv",
    "rc_metrics": "outputs/rc_v1/rc_metrics.json",
    "territorial_localidad": "data/processed/bogota_territorial_v1.csv",
    "territorial_upz": "data/processed/bogota_upz_territorial_v1.csv",
    "validation_results": "validation/validation_results.json",
    "source_registry": "metadata/source_registry.json",
    "config": "config/release_zoom_bogota_v1.yaml",
}
registry = [{"artifact_id": k, "run_id": RUN_ID, "path": v, "hash": H(v),
             "produced_by": "pipeline RC", "status": "current"} for k, v in arts.items()]
(META / "artifact_registry.json").write_text(json.dumps({"run_id": RUN_ID, "artifacts": registry}, ensure_ascii=False, indent=2), encoding="utf-8")

# ---- RUN MANIFEST (Sec 51) ----
manifest = {
    "RUN_ID": RUN_ID, "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "git_commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "python_version": sys.version.split()[0], "random_seed": 42,
    "config_hash": H("config/release_zoom_bogota_v1.yaml"),
    "source_manifest_hash": H("metadata/source_registry.json"),
    "input_hashes": {k: v for k, v in {
        "bitacora": H("data/raw/bogota/bitacora_emergencias.csv"),
        "sab_lluvia": H("data/raw/bogota/sab_lluvia_diaria.csv"),
        "sab_estaciones": H("data/raw/bogota/sab_estaciones.csv")}.items()},
    "output_hashes": {k: H(v) for k, v in arts.items()},
    "validation_status": json.loads((ROOT / "validation" / "validation_results.json").read_text())["OVERALL_RELEASE"]
        if (ROOT / "validation" / "validation_results.json").exists() else "unknown",
}
(META / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

print("metadata generada:")
print(f"  data_lineage.json     ({len(lineage)} campos)")
print(f"  artifact_registry.json ({len(registry)} artefactos, run {RUN_ID})")
print(f"  run_manifest.json     (validation_status = {manifest['validation_status']})")
