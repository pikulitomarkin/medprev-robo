from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from medbh_rpa.config import get_settings


def ask_vision_json(
    image_path: Path,
    prompt: str,
    *,
    max_tokens: int = 1200,
) -> dict[str, Any]:
    """Envia imagem + prompt para OpenAI Vision e tenta parsear JSON da resposta."""
    settings = get_settings()
    if not settings.openai_api_key:
        return {"ok": False, "message": "OPENAI_API_KEY ausente no .env"}

    from urllib import request

    raw = Path(image_path).read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    payload = {
        "model": settings.agent_model or "gpt-4.1-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": max_tokens,
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
        with request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return {"ok": False, "message": str(exc)}

    text = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = _parse_json_loose(text)
    return {
        "ok": parsed is not None,
        "data": parsed,
        "raw_text": text,
        "model": settings.agent_model,
        "message": None if parsed is not None else "resposta nao era JSON",
    }


def _parse_json_loose(text: str) -> Any | None:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        chunk = raw[start : end + 1]
        try:
            return json.loads(chunk)
        except Exception:
            # tenta trocar aspas tipograficas
            try:
                return json.loads(
                    chunk.replace("“", '"').replace("”", '"').replace("’", "'")
                )
            except Exception:
                return None
    return None


def describe_screen(image_path: Path) -> dict[str, Any]:
    """Usa OpenAI Vision para listar botoes/campos visiveis (ajuda no mapeamento)."""
    prompt = (
        "Esta e a tela do sistema mxAdmin (intermediacao medica). "
        "Liste em JSON os elementos clicaveis visiveis: menus, botoes, "
        "campos e abas. Formato: "
        '{"elements":[{"name":"...","type":"button|field|menu|tab",'
        '"x":int,"y":int,'
        '"approx_position":"top|center|bottom left|right",'
        '"notes":"..."}],'
        '"screen_title":"...","purpose":"..."} '
        "x,y = centro aproximado em pixels. "
        "NAO inclua CPF, senhas, tokens ou dados pessoais completos — "
        "use rotulos genericos (ex.: campo CPF). Sem markdown, so JSON."
    )
    result = ask_vision_json(image_path, prompt, max_tokens=1200)
    if not result.get("ok"):
        return result
    parsed = result.get("data") or {}
    return {
        "ok": True,
        "raw_text": result.get("raw_text"),
        "elements": parsed.get("elements") if isinstance(parsed, dict) else None,
        "model": result.get("model"),
    }
