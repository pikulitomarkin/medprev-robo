$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "== MedBH RPA update ==" -ForegroundColor Cyan

if (Test-Path .git) {
    git pull
} else {
    Write-Host "Sem .git nesta pasta. Pule o pull ou clone o repositorio." -ForegroundColor Yellow
}

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    Write-Error "venv nao encontrado. Rode scripts\install.ps1 primeiro."
}

& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install -e .
Write-Host "Atualizado." -ForegroundColor Green
