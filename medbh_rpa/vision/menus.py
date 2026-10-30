from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

from medbh_rpa.vision.describe import ask_vision_json
from medbh_rpa.vision.input_win import click_with_glide, press_key
from medbh_rpa.vision.capture import find_window, focus_window

log = logging.getLogger(__name__)

# Fallback se top_menus.json ainda nao tiver coords
FALLBACK_MENU_COORDS: dict[str, tuple[int, int]] = {
    "sistema": (50, 18),
    "cadastros": (141, 18),
    "atendimento": (219, 18),
    "caixa": (275, 18),
    "ferramentas mx": (350, 18),
    "financeiro": (426, 18),
    "relatorios": (483, 18),
    "relatórios": (483, 18),
    "ajuda": (560, 18),
}

# Ordem real do dropdown Atendimento (print 30/10/2026).
# y = menu_y + first_offset + index * row_h  (relativo a janela)
ATENDIMENTO_ITEMS: list[str] = [
    "Agendar Atendimento",
    "Cancelar Atendimento",
    "Transferir Propriedade",
    "Transferência Programada",
    "Meus Atendimentos",
    "Meus Atendimentos Transferidos",
    "Histórico de alterações",
    "Análise de Atendimentos",
    "Rastreamento de Atendimento",
    "Observações de Atendimentos",
    "Retirar do pagamento web",
    "Pré-Cancelamento",
    "Validar e-Guia",
    "Guias Manuais",
    "PIX - Envio de atendimentos",
]

MENU_ITEM_LAYOUT: dict[str, dict[str, Any]] = {
    "atendimento": {
        "item_x": 300,
        "first_offset": 28,
        "row_h": 22,
        "items": ATENDIMENTO_ITEMS,
    },
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _load_menu_coords(maps_dir: Path) -> dict[str, tuple[int, int, float | None]]:
    out: dict[str, tuple[int, int, float | None]] = {
        k: (v[0], v[1], None) for k, v in FALLBACK_MENU_COORDS.items()
    }
    path = maps_dir / "top_menus_index.json"
    if not path.exists():
        path = maps_dir / "top_menus.json"
    if not path.exists():
        return out
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("falha lendo %s: %s", path, exc)
        return out

    menus = data.get("menus") or []
    for m in menus:
        if not isinstance(m, dict):
            continue
        name = _norm(str(m.get("name") or ""))
        coords = m.get("coords") or {}
        if not name or coords.get("x") is None or coords.get("y") is None:
            continue
        conf = coords.get("confidence")
        out[name] = (int(coords["x"]), int(coords["y"]), float(conf) if conf is not None else None)
        # alias sem acento
        out[_norm(name)] = out[name]
    return out


def locate_dropdown_item(image_path: Path, item_label: str) -> dict[str, Any]:
    """Pede a Vision o centro (x,y) do item no dropdown aberto."""
    prompt = (
        "Imagem do mxAdmin com um menu dropdown aberto. "
        f"Localize o item de menu cujo texto e (ou mais perto de): '{item_label}'. "
        "Retorne SO JSON: "
        '{"found":true,"x":int,"y":int,"matched_label":"...","confidence":0.0,'
        '"all_visible":["label1","label2"]} '
        "x,y = centro do texto do item em pixels na imagem. "
        "Se nao achar, found=false e liste all_visible. Sem markdown."
    )
    return ask_vision_json(image_path, prompt, max_tokens=700)


def _resolve_item_coords(
    menu_key: str, item: str, mx: int, my: int
) -> tuple[int, int, str] | None:
    layout = MENU_ITEM_LAYOUT.get(menu_key)
    if not layout:
        return None
    want = _norm(item)
    items: list[str] = list(layout["items"])
    idx = next((i for i, label in enumerate(items) if want in _norm(label) or _norm(label) in want), None)
    if idx is None:
        return None
    ix = int(layout["item_x"])
    iy = int(my + layout["first_offset"] + idx * layout["row_h"])
    return ix, iy, items[idx]


def open_menu_item(
    controller: Any,
    menu: str,
    item: str,
    *,
    pause: float = 0.7,
    glide_ms: int = 1200,
    allow_write: bool = False,
    item_x: int | None = None,
    item_y: int | None = None,
    drag: bool = True,
) -> dict[str, Any]:
    """
    Abre menu do topo arrastando o mouse (drag) ate o item.
    WinForms fecha dropdown se soltar cedo ou teleportar o cursor.
    """
    _ = allow_write
    coords_map = _load_menu_coords(controller.maps_dir)
    key = _norm(menu)
    if key not in coords_map:
        hit = next((k for k in coords_map if key in k or k in key), None)
        if hit is None:
            return {
                "ok": False,
                "message": f"menu desconhecido: {menu}",
                "known": sorted(set(coords_map)),
            }
        key = hit

    mx, my, conf = coords_map[key]
    matched = item
    if item_x is not None and item_y is not None:
        ix, iy = int(item_x), int(item_y)
    else:
        resolved = _resolve_item_coords(key, item, mx, my)
        if resolved is None:
            return {
                "ok": False,
                "message": (
                    f"item '{item}' sem layout conhecido para menu '{menu}'. "
                    "Passe item_x/item_y ou cadastre em MENU_ITEM_LAYOUT."
                ),
                "hint": "Nao usamos Vision entre cliques — snapshot fecha o dropdown.",
            }
        ix, iy, matched = resolved

    info = find_window(controller.title_key)
    if info is None:
        return {"ok": False, "message": "janela nao encontrada"}
    focus_window(info.hwnd)
    time.sleep(0.15)

    press_key("{ESC}")
    time.sleep(0.3)

    sx_m = info.rect[0] + mx
    sy_m = info.rect[1] + my
    sx_i = info.rect[0] + ix
    sy_i = info.rect[1] + iy

    log.info(
        "glide menu=%s item=%s (%s,%s)->(%s,%s) ms=%s",
        menu,
        matched,
        sx_m,
        sy_m,
        sx_i,
        sy_i,
        glide_ms,
    )
    click_with_glide(sx_m, sy_m, sx_i, sy_i, glide_ms=int(glide_ms), drag=bool(drag))
    time.sleep(max(0.4, pause))

    after = controller.snapshot("after_menu_item")
    return {
        "ok": bool(after.get("ok")),
        "menu": menu,
        "item": item,
        "matched_label": matched,
        "mode": "drag" if drag else "glide",
        "glide_ms": glide_ms,
        "menu_coords": {"x": mx, "y": my, "confidence": conf},
        "item_coords": {"x": ix, "y": iy},
        "screen_menu": {"x": sx_m, "y": sy_m},
        "screen_item": {"x": sx_i, "y": sy_i},
        "snapshot": after.get("path"),
        "last": after.get("last"),
    }


def map_screen(
    controller: Any,
    name: str,
    *,
    close_after: bool = False,
) -> dict[str, Any]:
    """Snapshot + scan Vision + grava JSON em data/maps/screens/."""
    from medbh_rpa.vision.describe import describe_screen

    safe = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE).strip("_") or "screen"
    snap = controller.snapshot(f"map_{safe}")
    if not snap.get("ok"):
        return snap

    desc = describe_screen(Path(snap["path"]))
    screens_dir = controller.maps_dir / "screens"
    screens_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = screens_dir / f"{safe}_{stamp}.json"
    payload = {
        "name": name,
        "snapshot": snap,
        "describe": desc,
        "ts": stamp,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if close_after:
        press_key("{ESC}")
        time.sleep(0.3)

    return {
        "ok": bool(desc.get("ok")),
        "name": name,
        "map_file": str(out_path.resolve()),
        "snapshot": snap.get("path"),
        "elements": desc.get("elements"),
        "message": desc.get("message"),
    }


def list_maps(maps_dir: Path) -> dict[str, Any]:
    screens = sorted((maps_dir / "screens").glob("*.json")) if (maps_dir / "screens").exists() else []
    tops = []
    for name in ("top_menus_index.json", "top_menus.json"):
        p = maps_dir / name
        if p.exists():
            tops.append(str(p.resolve()))
    return {
        "ok": True,
        "top_menus": tops,
        "screens": [str(p.resolve()) for p in screens[-50:]],
        "templates": [
            str(p.resolve())
            for p in sorted((maps_dir / "templates").glob("*.png"))
            if (maps_dir / "templates").exists()
        ],
    }
