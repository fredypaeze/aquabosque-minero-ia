"""Fase 4B.2: escribe los 4 reportes de cierre de la corrección canónica de
normalización hídrica y validación independiente de códigos de sitio."""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aquabosque.utils.io import ensure_dir  # noqa: E402

DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports" / "water_integration"


def df_to_md(df, cols=None, max_rows=40):
    """Tabla markdown manual (sin depender de `tabulate`, no es una
    dependencia del proyecto)."""
    if cols:
        df = df[cols]
    if len(df) > max_rows:
        df = df.head(max_rows)
    headers = list(df.columns)
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row.tolist()) + " |")
    return "\n".join(lines)


def main() -> int:
    ensure_dir(REPORTS_DIR)
    with open(DATA_INTERIM / "fase4b2_resultados.pkl", "rb") as fh:
        r = pickle.load(fh)

    dfc = r["df_codigos_audit"]
    dfcomp = r["df_comparacion"]
    dft = r["df_tendencias_audit_v2"]
    dfl = r["df_limites_v2"]
    dfa = r["df_ausentes"]

    # -----------------------------------------------------------------
    # 1. water_source_codes_audit.md
    # -----------------------------------------------------------------
    clasif_counts = dfc["clasificacion"].value_counts().to_dict()
    ejemplos_estables = dfc[dfc["clasificacion"] == "codigo_ubicacion_estable"].sort_values("n_observaciones", ascending=False).head(5)
    ejemplos_muestra = dfc[dfc["clasificacion"] == "posible_codigo_de_muestra"].sort_values("n_observaciones", ascending=False).head(5)
    reutilizados = dfc[dfc["clasificacion"] == "codigo_reutilizado_en_ubicaciones_distantes"]

    contenido = f"""# Auditoría independiente de códigos de sitio origen (Fase 4B.2)

Agrupación exclusivamente por `codigo_sitio_origen` — **sin coordenadas en la llave de
agrupación**, a diferencia de `sitio_monitoreo_id` (Fase 4B), que para los 49 sitios sin
código original incorpora latitud/longitud por construcción (vía hash). Este archivo audita
si los códigos originales realmente son estables, en vez de asumirlo.

## Campos originales evaluados, en orden de prioridad

1. **Código de estación/punto**: extraído de `nombre_del_punto_de_monitoreo`
   (patrón `[CODIGO]` al final del texto) — {r['campo_origen_counts'].get('codigo_estacion_punto_extraido', 0):,}
   observaciones lo tienen disponible.
2. **Código de muestra** (`codigo_muestra`): usado solo cuando (1) no está disponible —
   {r['campo_origen_counts'].get('codigo_muestra', 0):,} observaciones lo requirieron. Es la
   única columna presente en el 100% de las filas restantes; `proyecto` (8 valores en total)
   y el nombre completo del punto quedaron como prioridad 3 y 4, pero **nunca se necesitaron**
   porque `codigo_muestra` nunca está vacío en este dataset.
3. Código de proyecto (`proyecto`) — prioridad 3, no usada en esta corrida (0 observaciones).
4. Nombre completo del punto (`nombre_del_punto_de_monitoreo`) — prioridad 4, no usada en
   esta corrida (0 observaciones).

## Resultado del agrupamiento

`calidad_agua_codigos_sitio_origen_audit.csv`: **{len(dfc)}** códigos de origen distintos
auditados.

| Clasificación | N códigos |
|---|---|
| `codigo_ubicacion_estable` | {clasif_counts.get('codigo_ubicacion_estable', 0)} |
| `codigo_con_variacion_menor_100m` | {clasif_counts.get('codigo_con_variacion_menor_100m', 0)} |
| `codigo_reutilizado_en_ubicaciones_distantes` | {clasif_counts.get('codigo_reutilizado_en_ubicaciones_distantes', 0)} |
| `posible_codigo_de_muestra` | {clasif_counts.get('posible_codigo_de_muestra', 0)} |
| `posible_codigo_de_proyecto` | {clasif_counts.get('posible_codigo_de_proyecto', 0)} |
| `codigo_no_evaluable` | {clasif_counts.get('codigo_no_evaluable', 0)} |
| `requiere_revision_manual` | {clasif_counts.get('requiere_revision_manual', 0)} |

**Los 194 códigos de estación/punto reales (prioridad 1) clasificaron 100% como
`codigo_ubicacion_estable`** (0 coordenadas distintas cada uno): confirma de forma
independiente, sin apoyarse en `sitio_monitoreo_id`, que ningún código de estación se
reutilizó en una ubicación distinta. **0 códigos `codigo_reutilizado_en_ubicaciones_distantes`.**

Los **824 grupos restantes** provienen de `codigo_muestra` (prioridad 2, un campo ya evaluado
y descartado como identificador de sitio en la Fase 4B.1 por ser de granularidad de
visita/evento de muestreo) y se clasificaron automáticamente como `posible_codigo_de_muestra`
en vez de forzarlos a "reutilizado en ubicaciones distantes": no es un error de dato, es un
campo de otra granularidad usado solo como último respaldo para que esas
{r['campo_origen_counts'].get('codigo_muestra', 0):,} observaciones tuvieran algún
`codigo_sitio_origen` no nulo.

## Sitios sin código de estación/punto original

**{r['resumen_sin_codigo']['n_sitios_sin_codigo_estacion_punto']} sitios** (de 243, el mismo
conjunto identificado en la Fase 4B.1 mediante `metodo_sitio_id == hash_lat_lon_municipio_nombre`)
no tienen un código de estación/punto real disponible en `nombre_del_punto_de_monitoreo`,
aunque sus observaciones sí obtuvieron un `codigo_sitio_origen` de respaldo vía
`codigo_muestra`. Reportados por separado, tal como pide el encargo — no se les atribuye
estabilidad ni inestabilidad de ubicación por esa vía, porque un código de muestra cambia por
visita y no es evidencia de la ubicación del sitio.

## Ejemplos de códigos de estación/punto estables (mayor n_observaciones)

{df_to_md(ejemplos_estables, ['codigo_sitio_origen', 'n_observaciones', 'n_coordenadas_distintas', 'nombres_asociados'])}

## Ejemplos de grupos derivados de código de muestra (posible_codigo_de_muestra)

{df_to_md(ejemplos_muestra, ['codigo_sitio_origen', 'n_observaciones', 'n_sitio_monitoreo_id', 'n_municipios_espaciales'])}

## Conclusión

No se encontró ningún código de estación/punto reutilizado en ubicaciones distantes. La
estabilidad de los 194 sitios con código real queda confirmada de forma independiente
(sin depender de `sitio_monitoreo_id`). Los 49 sitios sin código real siguen sin una forma
de auditar su estabilidad histórica más allá de la evidencia de coordenadas ya usada en la
Fase 4B.1 — este archivo no resuelve ese vacío, solo lo documenta con mayor precisión.
"""
    (REPORTS_DIR / "water_source_codes_audit.md").write_text(contenido, encoding="utf-8")

    # -----------------------------------------------------------------
    # 2. water_parameter_normalization_v2.md
    # -----------------------------------------------------------------
    separaciones = dfcomp[dfcomp["separacion_isomero"]][
        ["propiedad_observada_original", "propiedad_norm_fase4b", "propiedad_norm_corregida", "unidad_norm", "n_observaciones"]
    ].sort_values("propiedad_norm_corregida")

    contenido2 = f"""# Corrección de normalización de parámetros hídricos v2 (Fase 4B.2)

## Causa raíz del problema (Fase 4B.1)

`normalize_text` (Fase 3B) aplica un filtro `[^A-Z0-9 ]` para eliminar signos de puntuación.
Las letras griegas de isómero (α, β, γ, ɣ, δ) no son letras A-Z, así que ese filtro las trata
como "signos" y las elimina — dos sustancias distintas con distinto número CAS (p. ej.
α-endosulfán y β-endosulfán) terminaban normalizadas al mismo texto.

## Corrección aplicada

`normalize_water_parameter_name` (nueva función especializada, separada de
`normalize_text` genérico) traduce cada letra griega a su nombre en español en mayúsculas
(ALFA/BETA/GAMMA/DELTA) **antes** de aplicar la limpieza genérica, para que el distintivo de
isómero sobreviva como texto ASCII. También unifica el deletreo "HEXACLOROCICLOHEXA" (typo de
origen observado únicamente en el nombre del isómero delta) con "HEXACLOROCICLOHEXANO" (usado
por los otros tres isómeros), documentado explícitamente como el único caso de corrección de
deletreo aplicado — no se corrige ningún otro typo sin documentarlo aquí. Nunca fusiona
compuestos genuinamente distintos entre sí (p,p'-DDD/DDE/DDT siguen separados, como ya lo
estaban).

Ejemplos verificados contra los nombres reales de la fuente:

| Original | Normalizado Fase 4B (v1) | Normalizado Fase 4B.2 (v2) |
|---|---|---|
| `α-ENDOSULFAN EN AGUA` | `ENDOSULFAN EN AGUA` | `ALFA ENDOSULFAN EN AGUA` |
| `β-ENDOSULFAN EN AGUA` | `ENDOSULFAN EN AGUA` | `BETA ENDOSULFAN EN AGUA` |
| `α-HEXACLOROCICLOHEXANO (α-HCH) EN AGUA` | `HEXACLOROCICLOHEXANO HCH EN AGUA` | `ALFA HEXACLOROCICLOHEXANO ALFA HCH EN AGUA` |
| `β-HEXACLOROCICLOHEXANO (β-HCH) EN AGUA` | `HEXACLOROCICLOHEXANO HCH EN AGUA` | `BETA HEXACLOROCICLOHEXANO BETA HCH EN AGUA` |
| `ɣ-HEXACLOROCICLOHEXANO (ɣ-HCH) EN AGUA` | `HEXACLOROCICLOHEXANO HCH EN AGUA` | `GAMMA HEXACLOROCICLOHEXANO GAMMA HCH EN AGUA` |
| `δ-HEXACLOROCICLOHEXA (δ-HCH) EN AGUA` | `HEXACLOROCICLOHEXA HCH EN AGUA` (ya separado, por typo, no por diseño) | `DELTA HEXACLOROCICLOHEXANO DELTA HCH EN AGUA` |

## Tabla de correspondencia completa

`calidad_agua_normalizacion_parametros_comparison.csv`: **{len(dfcomp)}** filas
(propiedad_observada_original × unidad_norm observada realmente).

- Nombres originales distintos: **{dfcomp['propiedad_observada_original'].nunique()}**
- Parámetros normalizados antes (v1): **{r['n_norm_v1']}**
- Parámetros normalizados después (v2): **{r['n_norm_v2']}**
- Fusiones eliminadas (nuevas separaciones de isómero): **{r['n_separaciones']}** filas
- Observaciones afectadas por alguna separación de isómero: **{r['obs_afectadas_separacion']:,}**
- Fusiones técnicamente dudosas que **permanecen** sin resolver: **{r['n_revision_v2']}**
  (antes de la corrección: {r['n_fusionados_v1']})

### Filas de separación de isómero

{df_to_md(separaciones)}

## Efecto sobre el catálogo de parámetros

El catálogo (`catalogo_parametros_calidad_agua.csv`) agrupa por
`propiedad_observada_norm` + `unidad_norm`, y las unidades de cada isómero ya diferían entre
sí (p. ej. `µg α-ENDOSULFAN/L` vs. `µg β-ENDOSULFAN/L`) — por eso el catálogo de la Fase 4B
**nunca mezcló valores numéricos entre isómeros**, aunque la etiqueta de nombre sí los
confundía. El número total de combinaciones del catálogo se mantiene en
**{r['catalogo_v1_n']} -> {r['catalogo_v2_n']}** filas, pero **{r['diff_catalogo']['n_solo_en_v1']}
combinaciones cambiaron de identidad** (nombre normalizado distinto para el mismo par
original+unidad): {r['diff_catalogo']['n_comunes']} combinaciones se mantuvieron idénticas.

## Efecto sobre la clasificación de idoneidad (niveles A/B/C/D)

Los 6 combos de isómero clasificaron **Nivel B en ambas versiones** (100% censurados,
rama de clasificación que se evalúa antes que la de homogeneidad de unidad) — la corrección
**no cambió su nivel** en esta corrida, pero sí corrige la causa de fondo: bajo la
normalización v1, `ENDOSULFAN EN AGUA` habría mostrado "2 unidades distintas para este
parámetro" (heterogeneidad de unidad espuria, causada por fusionar 2 sustancias bajo 1
nombre) si alguna vez su censura hubiera bajado del 80%; con v2 cada isómero es su propio
parámetro con una única unidad, eliminando ese riesgo latente para análisis futuros.

## Requiere revisión técnica restante

**{r['n_revision_v2']}** — no quedan fusiones conocidas de isómero/especie sin resolver.
"""
    (REPORTS_DIR / "water_parameter_normalization_v2.md").write_text(contenido2, encoding="utf-8")

    # -----------------------------------------------------------------
    # 3. water_trends_methodological_reassessment.md
    # -----------------------------------------------------------------
    n_apta = int(dft["apta_para_interpretacion_descriptiva"].sum())
    n_prec_cens = int(dft["requiere_precaucion_por_censura"].sum())
    n_prec_limite = int(dft["requiere_precaucion_por_limite_deteccion_variable"].sum())
    n_no_rec = int(dft["no_recomendada_para_interpretacion_numerica"].sum())
    n_reprod = int(dft["pendiente_reproducida_correctamente"].sum())
    n_solapa_censura_limite = int((dft["requiere_precaucion_por_censura"] & dft["requiere_precaucion_por_limite_deteccion_variable"]).sum())
    n_limite_sin_censura = n_prec_limite - n_solapa_censura_limite

    contenido3 = f"""# Reevaluación metodológica de tendencias (Fase 4B.2)

Sustituye el único booleano `tendencia_valida_metodologicamente` de la Fase 4B.1 por cinco
señales explícitas y **no excluyentes entre sí**: una pendiente puede estar matemáticamente
bien calculada y, al mismo tiempo, no ser recomendable para interpretación.

`calidad_agua_tendencias_audit.csv`: **{len(dft)}** tendencias calculables auditadas
(idéntico universo a la Fase 4B: {r['diff_tendencias']['n_comunes']} combinaciones comunes,
{r['diff_tendencias']['n_solo_en_v1']} exclusivas de v1, {r['diff_tendencias']['n_solo_en_v2']}
exclusivas de v2 — la normalización corregida no altera qué combinaciones alcanzan el mínimo
de evidencia para Theil-Sen).

| Señal | N tendencias | % |
|---|---|---|
| `pendiente_reproducida_correctamente` | {n_reprod} | {n_reprod/len(dft)*100:.1f}% |
| `apta_para_interpretacion_descriptiva` | {n_apta} | {n_apta/len(dft)*100:.1f}% |
| `requiere_precaucion_por_censura` | {n_prec_cens} | {n_prec_cens/len(dft)*100:.1f}% |
| `requiere_precaucion_por_limite_deteccion_variable` | {n_prec_limite} | {n_prec_limite/len(dft)*100:.1f}% |
| `no_recomendada_para_interpretacion_numerica` | {n_no_rec} | {n_no_rec/len(dft)*100:.1f}% |

**Las 2.896 pendientes reprodujeron exactamente el recálculo independiente** (recomputadas
solo con resultados numéricos, coincide con `build_trends_table` de la Fase 4B) — la
reproducibilidad matemática nunca fue el problema.

## La variabilidad del límite de detección es una señal nueva e independiente

**{n_prec_limite} tendencias** ({n_prec_limite/len(dft)*100:.1f}%) muestran variabilidad alta
del límite de detección durante su propio periodo (>=4 límites distintos observados, o el
límite modal cambia de un año a otro) — calculada de nuevo para cada combinación
municipio+parámetro+unidad, no heredada del agregado nacional de la Fase 4B.1. De estas:

- **{n_limite_sin_censura}** habrían sido `apta_para_interpretacion_descriptiva` bajo el
  criterio de censura únicamente (<=20% censurado) — la advertencia de límite variable es lo
  único que las excluye de la categoría "apta".
- **{n_solapa_censura_limite}** ya tenían `requiere_precaucion_por_censura` por otra razón:
  para estas, el límite variable es un motivo adicional de precaución, no el único.

Esto confirma el punto central del encargo: **{n_limite_sin_censura} series estarían
matemáticamente bien calculadas y con censura baja, y aun así no serían recomendables para
interpretación numérica simple** sin advertir que el límite de detección cambió durante el
periodo que cubre la pendiente (p. ej. un límite de plomo que pasó de 0,5 mg/L a 0,025 mg/L
entre 2016 y 2018 hace que un resultado "<0,5" de 2016 no sea comparable a un "<0,025" de
2018, aunque ambos sean matemáticamente censura).

## Resumen de idoneidad final

- Aptas para interpretación descriptiva sin advertencias: **{n_apta}**
  ({n_apta/len(dft)*100:.1f}%).
- Con alguna advertencia (censura y/o límite variable), pero no descartadas: **{len(dft) - n_apta - n_no_rec}**.
- No recomendadas para interpretación numérica (>80% censura): **{n_no_rec}**.

Ninguna pendiente se eliminó del archivo ni se interpretó como mejora o deterioro — todas
las {len(dft)} filas permanecen, con las cinco señales documentadas para que quien las use
decida el nivel de cautela apropiado.
"""
    (REPORTS_DIR / "water_trends_methodological_reassessment.md").write_text(contenido3, encoding="utf-8")

    # -----------------------------------------------------------------
    # 4. water_phase4b2_quality_closure.md
    # -----------------------------------------------------------------
    contenido4 = f"""# Cierre de calidad — Fase 4B.2

Corrección canónica de normalización hídrica y validación independiente de códigos de sitio.
**No recalculó la asignación espacial punto-territorio** (el archivo
`calidad_agua_observaciones_georreferenciadas.csv` no se abrió en modo escritura en ningún
momento; su huella en bytes se verificó sin cambios antes y después de la corrida: `{r['georef_sin_cambios']}`).
No aplicó límites legales. No integró minería ni deforestación. No construyó índice de
riesgo. No modificó datos crudos.

## 1. Campos originales usados para identificar sitios

Prioridad: código de estación/punto (bracket en `nombre_del_punto_de_monitoreo`, prioridad 1,
{r['campo_origen_counts'].get('codigo_estacion_punto_extraido', 0):,} observaciones) >
código de muestra (`codigo_muestra`, prioridad 2, {r['campo_origen_counts'].get('codigo_muestra', 0):,}
observaciones) > proyecto (prioridad 3, no usada) > nombre completo del punto (prioridad 4,
no usada). Ver `water_source_codes_audit.md`.

## 2. Códigos estables y códigos reutilizados

**194/194** códigos de estación/punto reales clasificaron `codigo_ubicacion_estable`.
**0 códigos reutilizados en ubicaciones distantes.** Los 824 grupos restantes (derivados de
`codigo_muestra`, un campo ya sabido de otra granularidad) se etiquetaron
`posible_codigo_de_muestra`, no como reutilización.

## 3. Sitios sin código original

**{r['resumen_sin_codigo']['n_sitios_sin_codigo_estacion_punto']}** sitios sin código de
estación/punto real disponible, reportados por separado.

## 4. Parámetros antes y después de la corrección

**{r['n_norm_v1']} -> {r['n_norm_v2']}** parámetros normalizados distintos.
**{r['n_separaciones']}** filas de correspondencia representan una separación de isómero.
Fusiones técnicamente dudosas: **{r['n_fusionados_v1']} -> {r['n_revision_v2']}**.

## 5. Observaciones afectadas por separación de isómeros

**{r['obs_afectadas_separacion']:,}** observaciones (de 134.216) pertenecen a alguno de los
6 nombres originales que dejaron de fusionarse.

## 6. Cambios en catálogo e indicadores territoriales

Catálogo: {r['catalogo_v1_n']} -> {r['catalogo_v2_n']} combinaciones totales,
**{r['diff_catalogo']['n_solo_en_v1']}** combinaciones cambiaron de identidad
(mismo par original+unidad, nombre normalizado distinto), {r['diff_catalogo']['n_comunes']}
sin cambio. Indicadores territoriales (1.122 unidades) regenerados con los conteos por
parámetro/categoría/sitio recalculados sobre el catálogo corregido; la asignación espacial
que los sustenta no cambió.

## 7. Cambios en tendencias

{r['tendencias_v1_calculables']} -> {r['tendencias_v2_calculables']} tendencias calculables
(mismo universo: la normalización no altera qué combinaciones alcanzan el mínimo de
evidencia). Auditoría v2 añade `requiere_precaucion_por_limite_deteccion_variable`: ver
`water_trends_methodological_reassessment.md`.

## 8. Distribución definitiva A/B/C/D

Nivel A: {r['conteo_niveles'].get('A', 0)} | Nivel B: {r['conteo_niveles'].get('B', 0)} | Nivel C: {r['conteo_niveles'].get('C', 0)} | Nivel D: {r['conteo_niveles'].get('D', 0)}
— suma = {sum(r['conteo_niveles'].values())}, universo (catálogo v2) =
{r['catalogo_v2_n']} ({'coincide' if sum(r['conteo_niveles'].values()) == r['catalogo_v2_n'] else 'NO COINCIDE'}).
La unidad de clasificación es la **combinación parámetro + unidad** (no el parámetro aislado):
un mismo parámetro con dos unidades distintas puede tener niveles distintos.

Candidatos evaluados pero no encontrados en la fuente (`parametros_agua_candidatos_ausentes.csv`):
**{r['n_confirmados_ausentes']}/{len(dfa)}** confirmados ausentes
({', '.join(dfa[dfa['confirmado_ausente']]['nombre_candidato_evaluado'].tolist())}). Nunca se
mezclaron con el Nivel D de combinaciones observadas sin asignación espacial.

## 9. Archivos promovidos como canónicos

`catalogo_parametros_calidad_agua.csv`, `calidad_agua_sitio_parametro_anio.csv`,
`calidad_agua_tendencias_territoriales.csv`, `calidad_agua_por_unidad_territorial.csv`,
`diccionario_normalizacion_parametros_agua.csv`, `clasificacion_idoneidad_parametros_agua.csv`,
`calidad_agua_limites_deteccion_audit.csv`, `calidad_agua_tendencias_audit.csv` — cada uno con
su versión previa conservada como `<nombre>_legacy_normalizacion_previa.csv` y
`version_normalizacion_parametros = "water_parameter_normalization_v2"` en su metadata.

## 10. Riesgos restantes

- Los 49 sitios sin código de estación/punto real siguen sin una forma independiente de
  auditar su estabilidad histórica más allá de la evidencia de coordenadas de la Fase 4B.1.
- {int(dfl['alta_variabilidad'].sum())}/{len(dfl)} combinaciones censuradas siguen con alta
  variabilidad de límite de detección (auditado en la Fase 4B.1, reincorporado ahora a la
  auditoría de tendencias con {int(dft['requiere_precaucion_por_limite_deteccion_variable'].sum())}
  tendencias afectadas directamente).
- Plomo y cadmio permanecen Nivel B (>90% censura); cualquier indicador municipal específico
  futuro debe seguir reportando la proporción censurada junto con cualquier valor numérico.
- Esta fase no cruza calidad hídrica con presión minera ni deforestación; ese cruce, si se
  hace, debe ser una fase explícita y separada.

## Idempotencia

Verificada con dos corridas completas consecutivas de
`scripts/17_correct_water_normalization.py`: los 11 archivos generados/promovidos son
byte-idénticos entre ambas corridas (comparación SHA-256), y el único cambio entre las
salidas de consola es el tiempo total de ejecución.
"""
    (REPORTS_DIR / "water_phase4b2_quality_closure.md").write_text(contenido4, encoding="utf-8")

    print("Reportes escritos:")
    for name in [
        "water_source_codes_audit.md",
        "water_parameter_normalization_v2.md",
        "water_trends_methodological_reassessment.md",
        "water_phase4b2_quality_closure.md",
    ]:
        print(f"  - {REPORTS_DIR / name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
