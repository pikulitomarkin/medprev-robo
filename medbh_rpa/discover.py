from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

from medbh_rpa.config import get_settings

log = logging.getLogger(__name__)


def _progress(msg: str) -> None:
    """Progresso no stderr — nao mistura com o JSON final."""
    print(f"[discover] {msg}", file=sys.stderr, flush=True)


def _find_mxadmin(title_substr: str) -> dict[str, Any] | None:
    """Busca rapida so via EnumWindows (nao enumera Desktop UIA inteiro)."""
    try:
        import win32gui
        import win32process
    except ImportError:
        _progress("pywin32 ausente")
        return None

    title_l = title_substr.lower().strip()
    found: dict[str, Any] | None = None

    def _cb(hwnd: int, _acc: list) -> bool:
        nonlocal found
        if found is not None:
            return False
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = (win32gui.GetWindowText(hwnd) or "").strip()
            if not title or title_l not in title.lower():
                return True
            class_name = win32gui.GetClassName(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            found = {
                "hwnd": int(hwnd),
                "pid": int(pid),
                "title": title,
                "class_name": class_name,
                "rect": list(rect),
            }
            return False
        except Exception:
            return True

    win32gui.EnumWindows(_cb, [])
    return found


def _list_same_pid(pid: int, *, limit: int = 40) -> list[dict[str, Any]]:
    try:
        import win32gui
        import win32process
    except ImportError:
        return []

    out: list[dict[str, Any]] = []

    def _cb(hwnd: int, _acc: list) -> bool:
        if len(out) >= limit:
            return False
        try:
            _, wpid = win32process.GetWindowThreadProcessId(hwnd)
            if int(wpid) != int(pid):
                return True
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = (win32gui.GetWindowText(hwnd) or "").strip()
            class_name = win32gui.GetClassName(hwnd) or ""
            if not title and "WindowsForms" not in class_name:
                return True
            out.append(
                {
                    "hwnd": int(hwnd),
                    "title": title,
                    "class_name": class_name,
                }
            )
        except Exception:
            pass
        return True

    win32gui.EnumWindows(_cb, [])
    return out


def _screenshot_hwnd(hwnd: int, path: Any) -> bool:
    try:
        from pywinauto import Application

        # win32 connect e mais leve; timeout curto
        app = Application(backend="win32").connect(handle=hwnd, timeout=3)
        win = app.window(handle=hwnd)
        img = win.capture_as_image()
        img.save(str(path))
        return True
    except Exception as exc:
        _progress(f"screenshot falhou: {exc}")
        return False


def run_discover(*, dump: bool = True, fast: bool = True) -> dict[str, Any]:
    """
    fast=True (padrao): so acha a janela mxAdmin, lista forms do PID e tira screenshot.
    Nao chama print_control_identifiers (isso travava a sessao).
    """
    settings = get_settings()
    settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    title_key = settings.msadmin_window_title or "mxAdmin"
    _progress(f"procurando janela com titulo contendo '{title_key}'...")
    hit = _find_mxadmin(title_key)

    if hit is None:
        result = {
            "ok": False,
            "elapsed_sec": round(time.time() - t0, 2),
            "message": (
                f"Janela '{title_key}' nao encontrada. "
                "Abra o mxAdmin, deixe na frente e rode de novo."
            ),
            "msadmin_window_title_env": settings.msadmin_window_title,
            "msadmin_exe_env": settings.msadmin_exe,
        }
        out = settings.artifacts_dir / "discover_fast.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["result_file"] = str(out.resolve())
        return result

    _progress(f"achou hwnd={hit['hwnd']} pid={hit['pid']} title={hit['title']!r}")

    forms: list[dict[str, Any]] = []
    if dump:
        _progress("listando janelas do mesmo processo (limite 40)...")
        forms = _list_same_pid(int(hit["pid"]), limit=40)

    shot_path = settings.artifacts_dir / "mxadmin_window.png"
    shot_ok = False
    if dump:
        _progress("capturando screenshot da janela...")
        shot_ok = _screenshot_hwnd(int(hit["hwnd"]), shot_path)

    result: dict[str, Any] = {
        "ok": True,
        "mode": "fast" if fast else "full",
        "elapsed_sec": round(time.time() - t0, 2),
        "msadmin_window_title_env": settings.msadmin_window_title,
        "msadmin_exe_env": settings.msadmin_exe,
        "window": hit,
        "process_forms_count": len(forms),
        "process_forms": forms,
        "screenshot": str(shot_path.resolve()) if shot_ok else None,
        "automation_strategy": "image_ocr_or_coords",
        "note": (
            "Discover rapido: nao dumpa arvore UIA (travava). "
            "mxAdmin e WinForms 32-bit com pouca acessibilidade. "
            "Proximo passo: RPA por screenshot + coordenadas/OCR."
        ),
        "next_steps": [
            "Confirme que artifacts\\mxadmin_window.png mostra a tela do sistema",
            "No AnyDesk, deixe o mxAdmin na tela de Agenda",
            "Avise o Marcos para gravar o fluxo por imagem/coords",
        ],
    }

    out = settings.artifacts_dir / "discover_fast.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["result_file"] = str(out.resolve())
    _progress(f"ok em {result['elapsed_sec']}s -> {out}")
    return result
