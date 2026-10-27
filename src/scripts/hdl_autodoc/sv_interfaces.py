#!/usr/bin/env python3
"""
sv_interfaces.py
----------------
Helpers for SystemVerilog `interface ... endinterface` definitions, shared by
extract_block.py (block diagram + port table) and generate_rst.py.

  find_interface_names(text)      -> set of interface names defined in `text`
  parse_interface(text, name)     -> {"name", "members", "modports"} or None
  collect_interfaces(files)       -> {name: parsed interface} across several files
  find_interface_port(line, names)-> (interface, modport, port_name) or None

Interface *ports* only make sense relative to known interface names (so that an
ordinary type name is never mistaken for one); callers supply those names from
the interface definitions found in hierarchy.json's `support_files` plus the
module's own file.
"""

from __future__ import annotations

import re
from pathlib import Path

_LINE_COMMENT  = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)

_INTERFACE_RE = re.compile(
    r"^\s*interface\s+(?:automatic\s+|static\s+)?(\w+)", re.MULTILINE)

# logic [7:0] a, b;   types_pkg::byte_t d;   (typedef'd types need a package scope
# to be told apart from statements, so bare user types are not matched)
_MEMBER_RE = re.compile(
    r"^\s*(?:(?P<t>logic|wire|reg|bit)|(?P<pt>\w+::\w+))\s*"
    r"(?:signed\s+|unsigned\s+)?"
    r"(?:\[(?P<r>[^\]]*)\]\s*)?"
    r"(?P<names>\w+(?:\s*,\s*\w+)*)\s*;"
)

_DIR_NORM = {"input": "in", "output": "out", "inout": "inout", "ref": "ref"}


def _strip_comments(text: str) -> str:
    """Remove comments, keeping line structure (block comments keep their newlines)."""
    text = _BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _LINE_COMMENT.sub("", text)


def find_interface_names(text: str) -> set[str]:
    """Names of the interfaces defined in `text` (ignores `interface class`)."""
    return {m.group(1) for m in _INTERFACE_RE.finditer(_strip_comments(text))
            if m.group(1) != "class"}


def _comment_for(lines: list[str], idx: int) -> str:
    """Inline `//` comment on the line, else the `//` line directly above."""
    m = re.search(r"//\s*(.*)", lines[idx])
    if m:
        return m.group(1).strip()
    i = idx - 1
    while i >= 0 and lines[i].strip() == "":
        i -= 1
    if i >= 0 and lines[i].strip().startswith("//"):
        return re.sub(r"^//\s*", "", lines[i].strip()).strip()
    return ""


def _parse_modports(body: str) -> dict[str, dict[str, str]]:
    """{modport: {member: 'in'|'out'|'inout'|'ref'}} from a comment-free body."""
    modports: dict[str, dict[str, str]] = {}
    for m in re.finditer(r"\bmodport\s+(\w+)\s*\((.*?)\)\s*;", body, re.DOTALL):
        directions: dict[str, str] = {}
        current = "inout"
        for item in m.group(2).split(","):
            item = item.strip()
            if not item or item.startswith(("import", "export", ".")):
                continue
            first, _, rest = item.partition(" ")
            if first in _DIR_NORM:
                current = _DIR_NORM[first]
                item = rest.strip()
            name = item.split()[-1] if item.split() else ""
            if re.fullmatch(r"\w+", name):
                directions[name] = current
        modports[m.group(1)] = directions
    return modports


def parse_interface(text: str, name: str) -> dict | None:
    """
    Parse one interface definition.

    Returns {"name", "members": [{name, type, range, comment}],
             "modports": {modport: {member: direction}}}, or None if `name` is not
    defined in `text`.  The header port list (e.g. `(input logic clk)`) is not a
    member and is skipped.
    """
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if re.match(rf"\s*interface\s+(?:automatic\s+|static\s+)?{re.escape(name)}\b", l)),
                 None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines))
                if re.search(r"\bendinterface\b", lines[i])), len(lines))

    clean = _strip_comments("\n".join(lines)).splitlines()
    # The header (parameters + port list) runs to the first ';'.
    header_end = next((i for i in range(start, end) if ";" in clean[i]), start)

    members: list[dict] = []
    for idx in range(header_end + 1, end):
        m = _MEMBER_RE.match(clean[idx])
        if not m:
            continue
        comment = _comment_for(lines, idx)
        for n in re.split(r"\s*,\s*", m.group("names")):
            members.append({
                "name":    n,
                "type":    m.group("t") or m.group("pt"),
                "range":   (m.group("r") or "").strip(),
                "comment": comment,
            })

    body = "\n".join(clean[header_end + 1:end])
    return {"name": name, "members": members, "modports": _parse_modports(body)}


def collect_interfaces(files: list[Path]) -> dict[str, dict]:
    """
    Every interface defined in `files` (first definition wins), keyed by name.
    Unreadable files are skipped.
    """
    found: dict[str, dict] = {}
    for f in files:
        try:
            text = Path(f).read_text(errors="replace")
        except OSError:
            continue
        for name in find_interface_names(text):
            if name not in found:
                parsed = parse_interface(text, name)
                if parsed:
                    found[name] = parsed
    return found


_IFACE_PORT_RE = re.compile(
    r"^\s*(?P<ifc>\w+)(?:\s*\.\s*(?P<mp>\w+))?\s+(?P<name>\w+)\s*"
    r"(?:\[[^\]]*\]\s*)*[,)]?\s*;?\s*$"
)


def find_interface_port(line: str, interface_names: set[str] | frozenset[str]
                        ) -> tuple[str, str, str] | None:
    """
    Match a one-port-per-line header entry such as
        axil_if.slave s_axil,        or        axis_if m_axis
    and return (interface, modport or "", port_name) when the type is a known
    interface; otherwise None.  The line's trailing `//` comment is ignored.
    """
    if not interface_names:
        return None
    m = _IFACE_PORT_RE.match(_LINE_COMMENT.sub("", line))
    if m and m.group("ifc") in interface_names:
        return m.group("ifc"), m.group("mp") or "", m.group("name")
    return None
