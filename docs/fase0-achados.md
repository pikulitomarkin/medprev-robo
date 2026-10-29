# Fase 0 — Achados (29/10/2026)

## Sistema

- Titulo: `mxAdmin 1.0 [Rev 0.172] [FRANQUIAS]\onVIV2\`
- Classe: `WindowsForms10.Window.8.app.0.141b42a_r8_ad1` (WinForms / .NET)
- Processo relacionado: `RunAdmin.exe` (32 bits)
- Janela encontrada: sim (`hwnd` / `pid` ok)

## Problema de automacao UIA

`discover` retornou:

- `controls_count`: 0
- `named_controls_forms`: []
- `automation_strategy`: `image_ocr_or_coords`

Avisos do pywinauto na maquina do cliente:

1. **App 32-bit com Python 64-bit** — WinForms 32-bit precisa de Python **32-bit** para o backend win32/UIA acessar controles.
2. **Sem direito na GUI** — rodar o Git CMD / script **como Administrador**.

## Proximo passo tecnico

1. Instalar Python 3.12 **Windows installer (32-bit)** em python.org.
2. Criar venv 32-bit novo e reinstalar o pacote.
3. Abrir Git CMD **como Administrador**, abrir mxAdmin, rodar `discover` de novo.
4. Se ainda vier sem controles nomeados → RPA por **imagem/OCR/coordenadas** (pyautogui + template matching), nao por UIA.

## .env

- `MSADMIN_WINDOW_TITLE=mxAdmin` (ok)
- `MSADMIN_EXE` hoje aponta para pasta Desktop — trocar pelo caminho real do `RunAdmin.exe` (atalho → Propriedades → Destino).
