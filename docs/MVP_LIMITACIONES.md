# Limitaciones del MVP — AquaBosque Minero IA

## Alcance de causalidad

Este producto **no establece causalidad ambiental** entre minería, calidad de agua o
deforestación. La coincidencia territorial de una alta presión minera, una señal hídrica
atípica y detecciones DTD **no implica que una cause la otra** — son tres fuentes
independientes, combinadas únicamente para priorización de revisión técnica.

## Minería

- El catastro minero refleja **títulos formales vigentes**; el modelo **no detecta ni acusa
  minería ilegal**.
- `score_presion_minera=0` significa ausencia real de títulos registrados, no ausencia de
  actividad minera de cualquier tipo.
- El corte de actualización del catastro está documentado en
  `data/raw/mineria/catastro_minero_anm/*.metadata.json` — no es información en tiempo real.

## Calidad de agua

- El MVP **no clasifica legalmente la calidad del agua** ni aplica límites normativos
  (resoluciones de potabilidad, vertimientos, etc.).
- La "anomalía hídrica" es una **desviación estadística respecto a la distribución nacional del
  mismo parámetro+unidad** — un percentil alto no equivale a "agua contaminada", solo a un valor
  poco común frente al resto del país.
- Resultados **censurados** (bajo el límite de detección) se excluyen del cálculo estadístico —
  el score no penaliza ni premia la censura, solo usa datos cuantificados.
- 950 de 1.122 municipios (≈85 %) no tienen suficiente monitoreo hídrico evaluable con
  parámetros Nivel A — para esos, `score_senal_hidrica` queda `NaN`, explícitamente marcado
  como brecha de información, nunca como "sin problema".

## Bosque y deforestación

- **Solo Puerto Rico (Meta)** tiene bosque/deforestación confirmados con el piloto WCS IDEAM
  real. Los demás 1.121 municipios **no tienen** esta confirmación en el MVP — la ausencia de
  dato **nunca** equivale a "cero deforestación".
- La arquitectura para extender esta cobertura a nivel nacional ya fue diseñada y validada
  (Fases 2D.1-2D.4: grilla fija de 896 tiles, colormap propio por capa con 0 % de RGB
  desconocido) pero **no se ejecutó** la descarga nacional — queda fuera del alcance de este
  MVP.

## Detecciones tempranas de deforestación (DTD)

- Las detecciones DTD son **posibles** eventos de cambio, no deforestación confirmada ni
  cuantificada en hectáreas — nunca se convierten puntos en área.
- `cod_dtd` no es un identificador único de fila (hasta 12,8 % de un trimestre puede compartir
  un código placeholder, Fase 2D.2) — el MVP usa conteos de registros/coordenadas/núcleos, no
  `cod_dtd` distintos, como medida principal.
- Solo se usa el periodo 2025-IV (el más reciente completo); no refleja tendencias históricas.

## Modelo IA (IsolationForest)

- Es un modelo **no supervisado** entrenado sobre ~1.122 filas con variables imputadas por
  mediana donde faltan — no es un clasificador validado externamente ni un modelo predictivo.
- `contamination=0.10` es un parámetro de configuración (10 % más atípico), no una estimación
  de prevalencia real de ningún fenómeno.
- La "explicación" de cada anomalía son las 2 variables con mayor desviación respecto a la
  media del país — es una aproximación transparente y determinística, no una atribución causal
  ni una técnica de explicabilidad tipo SHAP.
- **Nunca** se presenta como: probabilidad de contaminación, predicción de deforestación,
  riesgo de minería ilegal, o cualquier enunciado de causalidad ambiental.

## Actualización y tiempo real

- Cada fuente (ANM, IDEAM agua, IDEAM DTD) tiene su propio corte temporal, documentado en los
  metadatos de `data/raw/`. El producto **no opera en tiempo real** — refleja el estado de las
  fuentes al momento de la última ejecución de `scripts/24_build_mvp_dataset.py`.

## Escalabilidad no implementada en este MVP

- No hay autenticación, API ni base de datos — es una aplicación de un solo archivo
  (`app.py`) sobre CSVs locales, pensada para demostración, no para producción.
- No se han calculado indicadores para las 1.122 unidades a nivel de bosque nacional (fuera de
  alcance, ver Fases 2D — riesgo pendiente documentado).
