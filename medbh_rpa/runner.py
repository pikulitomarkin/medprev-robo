from __future__ import annotations

import logging
import time
import traceback
from datetime import datetime
from typing import Any

from medbh_rpa.config import get_settings
from medbh_rpa.db.jobs import JobStore
from medbh_rpa.flows import get_flow
from medbh_rpa.ui import get_ui

log = logging.getLogger(__name__)


def run_flow(flow_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    ui = get_ui(settings)
    fn = get_flow(flow_name)
    payload = payload or {}
    log.info("executando fluxo=%s", flow_name)
    try:
        result = fn(ui, payload)
        log.info("fluxo=%s ok", flow_name)
        return result
    except Exception:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shot = settings.artifacts_dir / f"fail_{flow_name}_{stamp}.png"
        try:
            ui.screenshot(shot)
            log.error("falha no fluxo=%s — screenshot %s", flow_name, shot)
        except Exception:
            log.error("falha no fluxo=%s (screenshot também falhou)", flow_name)
        raise


def process_one_job(store: JobStore | None = None) -> bool:
    settings = get_settings()
    store = store or JobStore(settings.jobs_db_path)
    job = store.claim_next()
    if not job:
        return False

    log.info("job=%s flow=%s attempt=%s", job.id, job.flow, job.attempts)
    try:
        result = run_flow(job.flow, job.payload)
        store.mark_done(job.id, result)
        return True
    except Exception as exc:
        store.mark_failed(job.id, f"{exc}\n{traceback.format_exc()}")
        return True


def worker_loop(poll_seconds: float = 2.0) -> None:
    settings = get_settings()
    store = JobStore(settings.jobs_db_path)
    log.info("worker iniciado — db=%s", settings.jobs_db_path)
    while True:
        worked = process_one_job(store)
        if not worked:
            time.sleep(poll_seconds)
