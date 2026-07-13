# Arranque del MVP AquaBosque Minero IA.
# Activa el entorno virtual local, genera el dataset si falta y abre la app Streamlit.

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

$VenvPython = Join-Path $RepoRoot "venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "No se encontro el entorno virtual en venv\. Crea el venv e instala requirements.txt antes de continuar."
    exit 1
}

$DatasetPath = Join-Path $RepoRoot "data\processed\mvp\aquabosque_municipios_mvp.csv"
$GeoJsonPath = Join-Path $RepoRoot "data\processed\mvp\municipios_mvp_simplificado.geojson"

if (-not (Test-Path $DatasetPath) -or -not (Test-Path $GeoJsonPath)) {
    Write-Host "Generando el dataset del MVP (scripts/24_build_mvp_dataset.py)..."
    & $VenvPython "scripts\24_build_mvp_dataset.py"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "La generacion del dataset del MVP fallo."
        exit 1
    }
}

Write-Host "Iniciando la aplicacion Streamlit..."
& $VenvPython -m streamlit run "app.py"
