#!/usr/bin/env python3
"""
generate_rst.py
---------------
Scans src/ for VHDL entities and writes the RST scaffold under docs/modules/<entity>/.

Structure per module:
  docs/modules/<name>/index.rst        — module toctree (always regenerated)
  docs/modules/<name>/entity.rst       — vhdl:autoentity + literalinclude (write-if-missing)
  docs/modules/<name>/fsm.rst          — includes extracted FSM rst (always regenerated)
  docs/modules/<name>/timing.rst       — wavedrom timing page (write-if-missing)
  docs/modules/<name>/processes/       — written by extract_processes.py

Top-level:
  docs/index.rst                       — top-level toctree (always regenerated)
  docs/overview.rst                    — project overview table (always regenerated)

Usage:
    python scripts/generate_rst.py <src_dir> <docs_dir> [project_name]
"""

import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# VHDL entity extraction
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_RE = re.compile(r"\bentity\s+(\w+)\s+is\b", re.IGNORECASE)


PORT_RE = re.compile(
    r"^\s*(\w+)\s*:\s*(in|out|inout)\s+(\w[\w_]*)",
    re.IGNORECASE
)


def extract_entities(vhd_path: Path) -> list[dict]:
    lines    = vhd_path.read_text().splitlines()
    entities = []
    for i, line in enumerate(lines):
        m = ENTITY_RE.search(line)
        if not m:
            continue
        name        = m.group(1)
        brief_lines = []
        j = i - 1
        while j >= 0:
            stripped = lines[j].strip()
            if stripped.startswith("--"):
                text = re.sub(r"^--\s?", "", stripped).strip()
                if text and not re.match(r"^[-=*#]+$", text):
                    brief_lines.insert(0, text)
            elif stripped == "":
                j -= 1
                continue
            else:
                break
            j -= 1
        brief = " ".join(brief_lines[:2]) if brief_lines else f"{name} entity."

        # Extract ports from the entity body up to 'end entity'
        ports = []
        k = i + 1
        while k < len(lines):
            if re.search(r"\bend\s+entity\b", lines[k], re.IGNORECASE):
                break
            pm = PORT_RE.match(lines[k])
            if pm:
                pname      = pm.group(1)
                pdirection = pm.group(2).lower()
                ptype      = pm.group(3).lower()
                ports.append({"name": pname, "dir": pdirection, "type": ptype})
            k += 1

        entities.append({
            "name":  name,
            "brief": brief,
            "file":  vhd_path.name,
            "ports": ports,
        })
    return entities


def scan_src(src_dir: Path) -> list[dict]:
    entities = []
    for vhd in sorted(src_dir.glob("**/*.vhd")):
        entities.extend(extract_entities(vhd))
    return entities


# ─────────────────────────────────────────────────────────────────────────────
# Writers
# ─────────────────────────────────────────────────────────────────────────────

def write_if_missing(path: Path, content: str) -> str:
    if path.exists():
        return f"  (skipped — already exists) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"  → {path}"


def write_always(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"  → (regenerated) {path}"


# ─────────────────────────────────────────────────────────────────────────────
# Per-module RST generators
# ─────────────────────────────────────────────────────────────────────────────

def module_index_rst(entity: dict) -> str:
    """Always-regenerated toctree for one module."""
    name  = entity["name"]
    title = f"{name}"
    return "\n".join([
        title,
        "=" * len(title),
        "",
        f".. toctree::",
        "   :maxdepth: 2",
        "",
        "   entity",
        "   fsm",
        "   timing",
        "   processes/index",
        "",
    ])


def entity_rst(entity: dict) -> str:
    """Write-if-missing: vhdl:autoentity + literalinclude."""
    name  = entity["name"]
    title = f"{name} — Entity"
    return "\n".join([
        title,
        "=" * len(title),
        "",
        f"Auto-documented from ``src/{entity['file']}``.",
        "",
        f".. vhdl:autoentity:: {name}",
        "",
        "Annotated Source",
        "----------------",
        "",
        f".. literalinclude:: ../../../src/{entity['file']}",
        "   :language: vhdl",
        "   :linenos:",
        f"   :caption: src/{entity['file']}",
        "",
    ])


def fsm_rst(entity: dict) -> str:
    """Always-regenerated: includes the extracted FSM rst (co-located in module dir)."""
    name = entity["name"]
    return "\n".join([
        f".. include:: {name}.rst",
        "",
    ])


def extract_wavedrom_blocks(rst_text: str) -> list[list[str]]:
    """
    Parse an RST file and return a list of wavedrom blocks.
    Each block is a list of lines: the directive line, blank line, and indented JSON.
    """
    blocks  = []
    lines   = rst_text.splitlines()
    i       = 0
    while i < len(lines):
        if re.match(r"^\.\.\s+wavedrom::\s*$", lines[i]):
            block = [".. wavedrom::", ""]
            i += 1
            # Skip extra blank lines immediately after directive
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            while i < len(lines):
                line = lines[i]
                if line == "" or line.startswith("   "):
                    block.append(line)
                    i += 1
                else:
                    break
            # Trim trailing blank lines
            while block and block[-1].strip() == "":
                block.pop()
            block.append("")
            blocks.append(block)
        else:
            i += 1
    return blocks


def timing_rst(entity: dict, processes_dir: Path = None) -> str:
    """Always-regenerated: aggregates all wavedrom blocks from process RST files."""
    name  = entity["name"]
    title = f"{name} — Timing Diagrams"

    lines = [
        title,
        "=" * len(title),
        "",
        f"All timing diagrams extracted from ``{entity['file']}``.",
        "Diagrams are sourced from ``.. wavedrom::`` blocks in the VHDL",
        "source comments above each process.",
        "",
    ]

    found_any = False

    if processes_dir and processes_dir.exists():
        for proc_file in sorted(processes_dir.glob("p_*.rst")):
            rst_text = proc_file.read_text()
            blocks   = extract_wavedrom_blocks(rst_text)
            if not blocks:
                continue

            proc_name = proc_file.stem
            heading   = proc_name.replace("_", " ").title()
            lines += [heading, "-" * len(heading), ""]

            for block in blocks:
                lines.extend(block)

            found_any = True

    if not found_any:
        lines += [
            "No wavedrom diagrams found in process comments.",
            "",
            "Add ``.. wavedrom::`` blocks in the VHDL source above each",
            "process to have them appear here automatically.",
            "",
        ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Top-level RST generators
# ─────────────────────────────────────────────────────────────────────────────

def index_rst(entities: list[dict], project_name: str) -> str:
    lines = [
        project_name,
        "=" * len(project_name),
        "",
        ".. toctree::",
        "   :maxdepth: 2",
        "   :caption: Contents",
        "",
        "   overview",
    ]
    for e in entities:
        lines.append(f"   modules/{e['name']}/index")
    lines += [
        "",
        "Indices",
        "-------",
        "",
        "* :ref:`genindex`",
        "* :ref:`search`",
        "",
    ]
    return "\n".join(lines)


def overview_rst(entities: list[dict], project_name: str) -> str:
    title = f"{project_name} — Overview"
    lines = [
        title,
        "=" * len(title),
        "",
        f"This project contains {len(entities)} VHDL "
        f"{'entity' if len(entities) == 1 else 'entities'}.",
        "",
        "Modules",
        "-------",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Entity",
        "     - Source File",
        "     - Description",
        "",
    ]
    for e in entities:
        lines.append(f"   * - :doc:`modules/{e['name']}/index`")
        lines.append(f"     - ``{e['file']}``")
        lines.append(f"     - {e['brief']}")
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: generate_rst.py <src_dir> <docs_dir> [project_name]")

    src_dir      = Path(sys.argv[1])
    docs_dir     = Path(sys.argv[2])
    project_name = sys.argv[3] if len(sys.argv) > 3 else "HDL Project"

    entities = scan_src(src_dir)
    if not entities:
        sys.exit(f"ERROR: No VHDL entities found in {src_dir}")

    print(f"Found {len(entities)} entities: {[e['name'] for e in entities]}")
    print("Generating RST files...")

    results = []

    for entity in entities:
        name    = entity["name"]
        mod_dir = docs_dir / "modules" / name

        # Always regenerated — derived purely from entity structure
        results.append(write_always(
            mod_dir / "index.rst",
            module_index_rst(entity)
        ))
        results.append(write_always(
            mod_dir / "fsm.rst",
            fsm_rst(entity)
        ))

        # Write-if-missing — entity.rst may contain hand edits
        results.append(write_if_missing(
            mod_dir / "entity.rst",
            entity_rst(entity)
        ))
        # Always regenerated — aggregates wavedrom diagrams from process pages
        results.append(write_always(
            mod_dir / "timing.rst",
            timing_rst(entity, processes_dir=mod_dir / "processes")
        ))

    # Top-level always-regenerated
    results.append(write_always(docs_dir / "index.rst",    index_rst(entities, project_name)))
    results.append(write_always(docs_dir / "overview.rst", overview_rst(entities, project_name)))

    for r in results:
        print(r)