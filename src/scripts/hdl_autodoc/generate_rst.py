#!/usr/bin/env python3
"""
generate_rst.py
---------------
Generates RST scaffolding for all modules, hierarchy-aware when
docs/hierarchy.json is present (written by parse_hierarchy.py),
falling back to flat src/ glob otherwise.

Per-module files under docs/modules/<name>/:
  index.rst    — toctree (always regenerated); includes submodules section if children exist
  entity.rst   — vhdl:autoentity / source listing (write-if-missing)
  fsm.rst      — includes extracted FSM rst (always regenerated)
  timing.rst   — aggregated wavedrom diagrams (always regenerated)
  processes/   — written by extract_processes.py

Top-level:
  docs/index.rst          — always regenerated
  docs/overview.rst       — always regenerated

Usage:
    python scripts/generate_rst.py <src_dir> <docs_dir>
"""

import json
import re
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# VHDL / SV entity extraction (used for flat fallback mode)
# ─────────────────────────────────────────────────────────────────────────────

ENTITY_RE = re.compile(r"\bentity\s+(\w+)\s+is\b", re.IGNORECASE)
MODULE_RE  = re.compile(r"^\s*module\s+(\w+)", re.IGNORECASE | re.MULTILINE)

PORT_RE    = re.compile(
    r"^\s*(\w+)\s*:\s*(in|out|inout)\s+(\w[\w_]*)",
    re.IGNORECASE
)


def extract_entities(src_path: Path) -> list[dict]:
    lines  = src_path.read_text().splitlines()
    is_sv  = src_path.suffix.lower() in (".sv", ".svh")
    pat    = MODULE_RE if is_sv else ENTITY_RE
    prefix = "//" if is_sv else "--"
    sv_port = re.compile(
        r"(input|output|inout)\s+(?:logic|wire|reg)?\s*(?:\[[^\]]*\])?\s*(\w+)",
        re.IGNORECASE
    )
    end_pat = re.compile(r"endmodule|\);", re.IGNORECASE) if is_sv \
              else re.compile(r"\bend\s+entity\b", re.IGNORECASE)

    entities = []
    for i, line in enumerate(lines):
        m = pat.search(line)
        if not m:
            continue
        name = m.group(1)

        # Brief from preceding comments
        brief_lines = []
        j = i - 1
        while j >= 0:
            s = lines[j].strip()
            if s.startswith(prefix):
                text = re.sub(rf"^{re.escape(prefix)}\s?", "", s).strip()
                if text and not re.match(r"^[-=*#/]+$", text):
                    brief_lines.insert(0, text)
            elif s == "":
                j -= 1; continue
            else:
                break
            j -= 1
        brief = " ".join(brief_lines[:2]) if brief_lines else f"{name} entity."

        # Port extraction
        ports = []
        k = i + 1
        while k < len(lines):
            if end_pat.search(lines[k]):
                break
            if is_sv:
                pm = sv_port.search(lines[k])
                if pm:
                    ports.append({"name": pm.group(2), "dir": pm.group(1).lower(),
                                  "type": "logic"})
            else:
                pm = PORT_RE.match(lines[k])
                if pm:
                    ports.append({"name": pm.group(1), "dir": pm.group(2).lower(),
                                  "type": pm.group(3).lower()})
            k += 1

        entities.append({"name": name, "brief": brief,
                         "file": src_path.name, "ports": ports})
    return entities


def scan_src(src_dir: Path) -> list[dict]:
    entities = []
    for path in sorted(src_dir.glob("**/*")):
        if path.suffix.lower() in (".vhd", ".vhdl", ".sv", ".svh"):
            entities.extend(extract_entities(path))
    return entities


# ─────────────────────────────────────────────────────────────────────────────
# Hierarchy loader
# ─────────────────────────────────────────────────────────────────────────────

def load_hierarchy(docs_dir: Path) -> dict | None:
    h_path = docs_dir / "hierarchy.json"
    if not h_path.exists():
        return None
    return json.loads(h_path.read_text())


def entity_from_hierarchy(name: str, hmod: dict) -> dict:
    """Build a minimal entity dict from a hierarchy module entry."""
    src_path = Path(hmod["file"])
    entities = extract_entities(src_path)
    for e in entities:
        if e["name"].lower() == name.lower():
            return e
    # Fallback if name not matched
    return {"name": name, "brief": f"{name} module.",
            "file": src_path.name, "ports": []}


# ─────────────────────────────────────────────────────────────────────────────
# Writers
# ─────────────────────────────────────────────────────────────────────────────

def write_if_missing(path: Path, content: str) -> str:
    if path.exists():
        return f"  (skipped — already exists) {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"  → {path}"


def write_if_missing_or_pristine(path: Path, content: str, pristine) -> str:
    """
    Like write_if_missing, but also upgrades a shell that is byte-identical to
    what an older version generated, so hand-edited files are kept.  `pristine`
    is one string or an iterable of strings (every shape older versions wrote).
    """
    pristines = {pristine} if isinstance(pristine, str) else set(pristine)
    if path.exists() and path.read_text() in pristines and content not in pristines:
        path.write_text(content)
        return f"  → (upgraded unedited shell) {path}"
    return write_if_missing(path, content)


def write_always(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"  → (regenerated) {path}"


# ─────────────────────────────────────────────────────────────────────────────
# Per-module RST generators
# ─────────────────────────────────────────────────────────────────────────────

def module_index_rst(entity: dict, children: list[str],
                     shared_children: set[str],
                     has_processes: bool = True,
                     has_registers: bool = False,
                     has_synthesis: bool = False) -> str:
    """Always-regenerated toctree for one module."""
    name  = entity["name"]
    title = name
    lines = [
        title, "=" * len(title), "",
        ".. toctree::",
        "   :maxdepth: 3",
        "",
        "   entity",
        "   block",
        "   fsm",
        "   timing",
    ]
    if has_processes:
        lines.append("   processes/index")
    lines.append("   cdc")
    lines.append("   reset")
    if has_registers:
        lines.append("   registers")
    if has_synthesis:
        lines.append("   synthesis")
    lines.append("")

    if children:
        lines += [
            "Submodules",
            "----------",
            "",
            ".. toctree::",
            "   :maxdepth: 3",
            "   :caption: Submodules",
            "",
        ]
        for child in sorted(children):
            tag = " *(shared)*" if child in shared_children else ""
            # Reference sibling module dir
            lines.append(f"   ../{child}/index")
            if tag:
                # RST toctree entries can't have inline markup — add note after
                pass
        lines.append("")

        if shared_children & set(children):
            lines += [
                ".. note::",
                "",
                "   Modules marked **shared** are instantiated by multiple parents.",
                "   Their documentation appears once; all parents link to the same page.",
                "",
            ]

    return "\n".join(lines)


def sv_module_description(text: str, name: str) -> str:
    """
    Return the ``//`` comment block directly above ``module <name>`` as RST text.

    sphinx-vhdl does this for VHDL entities; SystemVerilog has no equivalent, so
    read the comment block ourselves.  Bare ``//`` lines become paragraph breaks
    and purely decorative banner lines (``//-----``, ``//=====``) are dropped.
    """
    lines = text.splitlines()
    idx = next((i for i, l in enumerate(lines)
                if re.match(rf"\s*(?:module|macromodule)\s+{re.escape(name)}\b", l)), None)
    if idx is None:
        return ""
    block = []
    i = idx - 1
    while i >= 0 and lines[i].strip().startswith("//"):
        block.append(re.sub(r"^\s*//\s?", "", lines[i]).rstrip())
        i -= 1
    block.reverse()
    block = ["" if not re.search(r"\w", l) else l for l in block]
    return "\n".join(block).strip()


def _entity_head(entity: dict, src_dir: Path = None) -> list[str]:
    """Title, source-file line, and the module description (everything above
    the annotated source)."""
    name  = entity["name"]
    fname = entity["file"]
    is_sv = fname.rsplit(".", 1)[-1].lower() in ("sv", "svh")
    title = f"{name} — Entity"

    lines = [title, "=" * len(title), "", f"Source file: ``src/{fname}``.", ""]

    if not is_sv:
        # sphinx-vhdl only handles VHDL entities
        lines += [f".. vhdl:autoentity:: {name}", ""]
    elif src_dir is not None:
        try:
            desc = sv_module_description(
                (Path(src_dir) / fname).read_text(errors="replace"), name)
        except OSError:
            desc = ""
        if desc:
            lines += [desc, ""]
    return lines


def _annotated_source_section(entity: dict, src_rel_to_docs: str) -> list[str]:
    fname = entity["file"]
    lang  = "systemverilog" if fname.rsplit(".", 1)[-1].lower() in ("sv", "svh") else "vhdl"
    return [
        "Annotated Source",
        "----------------", "",
        f".. literalinclude:: {src_rel_to_docs}/{fname}",
        f"   :language: {lang}",
        "   :linenos:",
        f"   :caption: src/{fname}",
        "",
    ]


def entity_rst(entity: dict, src_rel_to_docs: str = "../../src",
               src_dir: Path = None) -> str:
    """
    Write-once entity page.  The annotated source is pulled in from a separate,
    always-regenerated ``<name>_source.rst`` (see source_rst) so the
    ``ANNOTATED_SOURCE`` switch works on pages that already exist.
    """
    return "\n".join(_entity_head(entity, src_dir)
                     + [f".. include:: {entity['name']}_source.rst", ""])


def source_rst(entity: dict, src_rel_to_docs: str = "../../src",
               enabled: bool = True) -> str:
    """Always-regenerated annotated-source section; just a comment when disabled."""
    if not enabled:
        return ".. Annotated source disabled (ANNOTATED_SOURCE=0).\n"
    return "\n".join(_annotated_source_section(entity, src_rel_to_docs))


def legacy_entity_rsts(entity: dict, src_rel_to_docs: str, src_dir: Path = None) -> set[str]:
    """Every entity.rst shape earlier versions generated (annotated source inline),
    so an unedited one can be upgraded to the include form."""
    section = _annotated_source_section(entity, src_rel_to_docs)
    return {"\n".join(_entity_head(entity, d) + section) for d in (None, src_dir)}


def reset_rst(entity: dict, module_dir: Path = None) -> str:
    name      = entity["name"]
    extracted = module_dir / f"{name}_reset.rst" if module_dir else None
    if extracted and extracted.exists():
        return "\n".join([f".. include:: {name}_reset.rst", ""])
    title = f"{name} — Reset Domain Analysis"
    return "\n".join([
        title, "=" * len(title), "",
        ".. note::", "",
        "   Reset domain analysis pending — run ``make extract`` to generate.", "",
    ])


def block_rst(entity: dict, module_dir: Path = None) -> str:
    name      = entity["name"]
    extracted = module_dir / f"{name}_block.rst" if module_dir else None
    if extracted and extracted.exists():
        return "\n".join([f".. include:: {name}_block.rst", ""])
    title = f"{name} — Block Diagram"
    return "\n".join([
        title, "=" * len(title), "",
        ".. note::", "",
        "   Block diagram pending — run ``make extract`` to generate.", "",
    ])


def cdc_rst(entity: dict, module_dir: Path = None) -> str:
    name        = entity["name"]
    extracted   = module_dir / f"{name}_cdc.rst" if module_dir else None
    if extracted and extracted.exists():
        return "\n".join([f".. include:: {name}_cdc.rst", ""])
    title = f"{name} — Clock Domain Analysis"
    return "\n".join([
        title, "=" * len(title), "",
        ".. note::", "",
        "   CDC analysis pending — run ``make extract`` to generate.", "",
    ])


def fsm_rst(entity: dict, module_dir: Path = None) -> str:
    name = entity["name"]
    # Only include if the extracted FSM rst actually exists
    if module_dir and (module_dir / f"{name}.rst").exists():
        return "\n".join([f".. include:: {name}.rst", ""])
    title = f"{name} — State Machine"
    return "\n".join([
        title, "=" * len(title), "",
        f"No FSM detected in ``{entity['file']}``.", "",
        "This module is either a structural wrapper (no combinational",
        "state logic) or uses a coding style not yet supported by the",
        "FSM extractor.", "",
    ])


def timing_rst(entity: dict, processes_dir: Path = None) -> str:
    name  = entity["name"]
    title = f"{name} — Timing Diagrams"

    lines = [
        title, "=" * len(title), "",
        f"All timing diagrams extracted from ``{entity['file']}``.",
        "Diagrams are sourced from ``.. wavedrom::`` blocks in the VHDL",
        "source comments above each process.",
        "",
    ]

    found_any = False
    if processes_dir and processes_dir.exists():
        for proc_file in sorted(processes_dir.glob("p_*.rst")):
            blocks = extract_wavedrom_blocks(proc_file.read_text())
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
            "No wavedrom diagrams found in process comments.", "",
            "Add ``.. wavedrom::`` blocks in the VHDL source above each",
            "process to have them appear here automatically.", "",
        ]

    return "\n".join(lines)


def extract_wavedrom_blocks(rst_text: str) -> list[list[str]]:
    blocks = []
    lines  = rst_text.splitlines()
    i      = 0
    while i < len(lines):
        if re.match(r"^\.\.\s+wavedrom::\s*$", lines[i]):
            block = [".. wavedrom::", ""]
            i += 1
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            while i < len(lines):
                line = lines[i]
                if line == "" or line.startswith("   "):
                    block.append(line)
                    i += 1
                else:
                    break
            while block and block[-1].strip() == "":
                block.pop()
            block.append("")
            blocks.append(block)
        else:
            i += 1
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Top-level RST generators
# ─────────────────────────────────────────────────────────────────────────────

def hierarchy_dot(hierarchy: dict) -> str:
    """Graphviz dot for the full instantiation tree."""
    top     = hierarchy["top"]
    modules = hierarchy["modules"]
    lines   = [
        "digraph hierarchy {",
        "    rankdir=TB;",
        "    node [shape=box, style=filled, fillcolor=lightblue,",
        "          fontname=Helvetica, fontsize=12];",
        "    edge [fontname=Helvetica, fontsize=10];",
        "",
    ]
    # Mark shared nodes
    for name, mod in modules.items():
        if mod["shared"]:
            lines.append(
                f'    {name} [fillcolor=lightyellow, '
                f'label="{name}\\n(shared)"];'
            )
    lines.append("")
    # Edges
    visited_edges = set()
    for name, mod in modules.items():
        for child in mod["children"]:
            edge = (name, child)
            if edge not in visited_edges:
                lines.append(f"    {name} -> {child};")
                visited_edges.add(edge)
    lines.append("}")
    return "\n".join(lines)


def registers_rst(modules_with_regs: list[str]) -> str:
    """Top-level registers index page listing all modules with register maps."""
    title = "Register Maps"
    lines = [
        title, "=" * len(title), "",
        ".. toctree::",
        "   :maxdepth: 1",
        "",
    ]
    for name in modules_with_regs:
        lines.append(f"   modules/{name}/registers")
    lines.append("")
    return "\n".join(lines)


def index_rst(entities: list[dict], project_name: str,
              hierarchy: dict = None, has_coverage: bool = False,
              modules_with_regs: list[str] | None = None,
              has_synthesis: bool = False) -> str:
    lines = [
        project_name, "=" * len(project_name), "",
        ".. toctree::",
        "   :maxdepth: 4",
        "   :caption: Design",
        "",
        "   overview",
    ]

    if hierarchy:
        top = hierarchy["top"]
        lines += [
            f"   modules/{top}/index",
        ]
        if modules_with_regs:
            lines.append("   registers")
    else:
        for e in entities:
            lines.append(f"   modules/{e['name']}/index")
        if modules_with_regs:
            lines.append("   registers")

    if has_coverage:
        lines.append("   coverage")

    if has_synthesis:
        lines += [
            "",
            ".. toctree::",
            "   :maxdepth: 2",
            "   :caption: Implementation",
            "",
            "   synthesis/index",
        ]

    lines += [
        "",
        "Indices", "-------", "",
        "* :ref:`genindex`",
        "* :ref:`search`",
        "",
    ]
    return "\n".join(lines)


def overview_rst(entities: list[dict], project_name: str,
                 hierarchy: dict = None) -> str:
    """
    Single landing page: summary, instantiation tree (hierarchy.dot), shared
    components, and one module table.  With a hierarchy the table also shows
    each module's parents and children.
    """
    title = f"{project_name} — Overview"
    lines = [
        title, "=" * len(title), "",
        f"This project contains {len(entities)} VHDL/SV "
        f"{'module' if len(entities) == 1 else 'modules'}.",
        "",
    ]

    modules = hierarchy["modules"] if hierarchy else {}

    if hierarchy:
        top = hierarchy["top"]
        lines += [
            f"Top-level module: :doc:`modules/{top}/index`", "",
            "Instantiation Tree", "------------------", "",
            ".. graphviz:: hierarchy.dot", "",
        ]
        shared = [n for n, m in modules.items() if m["shared"]]
        if shared:
            lines += [
                "Shared Components", "-----------------", "",
                "The following modules are instantiated by more than one parent:", "",
            ]
            for name in shared:
                lines.append(f"- ``{name}`` — instantiated by: "
                             + ", ".join(f"``{p}``" for p in modules[name]["parents"]))
            lines.append("")

    header = ["Module", "Source File", "Description"]
    if hierarchy:
        header += ["Instantiated by", "Instantiates"]
    lines += [
        "Modules", "-------", "",
        ".. list-table::", "   :header-rows: 1", "",
        f"   * - {header[0]}",
    ] + [f"     - {h}" for h in header[1:]] + [""]
    for e in entities:
        lines.append(f"   * - :doc:`modules/{e['name']}/index`")
        lines.append(f"     - ``{e['file']}``")
        lines.append(f"     - {e['brief']}")
        if hierarchy and e["name"] in modules:
            mod = modules[e["name"]]
            lines.append("     - " + (", ".join(f"``{p}``" for p in mod["parents"]) or "*(top)*"))
            lines.append("     - " + (", ".join(f"``{c}``" for c in mod["children"]) or "—"))
        elif hierarchy:
            lines += ["     - —", "     - —"]
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    flags   = {a for a in sys.argv[1:] if a.startswith("--")}
    args    = [a for a in sys.argv[1:] if not a.startswith("--")]
    no_source = "--no-source" in flags
    if len(args) < 2:
        sys.exit("Usage: generate_rst.py <src_dir> <docs_dir> [project_name] [--no-source]")

    src_dir  = Path(args[0])
    docs_dir = Path(args[1])

    # Project name — from argument, or derived from parent folder name
    GENERIC_NAMES = {"src", "docs", "files", "hdl", "rtl", "vhdl", "verilog",
                     "source", "sources", "project", "projects", "workspace"}

    if len(args) > 2 and args[2].strip():
        project_name = args[2].strip()
    else:
        candidate = docs_dir.resolve().parent
        for _ in range(4):
            if candidate.name.lower() not in GENERIC_NAMES:
                break
            candidate = candidate.parent
        project_name = candidate.name.replace("_", " ").replace("-", " ").title()

    print(f"Project: {project_name}")

    # Load hierarchy if available
    hierarchy = load_hierarchy(docs_dir)

    if hierarchy:
        print(f"Hierarchy mode: top={hierarchy['top']}, "
              f"{len(hierarchy['modules'])} modules")
        entities = []
        for name, hmod in hierarchy["modules"].items():
            e = entity_from_hierarchy(name, hmod)
            entities.append(e)
    else:
        print("Flat mode: scanning src/")
        entities = scan_src(src_dir)
        if not entities:
            sys.exit(f"ERROR: No VHDL/SV entities found in {src_dir}")

    print(f"Found {len(entities)} entities: {[e['name'] for e in entities]}")
    print("Generating RST files...")

    # Build lookup by name
    entity_map = {e["name"].lower(): e for e in entities}

    # Shared components set
    shared_names = set()
    if hierarchy:
        shared_names = {n for n, m in hierarchy["modules"].items() if m["shared"]}

    results = []
    modules_with_regs: list[str] = []

    for entity in entities:
        name    = entity["name"].lower()
        mod_dir = docs_dir / "modules" / name

        children = []
        if hierarchy and name in hierarchy["modules"]:
            children = hierarchy["modules"][name]["children"]

        # Always regenerated
        has_processes  = (mod_dir / "processes" / "index.rst").exists()
        has_registers  = (mod_dir / "registers.rst").exists()
        has_synthesis  = (mod_dir / "synthesis.rst").exists()
        if has_registers:
            modules_with_regs.append(name)
        results.append(write_always(
            mod_dir / "index.rst",
            module_index_rst(entity, children, shared_names,
                             has_processes=has_processes,
                             has_registers=has_registers,
                             has_synthesis=has_synthesis)
        ))
        results.append(write_always(
            mod_dir / "fsm.rst",
            fsm_rst(entity, module_dir=mod_dir)
        ))
        results.append(write_always(
            mod_dir / "timing.rst",
            timing_rst(entity, processes_dir=mod_dir / "processes")
        ))
        results.append(write_always(
            mod_dir / "cdc.rst",
            cdc_rst(entity, module_dir=mod_dir)
        ))
        results.append(write_always(
            mod_dir / "block.rst",
            block_rst(entity, module_dir=mod_dir)
        ))
        results.append(write_always(
            mod_dir / "reset.rst",
            reset_rst(entity, module_dir=mod_dir)
        ))

        # Write-if-missing
        # literalinclude paths are relative to the RST file itself (mod_dir),
        # not to docs_dir — compute relpath from mod_dir to src_dir.
        import os as _os
        src_rel = _os.path.relpath(src_dir.resolve(), mod_dir.resolve())
        results.append(write_if_missing_or_pristine(
            mod_dir / "entity.rst",
            entity_rst(entity, src_rel_to_docs=src_rel, src_dir=src_dir),
            pristine=legacy_entity_rsts(entity, src_rel, src_dir),
        ))
        # Always regenerated, so ANNOTATED_SOURCE can be toggled at any time.
        results.append(write_always(
            mod_dir / f"{entity['name']}_source.rst",
            source_rst(entity, src_rel_to_docs=src_rel, enabled=not no_source),
        ))

    # Top-level always-regenerated
    has_coverage = (docs_dir / "coverage.rst").exists()
    if modules_with_regs:
        results.append(write_always(
            docs_dir / "registers.rst",
            registers_rst(modules_with_regs)
        ))
    has_synthesis_index = (docs_dir / "synthesis" / "index.rst").exists()
    results.append(write_always(
        docs_dir / "index.rst",
        index_rst(entities, project_name, hierarchy, has_coverage=has_coverage,
                  modules_with_regs=modules_with_regs or None,
                  has_synthesis=has_synthesis_index)
    ))
    results.append(write_always(
        docs_dir / "overview.rst",
        overview_rst(entities, project_name, hierarchy)
    ))

    if hierarchy:
        results.append(write_always(
            docs_dir / "hierarchy.dot",
            hierarchy_dot(hierarchy)
        ))
        # Merged into overview.rst; remove the page older versions generated so
        # Sphinx does not warn about a document missing from the toctree.
        stale = docs_dir / "hierarchy.rst"
        if stale.exists():
            stale.unlink()

    for r in results:
        print(r)