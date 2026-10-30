from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MatchResult:
    found: bool
    x: int
    y: int
    confidence: float
    method: str


def match_template(
    screenshot_path: Path,
    template_path: Path,
    *,
    threshold: float = 0.82,
) -> MatchResult:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV nao instalado. Rode: pip install opencv-python-headless numpy"
        ) from exc

    screen = cv2.imread(str(screenshot_path))
    templ = cv2.imread(str(template_path))
    if screen is None or templ is None:
        return MatchResult(False, 0, 0, 0.0, "opencv")

    result = cv2.matchTemplate(screen, templ, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    h, w = templ.shape[:2]
    cx = int(max_loc[0] + w / 2)
    cy = int(max_loc[1] + h / 2)
    return MatchResult(
        found=float(max_val) >= threshold,
        x=cx,
        y=cy,
        confidence=float(max_val),
        method="opencv",
    )


def to_dict(m: MatchResult) -> dict[str, Any]:
    return {
        "found": m.found,
        "x": m.x,
        "y": m.y,
        "confidence": round(m.confidence, 4),
        "method": m.method,
    }
