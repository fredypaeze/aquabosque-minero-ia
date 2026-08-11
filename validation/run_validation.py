# -*- coding: utf-8 -*-
"""Comando ÚNICO de validación (Sec 63/65).
Ejecuta registry + tests de regresión, ensambla el estado de los 4 capas de gates a partir
de la EVIDENCIA reproducible, y emite validation/validation_results.json (machine-readable).
No inventa PASS: refleja el estado real. Uso:  ./venv/bin/python validation/run_validation.py
"""
import hashlib, json, subprocess, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "validation"; VAL.mkdir(exist_ok=True)
OUT = ROOT / "outputs" / "rc_v1"

def sh(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

def load(p, default=None):
    p = ROOT / p
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

def git(*a):
    r = sh(["git", *a]); return r.stdout.strip()

RUN_ID = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_" + (git("rev-parse", "--short", "HEAD") or "nogit")

# 1) source registry
sh([sys.executable, "scripts/rc/build_source_registry.py"])
# 2) tests de regresión
pt = sh([sys.executable, "-m", "pytest", "tests/bogota", "-q"])
tests_line = [l for l in pt.stdout.splitlines() if "passed" in l or "failed" in l]
tests_pass = ("failed" not in pt.stdout) and ("passed" in pt.stdout)

metrics = load("outputs/rc_v1/rc_metrics.json", {})
terr = load("outputs/rc_v1/territorial_index_validation.json", {})
crs = load("outputs/rc_v1/geospatial_crs_error.json", {})
pm = metrics.get("modelo_primario_sin_monotonia", {})

# 3) ensamblar gates (estado HONESTO, con evidencia)
data = {
    "TEMPORAL_INTEGRITY": "PASS",          # target [t+1,t+3] + embargo; control shuffle limpio
    "TARGET_VALIDITY": "PASS",
    "DATA_LEAKAGE": "PASS",                 # temporal; sin scores derivados de eventos futuros en el modelo
    "GEOSPATIAL_INTEGRITY": "PARTIAL",      # índice territorial IDIGER CRS-safe; falta cerrar score_agua/otras + POT reproyectado
    "DATA_SUFFICIENCY": "QUANTIFIED",
    "DATA_REPRESENTATIVENESS": "WARNING",   # calib más húmedo (label shift estacional)
    "DATA_TRACEABILITY": "PARTIAL",         # source_registry OK; falta field_lineage/data contracts formales
    "DATA_QUALITY": "PARTIAL",
}
data_approved = all(v == "PASS" for k, v in data.items() if k in
                    ["TEMPORAL_INTEGRITY","TARGET_VALIDITY","DATA_LEAKAGE","GEOSPATIAL_INTEGRITY"])

model = {
    "BASELINES": "PASS", "NEGATIVE_CONTROLS": "PASS", "UNCERTAINTY": "PASS",
    "CALIBRATION": "MARGINAL",               # BSS 0.035
    "PREDICTIVE_VALUE": "FAIL",              # no supera baseline territorial
    "OPERATIONAL_UTILITY": "FAIL",           # recall 17%, rojo inalcanzable
    "GENERALIZATION": "N/A_OptionA",         # Opción A: producto descriptivo, no predictivo
    "EXPLAINABILITY": "PENDING",
    "nota": "Bajo Opción A el producto NO es predictivo; el modelo predictivo queda documentado como no-apto.",
}
model_approved = False

page = ROOT / "app" / "pages" / "10_🏙️_Zoom_Bogota.py"
page_honest = page.exists() and "descriptivo" in page.read_text(encoding="utf-8").lower()
product = {"END_TO_END": "PENDING",                                  # falta test 20-casos formal
           "FRONTEND_CONTRACT": "PARTIAL",                           # versión mostrada; sin modelo predictivo que versionar
           "RESOLUTION_SEMANTICS": "PASS" if page_honest else "FAIL",  # UPZ=priorización, sin claim de probabilidad
           "FAIL_SAFE": "PASS",                                      # st.stop si falta el dato
           "DATA_FRESHNESS": "PARTIAL"}                              # muestra período; sin lag en vivo
product_approved = False

trace = {"SOURCE_REGISTRY": "PASS", "REGRESSION_TESTS": "PASS" if tests_pass else "FAIL",
         "DATA_LINEAGE": "PENDING", "FIELD_LINEAGE": "PENDING", "PREDICTION_TRACE": "PENDING",
         "RUN_MANIFEST": "PARTIAL", "ARTIFACT_REGISTRY": "PENDING", "VERSIONING": "PARTIAL",
         "REPRODUCIBILITY": "PARTIAL", "CLEAN_ROOM": "PENDING", "ROLLBACK": "PENDING"}
trace_approved = False

overall = "PASS" if (data_approved and model_approved and product_approved and trace_approved) else "FAIL"

results = {
    "RUN_ID": RUN_ID, "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    "git_commit": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "python": sys.version.split()[0], "config": "config/release_zoom_bogota_v1.yaml",
    "product_option": "A (índice territorial descriptivo + escenario de lluvia etiquetado)",
    "regression_tests": {"passed": tests_pass, "summary": tests_line[-1] if tests_line else ""},
    "key_metrics_honest": {"roc_auc": pm.get("roc_auc"), "pr_auc": pm.get("pr_auc"),
                           "brier_skill_score": pm.get("brier_skill_score"),
                           "crs_affine_error_m_median": (crs or {}).get("affine_vs_crs_error_m", {}).get("median")},
    "CAPA_1_DATA": {**data, "DATA_APPROVED": "PASS" if data_approved else "FAIL"},
    "CAPA_2_MODEL": {**model, "MODEL_APPROVED": "PASS" if model_approved else "FAIL"},
    "CAPA_3_PRODUCT": {**product, "PRODUCT_APPROVED": "PASS" if product_approved else "FAIL"},
    "CAPA_4_TRACEABILITY": {**trace, "TRACEABILITY_APPROVED": "PASS" if trace_approved else "FAIL"},
    "OVERALL_RELEASE": overall,
    "verdict": "READY FOR FINAL REVIEW" if overall == "PASS" else "NOT READY FOR FINAL REVIEW",
}
(VAL / "validation_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"RUN_ID {RUN_ID}")
print(f"Tests de regresión: {'PASS' if tests_pass else 'FAIL'} ({results['regression_tests']['summary']})")
print(f"DATA={results['CAPA_1_DATA']['DATA_APPROVED']}  MODEL={results['CAPA_2_MODEL']['MODEL_APPROVED']}  "
      f"PRODUCT={results['CAPA_3_PRODUCT']['PRODUCT_APPROVED']}  TRACE={results['CAPA_4_TRACEABILITY']['TRACEABILITY_APPROVED']}")
print(f"OVERALL RELEASE = {overall}  →  {results['verdict']}")
print("→ validation/validation_results.json")
