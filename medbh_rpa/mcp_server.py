from __future__ import annotations

"""
Servidor HTTP lite para controlar o mxAdmin (sem pacote `mcp` / cryptography).

Motivo: Python 3.14-32 no consultorio nao tem wheel de cryptography (MSVC).

Endpoints (Bearer MCP_TOKEN):
  GET  /health
  GET  /tools
  POST /tools/<name>   JSON body = argumentos da tool
  POST /mcp            alias JSON-RPC minimo { "method": "tools/call", "params": { "name", "arguments" } }

O Cursor pode usar type=http se o protocolo MCP completo estiver disponivel;
enquanto isso o agente no PC do Marcos chama estes endpoints via Tailscale.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

from medbh_rpa.config import get_settings
from medbh_rpa.logging_utils import setup_logging
from medbh_rpa.vision.controller import VisionController
from medbh_rpa.vision.describe import describe_screen
from medbh_rpa.vision.explore import DEFAULT_MENUS, explore_top_menus
from medbh_rpa.vision.input_win import press_key
from medbh_rpa.vision.menus import list_maps, map_screen, open_menu_item

log = logging.getLogger(__name__)

WRITE_BLOCKED = (
    "Acao bloqueada: allow_write=false (modo mapa). "
    "Passe allow_write=true so com supervisao humana."
)


def _require_write(allow_write: bool) -> dict[str, Any] | None:
    if allow_write:
        return None
    return {"ok": False, "blocked": True, "message": WRITE_BLOCKED}


def build_tools(vc: VisionController) -> dict[str, Callable[..., dict[str, Any]]]:
    settings = vc.settings

    def mx_focus() -> dict[str, Any]:
        return vc.focus()

    def mx_snapshot(name: str = "screen") -> dict[str, Any]:
        return vc.snapshot(name or "screen")

    def mx_scan() -> dict[str, Any]:
        snap = vc.snapshot("scan")
        if not snap.get("ok"):
            return snap
        desc = describe_screen(Path(snap["path"]))
        out = settings.artifacts_dir / "scan_elements.json"
        out.write_text(
            json.dumps({"snapshot": snap, "describe": desc}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "ok": bool(desc.get("ok")),
            "snapshot": snap.get("path"),
            "elements": desc.get("elements"),
            "message": desc.get("message"),
            "saved": str(out.resolve()),
            "describe": desc,
        }

    def mx_click(x: int, y: int, allow_write: bool = False) -> dict[str, Any]:
        _ = allow_write
        return vc.click_xy(int(x), int(y), absolute=False)

    def mx_click_template(
        name: str, threshold: float = 0.82, allow_write: bool = False
    ) -> dict[str, Any]:
        _ = allow_write
        return vc.click_template(name, threshold=float(threshold))

    def mx_type(text: str, allow_write: bool = False) -> dict[str, Any]:
        blocked = _require_write(bool(allow_write))
        if blocked:
            return blocked
        return vc.type_into(text)

    def mx_key(key: str = "{ESC}", allow_write: bool = False) -> dict[str, Any]:
        k = key or "{ESC}"
        if k.upper() not in ("{ESC}", "{TAB}", "{UP}", "{DOWN}", "{LEFT}", "{RIGHT}"):
            blocked = _require_write(bool(allow_write))
            if blocked:
                return blocked
        press_key(k)
        return {"ok": True, "key": k}

    def mx_explore_menus(menus: str = "", pause: float = 0.9) -> dict[str, Any]:
        menu_list = (
            [m.strip() for m in menus.split(",") if m.strip()]
            if menus
            else list(DEFAULT_MENUS)
        )
        return explore_top_menus(vc, menus=menu_list, pause=float(pause))

    def mx_open_menu_item(menu: str, item: str, pause: float = 0.7) -> dict[str, Any]:
        return open_menu_item(vc, menu, item, pause=float(pause))

    def mx_map_screen(name: str, close_after: bool = False) -> dict[str, Any]:
        return map_screen(vc, name, close_after=bool(close_after))

    def mx_list_maps() -> dict[str, Any]:
        return list_maps(vc.maps_dir)

    return {
        "mx_focus": mx_focus,
        "mx_snapshot": mx_snapshot,
        "mx_scan": mx_scan,
        "mx_click": mx_click,
        "mx_click_template": mx_click_template,
        "mx_type": mx_type,
        "mx_key": mx_key,
        "mx_explore_menus": mx_explore_menus,
        "mx_open_menu_item": mx_open_menu_item,
        "mx_map_screen": mx_map_screen,
        "mx_list_maps": mx_list_maps,
    }


TOOL_SCHEMA: list[dict[str, Any]] = [
    {"name": "mx_focus", "description": "Foca mxAdmin", "params": {}},
    {"name": "mx_snapshot", "description": "Screenshot PrintWindow", "params": {"name": "str"}},
    {"name": "mx_scan", "description": "Snapshot + OpenAI Vision", "params": {}},
    {"name": "mx_click", "description": "Clique x,y relativo", "params": {"x": "int", "y": "int"}},
    {
        "name": "mx_click_template",
        "description": "Clique por template",
        "params": {"name": "str", "threshold": "float"},
    },
    {
        "name": "mx_type",
        "description": "Digita (allow_write=true)",
        "params": {"text": "str", "allow_write": "bool"},
    },
    {"name": "mx_key", "description": "SendKeys", "params": {"key": "str"}},
    {
        "name": "mx_explore_menus",
        "description": "Mapeia menus do topo",
        "params": {"menus": "str", "pause": "float"},
    },
    {
        "name": "mx_open_menu_item",
        "description": "Abre menu+item por texto",
        "params": {"menu": "str", "item": "str", "pause": "float"},
    },
    {
        "name": "mx_map_screen",
        "description": "Grava mapa da tela",
        "params": {"name": "str", "close_after": "bool"},
    },
    {"name": "mx_list_maps", "description": "Lista mapas", "params": {}},
]


def create_app(token: str) -> Any:
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    settings = get_settings()
    vc = VisionController(settings)
    tools = build_tools(vc)

    def _auth_ok(request: Request) -> bool:
        auth = request.headers.get("authorization", "")
        if auth == f"Bearer {token}":
            return True
        return request.query_params.get("token") == token

    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"ok": True, "service": "medbh-mxadmin", "mode": "http-lite"})

    async def list_tools(request: Request) -> JSONResponse:
        if not _auth_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return JSONResponse({"ok": True, "tools": TOOL_SCHEMA})

    async def call_tool(request: Request) -> JSONResponse:
        if not _auth_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        name = request.path_params["name"]
        if name not in tools:
            return JSONResponse({"ok": False, "error": f"unknown tool: {name}"}, status_code=404)
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        try:
            result = tools[name](**body)
        except TypeError as exc:
            return JSONResponse({"ok": False, "error": f"bad args: {exc}"}, status_code=400)
        except Exception as exc:
            log.exception("tool %s failed", name)
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
        return JSONResponse(result)

    async def mcp_alias(request: Request) -> JSONResponse:
        """JSON-RPC minimo para clients que POSTam em /mcp."""
        if not _auth_ok(request):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        method = (payload or {}).get("method")
        params = (payload or {}).get("params") or {}
        req_id = (payload or {}).get("id")
        if method in ("tools/list", "list_tools"):
            return JSONResponse(
                {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOL_SCHEMA}}
            )
        if method in ("tools/call", "call_tool"):
            name = params.get("name")
            args = params.get("arguments") or params.get("args") or {}
            if name not in tools:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"unknown tool: {name}"},
                    }
                )
            try:
                result = tools[name](**args)
            except Exception as exc:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32000, "message": str(exc)},
                    }
                )
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
                    },
                }
            )
        if method in ("initialize", "notifications/initialized"):
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "medbh-mxadmin", "version": "0.1.0"},
                    },
                }
            )
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"method not found: {method}"},
            }
        )

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/tools", list_tools, methods=["GET"]),
        Route("/tools/{name}", call_tool, methods=["POST"]),
        Route("/mcp", mcp_alias, methods=["POST", "GET"]),
    ]
    return Starlette(routes=routes)


def main() -> None:
    setup_logging()
    settings = get_settings()
    token = (settings.mcp_token or os.environ.get("MCP_TOKEN") or "").strip()
    host = settings.mcp_host or "0.0.0.0"
    port = int(settings.mcp_port or 8765)

    if not token:
        log.error("Defina MCP_TOKEN no .env antes de subir o servidor.")
        raise SystemExit(2)

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn/starlette ausentes. Rode: python -m pip install uvicorn starlette anyio"
        ) from exc

    app = create_app(token)
    log.info("MedBH HTTP lite em http://%s:%s  (GET /health, POST /tools/<name>)", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
