from __future__ import annotations

from pathlib import Path

from medbh_rpa.db.jobs import JobStatus, JobStore


def test_enqueue_same_key_does_not_duplicate(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    a = store.enqueue("buscar_paciente", {"nome": "Ana"}, idempotency_key="k1")
    b = store.enqueue("buscar_paciente", {"nome": "Ana"}, idempotency_key="k1")
    assert a.id == b.id
    assert a.status == JobStatus.PENDING


def test_claim_marks_running(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.enqueue("healthcheck", {}, idempotency_key="h1")
    job = store.claim_next()
    assert job is not None
    assert job.status == JobStatus.RUNNING
    assert job.attempts == 1
    assert store.claim_next() is None
