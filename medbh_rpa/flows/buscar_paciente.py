from __future__ import annotations

from typing import Any

from medbh_rpa.ui.base import UiAdapter


def run(ui: UiAdapter, payload: dict[str, Any]) -> dict[str, Any]:
    ui.ensure_logged_in()
    return ui.find_patient(
        cpf=payload.get("cpf"),
        nome=payload.get("nome"),
    )
