from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    class_name: str
    rect: tuple[int, int, int, int]  # left, top, right, bottom


def _info_from_hwnd(hwnd: int) -> WindowInfo | None:
    import win32gui
    import win32process

    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    try:
        title = (win32gui.GetWindowText(hwnd) or "").strip()
        class_name = win32gui.GetClassName(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        rect = win32gui.GetWindowRect(hwnd)
        return WindowInfo(
            hwnd=int(hwnd),
            pid=int(pid),
            title=title,
            class_name=class_name,
            rect=(int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])),
        )
    except Exception as exc:
        log.warning("hwnd %s ilegivel: %s", hwnd, exc)
        return None


def _match_title(title: str, title_substr: str) -> bool:
    t = (title or "").lower().strip()
    key = title_substr.lower().strip()
    if not t or not key:
        return False
    return key in t


def _find_via_enum_win32(title_substr: str) -> WindowInfo | None:
    import win32gui

    found: WindowInfo | None = None

    def _cb(hwnd: int, _acc: list) -> bool:
        nonlocal found
        if found is not None:
            return False
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = (win32gui.GetWindowText(hwnd) or "").strip()
            if not _match_title(title, title_substr):
                return True
            found = _info_from_hwnd(int(hwnd))
            return False
        except Exception:
            return True

    win32gui.EnumWindows(_cb, [])
    return found


def _find_via_enum_ctypes(title_substr: str) -> WindowInfo | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found: WindowInfo | None = None

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @WNDENUMPROC
    def _cb(hwnd: int, _lparam: int) -> bool:
        nonlocal found
        if found is not None:
            return False
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if not _match_title(buf.value, title_substr):
            return True
        found = _info_from_hwnd(int(hwnd))
        return False

    if not user32.EnumWindows(_cb, 0):
        err = ctypes.get_last_error()
        if err:
            log.warning("ctypes EnumWindows last_error=%s", err)
    return found


def _find_via_powershell(title_substr: str) -> WindowInfo | None:
    """Usa MainWindowHandle do processo — as vezes sobrevive quando EnumWindows falha."""
    key = title_substr.replace("'", "''")
    ps = (
        f"Get-Process | Where-Object {{ $_.MainWindowTitle -and "
        f"($_.MainWindowTitle -like '*{key}*') }} | "
        "Select-Object -First 1 Id, MainWindowHandle, MainWindowTitle | "
        "ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except Exception as exc:
        log.warning("powershell find: %s", exc)
        return None
    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    import json

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        data = data[0] if data else {}
    hwnd = int(data.get("MainWindowHandle") or 0)
    if hwnd <= 0:
        return None
    return _info_from_hwnd(hwnd)


def _find_via_foreground(title_substr: str) -> WindowInfo | None:
    import win32gui

    hwnd = int(win32gui.GetForegroundWindow() or 0)
    info = _info_from_hwnd(hwnd)
    if info and _match_title(info.title, title_substr):
        return info
    return None


def _find_via_env_hwnd() -> WindowInfo | None:
    raw = (os.environ.get("MSADMIN_HWND") or "").strip()
    if not raw:
        return None
    try:
        return _info_from_hwnd(int(raw, 0))
    except ValueError:
        return None


def find_window(title_substr: str) -> WindowInfo | None:
    """Localiza janela mxAdmin com varios fallbacks (AnyDesk / elevacao)."""
    try:
        import win32gui  # noqa: F401
        import win32process  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("pywin32 necessario") from exc

    env_hit = _find_via_env_hwnd()
    if env_hit is not None:
        return env_hit

    errors: list[str] = []

    for name, fn in (
        ("enum_win32", lambda: _find_via_enum_win32(title_substr)),
        ("enum_ctypes", lambda: _find_via_enum_ctypes(title_substr)),
        ("powershell", lambda: _find_via_powershell(title_substr)),
        ("foreground", lambda: _find_via_foreground(title_substr)),
    ):
        try:
            hit = fn()
            if hit is not None:
                log.info("janela achada via %s hwnd=%s title=%s", name, hit.hwnd, hit.title)
                return hit
        except Exception as exc:
            msg = f"{name}: {exc}"
            errors.append(msg)
            log.warning("find_window %s", msg)

    if errors:
        log.error(
            "find_window falhou (%s). Rode o CMD como Administrador "
            "(mesmo nivel do mxAdmin) e clique na janela mxAdmin antes.",
            "; ".join(errors),
        )
    return None


def focus_window(hwnd: int) -> None:
    import win32con
    import win32gui

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception as exc:
        log.warning("SetForegroundWindow: %s", exc)
        try:
            import win32com.client

            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys("%")
            win32gui.SetForegroundWindow(hwnd)
        except Exception as exc2:
            log.warning("focus fallback: %s", exc2)


def _capture_printwindow(hwnd: int, path: Path) -> bool:
    """PrintWindow — funciona melhor que pywinauto em WinForms/AnyDesk."""
    import ctypes

    import win32gui
    import win32ui
    from PIL import Image

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = max(1, right - left)
    height = max(1, bottom - top)

    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)

    # PW_RENDERFULLCONTENT = 2 (Win8+)
    result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
    if result != 1:
        result = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 0)

    bmpinfo = bitmap.GetInfo()
    bmpstr = bitmap.GetBitmapBits(True)
    img = Image.frombuffer(
        "RGB",
        (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
        bmpstr,
        "raw",
        "BGRX",
        0,
        1,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)

    win32gui.DeleteObject(bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)
    return path.exists() and path.stat().st_size > 0


def _capture_imagegrab(rect: tuple[int, int, int, int], path: Path) -> bool:
    from PIL import ImageGrab

    img = ImageGrab.grab(bbox=rect, all_screens=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path.exists() and path.stat().st_size > 0


def capture_window(
    title_substr: str,
    path: Path,
    *,
    bring_to_front: bool = True,
) -> dict[str, Any]:
    info = find_window(title_substr)
    if info is None:
        return {
            "ok": False,
            "message": (
                f"Janela nao encontrada: {title_substr}. "
                "Abra o CMD como Administrador (mxAdmin elevado exige o mesmo nivel), "
                "clique na janela mxAdmin e tente de novo."
            ),
            "path": None,
        }

    if bring_to_front:
        focus_window(info.hwnd)

    path = Path(path)
    errors: list[str] = []

    try:
        if _capture_printwindow(info.hwnd, path):
            return {
                "ok": True,
                "method": "printwindow",
                "path": str(path.resolve()),
                "window": {
                    "hwnd": info.hwnd,
                    "pid": info.pid,
                    "title": info.title,
                    "class_name": info.class_name,
                    "rect": list(info.rect),
                },
            }
        errors.append("printwindow retornou vazio")
    except Exception as exc:
        errors.append(f"printwindow: {exc}")

    try:
        if _capture_imagegrab(info.rect, path):
            return {
                "ok": True,
                "method": "imagegrab",
                "path": str(path.resolve()),
                "window": {
                    "hwnd": info.hwnd,
                    "pid": info.pid,
                    "title": info.title,
                    "class_name": info.class_name,
                    "rect": list(info.rect),
                },
            }
        errors.append("imagegrab retornou vazio")
    except Exception as exc:
        errors.append(f"imagegrab: {exc}")

    return {
        "ok": False,
        "message": "; ".join(errors) or "falha na captura",
        "path": None,
        "window": {
            "hwnd": info.hwnd,
            "pid": info.pid,
            "title": info.title,
            "class_name": info.class_name,
            "rect": list(info.rect),
        },
    }
