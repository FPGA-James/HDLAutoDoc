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


def split_lines(text: str) -> list[str]:
    """
    `text` as the lines an editor shows: broken at `\\n` (a `\\r` before it is dropped) and
    nowhere else.  `str.splitlines()` also breaks at form feeds, U+0085, U+2028 and others,
    which an editor does not, so line numbers computed from it drift.  For text without those
    characters the result equals `text.splitlines()`.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


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
