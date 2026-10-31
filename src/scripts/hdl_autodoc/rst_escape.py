"""rst_escape.py — escape arbitrary text (comments, log messages) for reStructuredText."""
from __future__ import annotations

import re


def escape_rst(text: str) -> str:
    """
    Escape RST inline markup so the text renders literally: \\, *, `, | and any
    underscore that is not followed by a letter or digit (``a_``, ``a__ b`` would
    otherwise be read as hyperlink references).  Underscores inside a word are left alone.
    """
    text = text.replace("\\", "\\\\")
    text = re.sub(r"([*`|])", r"\\\1", text)
    return re.sub(r"_(?![A-Za-z0-9])", r"\\_", text)
