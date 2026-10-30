# MCP de controle do mxAdmin

O Cursor (PC do Marcos) controla o mxAdmin no consultório via **Tailscale + MCP HTTP**, sem colar comando por comando no AnyDesk.

```
Cursor (Marcos) --Tailscale--> http://100.x.y.z:8765/mcp --Bearer--> vision RPA --> mxAdmin
```

## 1. Consultório (uma vez)

1. Instalar [Tailscale](https://tailscale.com/download) e entrar na **mesma conta/tailnet** do Marcos.
2. Anotar o IP Tailscale — `tailscale ip -4` (consultório atual: `100.74.86.51`).
3. No repo:

```bat
cd /d C:\Users\Consultório 3\MedBH\rpa
git pull
.\.venv32\Scripts\python.exe -m pip install -r requirements.txt
.\.venv32\Scripts\python.exe -m pip install -e .
```

4. No `.env` (gerar token):

```bat
powershell -NoProfile -Command "[guid]::NewGuid().ToString('N')"
```

```env
MCP_TOKEN=<cole_o_guid>
MCP_HOST=0.0.0.0
MCP_PORT=8765
OPENAI_API_KEY=sk-...
MSADMIN_WINDOW_TITLE=mxAdmin
```

5. Liberar porta no firewall (se necessário) só na rede Tailscale.

## 2. Subir o MCP (cada sessão)

1. Abrir **mxAdmin** e logar.
2. Abrir **CMD como Administrador**.
3. Rodar:

```bat
cd /d C:\Users\Consultório 3\MedBH\rpa
scripts\start-mcp.bat
```

Deve aparecer: `MCP medbh-mxadmin em http://0.0.0.0:8765/mcp`.

Deixar essa janela aberta.

## 3. Cursor no PC do Marcos

1. Copiar [`mcp.json.example`](mcp.json.example) para a config MCP do Cursor.
2. URL `http://100.74.86.51:8765/mcp` + o mesmo `MCP_TOKEN` do `.env` do consultório.
3. Settings → MCP → Refresh. Namespace esperado: `medbh-mxadmin` (tools `mx_*`).

Exemplo de entrada:

```json
{
  "mcpServers": {
    "medbh-mxadmin": {
      "url": "http://100.x.y.z:8765/mcp",
      "headers": {
        "Authorization": "Bearer SEU_MCP_TOKEN"
      }
    }
  }
}
```

## 4. Tools

| Tool | Uso |
|---|---|
| `mx_focus` | Foca mxAdmin |
| `mx_snapshot` | PrintWindow |
| `mx_scan` | Snapshot + Vision (elementos) |
| `mx_click` | Clique x,y relativo à janela |
| `mx_click_template` | Clique por template OpenCV |
| `mx_type` | Digita (**exige** `allow_write=true`) |
| `mx_key` | SendKeys (`{ESC}` sempre ok) |
| `mx_explore_menus` | Mapeia dropdowns do topo |
| `mx_open_menu_item` | Ex.: menu=`Atendimento`, item=`Agendar Atendimento` |
| `mx_map_screen` | Grava mapa em `data/maps/screens/` |
| `mx_list_maps` | Lista mapas salvos |

## 5. Sessão de mapeamento Atendimento (P0)

Com MCP online e mxAdmin na home:

1. `mx_snapshot` — referência home  
2. `mx_open_menu_item` Atendimento → **Agendar Atendimento** → `mx_map_screen` name=`agendar_atendimento` → `mx_key` `{ESC}`  
3. Idem **Meus Atendimentos**  
4. Idem **Cancelar Atendimento** / **Pré-Cancelamento** (não confirmar)  
5. Idem **Validar e-Guia** e **Guias Manuais**  
6. `mx_list_maps` e consolidar em `docs/mapa-atendimento.md`

## Segurança

- Só Tailscale (não publicar 8765 na internet).
- `MCP_TOKEN` obrigatório.
- `mx_type` e teclas “perigosas” pedem `allow_write=true`.
- Scan orientado a **não** gravar CPF/senha completos.

## Checklist rápido

- [ ] Tailscale up nos dois PCs  
- [ ] `MCP_TOKEN` igual no `.env` e no Cursor  
- [ ] mxAdmin aberto  
- [ ] CMD Admin + `scripts\start-mcp.bat`  
- [ ] Cursor vê tools `mx_*`  
- [ ] `mx_snapshot` retorna `ok: true`
