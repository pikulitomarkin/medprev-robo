from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from medbh_rpa.config import Settings
from medbh_rpa.ui.base import UiAdapter

log = logging.getLogger(__name__)


class MockUi(UiAdapter):
    """Backend de desenvolvimento: não toca no msAdmin."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def healthcheck(self) -> dict[str, Any]:
        return {
            "ok": True,
            "backend": "mock",
            "msadmin_exe": self.settings.msadmin_exe or "(não configurado)",
            "window_title": self.settings.msadmin_window_title,
            "message": "Mock UI ativo — troque UI_BACKEND após mapear o msAdmin",
        }

    def ensure_logged_in(self) -> None:
        log.info("mock: ensure_logged_in")

    def find_patient(self, *, cpf: str | None = None, nome: str | None = None) -> dict[str, Any]:
        log.info("mock: find_patient cpf=%s nome=%s", cpf, nome)
        if not cpf and not nome:
            return {"found": False, "patient_id": None, "nome": None}
        return {
            "found": True,
            "patient_id": "MOCK-10482",
            "nome": nome or "Paciente Mock",
        }

    def create_appointment(self, payload: dict[str, Any]) -> dict[str, Any]:
        atendimento_id = f"MOCK-{uuid4().hex[:8].upper()}"
        log.info("mock: create_appointment -> %s payload=%s", atendimento_id, payload)
        return {"atendimento_id": atendimento_id, "status": "agendado"}

    def register_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        log.info("mock: register_payment payload=%s", payload)
        return {
            "status": "pago" if payload.get("forma") != "link" else "link_enviado",
            "link": payload.get("link") or "https://medbh.link/p/mock",
        }

    def emit_guia(self, payload: dict[str, Any]) -> dict[str, Any]:
        log.info("mock: emit_guia payload=%s", payload)
        return {
            "guia_digital_url": f"https://medbh.link/g/{payload.get('atendimento_id', 'mock')}",
            "impressa": True,
        }

    def screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")  # placeholder
        return path
