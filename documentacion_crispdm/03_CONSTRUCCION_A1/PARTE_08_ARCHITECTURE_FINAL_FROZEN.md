# PARTE 08 - ARQUITECTURA DOCUMENTAL FINAL FROZEN

## A. ARQUITECTURA NARRATIVA FINAL

### 1. Fuentes del componente nacional
- **Propósito narrativo:** identificar las fuentes que alimentan el indice nacional.
- **Contenido mínimo:** ANM/RUCOM para mineria formal; DANE/DIVIPOLA para municipios; IDEAM/SMByC o fuente oficial para deforestacion; IDEAM para agua; RUNAP/PDET para sensibilidad.
- **Afirmaciones que puede contener:** fuente, variable esperada, uso analitico y limitacion.
- **Afirmaciones que NO debe contener:** "100% verificado" si el registro tecnico dice REQUIERE_VETTING; mineria ilegal; dano ambiental probado.
- **Relación con partes anteriores y siguientes:** sustenta alcance y viabilidad.
- **Nivel de desarrollo esperado:** tabla narrativa o lista tecnica breve.

### 2. Fuentes de incendios y teledeteccion
- **Propósito narrativo:** separar senales satelitales disponibles de capacidades pendientes.
- **Contenido mínimo:** NASA FIRMS como focos termicos recientes si se usa; Sentinel-2/dNBR como medicion por ventana solo si existe evidencia validada; limitaciones de nube/proxy.
- **Afirmaciones que puede contener:** FIRMS es proxy de fuego/quema reciente, no clasificacion de perdida de bosque.
- **Afirmaciones que NO debe contener:** inferir deforestacion confirmada solo por foco termico.
- **Relación con partes anteriores y siguientes:** alimenta resultados y riesgos.
- **Nivel de desarrollo esperado:** medio.

### 3. Fuentes del componente Bogota
- **Propósito narrativo:** documentar fuentes urbanas sin mezclarlas con el indice nacional.
- **Contenido mínimo:** Bitacora IDIGER, SAB lluvia, estaciones, IDECA/POT segun estado de validacion.
- **Afirmaciones que puede contener:** cobertura temporal/espacial cuando este validada.
- **Afirmaciones que NO debe contener:** fuentes nacionales como si fueran Bogota o viceversa.
- **Relación con partes anteriores y siguientes:** sustenta la viabilidad del componente urbano.
- **Nivel de desarrollo esperado:** medio.

### 4. Estado de disponibilidad y limitaciones
- **Propósito narrativo:** declarar calidad, cobertura y actualizacion sin sobregeneralizar.
- **Contenido mínimo:** verificado, parcial, requiere vetting; cobertura temporal; sesgos conocidos.
- **Afirmaciones que puede contener:** ausencia de dato no equivale a ausencia de riesgo.
- **Afirmaciones que NO debe contener:** "sin vacios" o "calidad alta" sin evidencia.
- **Relación con partes anteriores y siguientes:** conecta con supuestos y riesgos.
- **Nivel de desarrollo esperado:** medio.

## B. MATRIZ DE EVIDENCIA

| Afirmacion o tema | Evidencia localizada | Tipo de evidencia | Nivel de certeza | Contradicciones detectadas | Vacio |
|---|---|---|---|---|---|
| Fuentes nacionales oficiales | README; config/data_sources.yaml; docs/diccionario_datos.md | Documentacion tecnica | Media | README declara 5/5 reales; config conserva estados REQUIERE_VETTING/GEOESPACIAL/PARCIAL_LOCAL | Si |
| RUCOM mineria formal | config/data_sources.yaml; docs/07_limitaciones.md | Fuente/documentacion | Alta | No capta mineria ilegal | No |
| DANE/DIVIPOLA 1122 | README; master/geojson | Resultado tecnico | Alta | Falta validacion bibliografica oficial | Si |
| FIRMS | firms_signal.py; fuego_summary | Codigo/resultado | Alta para uso interno | Requiere fuente oficial externa validada | Si |
| IDIGER/SAB Bogota | source_registry.json; PRODUCT_CONTRACT | Registro tecnico | Alta | Metricas/model cards no coinciden en estado predictivo | Si |

## C. NECESIDADES BIBLIOGRAFICAS

| Afirmacion a sustentar | Tipo de fuente requerida | Prioridad | Estado de validacion |
|---|---|---|---|
| ANM/RUCOM como fuente de mineria formal | Portal/documentacion oficial ANM/datos.gov.co | Alta | Pendiente |
| DANE/DIVIPOLA 2025 y numero de municipios | Fuente oficial DANE | Alta | Pendiente |
| IDEAM/SMByC deforestacion y DHIME/ICA | Fuente oficial IDEAM | Alta | Pendiente |
| RUNAP y PDET como sensibilidad territorial | Fuentes oficiales RUNAP/PDET | Alta | Pendiente |
| NASA FIRMS | Documentacion oficial NASA | Alta | Pendiente |
| IDIGER/SAB/IDECA | Fuentes oficiales Bogota | Alta | Pendiente |

## D. APLICABILIDAD DE PROTOCOLOS

| Protocolo | APLICA / NO_APLICA | Fundamento | Exigencia concreta para esta parte |
|---|---|---|---|
| PRD | APLICA | Fuentes son modulo sustantivo | Clasificar fuentes por componente |
| Separacion Narrativa/Evidencia | APLICA | Debe distinguir fuente, uso, limitacion | Evidencia detallada en matrices/tablas |
| PEDAT | APLICA | Requiere explicar fuentes comprimidas | Desarrollo proporcional por fuente |
| PBF | APLICA | Toda la parte depende de fuentes externas | No READY sin validacion bibliografica |
| PGV-ACG | APLICA | Es probable planificar tabla de fuentes | Tabla con fuente, variable, uso, limitacion y estado |
| PGV-MAPAS | APLICA | Fuentes geoespaciales/cartograficas | Registrar CRS, cobertura, geometria y escala cuando aplique |

## E. EVALUACION DEL BORRADOR ORIGINAL

| Aspecto | Evaluacion |
|---|---|
| Contenido reutilizable | Categorias de fuentes oficiales, geoespaciales, historicas y periodicas |
| Contenido a eliminar | Descripciones institucionales genericas; IDIGER como "Instituto de Geografia"; verificacion de aceptacion |
| Contenido a corregir | Estados de disponibilidad; fuentes parcialmente verificables; distinguir FIRMS/dNBR/Sentinel |
| Afirmaciones no sustentadas | API en tiempo real, disponibilidad publica plena, calidad alta |
| Faltantes | Matriz por fuente con estado real y limitacion |

## F. READINESS

PARTIAL
