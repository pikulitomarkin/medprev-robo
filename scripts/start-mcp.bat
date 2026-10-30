@echo off
REM Sobe o HTTP lite do mxAdmin (sem pacote mcp/cryptography).
REM CMD como Administrador, mxAdmin aberto, Tailscale up.
cd /d "%~dp0.."

if not exist ".venv32\Scripts\python.exe" (
  echo [ERRO] .venv32 nao encontrado.
  exit /b 1
)

if not exist ".env" (
  echo [ERRO] .env ausente. Defina MCP_TOKEN + OPENAI_API_KEY.
  exit /b 1
)

echo.
echo === MedBH MCP HTTP lite ===
echo Sem cryptography. Porta 8765. mxAdmin aberto.
echo.

".venv32\Scripts\python.exe" -m pip install -q uvicorn starlette anyio
".venv32\Scripts\python.exe" -m pip install -q -e .
".venv32\Scripts\python.exe" -m medbh_rpa mcp
