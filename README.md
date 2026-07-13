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

## Instalación

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución

```powershell
# Opción 1: script de arranque (genera el dataset si falta y abre la app)
.\run_mvp.ps1

# Opción 2: manual
python scripts/24_build_mvp_dataset.py   # genera data/processed/mvp/*.csv y el modelo
python -m streamlit run app.py
```

## Estructura relevante del MVP

```
scripts/24_build_mvp_dataset.py   # construye el dataset integrado, el score y el modelo IA
app.py                             # aplicación Streamlit
models/isolation_forest_mvp.joblib # modelo entrenado
data/processed/mvp/                # dataset de entrega (regenerable, no versionado)
docs/MVP_METODOLOGIA.md            # metodología detallada
docs/MVP_LIMITACIONES.md           # limitaciones explícitas
docs/DEMO_GUION.md                 # guion de demo (máx. 4 minutos)
```

Para la estructura completa del repositorio (fases forestales/hídricas/mineras previas), ver
`docs/01` a `docs/11`.

## Limitaciones (resumen — detalle en `docs/MVP_LIMITACIONES.md`)

- No afirma causalidad ambiental entre minería, agua o bosque.
- No detecta ni acusa minería ilegal (solo catastro minero formal vigente).
- No clasifica legalmente la calidad del agua.
- No confirma deforestación a nivel nacional — solo Puerto Rico (Meta) tiene piloto forestal validado.
- No opera en tiempo real; cada fuente tiene su propio corte temporal.

## Escalabilidad

El dataset y el modelo son reproducibles ejecutando `scripts/24_build_mvp_dataset.py` sobre
datos actualizados. La arquitectura forestal nacional (grilla fija de 896 tiles, colormap
validado por capa) ya quedó diseñada y validada en las Fases 2D.1-2D.4
(`docs/11_fuentes_bosque_deforestacion.md`) para una futura adquisición de la serie completa —
extender la cobertura forestal confirmada a las 1.122 unidades es el siguiente paso natural, no
implementado en este MVP.

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
