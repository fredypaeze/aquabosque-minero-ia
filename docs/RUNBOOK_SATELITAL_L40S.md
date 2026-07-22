# Runbook — Capa 2 satelital: deep learning sobre Sentinel-2 (L40S, soberano local)

Guía para ingeniería. Corre en **terramin/skymin** (donde están las **3× NVIDIA L40S**), no en tuxilo-server (sin GPU). El dato satelital se **descarga a infraestructura del Ministerio y se procesa local** — soberanía de datos.

> **Honestidad (regla del proyecto):** la Capa 1 (FIRMS, focos térmicos NRT) ya está en producción y es honesta. Esta Capa 2 procesa **imagen cruda Sentinel-2 con IA** para detectar pérdida de bosque. Es la que responde de lleno al reto #6 ("imágenes satelitales"). Mientras no esté validada en producción, se presenta como capacidad en construcción con infraestructura real detrás — no como resultado ya operativo.

---

## 0. Objetivo

De imagen Sentinel-2 (10 m) a **pérdida de bosque por municipio**, para (a) refrescar `idx_deforestacion` con evidencia reciente y (b) mapas antes/después como showpiece. Dos motores:

- **Baseline sin etiquetas (rápido):** detección de cambio bi-temporal por índices (NDVI/NBR). Corre ya, da resultados en horas.
- **Avanzado (GPU):** segmentación **U-Net** bosque/no-bosque (PyTorch) con etiquetas débiles de **ESA WorldCover 10 m**; la diferencia temporal de máscaras = pérdida.

---

## 1. Entorno (una vez, en terramin/skymin)

```bash
# CUDA 12.x ya presente con las L40S. Conda recomendado por rasterio/GDAL.
conda create -n aquabosque-sat python=3.11 -y && conda activate aquabosque-sat
conda install -c conda-forge rasterio pyproj shapely geopandas rioxarray \
                             pystac-client stackstac numpy pandas -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install segmentation-models-pytorch  # U-Net + encoders preentrenados

python -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# Esperado: CUDA: True  NVIDIA L40S
```

Fuente de imagen (sin credenciales): **Earth Search (AWS Open Data)** STAC de Sentinel-2 L2A.
Alternativa soberana UE: **Copernicus Data Space Ecosystem (CDSE)** — requiere cuenta gratuita; usar si se prefiere origen oficial europeo. Ambas se descargan a disco local (soberanía = el procesamiento y el almacenamiento son del Ministerio).

---

## 2. Áreas de interés (AOI)

Priorizar donde converge señal del modelo + FIRMS. Sugerido: los municipios de **prioridad máxima** (Alto/Crítico + fuego activo) y las regiones que el concurso enfatiza (Amazonía, Orinoquía, Pacífico). El módulo toma códigos DANE y saca el bbox desde `data/processed/municipios.geojson`.

```bash
# Ejemplo: Cumaribo (Vichada), Tibú (N. Santander), San Vicente del Caguán (Caquetá)
export AOI_CODS="99773,54810,18753"
```

---

## 3. Ejecución por etapas

```bash
cd aquabosque-minero-ia
export PYTHONPATH=src

# 3.1 Buscar y descargar Sentinel-2 L2A en dos fechas (época seca t0 y t1)
python -m aquabosque.satelital.sentinel2_deforestacion search \
    --cods "$AOI_CODS" --t0 2025-01-01/2025-03-31 --t1 2026-01-01/2026-03-31 \
    --max-cloud 20 --out data/raw/sentinel2

# 3.2 Baseline sin GPU: detección de cambio por NDVI/NBR → máscara de pérdida
python -m aquabosque.satelital.sentinel2_deforestacion change \
    --in data/raw/sentinel2 --out data/processed/deforestacion_s2 --thr-ndvi 0.15

# 3.3 (GPU) Entrenar U-Net bosque/no-bosque con etiquetas débiles WorldCover
python -m aquabosque.satelital.sentinel2_deforestacion train \
    --in data/raw/sentinel2 --worldcover data/raw/worldcover \
    --epochs 40 --batch 16 --device cuda --out models/unet_bosque.pt

# 3.4 (GPU) Inferir máscaras t0/t1 → pérdida → agregar a municipio
python -m aquabosque.satelital.sentinel2_deforestacion infer \
    --in data/raw/sentinel2 --weights models/unet_bosque.pt --device cuda \
    --out data/processed/deforestacion_s2

python -m aquabosque.satelital.sentinel2_deforestacion aggregate \
    --in data/processed/deforestacion_s2 --out data/processed/deforestacion_municipal.csv
```

**Notas L40S:** 48 GB permiten `batch 16–32` a 512×512 con encoder ResNet-34/50 y `amp` (mixed precision). Con 3 GPUs, paralelizar por AOI o `torchrun` para entrenamiento distribuido. Descarga y recorte por tiles (windowed reads de rasterio) para no cargar escenas completas en RAM.

---

## 4. Salidas e integración con AquaBosque

- `data/processed/deforestacion_municipal.csv` → `cod_mpio, ha_perdida_s2, periodo` → refresca `idx_deforestacion` en `build_master.py` (reemplaza el dato estático 2017-2021 por evidencia Sentinel-2 reciente).
- Tiles PNG antes/después + polígonos de pérdida → nueva sección "Deforestación Sentinel-2" en la app (junto a la de FIRMS).
- Cruce con Capa 1: pérdida S2 **+** focos FIRMS **+** prioridad del modelo = máxima confianza.

## 5. Validación y honestidad

- Validar la máscara U-Net contra **Hansen Global Forest Change** o **alertas AT-D del IDEAM** en las mismas AOI (IoU / matriz de confusión).
- Reportar métricas reales; no presentar cobertura nacional si solo se corrieron AOIs demo.
- Declarar límites de nube (usar Sentinel-1 SAR como complemento en Amazonía/Pacífico si la cobertura óptica falla).
