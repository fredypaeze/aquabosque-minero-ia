# AquaBosque Minero IA

## Problema

Colombia no cuenta con una vista territorial unificada que combine, para las 1.122 unidades
DIVIPOLA vigentes, la presión minera formal registrada, señales estadísticas de calidad de
agua, detecciones tempranas de posible deforestación y la cobertura forestal confirmada. Esa
fragmentación dificulta priorizar dónde enfocar revisión técnica ambiental.

## Solución

**AquaBosque Minero IA** integra fuentes oficiales (ANM, IDEAM, DANE) en un dataset único de
1.122 municipios, calcula un **score de prioridad por evidencia** transparente y explicable, y
entrena un modelo no supervisado (**IsolationForest**) para señalar **patrones territoriales
atípicos** — sin afirmar causalidad ambiental, sin detectar minería ilegal y sin clasificar
legalmente la calidad del agua. Se presenta en una aplicación Streamlit con mapa nacional,
ranking filtrable y detalle por municipio.

## Secciones de la aplicación

1. **Inicio** — KPIs nacionales y alcance del producto.
2. **Mapa nacional** — coropletas por prioridad de evidencia o anomalía IA, filtro por departamento.
3. **Ranking** — top nacional filtrable por departamento, nivel, agua y DTD, con descarga CSV.
4. **Detalle territorial** — tarjetas por municipio (minería, agua, DTD, bosque, IA) con explicación textual.
5. **Metodología y limitaciones** — fuentes, tratamiento de datos faltantes, alcance real del modelo.

## Fuentes de datos

| Fuente | Origen | Identificador |
|---|---|---|
| Calidad de agua histórica IDEAM | datos.gov.co (API Socrata) | [`62gv-3857`](https://www.datos.gov.co/resource/62gv-3857.json) |
| Anotaciones de títulos mineros (RMN) | datos.gov.co (API Socrata) | [`si2v-pbq5`](https://www.datos.gov.co/resource/si2v-pbq5.json) |
| Catastro Minero ANM (títulos vigentes) | geo.anm.gov.co (WFS) | `ANM/ServiciosANM/MapServer` |
| Detecciones Tempranas de Deforestación (DTD) | IDEAM (ArcGIS FeatureServer) | `Hosted/DTD_Trimestral` |
| Bosque y cambio de cobertura (ráster WCS) | IDEAM (ArcGIS MapServer/WCS) | `Superficie_Bosque`, `Dinamica_Cambio_Cobertura_Bosque` |
| Unidades territoriales DIVIPOLA/MGN2025 | DANE | ver `docs/08_base_geometrica_nacional_mgn2025.md` |

Todos los identificadores de esta tabla ya estaban registrados en `data/raw/*/*.metadata.json`
al momento de construir el MVP — no se realizó ninguna búsqueda nueva.

## IA utilizada

`sklearn.ensemble.IsolationForest` (`random_state=42`, `contamination=0.10`, 200 árboles) sobre
variables de minería, agua, DTD y disponibilidad de datos — exclusivamente como **detector no
supervisado de patrones territoriales atípicos**. Ver `docs/MVP_METODOLOGIA.md` y
`docs/MVP_LIMITACIONES.md` para el alcance exacto y lo que el modelo NO afirma.

## Ejecución rápida para evaluación

El repositorio incluye ya los artefactos de datos y el modelo entrenado — no es necesario
descargar nada ni ejecutar el pipeline previo para ver la aplicación funcionando.

```powershell
git clone <URL_DEL_REPOSITORIO>
cd aquabosque-minero-ia
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py
```

## Instalación

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución

```powershell
# Opción 1: script de arranque (usa los artefactos ya incluidos; solo reconstruye si faltan)
.\run_mvp.ps1

# Opción 2: manual (los artefactos ya están versionados, este paso no es obligatorio)
python -m streamlit run app.py
```

## Estructura relevante del MVP

```
app.py                                        # aplicación Streamlit (lee directamente los artefactos versionados)
run_mvp.ps1                                   # arranque de un solo paso
scripts/24_build_mvp_dataset.py               # script de reproducibilidad: reconstruye dataset + modelo desde cero
models/isolation_forest_mvp.joblib            # modelo entrenado (versionado)
data/processed/mvp/
├── aquabosque_municipios_mvp.csv             # dataset integrado (1.122 municipios) — versionado
├── aquabosque_priorizacion_mvp.csv           # priorización + resultados IA — versionado
├── aquabosque_top20_mvp.csv                  # top 20 nacional — versionado
├── municipios_demo.csv                       # 3 municipios de demo — versionado
└── municipios_mvp_simplificado.geojson       # geometría simplificada para el mapa — versionado
docs/MVP_METODOLOGIA.md                       # metodología detallada
docs/MVP_LIMITACIONES.md                      # limitaciones explícitas
docs/DEMO_GUION.md                            # guion de demo (máx. 4 minutos)
```

Para la estructura completa del repositorio (fases forestales/hídricas/mineras previas), ver
`docs/01` a `docs/11`.

## Municipios demo

1. **Puerto Rico, Meta** — obligatorio: único municipio con bosque/deforestación confirmados con el piloto WCS IDEAM real (Fases 2D.1/2D.2).
2. **Montelíbano, Córdoba** — prioridad "Muy alta" con minería y agua disponibles simultáneamente.
3. **Marmato, Caldas** — anomalía IA alta (percentil 99) sin monitoreo hídrico disponible, perfil contrastante con el municipio 2.

Razón exacta de cada selección en `data/processed/mvp/municipios_demo.csv`.

## Reproducibilidad

Los artefactos versionados permiten evaluar el MVP sin reconstruir nada. Para regenerarlos
desde las fuentes (por ejemplo, tras actualizar los datos de agua, minería o DTD):

```powershell
python scripts/24_build_mvp_dataset.py
```

Esto sobrescribe `data/processed/mvp/*` y `models/isolation_forest_mvp.joblib` de forma
determinística (`random_state=42` en el modelo).

## Siguiente fase (posterior al concurso)

La arquitectura forestal nacional (grilla fija de 896 tiles, colormap propio validado por capa
con 0 % de RGB desconocido, mosaico y política de concurrencia de descarga) ya quedó diseñada
y validada en las Fases 2D.1-2D.4 (`docs/11_fuentes_bosque_deforestacion.md`). El siguiente
paso natural, no implementado en este MVP, es ejecutar la adquisición nacional con esa
arquitectura y extender la cobertura forestal confirmada de Puerto Rico (Meta) a las 1.122
unidades territoriales.

## Limitaciones (resumen — detalle en `docs/MVP_LIMITACIONES.md`)

- No afirma causalidad ambiental entre minería, agua o bosque.
- No detecta ni acusa minería ilegal (solo catastro minero formal vigente).
- No clasifica legalmente la calidad del agua.
- No confirma deforestación a nivel nacional — solo Puerto Rico (Meta) tiene piloto forestal validado.
- No opera en tiempo real; cada fuente tiene su propio corte temporal.

## Reglas de trabajo del proyecto

1. Trabajo restringido a esta carpeta del repositorio.
2. No se leen, borran, mueven ni modifican archivos fuera de esta carpeta.
3. No se instalan paquetes globales; todo el trabajo usa el entorno virtual local `venv`.
4. No se ejecutan comandos destructivos.
5. No se hace push a repositorios remotos.
6. No se usan servicios pagos.
7. No se descargan archivos pesados sin avisar previamente.
8. No se inventan datos.
9. No se afirma causalidad ambiental ni minería ilegal; los análisis se limitan a lo que los datos permiten sustentar.
