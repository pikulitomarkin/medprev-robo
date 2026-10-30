@echo off
REM Sobe o MCP do mxAdmin. Rodar CMD como Administrador, com mxAdmin aberto.
cd /d "%~dp0.."

if not exist ".venv32\Scripts\python.exe" (
  echo [ERRO] .venv32 nao encontrado. Crie o venv 32-bit antes.
  exit /b 1
)

if not exist ".env" (
  echo [ERRO] .env ausente. Copie .env.example e defina MCP_TOKEN + OPENAI_API_KEY.
  exit /b 1
)

echo.
echo === MedBH MCP ===
echo mxAdmin deve estar aberto. Tailscale up. Porta 8765.
echo.
".venv32\Scripts\python.exe" -m pip install -q -r requirements.txt
".venv32\Scripts\python.exe" -m pip install -q -e .
".venv32\Scripts\python.exe" -m medbh_rpa mcp
