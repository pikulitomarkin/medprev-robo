# MedBH RPA

Robô Python que opera o **msAdmin/Maxcore** na máquina do Instituto MedBH, com fila de jobs idempotente e (depois) agente de IA.

Plano interno: `../plano-rpa-agente-medbh.md`  
Escopo comercial: `../escopo-rpa-medbh.md`

## Requisitos

- Windows 10/11 (máquina onde o msAdmin roda)
- Python 3.11+
- msAdmin instalado e abrindo normalmente
- Git (para clonar/atualizar)

## Instalação rápida (máquina do cliente)

```powershell
cd C:\MedBH
git clone <URL_DO_REPO> rpa
cd rpa
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
copy .env.example .env
notepad .env
```

Ajuste no `.env` pelo menos:

- `MSADMIN_EXE` — caminho do sistema
- `MSADMIN_WINDOW_TITLE` — título parcial da janela
- `UI_BACKEND=mock` enquanto desenvolve sem o Maxcore; na produção use `auto` ou `uia`

## Comandos

```powershell
.\.venv\Scripts\Activate.ps1

# Saúde do ambiente
python -m medbh_rpa healthcheck

# Worker (processa fila)
python -m medbh_rpa worker

# Enfileirar um job (exemplo)
python -m medbh_rpa enqueue buscar_paciente --payload '{\"nome\":\"Ana\"}'

# Rodar um fluxo na hora (dev)
python -m medbh_rpa run healthcheck
```

## Atualizar

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\update.ps1
```

## Estrutura

| Pasta | Função |
|---|---|
| `medbh_rpa/flows/` | Fluxos de negócio (login, paciente, agendar, caixa, guia) |
| `medbh_rpa/ui/` | Adaptadores de UI (`mock`, `uia`, `playwright`) |
| `medbh_rpa/db/` | SQLite de jobs + idempotência |
| `medbh_rpa/agent/` | Agente de IA (fase posterior) |
| `data/` | Banco local (não versionado) |
| `artifacts/` | Screenshots de falha (não versionado) |

## Segurança

- Nunca commitar `.env`, senhas, CPF ou prints com paciente.
- Preferir usuário Windows e login msAdmin dedicados ao robô.
- CPF em logs deve ir mascarado.

## Status

Esqueleto inicial (28/10/2026). Fluxos reais dependem do mapeamento AnyDesk (Fase 0).
