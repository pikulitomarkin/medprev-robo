from __future__ import annotations

from pathlib import Path
from typing import Any

from medbh_rpa.config import Settings
from medbh_rpa.ui.base import UiAdapter


class PlaywrightUi(UiAdapter):
    """
    Adapter Playwright — usar se partes do msAdmin forem web / Electron.

    Seletores reais vêm após a Fase 0.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def healthcheck(self) -> dict[str, Any]:
        return {
            "ok": False,
            "backend": "playwright",
            "message": "Playwright reservado para UI web — mapear URL/seletores na Fase 0",
        }

    def ensure_logged_in(self) -> None:
        raise NotImplementedError("Playwright login: mapear na Fase 0")

    def find_patient(self, *, cpf: str | None = None, nome: str | None = None) -> dict[str, Any]:
        raise NotImplementedError("Playwright buscar paciente: mapear na Fase 0")

    def create_appointment(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Playwright agendar: mapear na Fase 0")

    def register_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Playwright caixa: mapear na Fase 0")

    def emit_guia(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Playwright guia: mapear na Fase 0")

    def screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
        return path
