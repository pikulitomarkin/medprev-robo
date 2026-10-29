from __future__ import annotations

import json
import logging
from typing import Any

from medbh_rpa.config import get_settings

log = logging.getLogger(__name__)

BACKENDS = ("uia", "win32")


def _list_via_desktop(backend: str) -> list[dict[str, Any]]:
    from pywinauto import Desktop

    out: list[dict[str, Any]] = []
    try:
        windows = Desktop(backend=backend).windows()
    except Exception as exc:
        log.warning("Desktop(%s) falhou: %s", backend, exc)
        return out

    for w in windows:
        try:
            text = (w.window_text() or "").strip()
            class_name = ""
            try:
                class_name = getattr(w.element_info, "class_name", "") or ""
            except Exception:
                class_name = ""
            if not text and not class_name:
                continue
            out.append(
                {
                    "backend": backend,
                    "title": text,
                    "class_name": class_name,
                    "handle": int(w.handle) if w.handle else None,
                }
            )
        except Exception:
            continue
    return out


def _list_via_win32_enum() -> list[dict[str, Any]]:
    """EnumWindows — pega titulos que o Desktop UIA as vezes nao lista."""
    try:
        import win32gui
    except ImportError:
        return []

    out: list[dict[str, Any]] = []

    def _cb(hwnd: int, _acc: list[dict[str, Any]]) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = (win32gui.GetWindowText(hwnd) or "").strip()
        if not title:
            return True
        try:
            class_name = win32gui.GetClassName(hwnd) or ""
        except Exception:
            class_name = ""
        out.append(
            {
                "backend": "win32_enum",
                "title": title,
                "class_name": class_name,
                "handle": int(hwnd),
            }
        )
        return True

    win32gui.EnumWindows(_cb, out)
    return out


def list_windows() -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for backend in BACKENDS:
        for item in _list_via_desktop(backend):
            key = (item.get("title", ""), item.get("class_name", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    for item in _list_via_win32_enum():
        key = (item.get("title", ""), item.get("class_name", ""))
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _find_window(title_substr: str, backend: str) -> Any | None:
    from pywinauto import Desktop

    title_l = title_substr.lower().strip()
    try:
        windows = Desktop(backend=backend).windows()
    except Exception:
        return None
    for w in windows:
        try:
            text = (w.window_text() or "").lower()
            if title_l and title_l in text:
                return w
        except Exception:
            continue
    return None


def dump_tree(title_substr: str, *, max_depth: int = 4) -> dict[str, Any]:
    tried: list[str] = []
    target = None
    used_backend = None

    for backend in BACKENDS:
        tried.append(backend)
        target = _find_window(title_substr, backend)
        if target is not None:
            used_backend = backend
            break

    # Fallback: connect by handle from EnumWindows
    if target is None:
        try:
            import win32gui
            from pywinauto import Application

            title_l = title_substr.lower().strip()
            hwnd_match = None

            def _cb(hwnd: int, _acc: list) -> bool:
                nonlocal hwnd_match
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                text = (win32gui.GetWindowText(hwnd) or "").lower()
                if title_l and title_l in text:
                    hwnd_match = hwnd
                    return False
                return True

            try:
                win32gui.EnumWindows(_cb, [])
            except Exception:
                pass

            if hwnd_match:
                for backend in BACKENDS:
                    try:
                        app = Application(backend=backend).connect(handle=hwnd_match)
                        target = app.window(handle=hwnd_match)
                        used_backend = f"{backend}+handle"
                        break
                    except Exception:
                        continue
        except ImportError:
            pass

    all_titles = [w["title"] for w in list_windows() if w.get("title")]
    if target is None:
        # Sugere titulos parecidos
        hints = [t for t in all_titles if "admin" in t.lower() or "max" in t.lower() or "mx" in t.lower()]
        return {
            "ok": False,
            "message": (
                f"Nenhuma janela contem '{title_substr}'. "
                "Confira MSADMIN_WINDOW_TITLE no .env. "
                f"Backends testados: {', '.join(tried)}."
            ),
            "hints": hints[:20],
            "windows": all_titles[:40],
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
                    "control_type": str(getattr(info, "control_type", "") or ""),
                    "name": str(getattr(info, "name", "") or ""),
                    "automation_id": str(getattr(info, "automation_id", "") or ""),
                    "class_name": str(getattr(info, "class_name", "") or ""),
                }
            )
            for child in elem.children():
                walk(child, depth + 1)
        except Exception:
            return

    walk(target, 0)
    return {
        "ok": True,
        "backend_used": used_backend,
        "window_title": target.window_text(),
        "class_name": str(getattr(target.element_info, "class_name", "") or ""),
        "controls_count": len(controls),
        "controls": controls[:500],
    }


def run_discover(*, dump: bool = True) -> dict[str, Any]:
    settings = get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    windows = list_windows()
    result: dict[str, Any] = {
        "ok": True,
        "msadmin_window_title_env": settings.msadmin_window_title,
        "msadmin_exe_env": settings.msadmin_exe,
        "windows_count": len(windows),
        "windows": windows,
    }

    out_windows = settings.artifacts_dir / "discover_windows.json"
    out_windows.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if dump and settings.msadmin_window_title:
        tree = dump_tree(settings.msadmin_window_title)
        result["tree"] = {
            "ok": tree.get("ok"),
            "backend_used": tree.get("backend_used"),
            "window_title": tree.get("window_title"),
            "controls_count": tree.get("controls_count"),
            "message": tree.get("message"),
            "hints": tree.get("hints"),
        }
        out_tree = settings.artifacts_dir / "discover_tree.json"
        out_tree.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        result["tree_file"] = str(out_tree.resolve())
        result["ok"] = bool(tree.get("ok"))

    result["windows_file"] = str(out_windows.resolve())
    return result
