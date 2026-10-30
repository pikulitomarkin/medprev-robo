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
from medbh_rpa.vision.controller import VisionController
from medbh_rpa.vision.describe import describe_screen


def _parse_payload(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(raw.replace("'", '"'))


def _print(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(prog="medbh-rpa", description="RPA Instituto MedBH")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("healthcheck", help="Verifica ambiente e UI")

    p_disc = sub.add_parser("discover", help="Acha mxAdmin + screenshot rapido")
    p_disc.add_argument("--no-tree", action="store_true")

    p_vis = sub.add_parser("vision", help="RPA por OpenCV / screenshot")
    vis_sub = p_vis.add_subparsers(dest="vision_cmd", required=True)
    vis_sub.add_parser("focus", help="Traz mxAdmin para frente")
    vis_sub.add_parser("snapshot", help="Captura tela do mxAdmin")
    p_scan = vis_sub.add_parser("scan", help="Snapshot + OpenAI lista elementos")
    p_scan.add_argument("--image", default="", help="PNG ja capturado (opcional)")
    p_click = vis_sub.add_parser("click", help="Clique por coordenadas relativas a janela")
    p_click.add_argument("x", type=int)
    p_click.add_argument("y", type=int)
    p_tpl = vis_sub.add_parser("click-template", help="Clique achar imagem template")
    p_tpl.add_argument("name")
    p_tpl.add_argument("--threshold", type=float, default=0.82)
    p_crop = vis_sub.add_parser("crop-template", help="Recorta template da last.png")
    p_crop.add_argument("name")
    p_crop.add_argument("left", type=int)
    p_crop.add_argument("top", type=int)
    p_crop.add_argument("right", type=int)
    p_crop.add_argument("bottom", type=int)
    p_type = vis_sub.add_parser("type", help="Digita texto")
    p_type.add_argument("text")
    p_rec = vis_sub.add_parser("record", help="Registra passo JSON no fluxo")
    p_rec.add_argument("flow")
    p_rec.add_argument("--step", required=True, help="JSON do passo")
    p_runf = vis_sub.add_parser("run-flow", help="Executa fluxo mapeado em data/maps")
    p_runf.add_argument("flow")
    p_exp = vis_sub.add_parser(
        "explore-menus",
        help="Clica Cadastros/Atendimento/Caixa/Financeiro/Relatorios e mapeia dropdowns",
    )
    p_exp.add_argument(
        "--menus",
        default="",
        help="Lista separada por virgula (padrao: 5 menus principais)",
    )
    p_exp.add_argument("--pause", type=float, default=0.9, help="Espera apos cada clique")

    p_run = sub.add_parser("run", help="Executa um fluxo stub (mock/uia)")
    p_run.add_argument("flow", choices=sorted(FLOWS.keys()))
    p_run.add_argument("--payload", default="{}")

    p_enq = sub.add_parser("enqueue", help="Enfileira job")
    p_enq.add_argument("flow", choices=sorted(FLOWS.keys()))
    p_enq.add_argument("--payload", default="{}")
    p_enq.add_argument("--key", default=None)

    p_worker = sub.add_parser("worker", help="Worker da fila")
    p_worker.add_argument("--poll", type=float, default=2.0)

    sub.add_parser("mcp", help="Sobe MCP HTTP (Tailscale) para o Cursor controlar o mxAdmin")

    args = parser.parse_args(argv)

    if args.command == "healthcheck":
        return print_healthcheck()

    if args.command == "discover":
        result = run_discover(dump=not args.no_tree, fast=True)
        slim = {
            "ok": result.get("ok"),
            "elapsed_sec": result.get("elapsed_sec"),
            "window": result.get("window"),
            "process_forms_count": result.get("process_forms_count"),
            "screenshot": result.get("screenshot"),
            "screenshot_method": result.get("screenshot_method"),
            "screenshot_error": result.get("screenshot_error"),
            "automation_strategy": result.get("automation_strategy"),
            "note": result.get("note"),
            "next_steps": result.get("next_steps"),
            "message": result.get("message"),
            "result_file": result.get("result_file"),
        }
        _print(slim)
        return 0 if result.get("ok") else 1

    if args.command == "vision":
        vc = VisionController()
        cmd = args.vision_cmd
        if cmd == "focus":
            _print(vc.focus())
            return 0
        if cmd == "snapshot":
            _print(vc.snapshot("screen"))
            return 0
        if cmd == "scan":
            from pathlib import Path

            if args.image:
                img = Path(args.image)
                snap = {"ok": img.exists(), "path": str(img), "last": str(img)}
            else:
                snap = vc.snapshot("scan")
            if not snap.get("ok"):
                _print(snap)
                return 1
            desc = describe_screen(Path(snap["path"]))
            out_path = get_settings().artifacts_dir / "scan_elements.json"
            out_path.write_text(
                json.dumps({"snapshot": snap, "describe": desc}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            _print(
                {
                    "ok": bool(desc.get("ok")),
                    "snapshot": snap.get("path"),
                    "elements": desc.get("elements"),
                    "message": desc.get("message"),
                    "saved": str(out_path.resolve()),
                }
            )
            return 0 if desc.get("ok") else 1
        if cmd == "click":
            _print(vc.click_xy(args.x, args.y, absolute=False))
            return 0
        if cmd == "click-template":
            _print(vc.click_template(args.name, threshold=args.threshold))
            return 0
        if cmd == "crop-template":
            _print(
                vc.save_template_crop(
                    args.name, args.left, args.top, args.right, args.bottom
                )
            )
            return 0
        if cmd == "type":
            _print(vc.type_into(args.text))
            return 0
        if cmd == "record":
            step = _parse_payload(args.step)
            _print(vc.record_step(args.flow, step))
            return 0
        if cmd == "run-flow":
            _print(vc.run_flow_file(args.flow))
            return 0
        if cmd == "explore-menus":
            from medbh_rpa.vision.explore import DEFAULT_MENUS, explore_top_menus

            menus = (
                [m.strip() for m in args.menus.split(",") if m.strip()]
                if args.menus
                else list(DEFAULT_MENUS)
            )
            result = explore_top_menus(vc, menus=menus, pause=args.pause)
            slim = {
                "ok": result.get("ok"),
                "mode": result.get("mode"),
                "missing": result.get("missing"),
                "map_file": result.get("map_file"),
                "index_file": result.get("index_file"),
                "out_dir": result.get("out_dir"),
                "menus": [
                    {
                        "name": m.get("name"),
                        "ok": m.get("ok"),
                        "coords": m.get("coords"),
                        "screen_summary": (m.get("describe") or {}).get("screen_summary"),
                        "items": [
                            i.get("label")
                            for i in ((m.get("describe") or {}).get("items") or [])
                        ],
                        "error": m.get("message") or m.get("describe_error"),
                    }
                    for m in (result.get("menus") or [])
                ],
                "message": result.get("message"),
            }
            _print(slim)
            return 0 if result.get("ok") else 1

    if args.command == "run":
        _print(run_flow(args.flow, _parse_payload(args.payload)))
        return 0

    if args.command == "enqueue":
        settings = get_settings()
        store = JobStore(settings.jobs_db_path)
        job = store.enqueue(
            args.flow, _parse_payload(args.payload), idempotency_key=args.key
        )
        _print(
            {
                "id": job.id,
                "flow": job.flow,
                "status": job.status.value,
                "idempotency_key": job.idempotency_key,
            }
        )
        return 0

    if args.command == "worker":
        worker_loop(poll_seconds=args.poll)
        return 0

    if args.command == "mcp":
        from medbh_rpa.mcp_server import main as mcp_main

        mcp_main()
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
