#!/usr/bin/env python3
"""
extract_processes.py
--------------------
Parses a VHDL source file and writes one RST file per labeled process
into an output directory, plus a processes/index.rst toctree page.

Supports extraction of:
  - Process label, sensitivity list, source line
  - Preceding block comments (plain text)
  - WaveDrom diagrams embedded in comments above the process
  - Signal assignment tables from case/when blocks
  - Raw VHDL source for the process body

Usage:
    python scripts/extract_processes.py <file.vhd> <output_dir>
"""

import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load(path: Path) -> list[str]:
    return path.read_text().splitlines()


def is_separator(text: str) -> bool:
    return bool(re.match(r"^[-=*#\s]*$", text))


def strip_comment_prefix(raw: str) -> str | None:
    """Strip leading -- from a VHDL comment line. Returns None if not a comment."""
    stripped = raw.strip()
    if not stripped.startswith("--"):
        return None
    return re.sub(r"^--\s?", "", stripped)


# ─────────────────────────────────────────────────────────────────────────────
# Comment block extraction — returns structured tokens
# ─────────────────────────────────────────────────────────────────────────────
# Each token is one of:
#   {"type": "text",     "lines": [...]}
#   {"type": "wavedrom", "lines": [...]}   ← wavedrom JSON body lines

def extract_comment_tokens(lines: list[str], end_idx: int) -> list[dict]:
    """
    Walk backwards from end_idx collecting contiguous -- comment lines,
    then parse them into structured tokens (text blocks and wavedrom blocks).
    """
    raw_comments = []
    i = end_idx - 1
    while i >= 0:
        stripped = lines[i].strip()
        if stripped.startswith("--"):
            text = strip_comment_prefix(stripped)
            if text is not None:
                raw_comments.insert(0, text)
        elif stripped == "":
            i -= 1
            continue
        else:
            break
        i -= 1

    # Now parse raw_comments into tokens
    tokens      = []
    text_buf    = []
    wave_buf    = None   # None = not in wavedrom block
    wave_indent = 0

    def flush_text():
        # Drop separator-only lines; keep the rest
        cleaned = [l for l in text_buf if not is_separator(l)]
        # Trim leading/trailing blanks
        while cleaned and cleaned[0].strip() == "":
            cleaned.pop(0)
        while cleaned and cleaned[-1].strip() == "":
            cleaned.pop()
        if cleaned:
            tokens.append({"type": "text", "lines": cleaned})
        text_buf.clear()

    for line in raw_comments:
        # Detect start of a wavedrom block: ".. wavedrom::"
        if re.match(r"^\s*\.\.\s+wavedrom\s*::\s*$", line):
            flush_text()
            wave_buf    = []
            wave_indent = len(line) - len(line.lstrip())
            continue

        if wave_buf is not None:
            # Empty line inside wavedrom block — keep it
            if line.strip() == "":
                wave_buf.append("")
                continue
            # Indented line — part of the wavedrom JSON body
            if line != line.lstrip():
                # Strip the common indentation
                wave_buf.append(line.strip())
                continue
            # Non-indented, non-empty line — wavedrom block ended
            tokens.append({"type": "wavedrom", "lines": wave_buf})
            wave_buf = None
            text_buf.append(line)
            continue

        text_buf.append(line)

    # Flush anything remaining
    if wave_buf is not None:
        tokens.append({"type": "wavedrom", "lines": wave_buf})
    else:
        flush_text()

    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# Process extraction
# ─────────────────────────────────────────────────────────────────────────────

PROCESS_RE = re.compile(r"^\s*(\w+)\s*:\s*process\s*\((.*?)\)", re.IGNORECASE)


def find_processes(lines: list[str]) -> list[dict]:
    processes = []
    i = 0
    while i < len(lines):
        m = PROCESS_RE.match(lines[i])
        if m:
            label       = m.group(1).strip()
            sensitivity = [s.strip() for s in m.group(2).split(",")]
            tokens      = extract_comment_tokens(lines, i)
            body        = []
            j           = i + 1
            while j < len(lines):
                body.append(lines[j])
                if re.search(r"\bend\s+process\b", lines[j], re.IGNORECASE):
                    break
                j += 1
            processes.append({
                "label":       label,
                "sensitivity": sensitivity,
                "tokens":      tokens,
                "body":        body,
                "line":        i + 1,
            })
            i = j + 1
        else:
            i += 1
    return processes


# ─────────────────────────────────────────────────────────────────────────────
# Assignment table extraction
# ─────────────────────────────────────────────────────────────────────────────

ASSIGN_RE = re.compile(r"(\w+)\s*<=\s*([^;]+);")
WHEN_RE   = re.compile(r"^\s*when\s+(\w+)\s*=>", re.IGNORECASE)


def extract_assignments(body: list[str]) -> dict[str, list[tuple[str, str]]]:
    result, current = {}, None
    for line in body:
        wm = WHEN_RE.match(line)
        if wm:
            current = wm.group(1).upper()
            result.setdefault(current, [])
            continue
        am = ASSIGN_RE.search(line)
        if am and current:
            sig = am.group(1).strip()
            val = am.group(2).strip().strip("'\" ")
            result[current].append((sig, val))
    return result


# ─────────────────────────────────────────────────────────────────────────────
# RST text block renderer (handles indented lines and colon escaping)
# ─────────────────────────────────────────────────────────────────────────────

def render_text_block(comment_lines: list[str]) -> list[str]:
    out      = []
    code_buf = []
    first    = True

    def flush_code():
        if not code_buf:
            return
        out.append(".. code-block:: none")
        out.append("")
        for cl in code_buf:
            out.append("   " + cl)
        out.append("")
        code_buf.clear()

    for raw in comment_lines:
        if raw == "":
            flush_code()
            out.append("")
            continue
        if raw != raw.lstrip():
            code_buf.append(raw)
            continue
        flush_code()
        line = raw
        if first and re.match(r"^\w[\w\s]*:", line):
            line = re.sub(r":", r"\:", line, count=1)
        first = False
        out.append(line)

    flush_code()
    return out


# ─────────────────────────────────────────────────────────────────────────────
# RST wavedrom block renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_wavedrom_block(json_lines: list[str]) -> list[str]:
    out = []
    out.append(".. wavedrom::")
    out.append("")
    for line in json_lines:
        if line.strip():
            out.append("   " + line)
        else:
            out.append("")
    out.append("")
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Per-process RST page renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_process_page(proc: dict, vhd_filename: str) -> str:
    label = proc["label"]
    sens  = ", ".join(f"``{s}``" for s in proc["sensitivity"])
    title = label
    under = "=" * len(title)

    out = []
    out.append(title)
    out.append(under)
    out.append("")
    out.append(f"| **Source file:** ``{vhd_filename}``")
    out.append(f"| **Source line:** {proc['line']}")
    out.append(f"| **Sensitivity list:** {sens}")
    out.append("")

    # Description + wavedrom blocks from tokens
    has_wavedrom = any(t["type"] == "wavedrom" for t in proc["tokens"])
    has_text     = any(t["type"] == "text"     for t in proc["tokens"])

    if has_text or has_wavedrom:
        out.append("Description")
        out.append("-----------")
        out.append("")
        for token in proc["tokens"]:
            if token["type"] == "text":
                out.extend(render_text_block(token["lines"]))
                out.append("")
            elif token["type"] == "wavedrom":
                out.extend(render_wavedrom_block(token["lines"]))

    # Signal assignment table
    assignments = extract_assignments(proc["body"])
    if assignments:
        all_sigs = []
        for assigns in assignments.values():
            for sig, _ in assigns:
                if sig not in all_sigs:
                    all_sigs.append(sig)
        if all_sigs:
            out.append("Signal Assignments")
            out.append("------------------")
            out.append("")
            out.append(".. list-table::")
            out.append("   :header-rows: 1")
            out.append("")
            out.append("   * - State")
            for sig in all_sigs:
                out.append(f"     - ``{sig}``")
            out.append("")
            for state, assigns in assignments.items():
                assign_map = dict(assigns)
                out.append(f"   * - ``{state}``")
                for sig in all_sigs:
                    val = assign_map.get(sig, "—")
                    out.append(f"     - {val}")
                out.append("")
            out.append("")

    # Raw VHDL source for this process
    out.append("Source")
    out.append("------")
    out.append("")
    out.append(".. code-block:: vhdl")
    out.append("")
    for line in proc["body"]:
        out.append("   " + line.rstrip())
    out.append("")

    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# Index page renderer
# ─────────────────────────────────────────────────────────────────────────────

def render_index_page(processes: list[dict], vhd_filename: str) -> str:
    out = []
    out.append("Processes")
    out.append("=========")
    out.append("")
    out.append(f"Auto-extracted from ``{vhd_filename}``.")
    out.append("")
    out.append(".. toctree::")
    out.append("   :maxdepth: 1")
    out.append("")
    for proc in processes:
        out.append(f"   {proc['label']}")
    out.append("")
    out.append("Summary")
    out.append("-------")
    out.append("")
    out.append(".. list-table::")
    out.append("   :header-rows: 1")
    out.append("")
    out.append("   * - Process")
    out.append("     - Type")
    out.append("     - Sensitivity List")
    out.append("     - Source Line")
    out.append("     - WaveDrom")
    out.append("")
    for proc in processes:
        label     = proc["label"]
        sens      = ", ".join(f"``{s}``" for s in proc["sensitivity"])
        ptype     = "Clocked" if "clk" in proc["sensitivity"] else "Combinational"
        has_wave  = "✔" if any(t["type"] == "wavedrom" for t in proc["tokens"]) else "—"
        out.append(f"   * - :doc:`{label}`")
        out.append(f"     - {ptype}")
        out.append(f"     - {sens}")
        out.append(f"     - {proc['line']}")
        out.append(f"     - {has_wave}")
        out.append("")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: extract_processes.py <file.vhd> <output_dir>")

    vhd_path   = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)

    lines     = load(vhd_path)
    processes = find_processes(lines)

    if not processes:
        sys.exit(f"ERROR: No labeled processes found in {vhd_path}")

    for proc in processes:
        page    = render_process_page(proc, vhd_path.name)
        outfile = output_dir / f"{proc['label']}.rst"
        outfile.write_text(page)
        print(f"  → {outfile}")

    index_page = render_index_page(processes, vhd_path.name)
    index_file = output_dir / "index.rst"
    index_file.write_text(index_page)
    print(f"  → {index_file}")