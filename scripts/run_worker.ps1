$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    Write-Error "venv não encontrado. Rode scripts\install.ps1 primeiro."
}

& .\.venv\Scripts\python.exe -m medbh_rpa worker
