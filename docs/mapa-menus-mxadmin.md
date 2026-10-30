# Mapa dos menus mxAdmin (explore-menus)

Gerado em: 2026-10-30 12:45 (`artifacts/explore_20261030_124520`)  
Unidade no título: `[FRANQUIAS]\onCPL\`  
Modo: só abriu dropdown + ESC (não entrou em formulários)

Coordenadas = centro do texto do menu, relativas à janela (y≈18 = barra de menu).

## Cadastros — (141, 18)

Área de cadastro/manutenção de entidades.

| Item | Tipo | Função |
|---|---|---|
| Cli/Cadastros | command | Cadastro de clientes/afins |
| Usuários | command | Gerencia usuários |
| Empresas | command | Empresas/franquias |
| Permissões | command | Permissões de acesso |
| Profissionais | command | Cadastro de profissionais |

## Atendimento — (219, 18)  ★ NÚCLEO DA IA

Menu mais usado. Integração principal do robô/IA.  
*(explore-menus capturou errado — lista abaixo corrigida pela tela real 30/10/2026)*

| # | Item | Tipo | Prioridade IA |
|---|---|---|---|
| 1 | **Agendar Atendimento** | command | P0 — fluxo principal |
| 2 | Cancelar Atendimento | command | P0 |
| 3 | Transferir Propriedade | command | P2 |
| 4 | Transferência Programada | command | P2 |
| 5 | Meus Atendimentos | command | P1 — consulta |
| 6 | Meus Atendimentos Transferidos | command | P2 |
| 7 | Histórico de alterações | command | P1 — auditoria |
| 8 | Análise de Atendimentos | command | P2 |
| 9 | Rastreamento de Atendimento | command | P1 |
| 10 | Observações de Atendimentos | command | P1 |
| 11 | Retirar do pagamento web | command | P1 — caixa/link |
| 12 | Pré-Cancelamento | command | P1 |
| 13 | **Validar e-Guia** | command | P0 — guia |
| 14 | Guias Manuais | submenu | P0 — guia |
| 15 | PIX - Envio de atendimentos | command | P1 — pagamento |

Atalho na home (botão esquerdo, fora do menu): **Agenda de Profissional** — também usado no dia a dia.

### Ordem de mapeamento RPA (Atendimento)

1. Abrir **Agendar Atendimento** → snapshot + listar campos/botões  
2. **Meus Atendimentos** / busca  
3. **Cancelar** + **Pré-Cancelamento**  
4. **Validar e-Guia** + **Guias Manuais**  
5. **Retirar do pagamento web** + **PIX**

## Caixa — (275, 18)

Controle e movimentação do caixa da unidade.

| Item | Tipo | Função |
|---|---|---|
| Abertura de Caixa | command | Abrir caixa do dia |
| Fechamento de Caixa | command | Encerrar caixa |
| Movimentação de Caixa | command | Entradas/saídas |
| Relatório de Caixa | command | Relatórios do caixa |
| Configurações | submenu | Preferências do caixa |

## Financeiro — (426, 18)

Contas, fluxo e relatórios financeiros.

| Item | Tipo | Função |
|---|---|---|
| Cadastros | submenu | Cadastros financeiros |
| Contas a Pagar | command | Contas a pagar |
| Contas a Receber | command | Contas a receber |
| Fluxo de Caixa | command | Fluxo financeiro |
| Conciliação Bancária | command | Conciliação |
| Relatórios Financeiros | submenu | Relatórios |
| Configurações Financeiras | command | Config do módulo |

## Relatórios — (483, 18)

Geração de relatórios operacionais.

| Item | Tipo | Função |
|---|---|---|
| Relatório de Atendimentos | command | Atendimentos realizados |
| Relatório Financeiro | submenu | Receitas/despesas |
| Relatório de Consultas | command | Consultas |
| Relatório de Procedimentos | command | Procedimentos |
| Relatório de Profissionais | command | Profissionais |

## Próximos fluxos a gravar (RPA)

1. **Atendimento → Agendar Atendimento** (P0 — núcleo IA)  
2. **Atendimento → Cancelar / e-Guia / Guias Manuais**  
3. **Cadastros → Cli/Cadastros / Profissionais** (apoio)  
4. **Caixa / PIX / pagamento web** (pós-agendamento)
