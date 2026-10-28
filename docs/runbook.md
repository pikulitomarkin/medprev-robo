# Runbook — MedBH RPA

## Robô não inicia

1. Máquina ligada e sessão Windows desbloqueada.
2. `python -m medbh_rpa healthcheck`
3. Conferir `.env` (`MSADMIN_EXE`, `UI_BACKEND`).
4. Ver logs do Agendador de Tarefas / `run_worker.ps1`.

## Job fica em failed

1. Abrir `data/jobs.sqlite3` ou log do worker.
2. Ver screenshot em `artifacts/fail_*.png`.
3. Se o Maxcore mudou a tela: atualizar seletores no adapter UIA/Playwright e `docs/mapa-fluxos.md`.

## Atualizar código

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\update.ps1
```

## Idempotência

Reenviar o mesmo `idempotency_key` não cria job duplicado. Sempre passar chave estável por atendimento (ex.: CPF+data+horario).
