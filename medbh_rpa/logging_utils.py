from __future__ import annotations

import logging
import re
import sys


_CPF_RE = re.compile(r"\b(\d{3})\.?\d{3}\.?\d{3}-?(\d{2})\b")


class MaskPiiFilter(logging.Filter):
    """Mascara CPF em mensagens de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _CPF_RE.sub(r"***.***.***-\2", record.msg)
        if record.args:
            record.args = tuple(
                _CPF_RE.sub(r"***.***.***-\2", a) if isinstance(a, str) else a
                for a in record.args
            )
        return True


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    handler.addFilter(MaskPiiFilter())
    root.addHandler(handler)
    root.setLevel(level)
