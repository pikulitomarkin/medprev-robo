from __future__ import annotations

from typing import Any

from medbh_rpa.ui.base import UiAdapter


def run(ui: UiAdapter, payload: dict[str, Any]) -> dict[str, Any]:
    ui.ensure_logged_in()
    if not payload.get("atendimento_id"):
        raise ValueError("guia exige atendimento_id")
    return ui.emit_guia(payload)
