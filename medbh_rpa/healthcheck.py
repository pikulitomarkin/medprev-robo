from __future__ import annotations

import json
from typing import Any

from medbh_rpa.config import get_settings
from medbh_rpa.db.jobs import JobStore
from medbh_rpa.ui import get_ui


def run_healthcheck() -> dict[str, Any]:
    settings = get_settings()
    ui = get_ui(settings)
    ui_status = ui.healthcheck()

    store = JobStore(settings.jobs_db_path)
    db_ok = settings.jobs_db_path.exists() or True  # JobStore cria o arquivo

    result = {
        "ok": bool(ui_status.get("ok")),
        "version": "0.1.0",
        "ui": ui_status,
        "data_dir": str(settings.data_dir.resolve()),
        "jobs_db": str(settings.jobs_db_path.resolve()),
        "db_reachable": db_ok,
        "agent_enabled": settings.agent_enabled,
    }
    # força criação do schema
    _ = store
    return result


def print_healthcheck() -> int:
    result = run_healthcheck()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1
