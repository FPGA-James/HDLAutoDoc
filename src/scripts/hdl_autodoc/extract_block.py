#!/usr/bin/env python3
"""
extract_block.py
----------------
Extracts the port interface, generics/parameters, and internal signals from a
VHDL entity or SystemVerilog module and writes:

  <module_name>_block.dot  — Graphviz block diagram (inputs left, outputs right)
  <module_name>_block.rst  — RST page with the diagram, port table,
                              generics/parameters table, and signals table

Port comments are captured from:
  - Same-line:      clk : in std_logic;  -- System clock.
  - Preceding-line: -- System clock.
                    clk : in std_logic;

Bus widths are computed from the port range where possible and shown as edge
labels on the diagram (e.g. "8" for std_logic_vector(7 downto 0)).

SystemVerilog interface ports (`axil_if.slave s_axil`, `axis_if m_axis`) are listed
when their interface is known — defined in a support file or the module's own file.
Each is one row in the port table (Direction = modport, Type = interface name) and
one bus-style port on the diagram labelled `name (interface)`.  Placement rule: a
port whose modport is master-like (master, manager, initiator, source/src, mst, tx,
producer, driver, out) is drawn on the right; every other interface port (slave,
subordinate, target, sink/snk, rx, ..., or no modport) is drawn on the left.  The
members of each interface used are listed under an "Interfaces" heading.

Usage:
    python scripts/hdl_autodoc/extract_block.py <file.vhd|file.sv> <module_name> <output_dir>
        [--bus-groups <path>] [--support <support_file> ...]
"""

import re
import sys
from pathlib import Path

from sv_interfaces import collect_interfaces, find_interface_port


# ─────────────────────────────────────────────────────────────────────────────
# Section extraction (depth-aware, handles nested parens)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_paren_section(text: str, keyword: str) -> str:
    """
    Find 'keyword (' in text (ignoring VHDL -- comments when scanning) and
    return everything between the opening paren and its matching close paren.
    Returns an empty string if the keyword is not found.
    """
    # Replace comments with spaces of equal length so character indices stay valid
    stripped = re.sub(r"--[^\n]*", lambda m: " " * len(m.group(0)), text)
    m = re.compile(rf"\b{keyword}\s*\(", re.IGNORECASE).search(stripped)
    if not m:
        return ""

    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        ch = text[i]
        # Skip VHDL line comments when depth-counting
        if ch == "-" and i + 1 < len(text) and text[i + 1] == "-":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                break
        i += 1

    return text[start:i]


# ─────────────────────────────────────────────────────────────────────────────
# Comment helpers
# ─────────────────────────────────────────────────────────────────────────────

def _inline_comment_vhdl(line: str) -> str:
    """Return text after -- on the line, or empty string."""
    m = re.search(r"--\s*(.*)", line)
    return m.group(1).strip() if m else ""


def _inline_comment_sv(line: str) -> str:
    """Return text after // on the line, or empty string."""
    m = re.search(r"//\s*(.*)", line)
    return m.group(1).strip() if m else ""


def _preceding_comment(lines: list[str], idx: int, prefix: str) -> str:
    """
    Look back from line idx for a comment line immediately above (ignoring
    blank lines).  Returns the comment text or empty string.
    """
    i = idx - 1
    while i >= 0 and lines[i].strip() == "":
        i -= 1
    if i >= 0 and lines[i].strip().startswith(prefix):
        return re.sub(rf"^{re.escape(prefix)}\s*", "", lines[i].strip()).strip()
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# VHDL extraction
# ─────────────────────────────────────────────────────────────────────────────

# Matches: name [, name2] : direction type[(range)]
_VHDL_PORT_RE = re.compile(
    r"(\w+(?:\s*,\s*\w+)*)\s*:\s*(in|out|inout)\s+"
    r"(std_logic(?:_vector)?|unsigned|signed|integer|natural|positive|"
    r"boolean|real|bit(?:_vector)?|std_ulogic(?:_vector)?|\w+)"
    r"(?:\s*\(\s*(.*?)\s*\))?",
    re.IGNORECASE,
)

# Matches: name : type := default
_VHDL_GENERIC_RE = re.compile(
    r"(\w+)\s*:\s*(\w+)\s*:=\s*([^;,\n]+)",
    re.IGNORECASE,
)


def extract_ports_vhdl(text: str) -> list[dict]:
    """
    Extract port declarations from a VHDL entity.
    Returns list of {name, dir, type, range, comment}.
    Comments are taken from same-line or the preceding comment line.
    """
    section = _extract_paren_section(text, "port")
    if not section:
        return []

    lines  = section.splitlines()
    ports  = []

    for idx, line in enumerate(lines):
        m = _VHDL_PORT_RE.search(re.sub(r"--.*", "", line))  # strip for matching
        if not m:
            continue

        comment = _inline_comment_vhdl(line) or _preceding_comment(lines, idx, "--")
        for name in [n.strip() for n in m.group(1).split(",")]:
            ports.append({
                "name":    name,
                "dir":     m.group(2).lower(),
                "type":    m.group(3).lower(),
                "range":   (m.group(4) or "").strip(),
                "comment": comment,
            })

    return ports


def extract_generics_vhdl(text: str) -> list[dict]:
    """
    Extract generic declarations from a VHDL entity.
    Returns list of {name, type, default, comment}.
    """
    section = _extract_paren_section(text, "generic")
    if not section:
        return []

    lines    = section.splitlines()
    generics = []

    for idx, line in enumerate(lines):
        m = _VHDL_GENERIC_RE.search(re.sub(r"--.*", "", line))
        if not m:
            continue

        comment = _inline_comment_vhdl(line) or _preceding_comment(lines, idx, "--")
        generics.append({
            "name":    m.group(1),
            "type":    m.group(2).lower(),
            "default": m.group(3).strip().rstrip(";,").strip(),
            "comment": comment,
        })

    return generics


# ─────────────────────────────────────────────────────────────────────────────
# SystemVerilog extraction
# ─────────────────────────────────────────────────────────────────────────────

# Matches: input/output/inout [logic/wire/reg] [[range]] name
_SV_PORT_RE = re.compile(
    r"^\s*(input|output|inout)\s+"
    r"(?:(logic|wire|reg|bit)\s*)?"
    r"(?:\[([^\]]*)\]\s*)?"
    r"(\w+)",
    re.IGNORECASE,
)

# Matches: parameter [type] name = default
_SV_PARAM_RE = re.compile(
    r"^\s*(parameter|localparam)\s+(?:(\w+)\s+)?(\w+)\s*=\s*([^,;/]+)",
    re.IGNORECASE,
)


def _match_paren(s: str, i: int) -> int:
    """Index of the `)` matching the `(` at s[i], or -1."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _sv_port_list_spans(text: str) -> list[tuple[int, int]]:
    """
    (start, end) character offsets of each module header's port list, i.e. the
    `( ... )` after `module name` and any `#( ... )` parameter list.  Interface
    ports are only looked for here, so an interface *instance* in a module body
    (`stream_if s (.clk(clk));`) is never read as a port.
    """
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    stripped = re.sub(r"/\*.*?\*/", blank, text, flags=re.DOTALL)
    stripped = re.sub(r"//[^\n]*", blank, stripped)
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"\b(?:module|macromodule)\s+(?:automatic\s+|static\s+)?\w+\s*",
                         stripped):
        i = m.end()
        if stripped[i:i + 1] == "#":
            i += 1
            i += len(stripped[i:]) - len(stripped[i:].lstrip())
            if stripped[i:i + 1] != "(":
                continue
            j = _match_paren(stripped, i)
            if j < 0:
                continue
            i = j + 1
            i += len(stripped[i:]) - len(stripped[i:].lstrip())
        if stripped[i:i + 1] == "(":
            j = _match_paren(stripped, i)
            if j > 0:
                spans.append((i + 1, j))
    return spans


def extract_ports_sv(text: str, interface_names: set[str] | None = None) -> list[dict]:
    """
    Extract port declarations from a SystemVerilog module.
    Returns list of {name, dir, type, range, comment}.

    With `interface_names` (the known `interface` definitions), interface-typed
    ports in the module header (`axil_if.slave s_axil`, `axis_if m_axis`) are also
    returned, in declaration order, with kind="interface", the `interface` name and
    its `modport` ("" if none); `dir` holds the modport ("—" if none) and `type`
    the interface name.  Without it behaviour is unchanged.
    """
    lines = text.splitlines()
    ports = []

    spans: list[tuple[int, int]] = []
    line_starts: list[int] = []
    if interface_names:
        spans = _sv_port_list_spans(text)
        pos = 0
        for l in lines:
            line_starts.append(pos)
            pos += len(l) + 1

    for idx, line in enumerate(lines):
        m = _SV_PORT_RE.match(line)
        if not m:
            if spans and any(s <= line_starts[idx] < e for s, e in spans):
                hit = find_interface_port(line, interface_names)
                if hit:
                    ifc, modport, pname = hit
                    ports.append({
                        "name":      pname,
                        "dir":       modport or "\u2014",
                        "type":      ifc,
                        "range":     "",
                        "comment":   _inline_comment_sv(line)
                                     or _preceding_comment(lines, idx, "//"),
                        "kind":      "interface",
                        "interface": ifc,
                        "modport":   modport,
                    })
            continue

        comment = _inline_comment_sv(line) or _preceding_comment(lines, idx, "//")
        # Normalise SV "input"/"output" to "in"/"out" to match VHDL convention
        raw_dir = m.group(1).lower()
        norm_dir = {"input": "in", "output": "out"}.get(raw_dir, raw_dir)
        ports.append({
            "name":    m.group(4),
            "dir":     norm_dir,
            "type":    (m.group(2) or "logic").lower(),
            "range":   (m.group(3) or "").strip(),
            "comment": comment,
        })

    return ports


def extract_params_sv(text: str) -> list[dict]:
    """
    Extract parameter and localparam declarations from a SystemVerilog module.
    Returns list of {name, type, default, comment, kind}.
    """
    lines  = text.splitlines()
    params = []

    for idx, line in enumerate(lines):
        m = _SV_PARAM_RE.match(line)
        if not m:
            continue

        comment = _inline_comment_sv(line) or _preceding_comment(lines, idx, "//")
        params.append({
            "name":    m.group(3),
            "type":    (m.group(2) or "").lower(),
            "default": m.group(4).strip().rstrip(",;").strip(),
            "comment": comment,
            "kind":    m.group(1).lower(),
        })

    return params


# ─────────────────────────────────────────────────────────────────────────────
# Internal signal extraction
# ─────────────────────────────────────────────────────────────────────────────

# Matches: signal name [, name2] : type[(range)] [:= init]
_VHDL_SIGNAL_RE = re.compile(
    r"^\s*signal\s+(\w+(?:\s*,\s*\w+)*)\s*:\s*([\w_]+)"
    r"(?:\s*\(\s*(.*?)\s*\))?"
    r"(?:\s*:=\s*([^;]+))?",
    re.IGNORECASE,
)

# Matches internal SV: logic/wire/reg [[range]] name [, name2]
_SV_SIGNAL_RE = re.compile(
    r"^\s*(logic|wire|reg)\s*(?:\[([^\]]*)\]\s*)?(\w+(?:\s*,\s*\w+)*)\s*;",
    re.IGNORECASE,
)

_SV_PORT_KW = {"input", "output", "inout"}


def extract_signals_vhdl(text: str) -> list[dict]:
    """
    Extract internal signal declarations from a VHDL architecture.

    Scans the declaration region between 'architecture X of Y is' and the
    first bare 'begin' line.  Returns list of {name, type, range, init, comment}.
    Comments from the preceding line or same line are captured.
    """
    lines = text.splitlines()

    arch_re  = re.compile(r"^\s*architecture\s+\w+\s+of\s+\w+\s+is\b", re.IGNORECASE)
    begin_re = re.compile(r"^\s*begin\s*$", re.IGNORECASE)

    decl_lines: list[str] = []
    in_decl = False
    for line in lines:
        if not in_decl:
            if arch_re.match(line):
                in_decl = True
        else:
            if begin_re.match(line):
                break
            decl_lines.append(line)

    signals = []
    for idx, line in enumerate(decl_lines):
        m = _VHDL_SIGNAL_RE.search(re.sub(r"--.*", "", line))
        if not m:
            continue
        comment = _inline_comment_vhdl(line) or _preceding_comment(decl_lines, idx, "--")
        for name in [n.strip() for n in m.group(1).split(",")]:
            signals.append({
                "name":    name,
                "type":    m.group(2).lower(),
                "range":   (m.group(3) or "").strip(),
                "init":    (m.group(4) or "").strip().rstrip(";").strip(),
                "comment": comment,
            })
    return signals


def extract_signals_sv(text: str) -> list[dict]:
    """
    Extract internal signal declarations from a SystemVerilog module.

    Matches 'logic', 'wire', or 'reg' declarations that are not port
    declarations (i.e. not prefixed with input/output/inout).
    Returns list of {name, type, range, init, comment}.
    """
    lines   = text.splitlines()
    signals = []

    for idx, line in enumerate(lines):
        stripped = line.strip().lower()
        if any(stripped.startswith(k) for k in _SV_PORT_KW):
            continue
        m = _SV_SIGNAL_RE.match(line)
        if not m:
            continue
        comment = _inline_comment_sv(line) or _preceding_comment(lines, idx, "//")
        for name in [n.strip() for n in m.group(3).split(",")]:
            signals.append({
                "name":    name,
                "type":    m.group(1).lower(),
                "range":   (m.group(2) or "").strip(),
                "init":    "",
                "comment": comment,
            })
    return signals


# ─────────────────────────────────────────────────────────────────────────────
# Width label helper
# ─────────────────────────────────────────────────────────────────────────────

def _width_label(port: dict) -> str:
    """
    Return a compact width string for diagram edge labels.
    Computes the numeric width from downto/to ranges where possible;
    returns the raw range expression for parametric widths.
    """
    rng = port.get("range", "")
    if rng:
        # Numeric: "7 downto 0" or "7:0"
        m = re.match(r"(\d+)\s+(?:downto|to)\s+(\d+)", rng, re.IGNORECASE)
        if m:
            return str(abs(int(m.group(1)) - int(m.group(2))) + 1)
        m = re.match(r"(\d+)\s*:\s*(\d+)", rng)
        if m:
            return str(abs(int(m.group(1)) - int(m.group(2))) + 1)
        # Parametric: return the expression
        return f"[{rng}]"

    t = port.get("type", "").lower()
    if t in ("integer", "natural", "positive", "real", "int"):
        return t
    return "1"


# ─────────────────────────────────────────────────────────────────────────────
# Graphviz dot writer  (TerosHDL-inspired style)
# ─────────────────────────────────────────────────────────────────────────────

import html as _html

def _safe(name: str) -> str:
    return re.sub(r"\W", "_", name)


# Modport-name tokens that mean "this port drives the bus": drawn on the right.
# Everything else (slave, subordinate, target, sink/snk, rx, no modport, ...) is
# drawn on the left, like an input.
_MASTER_LIKE = {"master", "manager", "initiator", "source", "src", "mst", "tx",
                "producer", "driver", "out"}


def interface_side(port: dict) -> str:
    """'right' for a master-like modport, else 'left' (see _MASTER_LIKE)."""
    tokens = [t for t in re.split(r"[^a-z]+", (port.get("modport") or "").lower()) if t]
    return "right" if any(t in _MASTER_LIKE for t in tokens) else "left"


def write_dot_block(module_name: str, ports: list[dict],
                    generics: list[dict]) -> str:
    """
    Generate a TerosHDL-inspired block diagram using Graphviz HTML table labels.

    Layout mirrors the TerosHDL documenter output:
      - Green box (top):   generics/parameters, one per row, stub on the left.
      - Yellow box (below): port interface.
          Left column  — inputs  (► name [width])
          Right column — outputs (name ◄)
      - Thick black stub lines on both sides; bus width labels on output stubs.

    Two separate flat-table nodes are used so that PORT attributes work for
    precise per-row edge attachment.  rank=same keeps them in one column;
    an invisible edge orders gen_box above port_box.
    """
    safe_mod   = _safe(module_name)
    # A modport can be called "in"/"out", so classify plain ports by kind first.
    plain      = [p for p in ports if p.get("kind") != "interface"]
    iface      = [p for p in ports if p.get("kind") == "interface"]
    inputs     = [p for p in plain if p["dir"] == "in"]
    outputs    = [p for p in plain if p["dir"] == "out"]
    inouts     = [p for p in plain if p["dir"] == "inout"]
    left_ports = inputs + inouts + [p for p in iface if interface_side(p) == "left"]
    outputs    = outputs + [p for p in iface if interface_side(p) == "right"]
    n_rows     = max(len(left_ports), len(outputs), 1)
    _ONE_BIT   = {"1", "integer", "natural", "positive", "real", "int"}

    lines = [
        f"digraph {safe_mod}_block {{",
        "    rankdir=LR;",
        "    nodesep=0.5;",
        "    ranksep=0.8;",
        '    node [fontname="Helvetica", fontsize=12, shape=none, margin=0];',
        '    edge [dir=none, penwidth=2.5, color="black"];',
        "",
    ]

    # ── Generics box (green) ──────────────────────────────────────────────────
    if generics:
        gen_rows = []
        for g in generics:
            name    = _html.escape(g["name"])
            default = f' = {_html.escape(str(g["default"]))}' if g.get("default") else ""
            gen_rows.append(
                f'<TR>'
                f'<TD PORT="g_{_safe(g["name"])}" ALIGN="LEFT" CELLPADDING="5">'
                f'{name}{default}'
                f'</TD>'
                f'</TR>'
            )
        gen_label = (
            '<\n        '
            '<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="3" CELLPADDING="0"'
            ' BGCOLOR="#c8f5c4" COLOR="#1a5c1a">\n          '
            + "\n          ".join(gen_rows)
            + "\n        </TABLE>>"
        )
        lines += [
            f"    // Generics box",
            f"    gen_box_{safe_mod} [label={gen_label}];",
            "",
        ]

    # ── Ports box (yellow) ────────────────────────────────────────────────────
    port_rows = []
    for i in range(n_rows):
        lp = left_ports[i] if i < len(left_ports) else None
        rp = outputs[i]    if i < len(outputs)    else None

        if lp and lp.get("kind") == "interface":
            # One bus-style port for the whole interface bundle.
            left_td = (
                f'<TD PORT="i_{_safe(lp["name"])}" ALIGN="LEFT" CELLPADDING="5">'
                f'&#x25B8;&#x25B8; {_html.escape(lp["name"])} (interface)</TD>'
            )
        elif lp:
            w     = _width_label(lp)
            sym   = "&#x25C2;&#x25B8;" if lp["dir"] == "inout" else "&#x25B8;"
            # _width_label returns "[expr]" for parametric, bare number for numeric
            _w_display = w if w.startswith("[") else f"[{w}]"
            w_ann = f' {_html.escape(_w_display)}' if w not in _ONE_BIT else ""
            left_td = (
                f'<TD PORT="i_{_safe(lp["name"])}" ALIGN="LEFT" CELLPADDING="5">'
                f'{sym} {_html.escape(lp["name"])}{w_ann}</TD>'
            )
        else:
            left_td = '<TD CELLPADDING="5"> </TD>'

        if rp and rp.get("kind") == "interface":
            right_td = (
                f'<TD PORT="o_{_safe(rp["name"])}" ALIGN="RIGHT" CELLPADDING="5">'
                f'{_html.escape(rp["name"])} (interface) &#x25C2;&#x25C2;</TD>'
            )
        elif rp:
            right_td = (
                f'<TD PORT="o_{_safe(rp["name"])}" ALIGN="RIGHT" CELLPADDING="5">'
                f'{_html.escape(rp["name"])} &#x25C2;</TD>'
            )
        else:
            right_td = '<TD CELLPADDING="5"> </TD>'

        port_rows.append(
            f'<TR>{left_td}<TD WIDTH="50"> </TD>{right_td}</TR>'
        )

    port_label = (
        '<\n        '
        '<TABLE BORDER="2" CELLBORDER="0" CELLSPACING="3" CELLPADDING="0"'
        ' BGCOLOR="#fffde7" COLOR="#5d4200">\n          '
        + "\n          ".join(port_rows)
        + "\n        </TABLE>>"
    )
    lines += [
        f"    // Ports box",
        f"    port_box_{safe_mod} [label={port_label}];",
        "",
    ]

    # ── Stack gen_box above port_box (rank=same + invisible ordering edge) ────
    if generics:
        lines += [
            f"    {{ rank=same; gen_box_{safe_mod}; port_box_{safe_mod} }}",
            f"    gen_box_{safe_mod} -> port_box_{safe_mod}"
            f' [style=invis, weight=100];',
            "",
        ]

    lines.append("}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# RST / HTML writers
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# HTML port table (used when bus groups are detected)
# ─────────────────────────────────────────────────────────────────────────────

def _html_port_table(bus_groups: list, remaining: list[dict]) -> str:
    """
    Render port table as an indented HTML block for use inside ``.. raw:: html``.
    Bus groups get a <details>/<summary> collapsible row; individual ports get
    plain <tr> rows.
    """
    rows: list[str] = []
    rows.append('<table class="port-table">')
    rows.append("  <thead>")
    rows.append("    <tr><th>Port</th><th>Direction</th>"
                "<th>Type</th><th>Description</th></tr>")
    rows.append("  </thead>")
    rows.append("  <tbody>")

    for bg in bus_groups:
        n = len(bg.ports)
        plural = "s" if n != 1 else ""
        rows.append('    <tr class="bus-group-row">')
        rows.append('      <td colspan="4">')
        rows.append("        <details>")
        rows.append(
            f"          <summary><strong>{_html.escape(bg.prefix)}</strong>"
            f" \u2014 {_html.escape(bg.bus_type)} ({n} port{plural})</summary>"
        )
        rows.append('          <table class="bus-ports-inner">')
        for p in bg.ports:
            type_text = _type_str(p).replace("`", "")
            rows.append("            <tr>")
            rows.append(f'              <td><code>{_html.escape(p["name"])}</code></td>')
            rows.append(f'              <td><code>{_html.escape(p["dir"])}</code></td>')
            rows.append(f'              <td><code>{_html.escape(type_text)}</code></td>')
            rows.append(f'              <td>{_html.escape(p["comment"] or "")}</td>')
            rows.append("            </tr>")
        rows.append("          </table>")
        rows.append("        </details>")
        rows.append("      </td>")
        rows.append("    </tr>")

    for p in remaining:
        type_text = _type_str(p).replace("`", "")
        rows.append("    <tr>")
        rows.append(f'      <td><code>{_html.escape(p["name"])}</code></td>')
        rows.append(f'      <td><code>{_html.escape(p["dir"])}</code></td>')
        rows.append(f'      <td><code>{_html.escape(type_text)}</code></td>')
        rows.append(f'      <td>{_html.escape(p["comment"] or "")}</td>')
        rows.append("    </tr>")

    rows.append("  </tbody>")
    rows.append("</table>")

    # Each line is indented 3 spaces to satisfy RST's ``.. raw:: html`` block
    return "\n".join("   " + line for line in rows)


_DIR_RST = {"in": "``in``", "out": "``out``", "inout": "``inout``"}


def _dir_rst(port: dict) -> str:
    """Direction cell: in/out/inout, or the modport for an interface port."""
    if port.get("kind") == "interface":
        return f"``{port['modport']}``" if port.get("modport") else "\u2014"
    return _DIR_RST.get(port["dir"], port["dir"])


def _type_str(port: dict) -> str:
    """
    Format port type + range as a readable string.
    VHDL uses parentheses: std_logic_vector(7 downto 0)
    SV uses square brackets:  logic[7:0]
    Detected from whether the range contains 'downto'/'to' (VHDL) or ':' (SV).
    """
    if port.get("kind") == "interface":
        return f"``{port['interface']}``"
    t = port["type"]
    r = port["range"]
    if r:
        if re.search(r"\bdownto\b|\bto\b", r, re.IGNORECASE):
            return f"``{t}({r})``"   # VHDL
        return f"``{t}[{r}]``"       # SV
    return f"``{t}``"


def _interfaces_rst(ports: list[dict], interfaces: dict[str, dict]) -> list[str]:
    """
    "Interfaces" section: one members table per interface used by an interface
    port (in port order).  The modport columns show each member's direction as
    seen through the modports this module's ports use.  Empty if there is nothing
    to show.
    """
    used: list[str] = []
    for p in ports:
        if p.get("kind") == "interface" and p["interface"] in interfaces \
                and p["interface"] not in used:
            used.append(p["interface"])
    if not used:
        return []

    lines = ["", "Interfaces", "----------", ""]
    for name in used:
        iface = interfaces[name]
        modports: list[str] = []
        for p in ports:
            if p.get("kind") == "interface" and p["interface"] == name \
                    and p["modport"] and p["modport"] in iface["modports"] \
                    and p["modport"] not in modports:
                modports.append(p["modport"])
        users = ", ".join(f"``{p['name']}``" for p in ports
                          if p.get("kind") == "interface" and p["interface"] == name)
        lines += [f"``{name}`` — used by {users}.", ""]
        if not iface["members"]:
            lines += ["*(no members found)*", ""]
            continue
        header = ["Signal", "Type"] + [f"{m}" for m in modports] + ["Description"]
        lines += [".. list-table::", "   :header-rows: 1", "",
                  f"   * - {header[0]}"] + [f"     - {h}" for h in header[1:]] + [""]
        for mem in iface["members"]:
            row = [f"``{mem['name']}``", _type_str(mem)]
            row += [iface["modports"][m].get(mem["name"], "\u2014") for m in modports]
            row += [mem["comment"] or "\u2014"]
            lines += [f"   * - {row[0]}"] + [f"     - {c}" for c in row[1:]] + [""]
    return lines


def write_rst_block(module_name: str, src_filename: str,
                    ports: list[dict], generics: list[dict],
                    signals: list[dict],
                    include_schematic: bool = False,
                    toml_path: Path | None = None,
                    interfaces: dict[str, dict] | None = None) -> str:
    dot_file = f"{module_name}_block.dot"
    title    = f"{module_name} — Block Diagram"
    lines    = [title, "=" * len(title), "",
                f"Auto-extracted from ``{src_filename}``.", "",
                f".. graphviz:: {dot_file}", ""]

    # ── Port table ──────────────────────────────────────────────────────────
    if ports:
        from detect_buses import group_ports
        # Interface ports are single bundled ports, never members of a name-prefix
        # bus group; keep them out of grouping and back in declaration order.
        plain = [p for p in ports if p.get("kind") != "interface"]
        bus_groups, remaining_plain = group_ports(plain, toml_path)
        remaining = [p for p in ports
                     if p.get("kind") == "interface"
                     or any(p is r for r in remaining_plain)]
        if bus_groups:
            lines += ["Ports", "-----", "", ".. raw:: html", ""]
            lines.append(_html_port_table(bus_groups, remaining))
            lines.append("")
        else:
            lines += [
                "Ports", "-----", "",
                ".. list-table::", "   :header-rows: 1", "",
                "   * - Port", "     - Direction", "     - Type", "     - Description", "",
            ]
            for p in ports:
                lines += [
                    f'   * - ``{p["name"]}``',
                    f'     - {_dir_rst(p)}',
                    f'     - {_type_str(p)}',
                    f'     - {p["comment"] or "—"}',
                    "",
                ]

    # ── Interfaces: members of each interface used by a port ─────────────────
    lines += _interfaces_rst(ports, interfaces or {})

    # ── Generics / parameters table ──────────────────────────────────────────
    if generics:
        heading = "Generics" if any(
            g.get("kind", "generic") == "generic" or "kind" not in g
            for g in generics
        ) else "Parameters"

        lines += [
            "",
            heading, "-" * len(heading), "",
            ".. list-table::", "   :header-rows: 1", "",
            "   * - Name", "     - Type", "     - Default", "     - Description", "",
        ]
        for g in generics:
            type_str = f'``{g["type"]}``' if g.get("type") else "—"
            lines += [
                f'   * - ``{g["name"]}``',
                f'     - {type_str}',
                f'     - ``{g["default"]}``',
                f'     - {g["comment"] or "—"}',
                "",
            ]

    # ── Signals table ────────────────────────────────────────────────────────
    if signals:
        lines += [
            "",
            "Signals", "-------", "",
            ".. list-table::", "   :header-rows: 1", "",
            "   * - Signal", "     - Type", "     - Description", "",
        ]
        for s in signals:
            lines += [
                f'   * - ``{s["name"]}``',
                f'     - {_type_str(s)}',
                f'     - {s["comment"] or "—"}',
                "",
            ]

    # ── RTL Schematic (optional — only present when SCHEMATICS=1) ────────────
    if include_schematic:
        # Wildcard extension lets Sphinx pick the right candidate per builder:
        # SVG for HTML, the PDF sibling (if generate_schematic.py produced one) for LaTeX.
        schematic_image = f"{module_name}_schematic.*"
        # Secondary detail.  HTML: collapsed <details> disclosure so the page leads
        # with the block diagram.  LaTeX/PDF: the schematic gets its own landscape
        # (rotated 90 degrees) page; Sphinx scales the image to fit the text area.
        lines += [
            "",
            "RTL Detail", "----------", "",
            "Gate-level netlist generated by ``yosys`` and rendered with ``netlistsvg``.", "",
            ".. only:: html", "",
            "   .. raw:: html", "",
            "      <details class=\"hdl-rtl-detail\">",
            "      <summary>Show RTL schematic</summary>", "",
            f"   .. image:: {schematic_image}",
            "      :align: center", "",
            "   .. raw:: html", "",
            "      </details>", "",
            ".. only:: latex", "",
            "   .. raw:: latex", "",
            "      \\begin{landscape}",
            # Sphinx caps image height at \spx@image@maxheight, fixed at document
            # start to the *portrait* text height -- taller than a landscape page.
            # Reset it from the landscape \textheight (minus room for spacing);
            # the assignment is local to the landscape environment.
            "      \\makeatletter",
            "      \\spx@image@maxheight=\\dimexpr\\textheight-4\\baselineskip\\relax",
            "      \\makeatother", "",
            f"   .. image:: {schematic_image}",
            "      :align: center", "",
            "   .. raw:: latex", "",
            "      \\end{landscape}", "",
        ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Usage: extract_block.py <file.vhd|file.sv> <module_name> <output_dir> "
                 "[--bus-groups <path>] [--support <support_file> ...]")

    src_path    = Path(sys.argv[1])
    module_name = sys.argv[2]
    output_dir  = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    args = sys.argv[4:]
    toml_path: Path | None = None
    if "--bus-groups" in args:
        idx = args.index("--bus-groups")
        if idx + 1 >= len(args):
            sys.exit("ERROR: --bus-groups requires a path argument")
        toml_path = Path(args[idx + 1])

    # Support files (packages, interfaces) from hierarchy.json; their `interface`
    # definitions, plus any in the module's own file, identify interface ports.
    support = [Path(args[i + 1]) for i, a in enumerate(args)
               if a == "--support" and i + 1 < len(args)]

    text = src_path.read_text()
    ext  = src_path.suffix.lower()
    interfaces: dict[str, dict] = {}

    if ext in (".vhd", ".vhdl"):
        ports    = extract_ports_vhdl(text)
        generics = extract_generics_vhdl(text)
        signals  = extract_signals_vhdl(text)
    elif ext in (".sv", ".svh"):
        interfaces = collect_interfaces([*support, src_path])
        ports    = extract_ports_sv(text, set(interfaces))
        generics = extract_params_sv(text)
        signals  = extract_signals_sv(text)
    else:
        sys.exit(f"ERROR: Unsupported file type '{ext}'")

    dot_path = output_dir / f"{module_name}_block.dot"
    rst_path = output_dir / f"{module_name}_block.rst"

    # Include RTL schematic section if generate_schematic.py already wrote the SVG.
    schematic_svg = output_dir / f"{module_name}_schematic.svg"
    include_schematic = schematic_svg.exists()

    dot_path.write_text(write_dot_block(module_name, ports, generics))
    print(f"  → {dot_path}")

    rst_path.write_text(write_rst_block(module_name, src_path.name, ports, generics, signals,
                                        include_schematic, toml_path, interfaces))
    print(f"  → {rst_path}")
