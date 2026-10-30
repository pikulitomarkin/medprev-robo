from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from medbh_rpa.vision.describe import ask_vision_json
from medbh_rpa.vision.input_win import press_key

log = logging.getLogger(__name__)

DEFAULT_MENUS = [
    "Cadastros",
    "Atendimento",
    "Caixa",
    "Financeiro",
    "Relatórios",
]


def locate_top_menus(image_path: Path, menus: list[str]) -> dict[str, Any]:
    """Pede a OpenAI as coordenadas pixel (relativas a imagem) de cada menu."""
    names = ", ".join(menus)
    prompt = (
        "Imagem do mxAdmin (WinForms). Na barra de menu superior horizontal "
        f"(abaixo do titulo), localize estes itens: {names}. "
        "Retorne SO JSON: "
        '{"menus":[{"name":"...","x":int,"y":int,"confidence":0.0}],'
        '"image_width":int,"image_height":int,'
        '"note":"..."} '
        "x,y = centro do texto do menu em pixels na imagem (origem canto superior esquerdo). "
        "Se um nome nao aparecer, omita. Sem markdown."
    )
    return ask_vision_json(image_path, prompt, max_tokens=800)


def describe_menu_panel(image_path: Path, menu_name: str) -> dict[str, Any]:
    """Descreve o dropdown / painel aberto apos clicar no menu."""
    prompt = (
        f"Tela do mxAdmin logo apos abrir o menu '{menu_name}'. "
        "Liste os itens do dropdown/submenu visiveis e o que cada um parece fazer. "
        "Retorne SO JSON: "
        '{"menu":"' + menu_name + '",'
        '"items":[{"label":"...","kind":"command|submenu|separator",'
        '"purpose":"...","approx_y":int}],'
        '"screen_summary":"uma frase do que essa area controla",'
        '"risk":"read_only|may_open_form|may_change_data"} '
        "Sem markdown."
    )
    return ask_vision_json(image_path, prompt, max_tokens=1200)


def explore_top_menus(
    controller: Any,
    *,
    menus: list[str] | None = None,
    pause: float = 0.9,
) -> dict[str, Any]:
    """
    Assume o mouse: snapshot home -> localiza menus -> clica cada um ->
    snapshot dropdown -> IA descreve -> ESC -> grava mapa.
    Nao entra em formularios (so abre/fecha menus).
    """
    target = menus or list(DEFAULT_MENUS)
    maps_dir = controller.maps_dir
    artifacts = controller.settings.artifacts_dir
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = artifacts / f"explore_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    focus = controller.focus()
    if not focus.get("ok"):
        return focus

    home = controller.snapshot("explore_home")
    if not home.get("ok"):
        return home

    home_path = Path(home["path"])
    # copia para pasta da exploracao
    dest_home = out_dir / "00_home.png"
    dest_home.write_bytes(home_path.read_bytes())

    loc = locate_top_menus(home_path, target)
    if not loc.get("ok"):
        return {"ok": False, "stage": "locate", "locate": loc, "home": home}

    found = {
        str(m.get("name", "")).strip().lower(): m
        for m in (loc.get("data") or {}).get("menus") or []
        if isinstance(m, dict) and m.get("x") is not None and m.get("y") is not None
    }

    report: dict[str, Any] = {
        "ok": True,
        "mode": "menu_dropdown_only",
        "home": str(dest_home),
        "locate": loc.get("data"),
        "menus": [],
        "missing": [],
        "out_dir": str(out_dir.resolve()),
    }

    for name in target:
        key = name.lower()
        # aceita Relatorios / Relatórios
        match = found.get(key)
        if match is None:
            for fk, fm in found.items():
                if fk.replace("ó", "o").replace("á", "a") == key.replace("ó", "o").replace(
                    "á", "a"
                ):
                    match = fm
                    break
        if match is None:
            report["missing"].append(name)
            report["menus"].append({"name": name, "ok": False, "message": "nao localizado"})
            continue

        x, y = int(match["x"]), int(match["y"])
        log.info("explore click menu=%s at %s,%s", name, x, y)
        click = controller.click_xy(x, y, absolute=False)
        time.sleep(pause)

        snap = controller.snapshot(f"menu_{name}")
        snap_path = None
        if snap.get("ok") and snap.get("path"):
            snap_path = out_dir / f"menu_{name}.png"
            snap_path.write_bytes(Path(snap["path"]).read_bytes())

        desc: dict[str, Any] = {"ok": False}
        if snap_path and snap_path.exists():
            desc = describe_menu_panel(snap_path, name)

        # fecha dropdown
        press_key("{ESC}")
        time.sleep(0.35)

        entry = {
            "name": name,
            "ok": bool(click.get("ok")) and bool(snap.get("ok")),
            "click": click,
            "coords": {"x": x, "y": y, "confidence": match.get("confidence")},
            "screenshot": str(snap_path) if snap_path else None,
            "describe": desc.get("data") if desc.get("ok") else None,
            "describe_error": None if desc.get("ok") else desc.get("message"),
        }
        report["menus"].append(entry)

    map_path = maps_dir / "top_menus.json"
    map_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["map_file"] = str(map_path.resolve())

    # indice curto
    index = {
        "generated_at": stamp,
        "menus": [
            {
                "name": m["name"],
                "ok": m.get("ok"),
                "coords": m.get("coords"),
                "items": (m.get("describe") or {}).get("items"),
                "screen_summary": (m.get("describe") or {}).get("screen_summary"),
            }
            for m in report["menus"]
        ],
        "missing": report["missing"],
        "artifacts": report["out_dir"],
    }
    index_path = maps_dir / "top_menus_index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    report["index_file"] = str(index_path.resolve())
    return report
