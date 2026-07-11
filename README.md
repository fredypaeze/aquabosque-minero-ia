# AquaBosque Minero IA

Proyecto de análisis de datos aplicado a recursos hídricos, cobertura boscosa y actividad minera, mediante herramientas de IA.

## Estado del proyecto

Fase actual: **estructura base del repositorio**. Aún no se ha descargado ni cargado ningún dato.

## Estructura del repositorio

```
.
├── config/                # Archivos de configuración (parámetros, credenciales de ejemplo, etc.)
├── data/
│   ├── raw/                # Datos originales, sin modificar (no versionados en git)
│   ├── processed/          # Datos limpios/transformados (no versionados en git)
│   └── external/            # Datos de fuentes externas de referencia (no versionados en git)
├── docs/                   # Documentación del proyecto
├── notebooks/               # Notebooks de exploración y análisis
├── outputs/
│   ├── figures/             # Gráficos y visualizaciones generadas
│   └── reports/             # Reportes generados
├── scripts/                 # Scripts ejecutables (descarga, procesamiento, etc.)
├── src/aquabosque/          # Código fuente del paquete Python del proyecto
├── tests/                   # Pruebas automatizadas
├── venv/                    # Entorno virtual local (no versionado)
├── .gitignore
├── README.md
└── requirements.txt
```

## Reglas de trabajo

1. Trabajo restringido a esta carpeta del repositorio.
2. No se leen, borran, mueven ni modifican archivos fuera de esta carpeta.
3. No se instalan paquetes globales; todo el trabajo usa el entorno virtual local `venv`.
4. No se ejecutan comandos destructivos.
5. No se hace push a repositorios remotos.
6. No se usan servicios pagos.
7. No se descargan archivos pesados sin avisar previamente.
8. No se inventan datos.
9. No se afirma causalidad ambiental ni minería ilegal; los análisis se limitan a lo que los datos permiten sustentar.

## Entorno virtual

El entorno virtual ya existe en `venv/`. Para activarlo (PowerShell):

```powershell
.\venv\Scripts\Activate.ps1
```

## Próximos pasos

- Definir fuentes de datos a utilizar (pendiente de aprobación antes de descargar).
- Completar `requirements.txt` según las librerías que se necesiten.
- Documentar en `docs/` el alcance y la metodología del proyecto.
