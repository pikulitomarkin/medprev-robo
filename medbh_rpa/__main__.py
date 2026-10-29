from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from medbh_rpa.config import get_settings
from medbh_rpa.db.jobs import JobStore
from medbh_rpa.discover import run_discover
from medbh_rpa.flows import FLOWS
from medbh_rpa.healthcheck import print_healthcheck
from medbh_rpa.logging_utils import setup_logging
from medbh_rpa.runner import run_flow, worker_loop


def _parse_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # PowerShell costuma engolir aspas; tenta aspas simples → JSON
        return json.loads(raw.replace("'", '"'))


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(prog="medbh-rpa", description="RPA Instituto MedBH")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("healthcheck", help="Verifica ambiente e UI")

    p_disc = sub.add_parser(
        "discover",
        help="Lista janelas e dumpa a arvore UIA do msAdmin (Fase 0)",
    )
    p_disc.add_argument(
        "--no-tree",
        action="store_true",
        help="So lista janelas, sem dump da arvore",
    )

    p_run = sub.add_parser("run", help="Executa um fluxo imediatamente")
    p_run.add_argument("flow", choices=sorted(FLOWS.keys()))
    p_run.add_argument("--payload", default="{}", help="JSON do payload")

    p_enq = sub.add_parser("enqueue", help="Enfileira job idempotente")
    p_enq.add_argument("flow", choices=sorted(FLOWS.keys()))
    p_enq.add_argument("--payload", default="{}", help="JSON do payload")
    p_enq.add_argument("--key", default=None, help="Chave de idempotência")

    p_worker = sub.add_parser("worker", help="Processa a fila em loop")
    p_worker.add_argument("--poll", type=float, default=2.0)

    args = parser.parse_args(argv)

    if args.command == "healthcheck":
        return print_healthcheck()

    if args.command == "discover":
        result = run_discover(dump=not args.no_tree)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "run":
        payload = _parse_payload(args.payload)
        result = run_flow(args.flow, payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "enqueue":
        settings = get_settings()
        store = JobStore(settings.jobs_db_path)
        payload = _parse_payload(args.payload)
        job = store.enqueue(args.flow, payload, idempotency_key=args.key)
        print(
            json.dumps(
                {
                    "id": job.id,
                    "flow": job.flow,
                    "status": job.status.value,
                    "idempotency_key": job.idempotency_key,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "worker":
        worker_loop(poll_seconds=args.poll)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
