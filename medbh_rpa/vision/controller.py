from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from medbh_rpa.config import Settings, get_settings
from medbh_rpa.vision.capture import capture_window, find_window, focus_window
from medbh_rpa.vision.input_win import click_screen, press_key, type_text
from medbh_rpa.vision.match import match_template, to_dict

log = logging.getLogger(__name__)


class VisionController:
    """Controla o mxAdmin por screenshot + OpenCV + cliques."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.maps_dir = self.settings.data_dir / "maps"
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir = self.maps_dir / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    @property
    def title_key(self) -> str:
        return self.settings.msadmin_window_title or "mxAdmin"

    def snapshot(self, name: str = "screen") -> dict[str, Any]:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = self.settings.artifacts_dir / f"{name}_{stamp}.png"
        result = capture_window(self.title_key, path, bring_to_front=True)
        # tambem salva "last.png" para matching
        if result.get("ok") and result.get("path"):
            from shutil import copyfile

            last = self.settings.artifacts_dir / "last.png"
            copyfile(result["path"], last)
            result["last"] = str(last.resolve())
        return result

    def focus(self) -> dict[str, Any]:
        info = find_window(self.title_key)
        if info is None:
            return {"ok": False, "message": "janela nao encontrada"}
        focus_window(info.hwnd)
        return {"ok": True, "hwnd": info.hwnd, "title": info.title}

    def click_xy(self, x: int, y: int, *, absolute: bool = True) -> dict[str, Any]:
        """Clique. Se absolute=False, x/y sao relativos a janela mxAdmin."""
        info = find_window(self.title_key)
        if info is None:
            return {"ok": False, "message": "janela nao encontrada"}
        focus_window(info.hwnd)
        time.sleep(0.2)
        if absolute:
            sx, sy = int(x), int(y)
        else:
            sx = info.rect[0] + int(x)
            sy = info.rect[1] + int(y)
        click_screen(sx, sy)
        return {"ok": True, "screen_x": sx, "screen_y": sy}

    def click_template(
        self,
        template_name: str,
        *,
        threshold: float = 0.82,
    ) -> dict[str, Any]:
        tpl = self.templates_dir / f"{template_name}.png"
        if not tpl.exists():
            return {"ok": False, "message": f"template ausente: {tpl}"}

        snap = self.snapshot("match")
        if not snap.get("ok"):
            return snap

        # matching na imagem da janela; coords sao relativas ao bitmap
        # PrintWindow = origem (0,0) no canto da janela
        info = find_window(self.title_key)
        if info is None:
            return {"ok": False, "message": "janela sumiu"}

        m = match_template(Path(snap["path"]), tpl, threshold=threshold)
        out = to_dict(m)
        if not m.found:
            out["ok"] = False
            out["message"] = "template nao encontrado na tela"
            return out

        sx = info.rect[0] + m.x
        sy = info.rect[1] + m.y
        focus_window(info.hwnd)
        time.sleep(0.15)
        click_screen(sx, sy)
        out["ok"] = True
        out["screen_x"] = sx
        out["screen_y"] = sy
        out["template"] = template_name
        return out

    def type_into(self, text: str) -> dict[str, Any]:
        self.focus()
        time.sleep(0.1)
        type_text(text)
        return {"ok": True, "typed": text}

    def save_template_crop(
        self,
        name: str,
        left: int,
        top: int,
        right: int,
        bottom: int,
        *,
        from_last: bool = True,
    ) -> dict[str, Any]:
        """Recorta regiao da ultima screenshot e salva como template."""
        from PIL import Image

        src = self.settings.artifacts_dir / "last.png"
        if not from_last or not src.exists():
            snap = self.snapshot("crop_src")
            if not snap.get("ok"):
                return snap
            src = Path(snap["path"])

        img = Image.open(src)
        crop = img.crop((left, top, right, bottom))
        dest = self.templates_dir / f"{name}.png"
        crop.save(dest)
        return {
            "ok": True,
            "template": name,
            "path": str(dest.resolve()),
            "size": crop.size,
        }

    def record_step(self, flow: str, step: dict[str, Any]) -> dict[str, Any]:
        flow_path = self.maps_dir / f"{flow}.json"
        data: dict[str, Any]
        if flow_path.exists():
            data = json.loads(flow_path.read_text(encoding="utf-8"))
        else:
            data = {"flow": flow, "steps": []}
        data["steps"].append({**step, "ts": time.time()})
        flow_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "flow": flow, "steps": len(data["steps"]), "path": str(flow_path)}

    def run_flow_file(self, flow: str) -> dict[str, Any]:
        flow_path = self.maps_dir / f"{flow}.json"
        if not flow_path.exists():
            return {"ok": False, "message": f"fluxo nao mapeado: {flow_path}"}
        data = json.loads(flow_path.read_text(encoding="utf-8"))
        results = []
        for i, step in enumerate(data.get("steps", [])):
            kind = step.get("type")
            log.info("flow=%s step=%s type=%s", flow, i, kind)
            if kind == "snapshot":
                results.append(self.snapshot(step.get("name", f"step{i}")))
            elif kind == "click_xy":
                results.append(
                    self.click_xy(
                        step["x"],
                        step["y"],
                        absolute=bool(step.get("absolute", False)),
                    )
                )
            elif kind == "click_template":
                results.append(
                    self.click_template(
                        step["template"],
                        threshold=float(step.get("threshold", 0.82)),
                    )
                )
            elif kind == "type":
                results.append(self.type_into(step.get("text", "")))
            elif kind == "key":
                press_key(step.get("key", "{ENTER}"))
                results.append({"ok": True, "key": step.get("key")})
            elif kind == "wait":
                time.sleep(float(step.get("seconds", 1)))
                results.append({"ok": True, "wait": step.get("seconds", 1)})
            else:
                results.append({"ok": False, "message": f"tipo desconhecido: {kind}"})
            if results and results[-1].get("ok") is False:
                return {"ok": False, "failed_step": i, "results": results}
            time.sleep(float(step.get("pause", 0.4)))
        return {"ok": True, "flow": flow, "results": results}
