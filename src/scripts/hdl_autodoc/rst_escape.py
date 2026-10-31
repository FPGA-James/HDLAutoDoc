"""rst_escape.py — escape arbitrary text (comments, log messages) for reStructuredText."""
from __future__ import annotations

import re


def escape_rst(text: str) -> str:
    """Escape RST inline markup so the text renders literally: \\, *, `, |, trailing _."""
    text = text.replace("\\", "\\\\")
    text = re.sub(r"([*`|])", r"\\\1", text)
    return re.sub(r"_(?=\s|$)", r"\\_", text)
