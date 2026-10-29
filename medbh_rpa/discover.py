from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from medbh_rpa.config import get_settings

log = logging.getLogger(__name__)


def list_windows() -> list[dict[str, Any]]:
    from pywinauto import Desktop

    out: list[dict[str, Any]] = []
    for w in Desktop(backend="uia").windows():
        try:
            text = w.window_text() or ""
            if not text.strip():
                continue
            out.append(
                {
                    "title": text,
                    "class_name": getattr(w.element_info, "class_name", ""),
                    "handle": int(w.handle) if w.handle else None,
                }
            )
        except Exception:
            continue
    return out


def dump_tree(title_substr: str, *, max_depth: int = 4) -> dict[str, Any]:
    from pywinauto import Desktop

    title_l = title_substr.lower()
    windows = Desktop(backend="uia").windows()
    target = next(
        (w for w in windows if title_l in (w.window_text() or "").lower()),
        None,
    )
    if target is None:
        return {
            "ok": False,
            "message": f"Nenhuma janela contem: {title_substr}",
            "windows": [w["title"] for w in list_windows()[:30]],
        }

    controls: list[dict[str, Any]] = []

    def walk(elem: Any, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            info = elem.element_info
            controls.append(
                {
                    "depth": depth,
                    "control_type": getattr(info, "control_type", ""),
                    "name": getattr(info, "name", "") or "",
                    "automation_id": getattr(info, "automation_id", "") or "",
                    "class_name": getattr(info, "class_name", "") or "",
                }
            )
            for child in elem.children():
                walk(child, depth + 1)
        except Exception:
            return

    walk(target, 0)
    return {
        "ok": True,
        "window_title": target.window_text(),
        "class_name": getattr(target.element_info, "class_name", ""),
        "controls_count": len(controls),
        "controls": controls[:400],
    }


def run_discover(*, dump: bool = True) -> dict[str, Any]:
    settings = get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    windows = list_windows()
    result: dict[str, Any] = {
        "ok": True,
        "msadmin_window_title_env": settings.msadmin_window_title,
        "msadmin_exe_env": settings.msadmin_exe,
        "windows": windows,
    }

    out_windows = settings.artifacts_dir / "discover_windows.json"
    out_windows.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if dump and settings.msadmin_window_title:
        tree = dump_tree(settings.msadmin_window_title)
        result["tree"] = {
            "ok": tree.get("ok"),
            "window_title": tree.get("window_title"),
            "controls_count": tree.get("controls_count"),
            "message": tree.get("message"),
        }
        out_tree = settings.artifacts_dir / "discover_tree.json"
        out_tree.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        result["tree_file"] = str(out_tree.resolve())

    result["windows_file"] = str(out_windows.resolve())
    return result
