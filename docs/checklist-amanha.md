# Checklist — sessao AnyDesk com admin (proximo dia)

Objetivo: em 30–40 min fechar o discover e iniciar o RPA por imagem.

## Antes de conectar

- [ ] Cliente no PC (ou liberacao admin unica)
- [ ] AnyDesk com acesso desacompanhado + senha (se der para configurar)
- [ ] mxAdmin / RunAdmin.exe abre com a conta do consultorio

## Na sessao (ordem)

1. Abrir **mxAdmin** logado (tela Agenda).
2. Git CMD **normal** (nao precisa admin para estes comandos):

```bat
cd /d C:\Users\Consultório 3\MedBH\rpa
git pull
```

3. Python 32-bit (preferencial):

```bat
.\.venv32\Scripts\python.exe -m pip install -e .
.\.venv32\Scripts\python.exe -m medbh_rpa discover
```

Se nao existir `.venv32`:

```bat
py -3.14-32 -m venv .venv32
.\.venv32\Scripts\python.exe -m pip install -r requirements.txt
.\.venv32\Scripts\python.exe -m pip install -e .
.\.venv32\Scripts\python.exe -m medbh_rpa discover
```

4. Confirmar:
   - JSON com `"ok": true`
   - arquivo `artifacts\mxadmin_window.png` mostra a tela
5. Mandar print do JSON curto + do PNG para o Marcos.
6. Gravar 1 video curto (30–60s) do fluxo: buscar paciente → agendar → gravar.

## Se o discover travar

```bat
Ctrl+C
.\.venv32\Scripts\python.exe -m medbh_rpa discover --no-tree
```

## Nao fazer nesta sessao

- Nao instalar Build Tools / Playwright
- Nao depender de PowerShell admin para o robô
- Nao rodar discover “full” antigo (travava)

## Decisao ja tomada

- UIA do mxAdmin e pobre → estrategia `image_ocr_or_coords`
- Depois do screenshot ok, implementar cliques por imagem/coords
