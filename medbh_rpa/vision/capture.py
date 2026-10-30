from __future__ import annotations

import logging
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


def find_window(title_substr: str) -> WindowInfo | None:
    try:
        import win32gui
        import win32process
    except ImportError as exc:
        raise RuntimeError("pywin32 necessario") from exc

    title_l = title_substr.lower().strip()
    found: WindowInfo | None = None

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
            found = WindowInfo(
                hwnd=int(hwnd),
                pid=int(pid),
                title=title,
                class_name=class_name,
                rect=(int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])),
            )
            return False
        except Exception:
            return True

    win32gui.EnumWindows(_cb, [])
    return found


def focus_window(hwnd: int) -> None:
    import win32con
    import win32gui

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception as exc:
        # SetForegroundWindow falha sem foco as vezes — tenta Alt trick
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
            "message": f"Janela nao encontrada: {title_substr}",
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
