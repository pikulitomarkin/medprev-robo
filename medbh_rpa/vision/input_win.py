from __future__ import annotations

import time


def move_screen(x: int, y: int) -> None:
    import win32api

    win32api.SetCursorPos((int(x), int(y)))


def glide_screen(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    *,
    duration_ms: int = 900,
    steps: int | None = None,
) -> None:
    """Move o cursor em passos pequenos (dropdown WinForms sensivel)."""
    import win32api

    duration_ms = max(100, int(duration_ms))
    if steps is None:
        dist = max(abs(x2 - x1), abs(y2 - y1), 1)
        steps = max(12, min(60, dist // 3))
    steps = max(2, int(steps))
    win32api.SetCursorPos((int(x1), int(y1)))
    time.sleep(0.05)
    for i in range(1, steps + 1):
        t = i / steps
        # ease-out suave
        t = 1 - (1 - t) * (1 - t)
        x = int(x1 + (x2 - x1) * t)
        y = int(y1 + (y2 - y1) * t)
        win32api.SetCursorPos((x, y))
        time.sleep(duration_ms / 1000.0 / steps)


def click_screen(x: int, y: int, *, clicks: int = 1, button: str = "left") -> None:
    import win32api
    import win32con

    flags_down = win32con.MOUSEEVENTF_LEFTDOWN
    flags_up = win32con.MOUSEEVENTF_LEFTUP
    if button == "right":
        flags_down = win32con.MOUSEEVENTF_RIGHTDOWN
        flags_up = win32con.MOUSEEVENTF_RIGHTUP

    win32api.SetCursorPos((int(x), int(y)))
    time.sleep(0.08)
    for _ in range(max(1, clicks)):
        win32api.mouse_event(flags_down, 0, 0, 0, 0)
        time.sleep(0.04)
        win32api.mouse_event(flags_up, 0, 0, 0, 0)
        time.sleep(0.06)


def click_with_glide(
    x_menu: int,
    y_menu: int,
    x_item: int,
    y_item: int,
    *,
    glide_ms: int = 1100,
    hold_before_click_ms: int = 200,
    drag: bool = True,
) -> None:
    """
    Abre menu WinForms sensivel.
    drag=True (padrao): mouse DOWN no menu, desliza ate o item, UP (arrasta).
    drag=False: clique no menu, desliza, clique no item.
    """
    import win32api
    import win32con

    if drag:
        win32api.SetCursorPos((int(x_menu), int(y_menu)))
        time.sleep(0.12)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.2)
        # desce um pouco ainda pressionado (entra no dropdown)
        mid_y = y_menu + max(12, (y_item - y_menu) // 3)
        glide_screen(x_menu, y_menu, x_menu, mid_y, duration_ms=max(250, glide_ms // 3))
        glide_screen(x_menu, mid_y, x_item, y_item, duration_ms=glide_ms)
        time.sleep(hold_before_click_ms / 1000.0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.15)
        return

    click_screen(x_menu, y_menu)
    time.sleep(0.35)
    mid_y = y_menu + max(8, (y_item - y_menu) // 4)
    glide_screen(x_menu, y_menu, x_menu, mid_y, duration_ms=max(200, glide_ms // 3))
    glide_screen(x_menu, mid_y, x_item, y_item, duration_ms=glide_ms)
    time.sleep(hold_before_click_ms / 1000.0)
    click_screen(x_item, y_item)


def type_text(text: str, *, interval: float = 0.02) -> None:
    """Digita via SendKeys (Unicode limitado — use para textos ASCII/simples)."""
    import win32com.client

    shell = win32com.client.Dispatch("WScript.Shell")
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
