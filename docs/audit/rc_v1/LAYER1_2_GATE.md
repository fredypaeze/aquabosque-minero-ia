# Zoom Bogotá V1 — Gate Capa 1 (Datos) + Capa 2 (Modelo)

Rama `feature/zoom-bogota-rc-v1`. Todo desde `config/release_zoom_bogota_v1.yaml`;
métricas reproducibles con `PYTHONHASHSEED=0 ./venv/bin/python scripts/rc/build_and_validate.py`.
Evidencia machine-readable: `outputs/rc_v1/rc_metrics.json`, `baselines_ablation_controls.csv`, `gold_localidad_dia.csv`.

## Correcciones aplicadas (vs. auditoría inicial)
- **F1 fuga same-day → CORREGIDO:** target ahora **estrictamente futuro `[t+1, t+3]`** (el día t NO cuenta); features sólo con fecha `≤ t`.
- **F9 bleed de frontera → CORREGIDO:** **embargo de 3 días** al final de cada split; sin solapamiento (aserciones en código).
- **F2 thresholds sobre test → CORREGIDO:** bandas naranja/rojo derivadas de **CALIB**; calibración isotónica ajustada en **CALIB**.
- **F4 monotonía infla → NEUTRALIZADO:** el modelo primario va **sin monotonía**; el control lo confirma (abajo).

## Resultado honesto (test 2024, modelo primario sin monotonía, calibrado)
| Métrica | Antes (con fuga + monotonía) | **Ahora (honesto)** |
|---|---|---|
| ROC-AUC | 0.804 | **0.735** (IC95 0.67–0.78) |
| PR-AUC | 0.352 | **0.163** (base 0.063) |
| Brier (calibrado) | 0.053 | 0.057 |
| **Brier Skill Score** vs prevalencia train | — | **0.035** |

## Ablation / baselines / controles (mismo test)
| Modelo | ROC-AUC | PR-AUC |
|---|---|---|
| M0 prevalencia (train) | 0.500 | 0.063 |
| M1 estacionalidad | 0.576 | 0.095 |
| M3 lluvia sola | 0.601 | 0.096 |
| **M2 territorio (susceptibilidad)** | **0.740** | 0.140 |
| **LOCID (solo identidad de localidad)** | **0.741** | 0.140 |
| M5 lluvia + territorio | 0.745 | 0.198 |
| **M6 completo (primario)** | **0.735** | 0.163 |
| M6 con monotonía | 0.793 | 0.335 |
| **CTRL target-shuffle SIN monotonía** | **0.458** ✔ (≈azar, control limpio) | 0.064 |
| CTRL target-shuffle CON monotonía | 0.705 ✗ (prior espurio) | 0.263 |
| M6 + feature aleatoria | 0.740 | 0.173 |

## Lectura (evidencia, no interpretación)
1. **El poder predictivo es territorial estático, no meteorológico.** El modelo completo (ROC 0.735) **no supera** a "solo territorio" (0.740) ni a "solo identidad de localidad" (0.741). La lluvia sola discrimina poco (0.601). → La discriminación proviene de *qué localidad es*, no de *cuándo lloverá*.
2. **La lluvia aporta poco y sólo en precisión-recall:** añadir lluvia a territorio sube PR-AUC 0.140→0.198, pero **no** mejora ROC-AUC. Señal real pero débil.
3. **Habilidad calibrada marginal:** Brier Skill Score **0.035** → las probabilidades apenas mejoran a predecir la prevalencia constante.
4. **Operación pobre:** en umbral naranja (desde calib) recall **17%**, precisión 24%; el umbral rojo es **inalcanzable** (P calibrada máx < 0.28) → como sistema de alerta operativa **no rinde**.
5. **Controles limpios:** shuffle sin monotonía = 0.458 (≈azar) confirma que **ya no hay fuga**; shuffle con monotonía = 0.705 confirma que la monotonía fabrica habilidad aparente (por eso el 0.793/0.335 del M6-monótono **no es habilidad real**).

## Gate Capa 1 (Datos)
| Control | Estado |
|---|---|
| Integridad temporal (F1/F9) | **PASS** (target estrictamente futuro + embargo; control shuffle limpio) |
| Fuga de datos | **PASS** para temporal; **PENDIENTE** CRS (F3, ver abajo) |
| Trazabilidad / contrato / lineage | PARCIAL (contrato + config congelados; falta source registry + field lineage formal) |
| **Integridad geoespacial (CRS)** | **FAIL** (F3: `score_remocion` aún usa normalización afín de bounding-box; es la feature que porta casi toda la señal) |
| Suficiencia / representatividad | Cuantificada: prev train 0.059 / calib 0.080 / test 0.063; calib más húmedo (sesgo estacional) |
| Target validity | **PASS** (regex de tipos, dedup a día-localidad, ventana futura explícita) |

## Gate Capa 2 (Modelo)
| Control | Estado |
|---|---|
| Sin fuga / controles negativos | **PASS** |
| Baselines / ablation | **PASS** (ejecutados) |
| Calibración independiente | **PASS** (isotónica en calib) |
| Thresholds independientes de test | **PASS** (desde calib) |
| **Habilidad predictiva de la lluvia** | **FAIL** (no supera a territorio; BSS 0.035; recall operativo 17%) |

## VEREDICTO Capa 1+2: **NOT APPROVED**
Dos bloqueos: (a) **CRS** de la feature dominante sigue sin corregir (Capa 1); (b) **el producto, como "alerta temprana predictiva por lluvia" calibrada, no está sustentado por los datos** — la habilidad real es territorial estática (Capa 2).

→ Esto exige una **decisión de definición de producto** (target / horizonte / resolución / interpretación), que por la Regla 3 se eleva al responsable antes de continuar a Capa 3.
