# PARTE 04 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Necesidad de una lectura integrada del riesgo ambiental
- **Propósito narrativo:** explicar por que una priorizacion integrada es pertinente.
- **Contenido mínimo:** presiones ambientales distribuidas de forma desigual; necesidad de ordenar senales para monitoreo estrategico; datos abiertos como condicion de transparencia.
- **Afirmaciones que puede contener:** existen senales de mineria formal, deforestacion, agua, sensibilidad y fuego integrables por municipio.
- **Afirmaciones que NO debe contener:** dano ambiental probado, causalidad mineria-deforestacion/agua, ilegalidad, sancion, eficiencia institucional demostrada.
- **Relación con partes anteriores y siguientes:** justifica el objetivo y anticipa el problema analitico.
- **Nivel de desarrollo esperado:** sustantivo pero solo con evidencia validada.

### 2. Valor publico de la explicabilidad y la reproducibilidad
- **Propósito narrativo:** justificar por que el estudio no debe ser una caja negra.
- **Contenido mínimo:** trazabilidad de fuentes, formula tecnica declarada, SHAP como apoyo interpretativo, repositorio reproducible.
- **Afirmaciones que puede contener:** la explicabilidad facilita auditoria tecnica; no reemplaza revision humana.
- **Afirmaciones que NO debe contener:** adopcion oficial, cambios de politica publica o beneficios comprobados.
- **Relación con partes anteriores y siguientes:** conecta con problema analitico y riesgos.
- **Nivel de desarrollo esperado:** medio.

### 3. Utilidad delimitada de los componentes complementarios
- **Propósito narrativo:** justificar incendios y Bogota sin desplazar el nucleo nacional.
- **Contenido mínimo:** incendios aportan senal temporal/territorial; Bogota aporta caso urbano diferenciado.
- **Afirmaciones que puede contener:** componentes complementan la lectura; cada uno tiene limitaciones propias.
- **Afirmaciones que NO debe contener:** vigilancia satelital permanente o alerta urbana predictiva operativa si no esta aprobada.
- **Relación con partes anteriores y siguientes:** prepara alcance.
- **Nivel de desarrollo esperado:** breve.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Presion ambiental desigual requiere focalizacion | Documento historico A1 | Planteamiento historico | Media | Falta fuente externa sectorial | Si |
| Priorizacion transparente con datos abiertos | README; MODEL_CARD; codigo pipeline | Evidencia tecnica interna | Alta | No demuestra impacto publico | Si |
| Datos abiertos oficiales integrados | README; config/data_sources.yaml; docs/diccionario_datos.md | Documentacion tecnica | Media | config marca varias fuentes como REQUIERE_VETTING; README las presenta como verificadas | Si |
| Valor de reproducibilidad | README; tests; scripts | Evidencia tecnica | Media | No se ejecuto validacion completa en esta reconstruccion | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| Desigualdad espacial de presiones ambientales en Colombia | Reporte oficial o literatura cientifica | Alta | Pendiente |
| Uso de datos abiertos para transparencia en decision publica | Guia/norma oficial o literatura | Alta | Pendiente |
| Explicabilidad como requisito de confianza/auditoria en IA publica | Literatura o guia institucional | Media | Pendiente |
| Relacion entre priorizacion territorial y asignacion de recursos ambientales | Literatura o documento oficial | Alta | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Seccion argumentativa sustantiva | Estructura progresiva: necesidad, valor, delimitacion |
| Separacion Narrativa/Evidencia | APLICA | Alto riesgo de mezclar fuentes con narrativa | Evidencia y vacios fuera del cuerpo principal |
| PEDAT | APLICA | Requiere desarrollo argumentativo | Expandir con evidencia, no con retorica |
| PBF | APLICA | Justificacion depende de fuentes externas | No redactar como READY sin bibliografia validada |
| PGV-ACG | NO_APLICA | No se planifican visuales obligatorios | Sin exigencia visual |
| PGV-MAPAS | NO_APLICA | No se planifican mapas en la justificacion | Sin exigencia cartografica |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Idea central de presion desigual, datos abiertos y auditabilidad |
| Contenido a eliminar | Beneficios economicos/sociales no demostrados, verificacion de aceptacion, rutas |
| Contenido a corregir | ANM/IDEAM/NASA/IDIGER listados sin validacion suficiente; "impacto significativo" requiere fuente |
| Afirmaciones no sustentadas | Mejora de calidad de vida, reduccion de costos, efectividad de politicas |
| Faltantes | Bibliografia oficial/cientifica y delimitacion de no causalidad |

## F. READINESS

BLOCKED
