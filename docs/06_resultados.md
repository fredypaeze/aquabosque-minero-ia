# Resultados

## Distribución de priorización
| Nivel | Municipios | % |
|---|---|---|
| 🔴 Crítico | 57 | 5% |
| 🟠 Alto | 112 | 10% |
| 🟡 Medio | 281 | 25% |
| 🟢 Bajo | 672 | 60% |

## Top 10 territorios priorizados
| # | Municipio | Departamento | Nivel | Score |
|---|---|---|---|---|
| 1 | ORITO | PUTUMAYO | Crítico | 0.507 |
| 2 | SAN JOSÉ DEL GUAVIARE | GUAVIARE | Crítico | 0.497 |
| 3 | SAN VICENTE DEL CAGUÁN | CAQUETÁ | Crítico | 0.485 |
| 4 | LA MACARENA | META | Crítico | 0.464 |
| 5 | PUERTO GUZMÁN | PUTUMAYO | Crítico | 0.444 |
| 6 | SANTA ROSA | CAUCA | Crítico | 0.441 |
| 7 | TIMBIQUÍ | CAUCA | Crítico | 0.435 |
| 8 | BARRANCABERMEJA | SANTANDER | Crítico | 0.434 |
| 9 | ACACÍAS | META | Crítico | 0.433 |
| 10 | URIBE | META | Crítico | 0.431 |

Estos territorios (arco amazónico de deforestación + zonas de minería intensiva de oro/carbón) son focos reconocidos, lo que valida la coherencia de la priorización.

## Métricas del modelo
- Accuracy: 91.1% · línea base (clase mayoritaria): 59.8% · F1-macro: 0.78
- **Nota de honestidad:** La etiqueta es una fórmula compuesta; el modelo re-aprende parcialmente la regla, por eso la accuracy es alta por construcción y NO se presenta como mérito predictivo. Se reporta la línea base (clase mayoritaria) para contexto. El valor del modelo es la EXPLICABILIDAD (SHAP) y su capacidad de generalizar la priorización, no la exactitud.

## Importancia de variables (SHAP)
- idx_minero: 0.834
- idx_deforestacion: 0.740
- idx_sensibilidad: 0.606
- idx_hidrico: 0.589
- mineria_titulos: 0.489
- runap_areas: 0.419
- es_pdet: 0.412
- deforestacion_ha: 0.400