"""
hdl_text.py
-----------
Small text helpers shared by the extractors: comment stripping for the two source
languages, a Graphviz-safe identifier, and an RST page title.
"""

import re


def strip_vhdl_comments(text: str) -> str:
    """`text` without VHDL `--` comments."""
    return re.sub(r"--[^\n]*", "", text)


def strip_sv_comments(text: str) -> str:
    """`text` without SystemVerilog `//` and `/* */` comments."""
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def blank_vhdl_comments(text: str) -> str:
    """`text` with VHDL `--` comments replaced by spaces: every other character keeps its
    position, so an index into the result is an index into the original (and line
    numbers survive)."""
    return re.sub(r"--[^\n]*", lambda m: " " * len(m.group(0)), text)


def blank_sv_comments(text: str) -> str:
    """`text` with SystemVerilog `//` and `/* */` comments replaced by spaces, newlines
    kept; positions and line numbers are those of the original."""
    text = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), text)
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.DOTALL)


def safe_id(name: str) -> str:
    """A Graphviz-safe identifier: every non-word character becomes `_`."""
    return re.sub(r"\W", "_", name)


def title(text: str) -> list[str]:
    """RST lines for a page title: the text, an `=` underline, a blank line."""
    return [text, "=" * len(text), ""]
