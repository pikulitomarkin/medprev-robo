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
    seen: set[tuple[str, int | None]] = set()
    merged: list[dict[str, Any]] = []
    for backend in BACKENDS:
        for item in _list_via_desktop(backend):
            key = (item.get("title", ""), item.get("handle"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    for item in _list_via_win32_enum():
        key = (item.get("title", ""), item.get("handle"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _find_hwnd(title_substr: str) -> tuple[int | None, str | None, str | None]:
    """Retorna (hwnd, title, class_name) pelo titulo parcial."""
    title_l = title_substr.lower().strip()
    for w in list_windows():
        title = w.get("title") or ""
        if title_l and title_l in title.lower() and w.get("handle"):
            return int(w["handle"]), title, w.get("class_name")
    return None, None, None


def _connect_window(hwnd: int, backend: str) -> Any | None:
    from pywinauto import Application

    try:
        app = Application(backend=backend).connect(handle=hwnd)
        return app.window(handle=hwnd)
    except Exception as exc:
        log.warning("connect handle=%s backend=%s: %s", hwnd, backend, exc)
        return None


def _walk_controls(root: Any, *, max_depth: int = 6, limit: int = 800) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []

    def walk(elem: Any, depth: int) -> None:
        if depth > max_depth or len(controls) >= limit:
            return
        try:
            info = elem.element_info
            name = str(getattr(info, "name", "") or "")
            automation_id = str(getattr(info, "automation_id", "") or "")
            control_type = str(getattr(info, "control_type", "") or "")
            class_name = str(getattr(info, "class_name", "") or "")
            # Ignora nos internos vazios demais no nivel 0 ja capturado
            controls.append(
                {
                    "depth": depth,
                    "control_type": control_type,
                    "name": name,
                    "automation_id": automation_id,
                    "class_name": class_name,
                }
            )
        except Exception:
            return

        kids: list[Any] = []
        try:
            kids = list(elem.children())
        except Exception:
            kids = []
        if not kids and depth == 0:
            # WinForms: descendants costuma achar o que children nao traz
            try:
                kids = list(elem.descendants())
                # descendants ja e flat — registra e para
                for d in kids[:limit]:
                    try:
                        info = d.element_info
                        controls.append(
                            {
                                "depth": 1,
                                "control_type": str(getattr(info, "control_type", "") or ""),
                                "name": str(getattr(info, "name", "") or ""),
                                "automation_id": str(getattr(info, "automation_id", "") or ""),
                                "class_name": str(getattr(info, "class_name", "") or ""),
                            }
                        )
                    except Exception:
                        continue
                return
            except Exception:
                return

        for child in kids:
            walk(child, depth + 1)

    walk(root, 0)
    return controls


def dump_tree(title_substr: str, *, max_depth: int = 6) -> dict[str, Any]:
    hwnd, found_title, class_name = _find_hwnd(title_substr)
    all_titles = [w["title"] for w in list_windows() if w.get("title")]

    if hwnd is None:
        hints = [
            t
            for t in all_titles
            if any(x in t.lower() for x in ("admin", "max", "mx", "viv", "run"))
        ]
        return {
            "ok": False,
            "message": (
                f"Nenhuma janela contem '{title_substr}'. "
                "Confira MSADMIN_WINDOW_TITLE no .env."
            ),
            "hints": hints[:20],
            "windows": all_titles[:40],
        }

    # WinForms: preferir UIA no handle (arvore rica). win32 como fallback.
    used_backend = None
    target = None
    controls: list[dict[str, Any]] = []

    for backend in ("uia", "win32"):
        target = _connect_window(hwnd, backend)
        if target is None:
            continue
        used_backend = backend
        controls = _walk_controls(target, max_depth=max_depth)
        # Se UIA trouxe controles, para. Se zerou, tenta o outro backend.
        if controls and (len(controls) > 1 or backend == "win32"):
            break

    # Identifiers textuais (ajuda no mapeamento manual)
    identifiers = ""
    if target is not None:
        try:
            # pywinauto imprime em stdout; capturamos via wrapper se existir
            identifiers = target.dump_tree() if hasattr(target, "dump_tree") else ""
        except Exception:
            identifiers = ""
        if not identifiers:
            try:
                # Fallback: print_control_identifiers para string
                from io import StringIO
                import sys

                buf = StringIO()
                old = sys.stdout
                sys.stdout = buf
                try:
                    target.print_control_identifiers(depth=4)
                finally:
                    sys.stdout = old
                identifiers = buf.getvalue()
            except Exception as exc:
                identifiers = f"(identifiers indisponivel: {exc})"

    ok = bool(controls) or bool(identifiers)
    return {
        "ok": ok,
        "backend_used": used_backend,
        "hwnd": hwnd,
        "window_title": found_title,
        "class_name": class_name,
        "controls_count": len(controls),
        "controls": controls[:500],
        "identifiers_preview": (identifiers or "")[:8000],
        "note": (
            "WinForms (.NET). Use backend uia no handle. "
            "MSADMIN_EXE deve apontar para o .exe (ex.: RunAdmin.exe), nao para a pasta Desktop."
            if ok
            else "Janela achada mas sem controles — rode o Git CMD como Administrador se o mxAdmin for elevado."
        ),
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
            "hwnd": tree.get("hwnd"),
            "window_title": tree.get("window_title"),
            "class_name": tree.get("class_name"),
            "controls_count": tree.get("controls_count"),
            "message": tree.get("message"),
            "hints": tree.get("hints"),
            "note": tree.get("note"),
        }
        out_tree = settings.artifacts_dir / "discover_tree.json"
        out_tree.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")

        # Salva identifiers em texto puro para leitura humana
        ids = tree.get("identifiers_preview") or ""
        if ids:
            (settings.artifacts_dir / "discover_identifiers.txt").write_text(
                ids, encoding="utf-8"
            )
            result["identifiers_file"] = str(
                (settings.artifacts_dir / "discover_identifiers.txt").resolve()
            )

        result["tree_file"] = str(out_tree.resolve())
        result["ok"] = bool(tree.get("ok"))

    result["windows_file"] = str(out_windows.resolve())
    return result
