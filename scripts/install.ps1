$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "== MedBH RPA install ==" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python nao encontrado no PATH. Instale Python 3.11+ e marque Add to PATH."
}

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install -e .

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Criado .env a partir de .env.example. Edite as credenciais." -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path data, artifacts | Out-Null

Write-Host "OK. Ative com: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "Depois: python -m medbh_rpa healthcheck"
