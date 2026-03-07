#!/usr/bin/env python3
"""
extract_fsm.py
--------------
Parses a VHDL source file, extracts the FSM next-state case block,
and writes two files into the output directory:

  <module>.dot  — Graphviz dot source for the state diagram
  <module>.rst  — Full RST page: diagram + state output table

Usage:
    python scripts/extract_fsm.py <file.vhd> <module_name> <output_dir>

Example:
    python scripts/extract_fsm.py src/traffic_light.vhd traffic_light docs/fsm
"""

import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# State colour palette
# ─────────────────────────────────────────────────────────────────────────────

STATE_COLOURS = {
    "red":       "salmon",
    "red_amber": "lightyellow",
    "green":     "lightgreen",
    "amber":     "orange",
}
DEFAULT_COLOUR = "lightblue"


# ─────────────────────────────────────────────────────────────────────────────
# VHDL parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

def strip_comments(text: str) -> str:
    return re.sub(r"--[^\n]*", "", text)


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Transition extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_transitions(vhd_text: str) -> list[tuple[str, str, str]]:
    """Returns [(from_state, to_state, condition), ...]."""
    text = strip_comments(vhd_text)
    norm = normalise(text)

    case_match = re.search(
        r"case\s+\w+\s+is\s+(.*?)\s+end\s+case", norm, re.DOTALL
    )
    if not case_match:
        sys.exit("ERROR: No 'case state is ... end case' block found.")

    case_body   = case_match.group(1)
    clauses     = re.split(r"\bwhen\b", case_body)
    transitions = []

    for clause in clauses:
        clause = clause.strip()
        if not clause or clause.startswith("others"):
            continue

        state_match = re.match(r"(\w+)\s*=>", clause)
        if not state_match:
            continue
        from_state = state_match.group(1).upper()

        for m in re.finditer(
            r"if\s+([\w\s=/']+?)\s+then\s+next_state\s*<=\s*(\w+)", clause
        ):
            condition  = m.group(1).strip()
            to_state   = m.group(2).strip().upper()
            transitions.append((from_state, to_state, condition))

        body_after_arrow = re.sub(r"if\b.*?end\s+if", "", clause, flags=re.DOTALL)
        for m in re.finditer(r"next_state\s*<=\s*(\w+)", body_after_arrow):
            to_state = m.group(1).strip().upper()
            if to_state != from_state:
                transitions.append((from_state, to_state, ""))

    return transitions


def collect_states(transitions: list) -> list[str]:
    states = []
    for frm, to, _ in transitions:
        for s in (frm, to):
            if s not in states:
                states.append(s)
    return states


# ─────────────────────────────────────────────────────────────────────────────
# Output extraction (Moore outputs per state)
# ─────────────────────────────────────────────────────────────────────────────

ASSIGN_RE = re.compile(r"(\w+)\s*<=\s*'([01])'")
WHEN_RE   = re.compile(r"^\s*when\s+(\w+)\s*=>", re.IGNORECASE)


def extract_outputs(vhd_text: str) -> dict[str, dict[str, str]]:
    """
    Returns {state: {signal: value}} from the output decode process.
    Finds the process whose body contains output signal assignments in
    a case/when block but no next_state assignments.
    """
    # Find all process bodies
    processes = re.findall(
        r":\s*process\b.*?end\s+process", vhd_text, re.IGNORECASE | re.DOTALL
    )

    for proc in processes:
        if "next_state" in proc.lower():
            continue  # skip next-state process

        # Collect default assignments (before case)
        defaults = {}
        case_start = re.search(r"\bcase\b", proc, re.IGNORECASE)
        if case_start:
            pre = proc[:case_start.start()]
            for m in ASSIGN_RE.finditer(pre):
                defaults[m.group(1)] = m.group(2)

        if not defaults:
            continue  # not an output process

        # Walk case/when to build per-state assignments
        state_outputs: dict[str, dict[str, str]] = {}
        current = None
        for line in proc.splitlines():
            wm = WHEN_RE.match(line)
            if wm:
                current = wm.group(1).upper()
                state_outputs[current] = dict(defaults)
                # Capture assignments on the same line as 'when X =>'
                for m in ASSIGN_RE.finditer(line[wm.end():]):
                    state_outputs[current][m.group(1)] = m.group(2)
                continue
            if current:
                for m in ASSIGN_RE.finditer(line):
                    state_outputs[current][m.group(1)] = m.group(2)

        if state_outputs:
            return state_outputs

    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Dot file writer
# ─────────────────────────────────────────────────────────────────────────────

def write_dot(transitions: list, states: list, module_name: str) -> str:
    lines = []
    lines.append(f"digraph {module_name} {{")
    lines.append("    rankdir=LR;")
    lines.append("    node [shape=circle, style=filled, fontname=Helvetica, fontsize=12];")
    lines.append("    edge [fontname=Helvetica, fontsize=10];")
    lines.append("")
    lines.append("    __start [shape=point, width=0.2, fillcolor=black];")
    lines.append("")

    for s in states:
        colour = STATE_COLOURS.get(s.lower(), DEFAULT_COLOUR)
        lines.append(f"    {s} [fillcolor={colour}];")

    lines.append("")
    if states:
        lines.append(f"    __start -> {states[0]} [label=\"reset\"];")
    lines.append("")

    for frm, to, cond in transitions:
        label = cond if cond else "always"
        lines.append(f"    {frm} -> {to} [label=\"{label}\"];")

    lines.append("}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# RST page writer
# ─────────────────────────────────────────────────────────────────────────────

def write_rst(dot_filename: str, states: list, outputs: dict,
              transitions: list, module_name: str, vhd_filename: str) -> str:
    out = []
    title = f"{module_name} State Machine"
    out.append(title)
    out.append("=" * len(title))
    out.append("")
    out.append(f"Auto-extracted from ``{vhd_filename}``.")
    out.append("")

    # State diagram — reference the extracted dot file directly
    out.append("State Transition Diagram")
    out.append("------------------------")
    out.append("")
    out.append(f".. graphviz:: {dot_filename}")
    out.append("")

    # State output table — built from extracted outputs
    if outputs:
        all_sigs = []
        for sig_map in outputs.values():
            for sig in sig_map:
                if sig not in all_sigs:
                    all_sigs.append(sig)

        out.append("State Output Table")
        out.append("------------------")
        out.append("")
        out.append(".. list-table::")
        out.append("   :header-rows: 1")
        out.append("")
        out.append("   * - State")
        for sig in all_sigs:
            out.append(f"     - ``{sig}``")
        out.append("")

        for state in states:
            sig_map = outputs.get(state, {})
            out.append(f"   * - ``{state}``")
            for sig in all_sigs:
                out.append(f"     - {sig_map.get(sig, '—')}")
            out.append("")
        out.append("")

    # Transition table
    out.append("Transitions")
    out.append("-----------")
    out.append("")
    out.append(".. list-table::")
    out.append("   :header-rows: 1")
    out.append("")
    out.append("   * - From")
    out.append("     - To")
    out.append("     - Condition")
    out.append("")
    for frm, to, cond in transitions:
        out.append(f"   * - ``{frm}``")
        out.append(f"     - ``{to}``")
        out.append(f"     - ``{cond}``" if cond else "     - (always)")
        out.append("")

    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Usage: extract_fsm.py <file.vhd> <module_name> <output_dir>")

    vhd_path    = Path(sys.argv[1])
    module_name = sys.argv[2]
    output_dir  = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    vhd_text    = vhd_path.read_text()
    transitions = extract_transitions(vhd_text)
    states      = collect_states(transitions)
    outputs     = extract_outputs(vhd_text)

    if not transitions:
        sys.exit("ERROR: No transitions found.")

    # Write dot file
    dot_content  = write_dot(transitions, states, module_name)
    dot_filename = f"{module_name}.dot"
    dot_path     = output_dir / dot_filename
    dot_path.write_text(dot_content)
    print(f"  → {dot_path}")

    # Write RST page
    rst_content = write_rst(dot_filename, states, outputs,
                            transitions, module_name, vhd_path.name)
    rst_path    = output_dir / f"{module_name}.rst"
    rst_path.write_text(rst_content)
    print(f"  → {rst_path}")