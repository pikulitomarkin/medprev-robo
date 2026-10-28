from __future__ import annotations

from typing import Any

from medbh_rpa.ui.base import UiAdapter


def run(ui: UiAdapter, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = payload
    ui.ensure_logged_in()
    return {"status": "logged_in"}
