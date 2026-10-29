@echo off
setlocal
cd /d "%~dp0.."

echo == MedBH RPA install ==

where python >nul 2>&1
if errorlevel 1 (
  echo Python nao encontrado no PATH. Instale Python 3.11+ e marque Add to PATH.
  exit /b 1
)

python -m venv .venv
call .\.venv\Scripts\python.exe -m pip install --upgrade pip
call .\.venv\Scripts\python.exe -m pip install -r requirements.txt
call .\.venv\Scripts\python.exe -m pip install -e .

if not exist .env (
  copy .env.example .env >nul
  echo Criado .env a partir de .env.example. Edite as credenciais.
)

if not exist data mkdir data
if not exist artifacts mkdir artifacts

echo OK.
echo Ative com: .\.venv\Scripts\activate.bat
echo Depois: python -m medbh_rpa healthcheck
endlocal
