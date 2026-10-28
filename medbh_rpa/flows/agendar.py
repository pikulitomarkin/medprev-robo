from __future__ import annotations

from typing import Any

from medbh_rpa.ui.base import UiAdapter


def run(ui: UiAdapter, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Payload esperado (após Fase 0):
      patient_id | cpf | nome
      parceiro
      procedimento
      data (YYYY-MM-DD)
      horario (HH:MM)
    """
    ui.ensure_logged_in()
    if not payload.get("patient_id"):
        found = ui.find_patient(cpf=payload.get("cpf"), nome=payload.get("nome"))
        if not found.get("found"):
            return {"status": "paciente_nao_encontrado", **found}
        payload = {**payload, "patient_id": found["patient_id"]}
    return ui.create_appointment(payload)
