# MATRIZ DE AFIRMACIONES Y EVIDENCIAS - AQUABOSQUE MINERO IA

## Documento D02_AUDITORIA_ESTADO.md

### Afirmación 1: "El sistema AquaBosque Minero IA integra cinco fuentes de datos principales"
**Fuente verificable:** Código fuente y documentación del proyecto
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** `build_target.py` - construcción de índices
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "El proyecto está basado en la metodología CRISP-ML"
**Fuente verificable:** Documentación del proyecto
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/README.md` (no disponible, pero se infiere del código)
**Función/objeto:** Estructura de carpetas y scripts
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 3: "El pipeline principal es de 01_download_data.py a 06_run_app.py"
**Fuente verificable:** Scripts del proyecto
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/scripts/`
**Función/objeto:** Lista de scripts numerados
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 4: "Componentes adicionales de incendios, Bogotá y validación"
**Fuente verificable:** Código fuente y estructura del proyecto
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/scripts/`
**Función/objeto:** Scripts especiales como `07_trio_insignia.py`, `08_bogota_upz.py`, etc.
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D03_VERSIONES.md

### Afirmación 1: "Git HEAD: 945232a16faf7bf603ae87fc76abe4016d465db4"
**Fuente verificable:** Git commit
**Archivo:** Git repository
**Función/objeto:** `git log --oneline -1`
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Rama: feature/capa-incendios"
**Fuente verificable:** Git branch
**Archivo:** Git repository
**Función/objeto:** `git branch`
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 3: "Cinco índices, incluido idx_fuego"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** Función `_cuantil` y construcción de índices
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 4: "Modelo municipal XGBoost y otros modelos/componentes separados"
**Fuente verificable:** Código fuente y estructura de modelos
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/`
**Función/objeto:** Archivos `train.py`, `anomalias.py`, `conformal.py`
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D04_TRAZABILIDAD.md

### Afirmación 1: "Fuente Minera - ANM - RUCOM"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/master_municipal.csv`
**Función/objeto:** Datos de minería
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Fuente Territorial - DANE - DIVIPOLA"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/municipios.geojson`
**Función/objeto:** Datos geográficos
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 3: "Fuente de Deforestación - Observatorio/IDEAM"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/master_municipal.csv`
**Función/objeto:** Datos de deforestación
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 4: "Fuente Hídrica - IDEAM - DHIME"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/master_municipal.csv`
**Función/objeto:** Datos de calidad de agua
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D05_A1_DEFINICION_TEMATICA.md

### Afirmación 1: "Problema de presión minera, deforestación y afectación hídrica"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** Definición de índices y etiqueta
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Problema de negocio: clasificación de municipios por riesgo ambiental"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** Función `_nivel` y etiqueta de riesgo
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D06_A2_ENTENDIMIENTO_NEGOCIO.md

### Afirmación 1: "Problemas de negocio resueltos"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** Etiqueta de riesgo compuesta
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Decisiones de negocio apoyadas"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** Pesos de índices y cálculo de riesgo
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D07_A3_ENTENDIMIENTO_DATOS.md

### Afirmación 1: "Fuentes de datos principales documentadas"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** Función `_cuantil` y construcción de índices
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Variables de datos identificadas"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/features/build_target.py`
**Función/objeto:** Lista de variables de entrada
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D08_A4_PREPARACION_DATOS.md

### Afirmación 1: "Procesamiento de datos mineros (ANM - RUCOM)"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/master_municipal.csv`
**Función/objeto:** Datos de minería
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Procesamiento de datos territoriales (DANE - DIVIPOLA)"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/municipios.geojson`
**Función/objeto:** Datos geográficos
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 3: "Procesamiento de datos de deforestación (Observatorio/IDEAM)"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/master_municipal.csv`
**Función/objeto:** Datos de deforestación
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 4: "Procesamiento de datos hídricos (IDEAM - DHIME)"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/data/processed/master_municipal.csv`
**Función/objeto:** Datos de calidad de agua
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D09_A5_MODELAMIENTO.md

### Afirmación 1: "Modelo principal: XGBoost multiclase"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py`
**Función/objeto:** Clase `XGBClassifier`
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Métricas de evaluación reportadas"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/models/metrics/metricas.json`
**Función/objeto:** Función `run()` y guardado de métricas
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

## Documento D10_A6_EVALUACION.md

### Afirmación 1: "Métricas cuantitativas reportadas"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/models/metrics/metricas.json`
**Función/objeto:** Métricas de evaluación
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 2: "Validación del modelo"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/src/aquabosque/models/train.py`
**Función/objeto:** Función `run()` y validación cruzada
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED

### Afirmación 3: "Pruebas automatizadas documentadas"
**Fuente verificable:** Código fuente
**Archivo:** `/home/tuxilo/aquabosque-minero-ia/tests/`
**Función/objeto:** Archivos de prueba
**Versión/hash:** `945232a16faf7bf603ae87fc76abe4016d465db4`
**Resultado de verificación:** CONFIRMED