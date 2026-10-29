@echo off
setlocal
cd /d "%~dp0.."

echo == MedBH RPA install ==

where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERRO: Python nao encontrado no PATH.
  echo Instale Python 3.11 ou 3.12 em https://www.python.org/downloads/
  echo Marque a opcao: Add python.exe to PATH
  echo Depois feche e abra o Git CMD e rode este script de novo.
  exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERRO: Python invalido ou versao abaixo de 3.11.
  echo Nao use o atalho da Microsoft Store.
  echo Instale em https://www.python.org/downloads/ e marque Add python.exe to PATH
  exit /b 1
)

python -m venv .venv
if errorlevel 1 (
  echo ERRO: falha ao criar .venv
  exit /b 1
)

call .\.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1
call .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
call .\.venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 exit /b 1

if not exist .env (
  copy .env.example .env >nul
  echo Criado .env a partir de .env.example. Edite as credenciais.
)

if not exist data mkdir data
if not exist artifacts mkdir artifacts

echo.
echo OK.
echo Ative com: .\.venv\Scripts\activate.bat
echo Depois: python -m medbh_rpa healthcheck
endlocal
