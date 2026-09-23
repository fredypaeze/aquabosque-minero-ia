# D03 - VERSIONES Y CONTROL DE CAMBIOS

## Control de Versiones del Proyecto

El proyecto AquaBosque Minero IA utiliza Git como sistema de control de versiones, manteniendo un historial completo de cambios y releases. La rama principal del proyecto se encuentra en `feature/capa-incendios`, que incluye las últimas actualizaciones del sistema.

## Historial Reciente de Commits

Los últimos commits reflejan mejoras en la funcionalidad satelital y de análisis de datos:

1. **945232a** - auditoría de datos: perfilado con ydata-profiling (sucesor de pandas-profiling)
2. **9a05e82** - satelital: explorador 100% dinámico por municipio
3. **698d571** - satelital: KPI de focos con señal NRT fresca + imagen GIBS del último día publicado
4. **f5698a1** - incendios: capa nacional de crisis (detectar-medir-priorizar)
5. **c181080** - datos: refresco señal FIRMS nacional (4.326 focos, 328 municipios, corte 25-ago-2026)
6. **7eee6be** - satelital: completa set de 5 hotspots reales (result.json + index)
7. **d6f73d1** - satelital: deforestación REAL por municipio (Sentinel-2 NDVI-change) + retira cifras fabricadas
8. **e7f550a** - rc(zoom-bogota-v1): Capa 4 trazabilidad/ops + cierre (trace, lineage, manifests, informe final)
9. **ace4dbe** - rc(zoom-bogota-v1): Capa 3 — tablero reencuadrado al índice descriptivo (honesto)
10. **405fb91** - rc(zoom-bogota-v1): docs honestos (contract, model card, decision log, validation report)

## Estado Actual del Repositorio

El repositorio muestra cambios no confirmados en varios archivos de datos y código:

### Cambios no confirmados:
- `data/processed/fuego_municipal.csv`
- `data/processed/fuego_summary.json`
- `data/processed/rag_index.npz`
- `data/processed/rag_meta.json`
- `src/aquabosque/asistente/rag.py`
- `validation/validation_results.json`

### Archivos nuevos:
- `documentacion_crispdm/` (directorio de documentación creada por este proceso)
- `outputs/jurado_2026/AquaBosque_Presentacion_CON_RIGOR.pptx`
- `outputs/jurado_2026/GUION_ACTUALIZADO.docx`
- `outputs/jurado_2026/PREGUNTAS_DEFENSA_TECNICA.docx`
- `outputs/rc_v1/gold_localidad_dia.csv`
- `scripts/agregar_lamina_rigor.py`
- `scripts/guion_actualizado_word.py`
- `scripts/preguntas_defensa_word.py`
- `src/aquabosque/asistente/rag.py.bak-20260911`

## Estructura de Versiones

### Versiones Principales del Proyecto

1. **Versión inicial (0.1.0)**: Implementación básica del pipeline de procesamiento
2. **Versión de desarrollo (0.2.0)**: Incorporación de funcionalidades satelitales y mejoras en datos
3. **Versión de concurso (1.0.0)**: Versión final presentada para el Concurso Datos al Ecosistema 2026

### Rama Principal
- **Branch actual**: `feature/capa-incendios`
- **Estado**: Actualizada con respecto a `fredy/feature/capa-incendios`
- **Último commit**: `945232a` - auditoría de datos con ydata-profiling

## Gestión de Cambios

### Archivos de Configuración
- `requirements.txt` - Dependencias principales del proyecto
- `requirements-dev.txt` - Dependencias de desarrollo
- `requirements-profiling.txt` - Dependencias de profiling

### Scripts de Ejecución
- `run_mvp.sh` - Script de ejecución completa del MVP
- `run_mvp.ps1` - Script de ejecución completa del MVP (Windows)

### Documentación de Versiones
- `VERSION.md` - Archivo de control de versiones (si existe)

## Estado de Implementación por Componente

### Componentes Estables
- Pipeline de procesamiento principal (01-06)
- Dashboard Streamlit
- Modelo de machine learning XGBoost + SHAP
- Documentación técnica completa

### Componentes en Desarrollo
- Funcionalidades satelitales (capa de incendios)
- Sistema RAG (Retrieval-Augmented Generation)
- Funcionalidades de zoom de Bogotá

## Próximos Pasos

1. Verificación de la trazabilidad de datos desde el commit inicial
2. Análisis de las modificaciones recientes en componentes satelitales
3. Validación de la integridad de los datos procesados
4. Documentación de la estructura de versiones y control de cambios

## Referencias

- Sistema de control de versiones Git
- Metodología de gestión de versiones del proyecto
- Historial de commits del repositorio