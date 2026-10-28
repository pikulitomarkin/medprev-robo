from __future__ import annotations

from typing import Any


def list_tools() -> list[dict[str, Any]]:
    """Catálogo de tools que o agente poderá chamar (após RPA estável)."""
    return [
        {
            "name": "buscar_paciente",
            "description": "Busca paciente no msAdmin por CPF ou nome",
            "flow": "buscar_paciente",
        },
        {
            "name": "agendar",
            "description": "Cria agendamento no msAdmin",
            "flow": "agendar",
        },
        {
            "name": "caixa",
            "description": "Registra cobrança ou gera link de pagamento",
            "flow": "caixa",
        },
        {
            "name": "guia",
            "description": "Emite guia impressa e/ou digital",
            "flow": "guia",
        },
    ]
