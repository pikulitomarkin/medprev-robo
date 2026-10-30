# RPA por OpenCV / screenshot (mxAdmin)

O mxAdmin expoe pouco na UIA. Estrategia: **capturar tela + templates OpenCV + cliques**.

## Instalacao (maquina do cliente)

```bat
cd /d C:\Users\Consultório 3\MedBH\rpa
git pull
.\.venv32\Scripts\python.exe -m pip install -r requirements.txt
.\.venv32\Scripts\python.exe -m pip install -e .
```

Se `opencv` falhar no Python 3.14-32, avise — usamos so coordenadas + PrintWindow ate ter wheel.

## Comandos (mxAdmin aberto)

```bat
.\.venv32\Scripts\python.exe -m medbh_rpa vision snapshot
```

```bat
.\.venv32\Scripts\python.exe -m medbh_rpa vision scan
```

`scan` tira foto e manda para OpenAI listar botoes/campos (precisa `OPENAI_API_KEY` no `.env`).

### Mapear um botao

1. Snapshot
2. Abrir `artifacts\last.png` e anotar retangulo do botao (left top right bottom)
3. Salvar template:

```bat
.\.venv32\Scripts\python.exe -m medbh_rpa vision crop-template gravar 100 600 200 640
```

4. Clicar pelo template:

```bat
.\.venv32\Scripts\python.exe -m medbh_rpa vision click-template gravar
```

### Clique relativo a janela

```bat
.\.venv32\Scripts\python.exe -m medbh_rpa vision click 120 80
```

### Gravar fluxo

```bat
.\.venv32\Scripts\python.exe -m medbh_rpa vision record agenda --step "{\"type\":\"click_template\",\"template\":\"gravar\"}"
.\.venv32\Scripts\python.exe -m medbh_rpa vision run-flow agenda
```

## Explorar menus do topo (Cadastros / Atendimento / Caixa / Financeiro / Relatorios)

mxAdmin aberto na tela inicial. O robô assume o mouse, clica cada menu, tira foto do dropdown, pede a IA o que cada item faz, fecha com ESC e grava `data/maps/top_menus.json`.

```bat
.\.venv32\Scripts\python.exe -m medbh_rpa vision explore-menus
```

So abre/fecha menus — nao grava dados nem confirma formularios.

## Limitacao honesta

Entrar em todos os formularios automaticamente em ERP de producao e arriscado.
Depois do mapa dos menus, gravamos templates so dos fluxos criticos (paciente, agendar, caixa, guia).
