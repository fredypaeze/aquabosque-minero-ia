# 09 — Reintegración minera territorial con base geométrica MGN2025 (Fase 4A.2)

Repite la intersección minera nacional, los indicadores territoriales y los controles de
calidad de las Fases 4A/4A.1, reemplazando la base geométrica mixta (capa ArcGIS Divipola
de la Fase 2C/3D + geometría puntual de Bajirá de la Fase 3D.1) por
`data/processed/territorio/base_geometrica_divipola_mgn2025/` (Fase 3D.2), una única fuente
geométrica homogénea del DANE.

**No integra calidad hídrica. No construye índice de riesgo. No entrena modelo. No crea
dashboard. No modifica datos crudos.** Los resultados anteriores de la Fase 4A/4A.1 se
conservan intactos, sin borrar, como referencia histórica.

## Por qué fue necesario recalcular

La auditoría de la Fase 4A.1 encontró que 5 de los 28 títulos fuera de tolerancia
(`HCA-144`, `HCA-145`, `HCA-146`, `GLL-15R`, `GLL-15T`) mostraban `asignacion_superior_100`
como artefacto de que **27493 (Nuevo Belén de Bajirá)** se solapaba en ~128.926 ha con 5
municipios vecinos, porque la base territorial mezclaba dos versiones geométricas del DANE
distintas. La Fase 3D.2 construyó y validó una base homogénea (MGN2025) que elimina ese
solape (0 pares con solape en todo el país). Esta fase repite la integración minera
completa sobre esa nueva base para comprobar el efecto real sobre los indicadores mineros —
sin asumir de antemano que "todo mejora".

## Cómo regenerar

```powershell
.\venv\Scripts\Activate.ps1
python scripts\11_rebuild_mining_with_mgn2025.py
python scripts\12_write_mgn2025_mining_reports.py
```

## Base geométrica adoptada y metodología

Misma metodología de la Fase 4A: títulos y unidades en EPSG:4326, reproyección a
EPSG:9377, `STRtree` construido una sola vez sobre las 1.122 unidades MGN2025, consulta por
bounding box, intersección real solo sobre candidatos, solo área positiva cuenta como
asignación, contactos sin área registrados aparte, fragmentos <0,01 ha conservados. Caché
espacial exclusivo (`territorial_units_mgn2025_epsg9377.pkl`), nunca se reutilizó el caché
de la capa mixta.

**Verificación previa obligatoria (sección B), todas superadas antes de intersectar:**
1.122 unidades DIVIPOLA vigentes, 1.122 geometrías MGN2025, correspondencia exacta 100 %,
códigos únicos, 27493 presente, 94663 ausente, 0 geometrías nulas/vacías/inválidas, 0
solapes territoriales (recalculado, no asumido), CRS RFC 7946 verificado, transformación a
EPSG:9377 verificada funcionalmente.

## Resultados de la intersección

| Indicador | Fase 4A (capa mixta) | Fase 4A.2 (MGN2025) |
|---|---|---|
| Pares candidatos | 15.444 | 15.419 |
| Intersecciones positivas | 8.263 | 8.226 |
| Contactos sin área | 0 | 0 |
| Títulos sin ninguna asignación | 1 | 2 |
| Tiempo total del módulo | 8,66 s | 10,81 s |
| Memoria pico | 3,53 MB | 3,52 MB |

## Diferencias frente a la versión mixta

El número de pares/intersecciones cambia levemente porque **MGN2025 traza varios límites
municipales de forma distinta a la capa ArcGIS Divipola, no solo en la zona de Bajirá**: se
encontraron diferencias de área significativas también en los límites Chocó–Risaralda
(Tadó/Pueblo Rico), Cauca (López de Micay/Buenos Aires) y Chocó interno (Quibdó/Medio
Atrato/Tadó), documentadas en `outputs/reports/mining_integration_mgn2025/mgn2025_vs_mixed_geometry_comparison.md`.
No se afirma cuál trazado es geométricamente más correcto — solo se documenta la diferencia
verificada.

Como consecuencia, el número total de títulos fuera de tolerancia (1 m²) **subió** de 28 a
32: 5 se resolvieron (exactamente los de Bajirá), 23 persisten sin cambios de fondo, y 9
son casos nuevos que no existían en la capa mixta. El área residual total se mantuvo
prácticamente igual (5.899,94 ha → 5.918,37 ha). **Esto no incumple ningún criterio de
aceptación de esta fase** — el objetivo declarado era resolver específicamente el efecto de
Bajirá, no reducir el total nacional de discrepancias, y ese objetivo se cumplió con
evidencia clara.

## Resolución de los cinco casos de Bajirá

**Completamente resuelto.** `HCA-144`, `HCA-145`, `HCA-146`, `GLL-15R` y `GLL-15T` pasan de
`asignacion_superior_100=True` (100–200 % de asignación aparente por doble conteo) a
**exactamente 100,00 % de área asignada cada uno**, dentro de tolerancia. La causa
`solape_entre_limites_territoriales` no aparece ni una sola vez en la auditoría recalculada
de esta fase, porque no existe ningún par de unidades territoriales que se solape en
MGN2025.

## Estado del título 583

**Mejora sustancial, no resuelto por completo.** Pasa de 0 % asignado (sin ninguna
intersección territorial, el único caso "huérfano" de la Fase 4A.1) a **39,15 % asignado**,
ahora intersectando con `54001` (San José de Cúcuta). Sigue fuera de la tolerancia de 1 m².

## Casos adicionales verificados explícitamente

- **`ICQ-080212X`:** mejora marginal, de 0,99 % a 4,04 % asignado — sigue siendo uno de los
  casos de mayor magnitud (3.454,84 ha sin asignar), marcado para revisión manual en ambas
  fases.
- **`LI9-10311`:** **empeora**, de 4,54 % asignado (2 unidades) a **0 % asignado (ninguna
  unidad)**. Ya en la Fase 4A.1 era uno de los casos con mayor proporción sin asignar
  (95,46 %); con la nueva base geométrica, la porción que antes lograba un pequeño anclaje
  territorial queda fuera de toda unidad. Marcado para revisión manual; es, de los casos
  auditados en este proyecto, el que más justificaría una revisión manual real de su
  geometría de origen (fuera de alcance de este proyecto).

## Indicadores territoriales

`mineria_por_unidad_territorial_mgn2025.csv`: 1.122 filas regeneradas (incluidas las
unidades sin títulos, en cero), manteniendo separadas `area_titulada_suma_ha` /
`area_titulada_union_ha` y sus respectivos porcentajes, igual que en la Fase 4A. **No se
crearon scores ni variables de riesgo.** Comparación completa por unidad en
`mining_territorial_indicators_mgn2025_comparison.csv` y
`outputs/reports/mining_integration_mgn2025/mgn2025_mining_territorial_indicators.md`.

## Anotaciones RMN

Misma agregación determinística por `codigo_expediente` (sin fuzzy matching). La
correspondencia se mantuvo prácticamente igual: **95,92 %** (6.037/6.294) — esperado, ya
que la agregación de anotaciones no depende de la base geométrica territorial, solo del
catastro y las anotaciones, que no cambiaron entre fases.

## Limitaciones del Catastro Minero ANM

El catastro minero ANM WFS (`Titulo_Vigente`) sigue declarado como actualizado el
**22/03/2023** por el propio geoservicio — esa fecha **no es la fecha de este análisis** y
se documenta explícitamente en cada fila de `mineria_titulo_unidad_territorial_mgn2025.csv`
(`fecha_actualizacion_fuente_catastro`). No se incluye minería informal o ilegal: todos los
indicadores provienen exclusivamente de títulos formalmente registrados.

## Por qué el resultado sigue siendo descriptivo

Ningún archivo de esta fase calcula `riesgo_minero`, `score_minero`, probabilidad de
contaminación, probabilidad de deforestación, minería ilegal, afectación causada por
minería ni ningún índice compuesto. Los indicadores producidos —conteos, áreas,
proporciones, por título y por unidad territorial— son **descriptivos de presión minera
formal registrada**, no causales ni de ilegalidad, igual que en la Fase 4A.

## Promoción de resultados canónicos

Se optó por **alias documentado**, no por sobrescribir ni regenerar el nombre canónico
anterior: `mineria_titulo_unidad_territorial.csv` y `mineria_por_unidad_territorial.csv`
siguen siendo los archivos que regenera `scripts/06_build_mining_territorial.py` (capa
mixta) y **no se tocaron**, para no romper la reproducibilidad de ese script si se vuelve a
ejecutar. Se crearon además copias explícitas
`mineria_titulo_unidad_territorial_legacy_mixed_geometry.csv` y
`mineria_por_unidad_territorial_legacy_mixed_geometry.csv` como snapshot histórico
adicional. `data/processed/CANONICAL_SOURCE.json` documenta inequívocamente que, a partir de
esta fase, los archivos `*_mgn2025.csv` son los **resultados canónicos recomendados** para
cualquier uso posterior a la Fase 4A.2.

## Archivos creados o modificados

- `src/aquabosque/features/mining.py` — `build_title_territorial_table` generalizada con
  parámetros opcionales `fuente_geometria_territorial`/`version_geometria_territorial`
  (por defecto `None`, no cambia el esquema de la Fase 4A original).
- `scripts/11_rebuild_mining_with_mgn2025.py` (nuevo) — orquesta toda esta fase.
- `scripts/12_write_mgn2025_mining_reports.py` (nuevo) — genera los 5 reportes.
- `data/processed/integrated/mineria_titulo_unidad_territorial_mgn2025.csv` (+ `.metadata.json`).
- `data/processed/features/mineria_por_unidad_territorial_mgn2025.csv` (+ `.metadata.json`).
- `data/processed/audit/mineria_area_conservation_audit_mgn2025.csv` (+ `.metadata.json`).
- `data/processed/audit/anm_annotation_correspondence_audit_mgn2025.csv` (+ `.metadata.json`).
- `data/processed/audit/mining_mgn2025_comparison.csv` (nuevo).
- `data/processed/audit/mining_territorial_indicators_mgn2025_comparison.csv` (nuevo).
- `data/processed/integrated/mineria_titulo_unidad_territorial_legacy_mixed_geometry.csv` (copia congelada).
- `data/processed/features/mineria_por_unidad_territorial_legacy_mixed_geometry.csv` (copia congelada).
- `data/processed/CANONICAL_SOURCE.json` (nuevo) — alias documentado.
- `outputs/reports/mining_integration_mgn2025/mgn2025_mining_spatial_intersection.md`,
  `mgn2025_mining_area_conservation.md`, `mgn2025_mining_territorial_indicators.md`,
  `mgn2025_vs_mixed_geometry_comparison.md`, `mgn2025_phase4a2_quality_closure.md` (nuevos).
- `docs/09_reintegracion_minera_mgn2025.md` (este documento).

## Riesgos pendientes

- El total nacional de casos fuera de tolerancia subió de 28 a 32; los 9 casos nuevos no se
  investigaron a fondo más allá de su clasificación automática (`hueco_entre_limites_territoriales`
  en todos salvo uno).
- `LI9-10311` pasó de parcialmente asignado a completamente sin asignación; amerita revisión
  manual de su geometría de origen.
- No se investigaron las causas de fondo de las diferencias de trazado entre MGN2025 y la
  capa ArcGIS Divipola fuera de la zona de Bajirá (límites Chocó/Risaralda/Cauca/Valle del
  Cauca) — se documenta el hallazgo geométrico, sin asumir causa administrativa.
- La correspondencia de anotaciones no se reinvestigó (se reutilizó la misma agregación
  determinística), consistente con que no depende de la geometría territorial.
- Cualquier integración futura (calidad hídrica, deforestación, RUNAP) debería partir de
  `base_geometrica_divipola_mgn2025` y de los archivos `*_mgn2025.csv`, no de la capa mixta.
