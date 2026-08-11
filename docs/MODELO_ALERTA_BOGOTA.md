# Modelo de Alerta Temprana por Lluvia — Bogotá (IDIGER)

Guía de validación para revisión técnica. Módulo **Zoom Bogotá** dentro de AquaBosque
(bonus track para el Instituto Distrital de Gestión de Riesgos, IDIGER). Refuerza el
criterio de escala/replicabilidad: el motor nacional baja a escala intraurbana.

## 1. Qué es
Modelo **supervisado** que aprende de 8 años de historia la relación **lluvia → emergencia**
y predice, por unidad territorial y día, la **probabilidad calibrada de una emergencia por
remoción en masa o inundación en las próximas 72 h**. Sustituye el enfoque de **umbral de
lluvia fijo** (el que opera IDIGER hoy) por un **umbral aprendido** por nivel de susceptibilidad.

## 2. Datos (procedencia oficial)

| Rol | Dataset | Fuente | Cobertura | Volumen |
|---|---|---|---|---|
| **Etiqueta** | Bitácora de Emergencias | IDIGER / SIRE (Datos Abiertos Bogotá, CC-BY 4.0) | 2017-01 → 2025-06 | 859.390 registros (fecha, localidad, UPZ, tipo) |
| **Features** | SAB Lluvia diaria | IDIGER — Sistema de Alerta de Bogotá | 2021-09 → 2024-12 | 70 estaciones × 1.218 días |
| Geo estaciones | Catálogo hidrometeorológico | IDIGER — SAB | — | 77 estaciones (lat/lon, localidad) |
| Susceptibilidad | score_remocion / score_agua | AquaBosque (POT/SIRE/SAB) | — | por localidad |
| Geometría fina | UPZ | IDECA / Sec. Gobierno | 116 UPZ | 115 útiles |

Curación y reproducibilidad documentadas en [`data/CATALOGO_DATOS.md`](../data/CATALOGO_DATOS.md).
Eventos detonados por lluvia usados como positivo: **2.092 remoción + 1.952 inundación/encharcamiento**.

## 3. Unidad de análisis y etiqueta
- **Unidad:** localidad-día (rejilla continua 2021-09 → 2024-12 × 20 localidades = 24.360 filas).
- **Etiqueta y = 1** si hay ≥1 evento de remoción o inundación en la localidad dentro de la
  **ventana [t, t+2] (72 h)**. Tasa de positivos: **6,2 %** (evento raro).

## 4. Features
Lluvia acumulada **p1, p3 (72h), p7, p15** (antecedente), intensidad **pmax3**, días húmedos
**wet7**; **susceptibilidad** (score_remocion, score_agua); **estacionalidad** (mes seno/coseno).
La misma regla `lluvia 72h → features` se usa en entrenamiento y en el simulador (trazable).

## 5. Modelo y decisiones de diseño
- **XGBoost** (clasificación), `max_depth=4`, `n_estimators=500`, `scale_pos_weight` para el desbalance.
- **Restricciones de monotonía**: la probabilidad **no puede decrecer** si sube la lluvia o la
  susceptibilidad (coherencia física; también actuó como regularizador — subió ROC-AUC de 0.75 a 0.80).
- **Calibración isotónica** en una ventana de calibración temporal separada (2023-09..12).

## 6. Validación (métricas honestas de test 2024)

| Métrica | Valor | Lectura |
|---|---|---|
| Partición | train <2023-09 · calib 2023-09..12 · **test 2024** | temporal, **sin fuga** |
| ROC-AUC | **0.804** | buena discriminación |
| PR-AUC | **0.352** (base 0.062) | **lift ×5.6** sobre el azar |
| Brier | 0.146 → **0.053** | mejora por calibración |
| n | train 14.600 · test 7.320 | — |

## 7. Explicabilidad (SHAP, |valor| medio)
`score_remocion (1.96) > score_agua (0.64) > mes_cos (0.61) > p15 (0.44) > p7 (0.37) …`
Coherente con la física: **susceptibilidad + estacionalidad + lluvia antecedente** (p15/p7 pesan
más que la lluvia del día p1) — así se comportan la remoción en masa y la inundación.

## 8. Salida operativa
- **P(emergencia 72h)** por localidad y por UPZ (el deslizador del tablero consulta el modelo).
- **Umbral de lluvia aprendido** por localidad (`outputs/tables/bogota_umbrales_aprendidos.csv`):
  p. ej. Ciudad Bolívar/Usme se disparan con muy poca lluvia (riesgo casi crónico), mientras
  Suba requiere ~48 mm y Santa Fe ~76 mm para rojo. Bandas: naranja P≥0.156, rojo P≥0.218 (≈2.5× y 3.5× el riesgo base).

## 9. Cruce fino UPZ ↔ amenaza IDIGER
La susceptibilidad por UPZ (115) = **½ perfil físico de la localidad (POT) + ½ amenaza observada**:
el número real de emergencias por UPZ de la Bitácora (join 111/115, normalizado al p90).
**Lucero (Ciudad Bolívar) = 140 remociones → hotspot #1**; los UPR rurales sin registro no se
sobrestiman. Es el registro real de IDIGER, no un proxy.

## 10. Reproducir desde cero
```bash
python scripts/08_bogota_upz.py        # capa UPZ + cruce con amenaza observada
python scripts/09_bogota_alerta_ml.py  # descarga bronze oficial si falta → dataset → XGBoost → métricas + umbrales
```
El crudo grande (bitácora, 78 MB) se descarga de la fuente oficial vía `scripts/_bogota_sources.py`
(gitignored); el gold se versiona para reentrenar sin el crudo.

## 11. Cómo verlo
Demo: **https://streamlit.spartanit.pro/** → página **Zoom Bogota** → pestaña **🚨 Alerta temprana**.
Toggles: **Motor IA / Regla** y **Resolución Localidad / UPZ**. Mueve el deslizador de lluvia.

## 12. Qué revisar
- `scripts/09_bogota_alerta_ml.py` — pipeline de datos + entrenamiento + validación.
- `scripts/08_bogota_upz.py` — capa UPZ + cruce fino con amenaza observada.
- `app/pages/10_🏙️_Zoom_Bogota.py` — integración en el simulador (tab «Alerta temprana»).
- `models/metrics/bogota_alerta_metrics.json` — métricas. `outputs/tables/bogota_*` — dataset, umbrales, SHAP.
- Commits: `9386b74` (modelo + UPZ + catálogo) · `76d417e` (cruce fino UPZ↔amenaza).

## 13. Honestidad y limitaciones
- **Evento raro** (base 6 %): el mérito NO es una accuracy inflada sino el **lift PR-AUC ×5.6**,
  la calibración y la explicabilidad. Reportamos test temporal, no aleatorio.
- **Cobertura de estaciones**: 44/70 estaciones mapean directo a localidad (63 % de lecturas);
  las localidades sin estación usan media-ciudad como respaldo.
- **Huecos de reporte** en 2022 y 2024 en algunas categorías (se maneja con la ventana temporal).
- **Susceptibilidad domina** el SHAP: el efecto de la lluvia satura hacia ~20–30 mm (suelo saturado).
- **Resolución del modelo = localidad-día**; a UPZ se lleva por susceptibilidad (física + amenaza
  observada). Refinamiento futuro: modelo nativo UPZ-día y cruce con las capas IDIGER de amenaza
  por movimiento en masa (IDECA `emergencias/gestionriesgos`).

---
_AquaBosque · Grupo de Datos Estratégicos, MinEnergía · agosto 2026._
