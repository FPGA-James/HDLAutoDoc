"""
hdl_scan.py
-----------
Scanning helpers for the places where a regular expression cannot do the job because the
text nests: balanced parentheses, instance parameter and port lists, named connections.

Everything here expects text whose comments have already been removed (see hdl_text) and
uses only the standard library.
"""

import re

# Words that can start a line and be followed by an identifier and `(`, but are not a
# module being instantiated.
_SV_NOT_A_MODULE = frozenset({
    "module", "macromodule", "endmodule", "interface", "endinterface", "package",
    "endpackage", "program", "endprogram", "input", "output", "inout", "ref", "wire", "reg",
    "logic", "bit", "byte", "int", "integer", "shortint", "longint", "real", "time",
    "genvar", "parameter", "localparam", "typedef", "enum", "struct", "union", "import",
    "export", "assign", "always", "always_ff", "always_comb", "always_latch", "initial",
    "final", "if", "else", "for", "foreach", "while", "do", "repeat", "forever", "case",
    "casex", "casez", "endcase", "begin", "end", "generate", "endgenerate", "function",
    "endfunction", "task", "endtask", "return", "assert", "assume", "cover", "property",
    "sequence", "clocking", "modport", "specify", "default", "automatic", "static",
})

_OPEN, _CLOSE = "([{", ")]}"


def matching_paren(text: str, open_idx: int) -> int | None:
    """Index of the `)` that closes the `(` at `open_idx`, or None if it is never closed."""
    if text[open_idx] != "(":
        raise ValueError(f"no '(' at index {open_idx}")
    depth = 0
    for i in range(open_idx, len(text)):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def named_connections(text: str) -> dict[str, str]:
    """`.name(expr), .other(expr)` -> {name: expr}; expressions may nest."""
    found: dict[str, str] = {}
    pos = 0
    pattern = re.compile(r"\.\s*(\w+)\s*\(")
    while (m := pattern.search(text, pos)):
        close = matching_paren(text, m.end() - 1)
        if close is None:
            break
        found[m.group(1)] = text[m.end():close].strip()
        pos = close + 1
    return found


def split_top_level(text: str, sep: str = ",") -> list[str]:
    """`text` split at `sep` outside any parentheses, brackets or braces."""
    parts, depth, start = [], 0, 0
    for i, c in enumerate(text):
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def vhdl_associations(text: str) -> dict[str, str]:
    """`a => x, b => f(y, z)` -> {a: x, b: f(y, z)}; positional entries are skipped."""
    found: dict[str, str] = {}
    for item in split_top_level(text):
        name, arrow, value = item.partition("=>")
        if arrow:
            found[name.strip()] = value.strip()
    return found


_SV_START = re.compile(r"(?m)^[ \t]*([A-Za-z_]\w*)")
_SV_PARAMS = re.compile(r"\s*#\s*\(")
_SV_INSTANCE = re.compile(r"\s*([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*\(")


def scan_sv_instances(text: str) -> list[dict]:
    """
    Module instantiations in SystemVerilog source:
    `[{component, instance, params, ports, start, end}]`.  `params` and `ports` are the
    text between the parentheses (empty if there is no `#(...)`); the parameter list may
    contain nested parentheses, as may the connections.
    """
    found: list[dict] = []
    consumed = 0
    for m in _SV_START.finditer(text):
        if m.start() < consumed or m.group(1) in _SV_NOT_A_MODULE:
            continue
        pos, params = m.end(), ""
        hashed = _SV_PARAMS.match(text, pos)
        if hashed:
            close = matching_paren(text, hashed.end() - 1)
            if close is None:
                continue
            params, pos = text[hashed.end():close].strip(), close + 1
        named = _SV_INSTANCE.match(text, pos)
        if not named:
            continue
        close = matching_paren(text, named.end() - 1)
        if close is None or not re.match(r"\s*;", text[close + 1:]):
            continue
        consumed = close + 1
        found.append({"component": m.group(1), "instance": named.group(1), "params": params,
                      "ports": text[named.end():close], "start": m.start(), "end": close + 1})
    return found


_VHDL_START = re.compile(
    r"\b(\w+)\s*:\s*(?:(?:entity|component|configuration)\s+)?(?:\w+\s*\.\s*)?(\w+)"
    r"(?:\s*\(\s*\w+\s*\))?\s*(?=generic\s+map\b|port\s+map\b)", re.IGNORECASE)
_VHDL_GENERIC_MAP = re.compile(r"\s*generic\s+map\s*\(", re.IGNORECASE)
_VHDL_PORT_MAP = re.compile(r"\s*port\s+map\s*\(", re.IGNORECASE)


def scan_vhdl_instances(text: str) -> list[dict]:
    """
    Component and entity instantiations in VHDL source:
    `[{component, instance, generics, ports, start, end}]`; `generics` and `ports` are the
    text inside `generic map (...)` and `port map (...)`.
    """
    found: list[dict] = []
    consumed = 0
    for m in _VHDL_START.finditer(text):
        if m.start() < consumed:
            continue
        pos, generics = m.end(), ""
        gm = _VHDL_GENERIC_MAP.match(text, pos)
        if gm:
            close = matching_paren(text, gm.end() - 1)
            if close is None:
                continue
            generics, pos = text[gm.end():close].strip(), close + 1
        pm = _VHDL_PORT_MAP.match(text, pos)
        if not pm:
            continue
        close = matching_paren(text, pm.end() - 1)
        if close is None or not re.match(r"\s*;", text[close + 1:]):
            continue
        consumed = close + 1
        found.append({"component": m.group(2), "instance": m.group(1), "generics": generics,
                      "ports": text[pm.end():close], "start": m.start(), "end": close + 1})
    return found
