from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from medbh_rpa.config import get_settings


def describe_screen(image_path: Path) -> dict[str, Any]:
    """Usa OpenAI Vision para listar botoes/campos visiveis (ajuda no mapeamento)."""
    settings = get_settings()
    if not settings.openai_api_key:
        return {
            "ok": False,
            "message": "OPENAI_API_KEY ausente no .env",
        }

    try:
        from urllib import request
    except ImportError:
        return {"ok": False, "message": "urllib indisponivel"}

    raw = Path(image_path).read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    payload = {
        "model": settings.agent_model or "gpt-4.1-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Esta e a tela do sistema mxAdmin (intermediacao medica). "
                            "Liste em JSON os elementos clicaveis visiveis: menus, botoes, "
                            "campos e abas. Formato: "
                            '{"elements":[{"name":"...","type":"button|field|menu|tab",'
                            '"approx_position":"top|center|bottom left|right",'
                            '"notes":"..."}]} '
                            "Sem markdown, so JSON."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 1200,
    }

    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "message": str(exc)}

    text = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except Exception:
        # tenta extrair bloco JSON
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
            except Exception:
                parsed = None

    return {
        "ok": True,
        "raw_text": text,
        "elements": (parsed or {}).get("elements") if isinstance(parsed, dict) else None,
        "model": settings.agent_model,
    }
