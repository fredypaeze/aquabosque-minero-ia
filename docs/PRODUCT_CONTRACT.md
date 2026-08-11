# Product Contract — Zoom Bogotá V1

Fuente de verdad: `config/release_zoom_bogota_v1.yaml` (este documento es una vista, Sec 66).

## Qué es (Opción A)
Un **índice territorial descriptivo** de densidad histórica de emergencias asociadas a lluvia
(remoción en masa e inundación) por localidad de Bogotá, con una **capa de escenario de lluvia
etiquetada**. Sirve para **priorización** de vigilancia.

## Qué NO es
- **NO** es una probabilidad predictiva calibrada de emergencia.
- **NO** es un pronóstico. El componente predictivo por lluvia fue evaluado y **no tiene habilidad
  útil** (ver MODEL_CARD); por eso no se presenta como tal.
- La lluvia mostrada es **escenario/observación etiquetada** (`SYNTHETIC`/`OBSERVED`), no un pronóstico.
- La resolución UPZ es **priorización espacial**, no probabilidad (Sec 45).

## Definiciones temporales (congeladas)
- `t` = día calendario (America/Bogota). `t+1, t+2, t+3` = los tres días siguientes.
- `72 horas` = ventana `{t+1, t+2, t+3}` (estrictamente futura; el día t NO cuenta).
- Momento de predicción (para el análisis predictivo evaluado): cierre del día `t`; features con fecha `≤ t`.

## Inputs / Outputs
- Inputs: Bitácora IDIGER (etiqueta/densidad), SAB lluvia (escenario/contexto), estaciones (geo).
- Output: índice territorial por localidad/UPZ (descriptivo) + banda relativa; capa de escenario de lluvia.

## Uso previsto / no previsto
- Previsto: priorizar monitoreo/alistamiento por historial territorial y escenarios de lluvia.
- No previsto: sustituir el juicio de IDIGER; decisiones automáticas de evacuación; uso fuera de Bogotá;
  interpretar el índice como probabilidad.

## Limitaciones materiales
Densidad observada sujeta a **sesgo de reporte** (exposición/monitoreo). No es susceptibilidad física.
Calibración del componente probabilístico marginal (no se muestran porcentajes como probabilidad).
