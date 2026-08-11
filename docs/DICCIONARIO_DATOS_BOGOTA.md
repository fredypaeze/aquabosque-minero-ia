# Diccionario de Datos — Zoom Bogotá / Alerta Temprana

Explica **cada campo de cada dataset** del módulo, organizado por el flujo
**bronze (crudo oficial) → gold (analítico) → capa territorial → tablero**.
Complemento de [`MODELO_ALERTA_BOGOTA.md`](MODELO_ALERTA_BOGOTA.md) y [`../data/CATALOGO_DATOS.md`](../data/CATALOGO_DATOS.md).

Convención de tipos: `int`, `float`, `str`, `fecha`, `bin` (0/1), `cat` (categórico).
Los `score_*` están normalizados en **[0, 1]** (0 = mínima, 1 = máxima).

---

## A. BRONZE — datos crudos oficiales (IDIGER / IDECA)

### A.1 `bitacora_emergencias.csv` — registro histórico de emergencias (la etiqueta)
| Campo | Tipo | Significado |
|---|---|---|
| Identificador | int | ID único del reporte de emergencia. |
| Fecha reporte | fecha | Fecha del evento (formato `dd/mm/YYYY`). |
| Localidad | str | Localidad con prefijo de código (ej. `19 Ciudad Bolívar`). |
| Barrio | str | Barrio del evento. |
| Upz | str | UPZ con prefijo de código (ej. `50 La Gloria`); `N/A` si no aplica. |
| Dirección | str | Dirección aproximada. |
| Tipo de afectación | cat | Clase del evento (ej. `Fenómeno de Remoción en Masa`, `Inundación`, `Encharcamiento`, `Caída de árbol`). Define el positivo. |

### A.2 `sab_lluvia_diaria.csv` — lluvia diaria por estación (los features)
| Campo | Tipo | Unidad | Significado |
|---|---|---|---|
| FECHALECTURA | fecha | — | Día de la lectura (ISO). |
| *(70 columnas, una por estación)* | float | mm | Lluvia acumulada del día en esa estación. En crudo usa **coma decimal** (`3,1` = 3.1 mm). |

### A.3 `sab_estaciones.csv` — catálogo de estaciones (geo-referencia)
| Campo | Tipo | Significado |
|---|---|---|
| Tipo | cat | Tipo de estación (PM = pluviométrica, HMT = hidrometeorológica…). |
| Estación | str | Nombre de la estación (cruce con las columnas de A.2). |
| Codigo CNE | str | Código nacional de la estación. |
| Latitud / Longitud | float | Coordenadas (crudo con **punto de miles**: `458.074` = 4.58074). |
| Elevacion | float | Altitud (msnm). |
| Entidad | str | Operador (IDIGER). |
| Localidad | str | Localidad donde está la estación (llave estación → localidad). |
| Estado… / Fecha… | str | Estado operativo e inicio de series por variable. |

---

## B. GOLD — datos analíticos del modelo

### B.1 `bogota_alerta_dataset.csv` — matriz supervisada (unidad = localidad-día)
| Campo | Tipo | Unidad | Significado |
|---|---|---|---|
| cod | str | — | Código de localidad (`01`–`20`, DANE distrital). |
| fecha | fecha | — | Día. |
| **p1** | float | mm | Lluvia del día. |
| **p3** | float | mm | Lluvia acumulada 72 h (suma de 3 días). *Es la variable del deslizador.* |
| **p7** | float | mm | Lluvia acumulada 7 días. |
| **p15** | float | mm | Lluvia acumulada 15 días (**antecedente**, saturación del suelo). |
| **pmax3** | float | mm | Máxima lluvia diaria en 3 días (**intensidad**). |
| **wet7** | int | días | Nº de días con lluvia > 1 mm en 7 días. |
| **score_remocion** | float | [0,1] | Susceptibilidad a remoción en masa (deslizamiento). |
| **score_agua** | float | [0,1] | Susceptibilidad a inundación / anegamiento. |
| **mes_sin / mes_cos** | float | — | Mes en codificación cíclica (estacionalidad, sin salto dic↔ene). |
| **y** | bin | — | **Etiqueta**: 1 si hubo evento de remoción o inundación en la localidad dentro de `[t, t+2]` (ventana 72 h). |

### B.2 `bogota_umbrales_aprendidos.csv` — umbral de lluvia aprendido por localidad
| Campo | Tipo | Unidad | Significado |
|---|---|---|---|
| cod / localidad | str | — | Localidad. |
| score_remocion / score_agua | float | [0,1] | Susceptibilidad usada. |
| **umbral_naranja_mm72h** | float | mm/72h | Lluvia a partir de la cual el modelo da P ≥ 0.156 (**naranja**). |
| **umbral_rojo_mm72h** | float | mm/72h | Lluvia a partir de la cual P ≥ 0.218 (**rojo**). |
| **p_max** | float | prob. | Probabilidad máxima alcanzable en esa localidad. |

### B.3 `bogota_alerta_importancia.csv` — explicabilidad
| Campo | Tipo | Significado |
|---|---|---|
| feature | str | Nombre del feature. |
| shap_abs | float | Importancia SHAP = |valor SHAP| medio (cuánto mueve la predicción). |

### B.4 `bogota_alerta_metrics.json` — métricas y configuración
| Clave | Significado |
|---|---|
| n_train / n_calib / n_test | Tamaños de las particiones temporales. |
| pos_rate_test | Tasa de positivos en test (**riesgo base**, ≈ 0.062). |
| roc_auc | Área bajo la curva ROC (discriminación). |
| pr_auc / pr_auc_baseline / lift_pr_auc | Precisión-Recall del modelo vs. azar y su cociente (**lift**). |
| brier_uncal / brier_cal | Error de Brier antes/después de calibrar (menor = mejor). |
| ventana / particion | Definición de etiqueta y esquema de validación temporal. |
| top_features | Features más influyentes (SHAP). |
| bandas | Cortes de probabilidad: base_rate, p_naranja (0.156), p_rojo (0.218). |

---

## C. CAPA TERRITORIAL

### C.1 `bogota_upz.csv` — 115 UPZ (Unidad de Planeamiento Zonal)
| Campo | Tipo | Significado |
|---|---|---|
| codigo | str | Código UPZ (`UPZ##`, geometría IDECA). |
| upz | str | Nombre de la UPZ. |
| localidad / localidad_codigo | str | Localidad y su código. |
| score_remocion / score_agua | float [0,1] | Susceptibilidad UPZ = **½ perfil físico de la localidad (POT) + ½ amenaza observada** (nº de emergencias por UPZ, normalizado). |
| score_fuego_estructural / score_operativo | float [0,1] | Heredados de la localidad. |
| indice_presion_ecoterritorial_bogota | float [0,1] | Índice compuesto de presión eco-territorial. |
| nivel | cat | Crítico / Alto / Medio / Bajo. |
| lluvia_72h_mm / incidentes_7d | int | Señal operativa (heredada de la localidad). |
| **eventos_remocion / eventos_inundacion** | int | **Nº real de emergencias históricas** de ese tipo en la UPZ (Bitácora IDIGER 2017–2025). |

### C.2 `bogota_upz_eventos.csv` — conteo curado de amenaza observada
| Campo | Tipo | Significado |
|---|---|---|
| cod_num | str | Código numérico de la UPZ. |
| eventos_remocion / eventos_inundacion | int | Nº histórico de emergencias por tipo (fuente del cruce fino). |

### C.3 `bogota_zoom.csv` — 20 localidades (dataset base del módulo)
**Identificación y decisión**
| Campo | Significado |
|---|---|
| codigo / localidad | Localidad (código `01`–`20` + nombre). |
| nivel | Nivel de presión (Crítico/Alto/Medio/Bajo). |
| driver_principal | Eje que más pesa en esa localidad. |
| corredor_estrategico | Corredor geográfico (cerros, río, laderas…). |
| resumen | Lectura ejecutiva en texto. |

**Puntajes por eje (susceptibilidad, [0,1])**
| Campo | Significado |
|---|---|
| score_fuego_estructural | Cerros e incendio forestal. |
| score_agua | Agua y anegamiento (río, humedales). |
| score_remocion | Ladera y remoción en masa. |
| score_operativo | Señal operativa reciente (lluvia + incidentes). |

**Índices**
| Campo | Significado |
|---|---|
| indice_bogota_base | Componente estructural (fijo). |
| indice_bogota_dinamico | Componente con señal reciente (lluvia/incidentes). |
| indice_presion_ecoterritorial_bogota | Índice final combinado. |

**Señal operativa y capas reales**
| Campo | Significado |
|---|---|
| incidentes_7d | Incidentes reportados en los últimos 7 días (SIRE). |
| lluvia_72h_mm | Lluvia acumulada 72 h (SAB). |
| water_area / water_feature_count / water_rio_bogota | Cuerpos de agua (área, conteo, presencia del río Bogotá). |
| humedal_area_proxy / humedal_feature_count | Humedales (área proxy y conteo). |
| fire_area_proxy / fire_feature_count / fire_hist_event_count | Incendio forestal (área proxy, conteo, eventos históricos). |
| sab_lluvia_max_mm / sab_lluvia_mean_mm / sab_lectura_max_mm | Lluvia SAB (máx, media, lectura máx) del día. |
| sab_estaciones_activas / sab_ultima_lectura | Estaciones SAB activas y fecha de última lectura. |
| mm_area_proxy / mm_feature_count | Movimiento en masa: área proxy y conteo de polígonos. |
| mm_riesgo_count | Polígonos en **condición de riesgo** por remoción (POT). |
| mm_amenaza_urb_count / mm_amenaza_rur_count | Polígonos de **amenaza** urbana / rural por remoción (POT). |
| score_*_real / score_*_demo | Versión del score con dato real vs. ilustrativo (transición demo→producto). |
| fuente_*_real | Fuente activa usada en ese eje. |

---

## D. CAMPOS DEL TABLERO (derivados en tiempo real, no almacenados)
Se calculan al mover el deslizador; aparecen en el mapa/hover de la pestaña *Alerta temprana*.
| Campo | Significado |
|---|---|
| susc | Susceptibilidad combinada = 0.6·score_remocion + 0.4·score_agua. |
| alerta | Puntaje de alerta: **P del modelo IA**, o `susc × factor_lluvia` en el motor "Regla". |
| nivel_alerta | Banda: Rojo / Naranja / Amarillo / Verde. |
| driver_lluvia | Peligro dominante: *Remoción en masa* o *Inundación / anegamiento*. |
| umbral_naranja_mm | Lluvia (mm/72h) que dispara naranja (motor "Regla"). |
| **p_ia** | **Probabilidad calibrada de emergencia en 72 h** que entrega el modelo. |
| unidad | Nombre a mostrar (`UPZ · localidad` o `localidad`). |

---

## E. GLOSARIO DE CONCEPTOS
| Término | Definición |
|---|---|
| **Susceptibilidad** | Propensión estructural de un territorio a un peligro (no depende del clima del día). |
| **Ventana 72 h** | Horizonte de la predicción: ¿ocurre un evento en las próximas 72 h? |
| **Umbral aprendido** | Lluvia a la que la probabilidad cruza una banda; se **aprende de la historia**, no se fija a mano. |
| **Banda de alerta** | Verde / Amarillo / Naranja / Rojo según cortes de probabilidad relativos al riesgo base. |
| **Monotonía** | Restricción del modelo: más lluvia o más susceptibilidad ⇒ la probabilidad **nunca baja**. |
| **Calibración (isotónica)** | Ajuste para que "P = 30 %" signifique de verdad 30 % de frecuencia observada. |
| **Riesgo base (base rate)** | Frecuencia natural del evento (≈ 6 %); referencia contra la que se mide el modelo. |
| **ROC-AUC** | Capacidad de ordenar días de más a menos riesgo (0.5 = azar, 1 = perfecto). |
| **PR-AUC / lift** | Precisión-Recall; el **lift** dice cuántas veces supera al azar (×5.6). |
| **Brier** | Error cuadrático medio de la probabilidad (menor = mejor calibrada). |
| **SHAP** | Aporte de cada variable a cada predicción (explicabilidad). |
| **p90** | Percentil 90; se usa para normalizar el conteo de eventos por UPZ. |
| **Medallón (bronze/silver/gold)** | Capas de datos: crudo oficial → curado por script → analítico. |
| **Código de localidad** | Numeración distrital 1–20 (1 Usaquén … 19 Ciudad Bolívar, 20 Sumapaz). |

---
_AquaBosque · Grupo de Datos Estratégicos, MinEnergía · agosto 2026._
