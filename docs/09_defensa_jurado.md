# Guion de defensa ante jurado — AquaBosque Minero IA

## Pitch (3-4 minutos)

**Apertura:**
> Colombia cuenta con datos abiertos sobre minería, bosques, agua y territorio. El problema es que están dispersos y no se transforman en señales tempranas para decidir. AquaBosque Minero IA integra esas fuentes y usa inteligencia artificial explicable para priorizar territorios donde confluyen señales de presión minera, deforestación y afectación hídrica.

**Cuerpo:**
1. **Problema** — datos dispersos, sin priorización accionable.
2. **Solución** — 7 fuentes oficiales → 1.122 municipios clasificados en 4 niveles de riesgo.
3. **Datos abiertos** — ANM, IDEAM, RUNAP, DANE, PDET. Todas públicas y verificadas.
4. **Modelo** — XGBoost + SHAP. No es caja negra: explica qué factor pesa en cada territorio.
5. **Demo** — mapa, ranking, ficha por municipio, explicabilidad (dashboard en vivo, puerto 8510).
6. **Impacto** — el Estado sabe dónde mirar primero; escalable a cuencas y satélite.

**Cierre:**
> No proponemos un sistema sancionatorio ni una caja negra. Proponemos una herramienta reproducible, explicable y basada en datos abiertos para ayudar al Estado a mirar primero donde el riesgo ambiental puede ser mayor.

---

## Preguntas difíciles del jurado (con respuesta)

**1. ¿El modelo prueba que la minería causa contaminación?**
No. No prueba causalidad. Integra señales de presión minera, deforestación, calidad hídrica y sensibilidad para priorizar zonas que requieren revisión técnica. Es monitoreo y priorización, no sanción.

**2. ¿Detecta minería ilegal?**
No directamente. Usa datos oficiales de actividad minera FORMAL (RUCOM) y variables ambientales. Identifica zonas con señales de riesgo donde conviene profundizar, pero no declara ilegalidad.

**3. ¿Por qué IA y no solo un tablero?**
Porque no solo visualiza: construye variables integradas, clasifica niveles y —con SHAP— explica qué factores pesan en cada clasificación. Convierte datos dispersos en priorización explicable.

**4. Si la etiqueta es una fórmula, ¿el modelo no es tautológico?**
Es una observación válida y la declaramos abiertamente: el modelo re-aprende parcialmente la regla, por eso su accuracy (91%) NO se presenta como mérito predictivo, y reportamos la línea base (60%). El valor real es doble: (a) SHAP explica cada caso de forma transparente, y (b) el sistema generaliza y hace operativa la priorización sobre 1.122 municipios de forma consistente y auditable.

**5. ¿Qué tan reproducible es?**
Totalmente: pipeline de 6 scripts + dashboard, corre en cualquier PC sin GPU. Cada fuente documenta origen, fecha y limitaciones. `data/raw` es re-descargable.

**6. ¿Por qué municipio y no píxel satelital?**
El municipio permite un MVP robusto, integrable con datos abiertos oficiales y comprensible para política pública. Es escalable a cuencas, subzonas hidrográficas o grillas en fases posteriores.

**7. ¿Qué pasa si un dataset no está actualizado?**
Se documenta fecha, cobertura y limitaciones. No se presenta como tiempo real; se habla de actualización periódica según disponibilidad. Lo que no se puede verificar se declara, no se inventa.

**8. ¿Qué aporta al Ministerio?**
Prioriza territorios, orienta análisis técnico, focaliza capacidades institucionales y transforma datos sectoriales y ambientales en conocimiento estratégico para política pública.
