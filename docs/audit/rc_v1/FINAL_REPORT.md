============================================================
ZOOM BOGOTÁ V1 — RELEASE CANDIDATE (INFORME ÚNICO)
============================================================

RELEASE_ID: ZOOM_BOGOTA_V1_RC_WIP
COMMIT: rama `feature/zoom-bogota-rc-v1` (ver metadata/run_manifest.json)
RUN_ID: ver validation/validation_results.json

CONTRATO
- Target: emergencia (remoción/inundación) en [t+1, t+3] (estrictamente futuro).
- Horizonte: 72 h futuras (día t excluido).
- Momento de predicción: cierre del día t; features con fecha ≤ t.
- Resolución estadística: localidad-día. Resolución territorial secundaria: UPZ (solo priorización).
- Inputs: Bitácora IDIGER (etiqueta/densidad) · SAB lluvia (escenario) · estaciones (geo).
- Outputs: índice territorial DESCRIPTIVO por localidad/UPZ + escenario de lluvia etiquetado.

------------------------------------------------------------
CAPA 1 — DATA
------------------------------------------------------------
QUALITY               PARTIAL   (profiling básico + p1≤p3≤p7≤p15 verificado en trazas; falta contract formal)
TRACEABILITY          PARTIAL   (source_registry + data_lineage + trace_observation OK; field lineage completo parcial)
COVERAGE              QUANTIFIED
SUFFICIENCY           QUANTIFIED (pos: train 853 / calib 190 / test 455)
REPRESENTATIVENESS    WARNING   (calib más húmedo: prev 0.080 vs test 0.063)
TARGET                PASS
TEMPORAL              PASS      (target [t+1,t+3] + embargo; control shuffle limpio 0.458)
GEOSPATIAL            PARTIAL   (índice territorial IDIGER CRS-safe error 0; POT/`score_agua` pendientes)
LEAKAGE               PASS (temporal)

DATA APPROVED         FAIL

Datos: período Bitácora 2017–2025 · SAB 2021–2024 · 2.092 remoción + 1.952 inundación ·
prevalencia train/calib/test 0.059/0.080/0.063 · estaciones mapeadas 44/70.

------------------------------------------------------------
CAPA 2 — MODEL
------------------------------------------------------------
BASELINES             PASS
PREDICTIVE VALUE      FAIL   (0.735 ≤ territorio-solo 0.740; lluvia sola 0.601)
GENERALIZATION        N/A    (Opción A: producto descriptivo)
CALIBRATION           MARGINAL (Brier Skill Score 0.035)
UNCERTAINTY           PASS   (IC95 por bootstrap de bloque)
NEGATIVE CONTROLS     PASS   (shuffle sin monotonía 0.458; con monotonía 0.705 = prior espurio)
ROBUSTNESS            PENDING
EXPLAINABILITY        PENDING (SHAP a recomputar; SHAP≠causalidad)
OPERATIONAL UTILITY   FAIL   (recall @naranja 17%, rojo inalcanzable)

MODEL APPROVED        FAIL

Métricas finales (test 2024): ROC-AUC 0.735 (IC95 0.67–0.78) · PR-AUC 0.163 (base 0.063) ·
Brier 0.057 · Brier Skill Score 0.035. Ablation y controles en outputs/rc_v1/.

------------------------------------------------------------
CAPA 3 — PRODUCT
------------------------------------------------------------
END_TO_END            PENDING (falta test formal 20-casos)
FRONTEND_CONTRACT     PARTIAL (versión mostrada)
RESOLUTION_SEMANTICS  PASS    (UPZ=priorización; sin claim de probabilidad)
FAIL_SAFE             PASS    (st.stop si falta el dato)
DATA_FRESHNESS        PARTIAL (muestra período; sin lag en vivo)

PRODUCT APPROVED      FAIL

------------------------------------------------------------
CAPA 4 — TRACEABILITY
------------------------------------------------------------
SOURCE_REGISTRY       PASS
DATA_LINEAGE          PARTIAL (field-level presente; ampliable)
FIELD_LINEAGE         PARTIAL
PREDICTION_TRACE      PASS    (audit/trace_observation.py reconstruye genealogía + hash)
RUN_MANIFEST          PASS    (metadata/run_manifest.json con hashes)
ARTIFACT_REGISTRY     PASS
VERSIONING            PARTIAL (release_manifest presente)
REPRODUCIBILITY       PARTIAL (REBUILD documentado; determinismo verificado)
CLEAN_ROOM            PENDING (falta corrida en entorno limpio)
ROLLBACK              PARTIAL (procedimiento documentado; sin prueba automatizada)

TRACEABILITY APPROVED FAIL

------------------------------------------------------------
LIMITACIONES REALES (materiales)
------------------------------------------------------------
1. El índice territorial es DESCRIPTIVO (densidad histórica), con sesgo de reporte; no es susceptibilidad física ni pronóstico.
2. El modelo predictivo por lluvia no tiene habilidad útil (documentado, no usado).
3. `score_agua` y capas POT físicas pendientes de georreferenciación CRS-safe.
4. Calibración marginal → no se muestran porcentajes como probabilidad.
5. Cobertura de estaciones 44/70; localidades sin estación usan respaldo media-ciudad.
6. Representatividad: calib estacionalmente más húmedo que test.

------------------------------------------------------------
DEUDA TÉCNICA (no bloqueante del hallazgo, sí de la RC completa)
------------------------------------------------------------
- Clean-room reproduction en entorno nuevo. - Data contracts formales por dataset. - Walk-forward
multi-ventana. - SHAP recomputado + explainability formal. - Observability/drift. - Test end-to-end 20-casos.
- CRS autoritativo IDECA para recuperar las capas POT físicas.

------------------------------------------------------------
VEREDICTO
------------------------------------------------------------
NOT READY FOR FINAL REVIEW.

Razón: OVERALL RELEASE = FAIL. Se corrigieron los defectos críticos (fuga temporal, thresholds
sobre test, CRS afín de 57 km) y se reencuadró el producto a lo que el dato sustenta (índice
descriptivo). El núcleo territorial es válido y trazable; el componente predictivo se documenta
como no apto. Faltan Capa 4 completa (clean-room, rollback probado, observability) y cierres de
Capa 1/3 para poder declarar READY. No se hizo merge; master intacto.
