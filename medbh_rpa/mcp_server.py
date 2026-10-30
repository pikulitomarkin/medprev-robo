from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

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
    "So navegacao/snapshot/scan liberados. Passe allow_write=true "
    "apenas com supervisao humana para gravar/cancelar/emitir."
)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _require_write(allow_write: bool) -> dict[str, Any] | None:
    if allow_write:
        return None
    return {"ok": False, "blocked": True, "message": WRITE_BLOCKED}


def build_server() -> Any:
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.server.transport_security import TransportSecuritySettings
    except ImportError as exc:
        raise RuntimeError(
            "Pacote mcp necessario: pip install 'mcp>=1.9' uvicorn starlette"
        ) from exc

    settings = get_settings()
    vc = VisionController(settings)
    server = MCPServer(
        "medbh-mxadmin",
        instructions=(
            "Controla o mxAdmin no PC do consultorio via OpenCV/PrintWindow. "
            "Use mx_snapshot/mx_scan/mx_open_menu_item/mx_map_screen para mapear. "
            "Modo seguro: allow_write=false (padrao). Nao grave atendimento real "
            "sem confirmacao humana."
        ),
    )

    @server.tool()
    def mx_focus() -> str:
        """Traz a janela mxAdmin para frente."""
        return _json(vc.focus())

    @server.tool()
    def mx_snapshot(name: str = "screen") -> str:
        """Captura screenshot da janela mxAdmin (PrintWindow)."""
        return _json(vc.snapshot(name or "screen"))

    @server.tool()
    def mx_scan() -> str:
        """Snapshot + OpenAI Vision lista elementos (sem dados pessoais)."""
        snap = vc.snapshot("scan")
        if not snap.get("ok"):
            return _json(snap)
        desc = describe_screen(Path(snap["path"]))
        out = settings.artifacts_dir / "scan_elements.json"
        payload = {"snapshot": snap, "describe": desc}
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return _json(
            {
                "ok": bool(desc.get("ok")),
                "snapshot": snap.get("path"),
                "elements": desc.get("elements"),
                "screen_title": (desc.get("elements") and None),
                "raw_ok": desc.get("ok"),
                "message": desc.get("message"),
                "saved": str(out.resolve()),
                "describe": desc,
            }
        )

    @server.tool()
    def mx_click(x: int, y: int, allow_write: bool = False) -> str:
        """Clique relativo a janela mxAdmin (origem canto superior esquerdo da captura)."""
        blocked = _require_write(allow_write)
        # clique de navegacao permitido; allow_write so documenta intencao
        _ = blocked
        return _json(vc.click_xy(int(x), int(y), absolute=False))

    @server.tool()
    def mx_click_template(name: str, threshold: float = 0.82, allow_write: bool = False) -> str:
        """Clique por template OpenCV em data/maps/templates/<name>.png."""
        _ = allow_write
        return _json(vc.click_template(name, threshold=float(threshold)))

    @server.tool()
    def mx_type(text: str, allow_write: bool = False) -> str:
        """Digita texto na janela focada. Requer allow_write=true (pode alterar campos)."""
        blocked = _require_write(allow_write)
        if blocked:
            return _json(blocked)
        return _json(vc.type_into(text))

    @server.tool()
    def mx_key(key: str = "{ESC}", allow_write: bool = False) -> str:
        """SendKeys (ex.: {ESC}, {ENTER}, {TAB}). ESC sempre permitido."""
        k = key or "{ESC}"
        if k.upper() not in ("{ESC}", "{TAB}", "{UP}", "{DOWN}", "{LEFT}", "{RIGHT}"):
            blocked = _require_write(allow_write)
            if blocked:
                return _json(blocked)
        press_key(k)
        return _json({"ok": True, "key": k})

    @server.tool()
    def mx_explore_menus(menus: str = "", pause: float = 0.9) -> str:
        """Clica menus do topo e mapeia dropdowns (Cadastros/Atendimento/...)."""
        menu_list = (
            [m.strip() for m in menus.split(",") if m.strip()]
            if menus
            else list(DEFAULT_MENUS)
        )
        return _json(explore_top_menus(vc, menus=menu_list, pause=float(pause)))

    @server.tool()
    def mx_open_menu_item(menu: str, item: str, pause: float = 0.7) -> str:
        """Abre menu do topo e clica item pelo texto (Vision). Ex.: Atendimento + Agendar Atendimento."""
        return _json(open_menu_item(vc, menu, item, pause=float(pause)))

    @server.tool()
    def mx_map_screen(name: str, close_after: bool = False) -> str:
        """Snapshot + scan e grava data/maps/screens/<name>_*.json."""
        return _json(map_screen(vc, name, close_after=bool(close_after)))

    @server.tool()
    def mx_list_maps() -> str:
        """Lista mapas e templates ja salvos em data/maps."""
        return _json(list_maps(vc.maps_dir))

    # guarda settings de transport no server object
    server._medbh_transport_security = TransportSecuritySettings(  # type: ignore[attr-defined]
        enable_dns_rebinding_protection=False,
    )
    return server


class _BearerAuthMiddleware:
    """ASGI middleware — exige Authorization: Bearer <MCP_TOKEN>."""

    def __init__(self, app: Any, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.token:
            await self._send_json(send, 503, {"error": "MCP_TOKEN ausente no .env"})
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers") or []}
        auth = headers.get("authorization", "")
        ok = auth == f"Bearer {self.token}"
        if not ok:
            # query ?token=
            qs = scope.get("query_string", b"").decode()
            from urllib.parse import parse_qs

            q = parse_qs(qs).get("token", [None])[0]
            ok = q == self.token
        if not ok:
            await self._send_json(send, 401, {"error": "unauthorized"})
            return
        await self.app(scope, receive, send)

    async def _send_json(self, send: Any, status: int, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": raw})


def main() -> None:
    setup_logging()
    settings = get_settings()
    token = (settings.mcp_token or os.environ.get("MCP_TOKEN") or "").strip()
    host = settings.mcp_host or "0.0.0.0"
    port = int(settings.mcp_port or 8765)

    if not token:
        log.error("Defina MCP_TOKEN no .env antes de subir o MCP.")
        raise SystemExit(2)

    server = build_server()
    try:
        import uvicorn
        from mcp.server.transport_security import TransportSecuritySettings
    except ImportError as exc:
        raise SystemExit(f"deps MCP ausentes: {exc}") from exc

    security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    starlette_app = server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        transport_security=security,
        host=host,
    )
    app = _BearerAuthMiddleware(starlette_app, token)

    log.info("MCP medbh-mxadmin em http://%s:%s/mcp (Bearer auth)", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
