# Decision Log — Zoom Bogotá V1 (decisiones metodológicas, Sec 54/84)

| DECISION_ID | Fecha | Pregunta | Decisión | Evidencia | Rationale |
|---|---|---|---|---|---|
| D1 | 2026-08-11 | ¿Ventana del target? | **Estrictamente futura `[t+1,t+3]`**; el día t no cuenta | Fuga same-day (F1): con `[t,t+2]` ROC 0.804 inflado | Regla temporal (Sec 18): features ≤ t, target > t |
| D2 | 2026-08-11 | ¿El predictivo por lluvia es viable? | **No**; reencuadre a producto DESCRIPTIVO (Opción A) | Ablation: modelo 0.735 ≤ territorio 0.740; BSS 0.035; recall 17% | Evidencia empírica (Regla 3/21/72) — decisión aprobada por el responsable |
| D3 | 2026-08-11 | ¿Monotonía global? | **No** por defecto | Control shuffle con monotonía 0.705 (prior espurio) vs sin 0.458 | Metodológico (Sec 30): no imponer sin justificación validada |
| D4 | 2026-08-11 | ¿De dónde salen los thresholds? | **De CALIB**, nunca test | F2: `base=yte.mean()` usaba test | Regla 0.7 / Sec 32 |
| D5 | 2026-08-11 | ¿Cómo georreferenciar la susceptibilidad? | **Geocodificación IDIGER por localidad/UPZ** (sin CRS) | F3: método afín de bbox con error mediana **57 km** | Físico/operacional: el índice descriptivo no requiere reproyectar; error 0 |
| D6 | 2026-08-11 | ¿Probabilidad a nivel UPZ? | **No**; UPZ = priorización espacial | Modelo validado solo a localidad-día | Sec 45: no presentar una resolución que el modelo no tiene |
| D7 | 2026-08-11 | ¿Capas POT (amenaza física)? | **Diferidas** hasta CRS autoritativo IDECA | POT en CRS local Bogotá sin etiquetar | No usar dato espacialmente inválido (Sec 19) |

_Cada decisión que puede cambiar el significado del producto queda aquí. Ver `RC_STATUS.md` para el estado de gates._
