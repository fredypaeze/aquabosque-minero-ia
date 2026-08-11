# Architecture — Zoom Bogotá V1 (DAG del pipeline, Sec 53)

Ninguna transformación importante existe fuera de este DAG.

```
[IDIGER_BITACORA_V202608]        [IDIGER_SAB_LLUVIA_V202608] [IDIGER_SAB_ESTACIONES]
 (bronze, hash)                   (bronze, hash)              (bronze, hash)
        │                                │                        │
        │                                └──────────┬─────────────┘
        │                                   clean_sab (decimal-coma, clip, melt)
        │                                           │
        │                                  aggregate_station→localidad
        │                                           │
        │                                  build_rain_features (p1,p3,p7,p15,pmax3,wet7  BACKWARD ≤ t)
        │                                           │
        ├── build_target (fwd_target [t+1,t+3]  ESTRICTAMENTE FUTURO)  ──┐
        │                                           │                    │
        │                                  assemble_dataset (localidad-día)
        │                                           │
        │                            split+embargo → train / calib / test
        │                                           │
        │                            train_model (XGBoost) → calibrate(calib) → validate
        │                                           │
        │                     [rc_metrics.json + baselines_ablation_controls.csv]
        │                     (RESULTADO: predictivo NO apto → documentado, no usado)
        │
        └── build_territorial_index (densidad histórica por localidad/UPZ, geocod. IDIGER, CRS error 0)
                    │
            [bogota_territorial_v1.csv / bogota_upz_territorial_v1.csv]  ← NÚCLEO DEL PRODUCTO
                    │
            publish → app/pages/10_🏙️_Zoom_Bogota.py (índice descriptivo + escenario etiquetado)
```

## Nodos y código
| NODE | CÓDIGO | OUTPUT | VALIDACIÓN |
|---|---|---|---|
| clean_sab / features | `scripts/rc/build_and_validate.py` + `rc_lib.py` | p1..wet7 | `tests/bogota` (temporal) |
| build_target | `rc_lib.py::fwd_target` | y [t+1,t+3] | `test_fwd_target_*` |
| split+embargo | `rc_lib.py::split_with_embargo` | train/calib/test | `test_temporal_splits_*` |
| train/calibrate/validate | `build_and_validate.py` | rc_metrics.json | ablation + controles |
| **build_territorial_index** | `scripts/rc/build_territorial_index.py` | territorial_v1.csv | `test_territorial_*` |
| trazabilidad | `audit/trace_observation.py` | genealogía | Sec 41 |
| validación global | `validation/run_validation.py` | validation_results.json | Sec 63/65 |

## Componentes (Sec 58 — separación DATA/CONFIG/MODEL/UI)
- **DATA:** `data/raw` (bronze) → `data/processed` + `outputs/rc_v1` (gold).
- **CONFIG:** `config/release_zoom_bogota_v1.yaml` (único; sin magic numbers).
- **MODEL:** evaluado y no usado como producto (Opción A).
- **UI:** `app/pages/10_🏙️_Zoom_Bogota.py`.
- **META:** `metadata/` (source_registry, data_lineage, artifact_registry, run_manifest).
