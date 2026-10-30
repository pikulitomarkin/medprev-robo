from __future__ import annotations

import time


def click_screen(x: int, y: int, *, clicks: int = 1, button: str = "left") -> None:
    import win32api
    import win32con

    flags_down = win32con.MOUSEEVENTF_LEFTDOWN
    flags_up = win32con.MOUSEEVENTF_LEFTUP
    if button == "right":
        flags_down = win32con.MOUSEEVENTF_RIGHTDOWN
        flags_up = win32con.MOUSEEVENTF_RIGHTUP

    win32api.SetCursorPos((int(x), int(y)))
    time.sleep(0.05)
    for _ in range(max(1, clicks)):
        win32api.mouse_event(flags_down, 0, 0, 0, 0)
        time.sleep(0.03)
        win32api.mouse_event(flags_up, 0, 0, 0, 0)
        time.sleep(0.05)


def type_text(text: str, *, interval: float = 0.02) -> None:
    """Digita via SendKeys (Unicode limitado — use para textos ASCII/simples)."""
    import win32com.client

    shell = win32com.client.Dispatch("WScript.Shell")
    # Escape especial SendKeys
    escaped = (
        text.replace("{", "{{")
        .replace("}", "}}")
        .replace("+", "{+}")
        .replace("^", "{^}")
        .replace("%", "{%}")
        .replace("~", "{~}")
        .replace("(", "{(}")
        .replace(")", "{)}")
    )
    for ch in escaped:
        shell.SendKeys(ch)
        time.sleep(interval)


def press_key(key: str) -> None:
    import win32com.client

    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys(key)
