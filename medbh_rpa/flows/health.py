from __future__ import annotations

from typing import Any

from medbh_rpa.ui.base import UiAdapter


def run(ui: UiAdapter, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = payload
    return ui.healthcheck()
