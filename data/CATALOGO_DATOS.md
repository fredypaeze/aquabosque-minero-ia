# Catálogo de Datos — Grupo de Datos Estratégicos

> Registro de **procedencia** y **curación** de los datos que alimentan AquaBosque y el
> módulo Zoom Bogotá / Alerta Temprana. Pensado para auditoría técnica: cada dato
> tiene fuente oficial, fecha de extracción, licencia y una cadena reproducible
> bronze → silver → gold.

## Principio de curación (arquitectura medallón)

| Capa | Qué es | Dónde | Regla |
|---|---|---|---|
| **Bronze** (crudo) | Copia exacta de la fuente oficial, sin tocar | `data/raw/` | Inmutable; nunca se edita a mano |
| **Silver** (curado) | Limpieza reproducible: encoding, tipos, llaves de cruce, dedup, outliers | scripts `scripts/*.py` | 100 % por código versionado, 0 % manual |
| **Gold** (analítico) | Tablas listas para modelo/tablero | `data/processed/`, `outputs/tables/` | Cada gold traza a su bronze + el script que lo produjo |

**"Curada" significa aquí, de forma verificable:**
1. **Trazable** — fuente, URL, licencia y fecha de extracción registradas (tabla de abajo).
2. **Reproducible** — el gold se regenera desde el bronze con un solo comando; sin pasos manuales.
3. **Validada** — chequeos automáticos: rango de fechas, nulos, outliers, consistencia de llaves (p. ej. `ids geojson == ids csv`).
4. **Honesta** — toda transformación queda documentada; los proxies se etiquetan como tales y no se inventan valores.

## Procedencia de las fuentes consumidas (Zoom Bogotá)

| Dataset (bronze) | Entidad / fuente | Licencia | Extraído | Cobertura | Granularidad | Volumen | Curación aplicada (silver) → gold |
|---|---|---|---|---|---|---|---|
| `bitacora_emergencias.csv` | **IDIGER / SIRE** — Datos Abiertos Bogotá | CC-BY 4.0 | 2026-08-10 | ene-2017 → jun-2025 | evento (fecha, localidad, UPZ, tipo de afectación) | 859.390 filas / 78 MB | encoding latin-1 mixto → normalización ASCII; parse fecha `dd/mm/YYYY`; código de localidad desde prefijo; filtro remoción/inundación; agregación a **localidad-día**. Script `09_bogota_alerta_ml.py` → `outputs/tables/bogota_alerta_dataset.csv` |
| `sab_lluvia_diaria.csv` | **IDIGER — SAB** (Sistema de Alerta de Bogotá) | CC-BY 4.0 | 2026-08-10 | sep-2021 → dic-2024 | estación-día (mm) | 70 estaciones × 1.218 días | decimal-coma → float; clip 0–400 mm (outliers); `melt` a formato largo; cruce estación→localidad. Script `09_bogota_alerta_ml.py` |
| `sab_estaciones.csv` | **IDIGER — SAB** (catálogo hidrometeorológico) | CC-BY 4.0 | 2026-08-10 | 77 estaciones | estación (lat/lon, localidad) | 77 filas | lat/lon con punto de miles → `/1e5`; normalización de nombre; llave estación→localidad (44/70 directas + respaldo media-ciudad) |
| UPZ Bogotá (en vivo) | **IDECA / Sec. de Gobierno** — waserver Mapa_Base capa UPZ | Datos Abiertos Bogotá | 2026-08-10 | 116 UPZ (115 útiles) | polígono UPZ (con localidad) | 1,6 MB geojson | centroide → localidad (point-in-polygon); redondeo de geometría a 4 decimales; **cruce fino UPZ↔amenaza IDIGER**: susceptibilidad = perfil físico de localidad (POT) + amenaza observada (nº de emergencias por UPZ de la Bitácora, normalizado p90). Script `08_bogota_upz.py` → `data/processed/bogota_upz.{csv,geojson}` (+ `bogota_upz_eventos.csv`) |

## Salidas gold (productos de datos)

| Producto | Qué contiene | Ruta |
|---|---|---|
| Dataset supervisado | localidad-día con features de lluvia + susceptibilidad + etiqueta (evento 72 h) | `outputs/tables/bogota_alerta_dataset.csv` |
| Modelo entrenado | XGBoost monotónico + calibrador isotónico + metadatos | `models/bogota_alerta_xgb.joblib` |
| Métricas de validación | ROC-AUC, PR-AUC, Brier, partición temporal, top-SHAP | `models/metrics/bogota_alerta_metrics.json` |
| Umbrales aprendidos | lluvia 72 h que dispara naranja/rojo por localidad | `outputs/tables/bogota_umbrales_aprendidos.csv` |
| Capa UPZ | 115 UPZ con perfil de amenaza y geometría | `data/processed/bogota_upz.{csv,geojson}` |

## Reproducir desde cero

```bash
# 1) capa UPZ (baja geometría oficial IDECA y la cura)
python scripts/08_bogota_upz.py
# 2) modelo de alerta temprana (bitácora + SAB → dataset → XGBoost → métricas + umbrales)
python scripts/09_bogota_alerta_ml.py
```

## Próximo paso: catálogo central del ecosistema

Este archivo es la **plantilla**. La directriz "los modelos son un solo ecosistema" implica un
**registro único** que cubra también MIRHE (XM/SIMEM/BEC), GasFirme, ComunEnergía (ZNI/frontera),
SDDP y el gemelo de apagón, con la misma ficha de procedencia + curación. Opcional: materializarlo
en una base consultable (**DuckDB/SQLite**) para que cualquiera del equipo consulte "¿de dónde salió
este dato y cómo se curó?" en una query.

_Última actualización: 2026-08-10._
