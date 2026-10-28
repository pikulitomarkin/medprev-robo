from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Job:
    id: str
    flow: str
    idempotency_key: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    result: dict[str, Any] | None
    error: str | None
    created_at: str
    updated_at: str


class JobStore:
    """Fila local com idempotência por (flow, idempotency_key)."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    flow TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(flow, idempotency_key)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status, created_at)"
            )
            conn.commit()

    def enqueue(
        self,
        flow: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> Job:
        key = idempotency_key or uuid.uuid4().hex
        now = _utc_now()
        job_id = uuid.uuid4().hex

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM jobs WHERE flow = ? AND idempotency_key = ?",
                (flow, key),
            ).fetchone()
            if existing:
                return self._row_to_job(existing)

            conn.execute(
                """
                INSERT INTO jobs (
                    id, flow, idempotency_key, payload_json, status,
                    attempts, result_json, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (job_id, flow, key, json.dumps(payload, ensure_ascii=False), JobStatus.PENDING.value, now, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return self._row_to_job(row)

    def claim_next(self) -> Job | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (JobStatus.PENDING.value,),
            ).fetchone()
            if not row:
                return None
            now = _utc_now()
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, attempts = attempts + 1, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (JobStatus.RUNNING.value, now, row["id"], JobStatus.PENDING.value),
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],)).fetchone()
            return self._row_to_job(updated)

    def mark_done(self, job_id: str, result: dict[str, Any] | None = None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, result_json = ?, error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    JobStatus.DONE.value,
                    json.dumps(result or {}, ensure_ascii=False),
                    _utc_now(),
                    job_id,
                ),
            )
            conn.commit()

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, error = ?, updated_at = ?
                WHERE id = ?
                """,
                (JobStatus.FAILED.value, error[:2000], _utc_now(), job_id),
            )
            conn.commit()

    def get(self, job_id: str) -> Job | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return self._row_to_job(row) if row else None

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            flow=row["flow"],
            idempotency_key=row["idempotency_key"],
            payload=json.loads(row["payload_json"] or "{}"),
            status=JobStatus(row["status"]),
            attempts=row["attempts"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
