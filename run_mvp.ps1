# Arranque de un paso (Windows): reconstruye modelo desde el raw y lanza el dashboard.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = if (Test-Path "venv\Scripts\python.exe") { "venv\Scripts\python.exe" } else { "python" }
Write-Host ">> Reconstruyendo features + etiqueta..."; & $py scripts\03_build_features.py
Write-Host ">> Entrenando modelo + SHAP...";          & $py scripts\04_train_model.py
Write-Host ">> Verificando artefactos...";            & $py scripts\05_generate_outputs.py
Write-Host ">> Lanzando dashboard en http://localhost:8510"; & $py scripts\06_run_app.py
