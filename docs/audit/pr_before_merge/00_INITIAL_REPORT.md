# AUDITORÍA PRE-MERGE — AQUABOSQUE — INFORME INICIAL (EN PROGRESO)

**PR:** #1 · **Rama origen:** `feature/trio-insignia` → **destino:** `master`
**Commit inicial (baseline):** `b61a910` · tag `audit/pre-merge-b61a910` · backup `audit-backup/trio-insignia`
**Estado:** **NOT READY FOR MERGE** — hay hallazgos CRÍTICOS abiertos. Auditoría en curso (fases 0–2 + hallazgos críticos demostrados; correcciones pendientes).

---

## 0. Estado Git / recuperación
- Rama `feature/trio-insignia`, HEAD `b61a910`. Base `fredy/master = 39ee98b` (merge-base = base; sin divergencia).
- Punto de recuperación creado: **tag** `audit/pre-merge-b61a910` + **rama** `audit-backup/trio-insignia`.
- **Cambios locales sin versionar (NO son del PR, WIP de otra sesión):** `data/processed/fuego_municipal.csv`, `fuego_summary.json` (M) y `outputs/jurado_2026/*`, `scripts/{agregar_lamina_rigor,guion_actualizado_word,preguntas_defensa_word}.py` (??). Registrados; no se tocan.

## 1. Alcance real del PR — MEZCLA 3 PRODUCTOS INDEPENDIENTES (hallazgo de alcance)
El PR (12 commits) combina productos lógicamente independientes:
- **PR-A · Trío insignia (nacional):** `scripts/07_trio_insignia.py`, `outputs/tables/{velocidad_degradacion,alertas_mineria_ilegal,anomalias_explicadas}.csv`, `models/metrics/trio_insignia_summary.json`, `app/pages/09_🚀_Alertas_anticipatorias.py`. (commit `6c9764b`)
- **PR-B · Monitoreo satelital:** `app/pages/07_🛰️_Monitoreo_satelital.py`. (commits `5da3480`,`3bc0ffb`)
- **PR-C · Zoom Bogotá:** `app/pages/10_…Zoom_Bogota.py`, `scripts/08_bogota_upz.py`, `09_bogota_alerta_ml.py`, `_bogota_sources.py`, `08/09/10/11_prepare_bogota_*.py`, `data/processed/bogota_*`, `data/raw/bogota/*`, `models/bogota_alerta_*`, `docs/*BOGOTA*`, `data/CATALOGO_DATOS.md`. (commits `086b13f`…`b61a910`)
- Compartidos: `app/branding.py`, `.gitignore`.

**Recomendación (no destructiva):** dividir en PR-A / PR-B / PR-C. Esta auditoría se concentra en **PR-C (Zoom Bogotá / modelo)**, que es el que se presentaría como "IA para alerta territorial". Riesgo de separar: bajo (dependencias sólo en `branding.py` nav y `.gitignore`).

## 2. Reproducibilidad / entorno
- Python 3.12.3 · numpy 2.4.6 · pandas 3.0.3 · sklearn 1.9.0 · xgboost 3.3.0 · shap 0.52.0 · joblib 1.5.3 · Linux 6.8.
- **Determinismo:** re-entrenamiento con mismo seed → ROC-AUC idéntico (diff 0.0e00). ✔ (pero `PYTHONHASHSEED`/threads no fijados; documentar).
- Hashes inputs (sha256, 16c): bitácora `e7d9a092…` (859.393 líneas), SAB lluvia `dcefca7f…`, estaciones `5963310d…`, zoom `6123f47f…`.
- Baseline guardado en `AUDIT_BASELINE/` (ablation_results.csv, baseline_metrics.json). **No sobreescribir.**

---

## HALLAZGOS (demostrados; correcciones pendientes)

| ID | Sev | Componente | Problema | Evidencia |
|---|---|---|---|---|
| F1 | **CRÍTICO** | Temporalidad / target | Etiqueta `y` = evento en `[t, t+2]` **incluye el día t**, y las features (p1…) usan lluvia **hasta t inclusive** → simultaneidad: "predice" el evento de hoy con la lluvia de hoy. No es prospectivo. | `09_bogota_alerta_ml.py:132-137` (`s[::-1].rolling(3).max()[::-1]`) + `:116-125` |
| F2 | **CRÍTICO** | Thresholds | `base = float(yte.mean())` (prevalencia del **TEST**) define P_naranja/P_rojo. Viola Regla 0.7. | `09_…:219-220` |
| F3 | **CRÍTICO** | Geoespacial / CRS | `score_remocion` (feature dominante, SHAP 1.96) asigna polígonos POT a localidades con **normalización afín de bounding-box** origen→Bogotá (método PROHIBIDO). Sin CRS real. | `11_prepare_bogota_remocion.py:9-13,166-176` |
| F4 | **ALTO** | Estadística / monotonía | Las **restricciones de monotonía inflan la métrica**: control target-shuffle CON monotonía = ROC-AUC **0.76** (debería ~0.5); SIN monotonía = **0.40**. El modelo obtiene ~0.76 con etiquetas aleatorias por el prior hard-codeado. Modelo real sin monotonía = **0.752** (vs 0.804). | `AUDIT_BASELINE/…` + prueba shuffle |
| F5 | **ALTO** | Interpretación | La discriminación proviene casi toda del **ranking espacial estático**, no de la lluvia: susceptibilidad-sola 0.729, solo-localidad 0.741 vs completo 0.804. La narrativa "alerta temprana por lluvia" sobreestima la habilidad **temporal**. | `AUDIT_BASELINE/ablation_results.csv` |
| F6 | **ALTO** | Documentación / "aprendido" | `feats_from_R` usa razones **hardcodeadas** (p1=R/3, p7=R×1.4, p15=R×1.9…) y **mes=4 fijo**. Llamarlo "umbral de lluvia aprendido" es incorrecto; además el mes fijo ≠ mes actual que usa el tablero. | `09_…:201-207` |
| F7 | **ALTO** | Localidad vs UPZ | El modelo se entrena/valida **localidad-día**, pero el tablero muestra **P(emergencia 72h) por UPZ** como probabilidad calibrada. La calibración sólo se demostró a nivel localidad. | `app/pages/10_…` (motor IA por UPZ) |
| F8 | **ALTO** | Leakage UPZ retrospectivo | La susceptibilidad UPZ mezcla `eventos_remocion/inundacion` contados sobre **2017–2025 (incluye el periodo test 2024)** y se usa para representar riesgo 2024. | `08_bogota_upz.py` (blend p90) |
| F9 | MEDIO | Split / frontera | Etiqueta de train/calib puede asomarse 2 días al periodo siguiente (bleed `[t,t+2]` cruza la frontera de partición). | `09_…:153-158` + F1 |
| F10 | MEDIO | Modelado | Las capas POT de amenaza se cuentan como `count=1` sin ponderar por categoría (alta/media/baja). | `11_…:218-221` |
| F11 | MEDIO | Reproducibilidad | Sin `PYTHONHASHSEED`/pin de threads; el pipeline descarga bronze de red (fuente puede cambiar). | entorno |

### Ablation (evidencia F4/F5) — MISMO test, sin recalibrar
| Modelo | ROC-AUC | PR-AUC | lift |
|---|---|---|---|
| Completo (con monotonía) | 0.804 | 0.352 | 5.6 |
| Solo susceptibilidad | 0.729 | 0.139 | 2.2 |
| Solo localidad (identidad) | 0.741 | 0.139 | 2.2 |
| Solo lluvia | 0.755 | 0.299 | 4.8 |
| Solo estacionalidad | 0.572 | 0.095 | 1.5 |
| Lluvia + susceptibilidad | 0.830 | 0.404 | 6.5 |
| **CONTROL target-shuffle (con monotonía)** | **0.760** | 0.226 | 3.6 |
| CONTROL target-shuffle (sin monotonía, x5) | ~0.39 | ~0.05 | — |
| Modelo real sin monotonía | 0.752 | 0.174 | 2.8 |

## GATES DE MERGE (estado preliminar)
| Gate | Estado |
|---|---|
| 1 Pipeline reproducible | PARCIAL (determinista ✔; depende de red + prep con CRS afín) |
| 2 Fuentes trazables | PASS (catálogo) |
| 3 Temporalidad | **FAIL** (F1) |
| 4 Sin leakage | **FAIL** (F1, F8) |
| 5 Train/calib/test limpios | PARCIAL (F9) |
| 6 Calibración independiente | PENDIENTE (verificar calibrador no ve test) |
| 7 Thresholds independientes de test | **FAIL** (F2) |
| 8 CRS correcto | **FAIL** (F3) |
| 9 Resolución localidad/UPZ | **FAIL** (F7, F8) |
| 10 Backend/frontend consistentes | PENDIENTE (test contract) |
| 11 Tests | **FAIL** (no hay suite Bogotá) |
| 12 Docs actualizadas | **FAIL** (F6 narrativa "aprendido"/"8 años") |
| 13 CI | PENDIENTE |
| 14 Sin CRÍTICOS abiertos | **FAIL** (F1,F2,F3) |

## VEREDICTO: **NOT READY FOR MERGE**
Motivo: hallazgos CRÍTICOS abiertos de temporalidad (F1), thresholds sobre test (F2) y CRS afín en la feature dominante (F3), más inflado por monotonía (F4) y sobre-interpretación de la habilidad temporal (F5).

## Plan de remediación (siguiente fase)
1. Redefinir el momento de predicción y la etiqueta a ventana **estrictamente futura** `[t+1, t+3]`; features hasta cierre de t. Tests temporales (Sección 5,6).
2. Thresholds desde train/calibración (o criterio operativo), nunca test (Sección 19).
3. CRS real para POT (pyproj/geopandas o reproyección oficial) + medir error afín en metros (Sección 8,9).
4. Reevaluar monotonía: justificar por variable; recalcular métricas sin el prior espurio; reportar honesto (Sección 13,37).
5. Separar/etiquetar UPZ como **priorización espacial**, no probabilidad calibrada; quitar eventos del periodo test del score UPZ (Secciones 22,23).
6. Renombrar "umbral aprendido" → "umbral bajo escenario de lluvia"; umbral por mes (Secciones 20,21).
7. Suite de tests `tests/bogota/*` + prueba "vivir 2024" congelada + walk-forward + bootstrap (Secciones 25,18,17,33).
8. Actualizar toda la documentación/Streamlit con período real, unidad, horizonte y limitaciones (Sección 32).

_NO MERGE. Evidencia base en `AUDIT_BASELINE/`. Continúa la auditoría._
