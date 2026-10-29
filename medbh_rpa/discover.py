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
        import win32process
    except ImportError:
        return []

    out: list[dict[str, Any]] = []

    def _cb(hwnd: int, _acc: list[dict[str, Any]]) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = (win32gui.GetWindowText(hwnd) or "").strip()
        try:
            class_name = win32gui.GetClassName(hwnd) or ""
        except Exception:
            class_name = ""
        pid = None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            pass
        if not title and not class_name:
            return True
        out.append(
            {
                "backend": "win32_enum",
                "title": title,
                "class_name": class_name,
                "handle": int(hwnd),
                "pid": pid,
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


def _find_hwnd(title_substr: str) -> tuple[int | None, str | None, str | None, int | None]:
    title_l = title_substr.lower().strip()
    for w in list_windows():
        title = w.get("title") or ""
        if title_l and title_l in title.lower() and w.get("handle"):
            return int(w["handle"]), title, w.get("class_name"), w.get("pid")
    return None, None, None, None


def _pid_of_hwnd(hwnd: int) -> int | None:
    try:
        import win32process

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return int(pid)
    except Exception:
        return None


def _enum_child_hwnds(parent: int) -> list[dict[str, Any]]:
    try:
        import win32gui
    except ImportError:
        return []

    kids: list[dict[str, Any]] = []

    def _cb(hwnd: int, _acc: list) -> bool:
        try:
            title = win32gui.GetWindowText(hwnd) or ""
            class_name = win32gui.GetClassName(hwnd) or ""
            visible = bool(win32gui.IsWindowVisible(hwnd))
            rect = win32gui.GetWindowRect(hwnd)
            kids.append(
                {
                    "handle": int(hwnd),
                    "title": title,
                    "class_name": class_name,
                    "visible": visible,
                    "rect": list(rect),
                }
            )
        except Exception:
            pass
        return True

    try:
        win32gui.EnumChildWindows(parent, _cb, [])
    except Exception as exc:
        log.warning("EnumChildWindows(%s): %s", parent, exc)
    return kids


def _windows_of_pid(pid: int) -> list[dict[str, Any]]:
    try:
        import win32gui
        import win32process
    except ImportError:
        return []

    found: list[dict[str, Any]] = []

    def _cb(hwnd: int, _acc: list) -> bool:
        try:
            _, wpid = win32process.GetWindowThreadProcessId(hwnd)
            if int(wpid) != int(pid):
                return True
            title = win32gui.GetWindowText(hwnd) or ""
            class_name = win32gui.GetClassName(hwnd) or ""
            visible = bool(win32gui.IsWindowVisible(hwnd))
            if not visible and not title:
                return True
            found.append(
                {
                    "handle": int(hwnd),
                    "title": title,
                    "class_name": class_name,
                    "visible": visible,
                }
            )
        except Exception:
            pass
        return True

    win32gui.EnumWindows(_cb, [])
    return found


def _connect_window(hwnd: int, backend: str) -> Any | None:
    from pywinauto import Application

    try:
        app = Application(backend=backend).connect(handle=hwnd)
        return app.window(handle=hwnd)
    except Exception as exc:
        log.warning("connect handle=%s backend=%s: %s", hwnd, backend, exc)
        return None


def _identifiers_text(target: Any, depth: int = 6) -> str:
    try:
        from io import StringIO
        import sys

        buf = StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            target.print_control_identifiers(depth=depth)
        finally:
            sys.stdout = old
        return buf.getvalue()
    except Exception as exc:
        return f"(identifiers indisponivel: {exc})"


def _walk_controls(root: Any, *, max_depth: int = 8, limit: int = 1500) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []

    def add_elem(elem: Any, depth: int) -> None:
        if len(controls) >= limit:
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
        except Exception:
            return

    # Preferir descendants (WinForms)
    try:
        add_elem(root, 0)
        for d in list(root.descendants())[:limit]:
            add_elem(d, 1)
            if len(controls) >= limit:
                break
        if len(controls) > 1:
            return controls
    except Exception:
        pass

    def walk(elem: Any, depth: int) -> None:
        if depth > max_depth or len(controls) >= limit:
            return
        add_elem(elem, depth)
        try:
            for child in elem.children():
                walk(child, depth + 1)
        except Exception:
            return

    walk(root, 0)
    return controls


def dump_tree(title_substr: str, *, max_depth: int = 8) -> dict[str, Any]:
    hwnd, found_title, class_name, pid = _find_hwnd(title_substr)
    all_titles = [w["title"] for w in list_windows() if w.get("title")]

    if hwnd is None:
        hints = [
            t
            for t in all_titles
            if any(x in t.lower() for x in ("admin", "max", "mx", "viv", "run"))
        ]
        return {
            "ok": False,
            "message": f"Nenhuma janela contem '{title_substr}'.",
            "hints": hints[:20],
            "windows": all_titles[:40],
        }

    if pid is None:
        pid = _pid_of_hwnd(hwnd)

    children = _enum_child_hwnds(hwnd)
    siblings = _windows_of_pid(pid) if pid else []

    # Dump UIA da janela principal
    used_backend = None
    controls: list[dict[str, Any]] = []
    identifiers = ""
    for backend in ("uia", "win32"):
        target = _connect_window(hwnd, backend)
        if target is None:
            continue
        used_backend = backend
        controls = _walk_controls(target, max_depth=max_depth)
        identifiers = _identifiers_text(target, depth=max_depth)
        if len(controls) > 2 or (identifiers and "Button" in identifiers):
            break

    # Dump de cada janela WinForms do mesmo PID (MDI / forms internas)
    form_dumps: list[dict[str, Any]] = []
    interesting = [
        w
        for w in siblings
        if w.get("visible")
        and "WindowsForms10" in (w.get("class_name") or "")
        and int(w["handle"]) != int(hwnd)
    ]
    # Limita para nao explodir
    for w in interesting[:25]:
        form: dict[str, Any] = {
            "handle": w["handle"],
            "title": w.get("title"),
            "class_name": w.get("class_name"),
        }
        t = _connect_window(int(w["handle"]), "uia")
        if t is None:
            t = _connect_window(int(w["handle"]), "win32")
        if t is not None:
            ctrls = _walk_controls(t, max_depth=5, limit=200)
            ids = _identifiers_text(t, depth=4)
            form["controls_count"] = len(ctrls)
            form["controls_sample"] = [
                c for c in ctrls if c.get("name") or c.get("automation_id")
            ][:40]
            form["identifiers_preview"] = ids[:4000]
            # nomes uteis
            form["named"] = sorted(
                {
                    c["name"]
                    for c in ctrls
                    if c.get("name") and len(c["name"]) < 80
                }
            )[:80]
        form_dumps.append(form)

    named_main = sorted(
        {c["name"] for c in controls if c.get("name") and len(c["name"]) < 80}
    )[:80]
    named_forms = sorted(
        {n for f in form_dumps for n in (f.get("named") or [])}
    )[:120]

    strategy = "uia"
    if len(controls) <= 3 and not named_forms:
        strategy = "image_ocr_or_coords"
    elif named_forms or len(controls) > 3:
        strategy = "uia_on_child_forms"

    ok = True  # janela encontrada; mesmo com poucos controles
    return {
        "ok": ok,
        "backend_used": used_backend,
        "hwnd": hwnd,
        "pid": pid,
        "window_title": found_title,
        "class_name": class_name,
        "controls_count": len(controls),
        "controls": controls[:500],
        "named_controls_main": named_main,
        "child_hwnd_count": len(children),
        "child_hwnds_sample": children[:40],
        "process_forms_count": len(interesting),
        "process_forms": form_dumps,
        "named_controls_forms": named_forms,
        "identifiers_preview": (identifiers or "")[:8000],
        "automation_strategy": strategy,
        "note": (
            "mxAdmin e WinForms. A janela principal expoe pouco na UIA (so TitleBar). "
            "Controles uteis costumam estar em forms filhas do mesmo PID (RunAdmin.exe). "
            "Se named_controls_forms estiver vazio, o app desenha a UI sem acessibilidade "
            "e o RPA precisa de imagem/OCR ou coordenadas."
        ),
    }


def run_discover(*, dump: bool = True) -> dict[str, Any]:
    settings = get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)

    windows = list_windows()
    # Resumo enxuto no stdout; completo no arquivo
    slim_windows = [
        w
        for w in windows
        if w.get("title")
        and any(
            x in (w.get("title") or "").lower()
            for x in ("mxadmin", "admin", "loader", "run", "anydesk", "git")
        )
    ]

    result: dict[str, Any] = {
        "ok": True,
        "msadmin_window_title_env": settings.msadmin_window_title,
        "msadmin_exe_env": settings.msadmin_exe,
        "windows_count": len(windows),
        "windows_interesting": slim_windows,
    }

    out_windows = settings.artifacts_dir / "discover_windows.json"
    out_windows.write_text(
        json.dumps({"windows": windows, **result}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if dump and settings.msadmin_window_title:
        tree = dump_tree(settings.msadmin_window_title)
        result["tree"] = {
            "ok": tree.get("ok"),
            "backend_used": tree.get("backend_used"),
            "hwnd": tree.get("hwnd"),
            "pid": tree.get("pid"),
            "window_title": tree.get("window_title"),
            "class_name": tree.get("class_name"),
            "controls_count": tree.get("controls_count"),
            "named_controls_main": tree.get("named_controls_main"),
            "process_forms_count": tree.get("process_forms_count"),
            "named_controls_forms": tree.get("named_controls_forms"),
            "automation_strategy": tree.get("automation_strategy"),
            "note": tree.get("note"),
            "message": tree.get("message"),
            "hints": tree.get("hints"),
        }
        out_tree = settings.artifacts_dir / "discover_tree.json"
        out_tree.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")

        ids = tree.get("identifiers_preview") or ""
        if ids:
            (settings.artifacts_dir / "discover_identifiers.txt").write_text(
                ids, encoding="utf-8"
            )
            result["identifiers_file"] = str(
                (settings.artifacts_dir / "discover_identifiers.txt").resolve()
            )

        # Resumo dos forms para leitura humana
        forms_summary = []
        for f in tree.get("process_forms") or []:
            forms_summary.append(
                {
                    "title": f.get("title"),
                    "handle": f.get("handle"),
                    "controls_count": f.get("controls_count"),
                    "named": f.get("named"),
                }
            )
        (settings.artifacts_dir / "discover_forms.json").write_text(
            json.dumps(forms_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result["forms_file"] = str(
            (settings.artifacts_dir / "discover_forms.json").resolve()
        )

        result["tree_file"] = str(out_tree.resolve())
        result["ok"] = bool(tree.get("ok"))

    result["windows_file"] = str(out_windows.resolve())
    return result
