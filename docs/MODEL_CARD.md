# Model Card — AquaBosque Minero IA

Ficha técnica del modelo, siguiendo la práctica de *Model Cards* (transparencia de ML).

## 1. Detalles del modelo
- **Nombre:** clasificador de priorización de riesgo ambiental municipal.
- **Tipo:** XGBoost multiclase (`multi:softprob`, 4 clases), 300 árboles, `max_depth=4`, `learning_rate=0.08`, `subsample=0.9`, `colsample_bytree=0.9`, `random_state=42`.
- **Explicabilidad:** SHAP (TreeExplainer) — importancia global y atribución por municipio.
- **Unidad de análisis:** municipio (1.122, DIVIPOLA 2025).
- **Corre en CPU**, sin GPU ni dependencias geoespaciales pesadas.

## 2. Uso previsto
- **Para:** priorizar territorios para monitoreo y decisión pública basada en evidencia.
- **NO para:** probar causalidad, acusar, sancionar ni determinar ilegalidad. La salida es una **priorización relativa**, no una medición de daño.

## 3. Variables (13)
Cuatro índices compuestos 0–1 (`idx_minero`, `idx_deforestacion`, `idx_hidrico`, `idx_sensibilidad`) más 9 variables crudas trazables (títulos, minerales, ha deforestadas, áreas/ha RUNAP, estaciones de agua, volumen de explotación, regalías, PDET).

## 4. Etiqueta (definición transparente)
Fórmula documentada: `riesgo = 0.35·minero + 0.30·deforestación + 0.25·hídrico + 0.10·sensibilidad`, clasificada por **cuantiles** (Crítico p95, Alto p85, Medio p60, Bajo resto).
Distribución resultante (1.122 municipios): **Bajo 672 · Medio 281 · Alto 112 · Crítico 57**.

## 5. Desempeño (partición estratificada 75/25)
| Métrica | Valor |
|---|---|
| Accuracy | **0.911** |
| Línea base (clase mayoritaria) | 0.598 |
| F1 macro | 0.784 |

Por clase (F1): Bajo 0.98 · Medio 0.88 · Alto 0.70 · **Crítico 0.57** (recall 0.43 — clase minoritaria, 14 casos en test).

## 6. Honestidad (declarada, no ocultada)
La etiqueta es una **fórmula compuesta**, por lo que el modelo **re-aprende parcialmente la regla**: la accuracy alta es *por construcción* y **no se presenta como mérito predictivo**. Se reporta la línea base para contexto. **El valor real del modelo es la EXPLICABILIDAD (SHAP)** y su capacidad de generalizar la priorización a municipios no vistos, no la exactitud.

No existe *ground-truth* oficial de "riesgo ambiental" por municipio; se asume una etiqueta técnica con total trazabilidad en vez de inventar una verdad.

## 7. Limitaciones
- La señal hídrica solo existe donde hay estación IDEAM; su ausencia se marca (`hidrico_sin_dato`) y se trata como 0 (conservador), no se imputa.
- Cobertura de deforestación concentrada en el arco amazónico (fuente oficial).
- Clase **Crítico** con pocos casos → recall bajo; usar con revisión humana.
- Los pesos de la fórmula son un supuesto de política, ajustables y auditables.

## 8. Datos y ética
Fuentes 100% abiertas y oficiales (ANM/RUCOM, DANE, IDEAM, RUNAP, PDET). Sin datos personales. Principio rector: priorizar, no acusar.

## 9. Reproducibilidad
`pip install -r requirements.txt` → `python scripts/06_run_app.py`. Batería de pruebas: `pytest` (16 pruebas: integridad de datos, fórmula de etiqueta, modelo vs. línea base, SHAP, artefactos).
