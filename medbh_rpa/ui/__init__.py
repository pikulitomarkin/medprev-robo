from __future__ import annotations

from medbh_rpa.config import Settings, get_settings
from medbh_rpa.ui.base import UiAdapter
from medbh_rpa.ui.mock import MockUi


def get_ui(settings: Settings | None = None) -> UiAdapter:
    settings = settings or get_settings()
    backend = settings.ui_backend

    if backend == "mock":
        return MockUi(settings)

    if backend == "uia":
        from medbh_rpa.ui.uia import UiaAdapter

        return UiaAdapter(settings)

    if backend == "playwright":
        from medbh_rpa.ui.playwright_ui import PlaywrightUi

        return PlaywrightUi(settings)

    # auto: tenta UIA; se falhar na Fase 0, documentar e forçar no .env
    try:
        from medbh_rpa.ui.uia import UiaAdapter

        return UiaAdapter(settings)
    except Exception:
        return MockUi(settings)


__all__ = ["UiAdapter", "get_ui"]
