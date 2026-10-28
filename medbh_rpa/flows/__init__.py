from __future__ import annotations

from typing import Any, Callable

from medbh_rpa.flows import agendar, buscar_paciente, caixa, guia, health, login
from medbh_rpa.ui.base import UiAdapter

FlowFn = Callable[[UiAdapter, dict[str, Any]], dict[str, Any]]

FLOWS: dict[str, FlowFn] = {
    "healthcheck": health.run,
    "login": login.run,
    "buscar_paciente": buscar_paciente.run,
    "agendar": agendar.run,
    "caixa": caixa.run,
    "guia": guia.run,
}


def get_flow(name: str) -> FlowFn:
    if name not in FLOWS:
        known = ", ".join(sorted(FLOWS))
        raise KeyError(f"Fluxo desconhecido: {name}. Disponíveis: {known}")
    return FLOWS[name]
