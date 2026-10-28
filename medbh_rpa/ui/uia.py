from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from medbh_rpa.config import Settings
from medbh_rpa.ui.base import UiAdapter

log = logging.getLogger(__name__)


class UiaAdapter(UiAdapter):
    """
    Adapter pywinauto (Windows UI Automation).

    Implementação real após Fase 0 (mapa de controles do msAdmin).
    Métodos levantam NotImplementedError até os seletores serem gravados.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        try:
            import pywinauto  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "pywinauto não instalado. Rode: pip install -r requirements.txt"
            ) from exc

    def healthcheck(self) -> dict[str, Any]:
        from pywinauto import Desktop

        title = self.settings.msadmin_window_title
        windows = Desktop(backend="uia").windows()
        matches = [w.window_text() for w in windows if title.lower() in (w.window_text() or "").lower()]
        return {
            "ok": bool(matches),
            "backend": "uia",
            "window_title_config": title,
            "matches": matches[:10],
            "message": "Janela encontrada" if matches else "Janela do msAdmin não encontrada",
        }

    def ensure_logged_in(self) -> None:
        raise NotImplementedError("UIA login: mapear na Fase 0 (AnyDesk)")

    def find_patient(self, *, cpf: str | None = None, nome: str | None = None) -> dict[str, Any]:
        raise NotImplementedError("UIA buscar paciente: mapear na Fase 0")

    def create_appointment(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("UIA agendar: mapear na Fase 0")

    def register_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("UIA caixa: mapear na Fase 0")

    def emit_guia(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("UIA guia: mapear na Fase 0")

    def screenshot(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from pywinauto import Desktop

            wins = Desktop(backend="uia").windows()
            title = self.settings.msadmin_window_title.lower()
            target = next((w for w in wins if title in (w.window_text() or "").lower()), None)
            if target is None:
                path.write_bytes(b"")
                return path
            target.capture_as_image().save(str(path))
        except Exception as exc:
            log.warning("screenshot falhou: %s", exc)
            path.write_bytes(b"")
        return path
