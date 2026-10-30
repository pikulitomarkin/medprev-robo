"""RPA por visao: captura, clique, template matching (OpenCV) e mapeamento."""

from medbh_rpa.vision.capture import capture_window, find_window, focus_window
from medbh_rpa.vision.controller import VisionController

__all__ = [
    "capture_window",
    "find_window",
    "focus_window",
    "VisionController",
]
