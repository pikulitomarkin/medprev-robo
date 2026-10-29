# Fase 0 — Como mapear o Maxcore / msAdmin

Objetivo: o robô "enxergar" a janela e os controles (botoes, campos) para depois automatizar.

## Preparacao (maquina do cliente)

1. Abrir o sistema (NexAdmin / msAdmin) e fazer login.
2. Deixar a janela principal aberta (nao minimizar).
3. No `.env` (ja preenchido):
   - `MSADMIN_EXE` = caminho real do .exe
   - `MSADMIN_WINDOW_TITLE` = pedaco do titulo da janela (ex.: `NexAdmin` ou `msAdmin`)
   - `UI_BACKEND=uia`
4. Git CMD na pasta do robô:

```bat
cd /d C:\Users\Consultório 3\MedBH\rpa
git pull
.\.venv\Scripts\activate.bat
python -m pip install -e .
```

## Passo 1 — Ver se a janela aparece

Com o sistema ABERTO:

```bat
python -m medbh_rpa discover
```

- Se `tree.ok` for `true`: a janela foi encontrada. Arquivos em `artifacts\discover_windows.json` e `artifacts\discover_tree.json`.
- Se `tree.ok` for `false`: ajuste `MSADMIN_WINDOW_TITLE` no `.env` com um pedaco do titulo listado em `windows` e rode de novo.

Tambem:

```bat
python -m medbh_rpa healthcheck
```

Com `UI_BACKEND=uia`, `"ok": true` significa janela encontrada.

## Passo 2 — Fluxos com o Adilson (AnyDesk)

Para cada fluxo, o atendente faz na tela e Marcos anota (ou grava video curto):

1. Login (se a sessao cair)
2. Buscar paciente (CPF / nome)
3. Novo agendamento (parceiro, procedimento, data, horario)
4. Caixa / link de pagamento
5. Emitir guia / e-guia

Preencher `docs\mapa-fluxos.md` com o texto do botao/campo (Name / AutomationId do `discover_tree.json`).

## Passo 3 — Codigo

Com o mapa em maos, implementamos os metodos em `medbh_rpa\ui\uia.py` (login, buscar, agendar...). So depois o agente de IA passa a chamar esses fluxos.

## Nao fazer ainda

- Nao ligar `AGENT_ENABLED=true` antes dos fluxos UIA estaveis.
- Nao rodar `agendar` de verdade em paciente real sem teste com dado de homologacao.
