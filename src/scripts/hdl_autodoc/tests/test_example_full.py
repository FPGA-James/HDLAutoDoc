"""
example_full must demonstrate every feature of the tool.

One test per row of the feature-coverage matrix in
docs/superpowers/specs/2026-10-31-mermaid-and-showcase-example-design.md.  Modules
are discovered by parsing, never named here, so the example's design can change
without touching this file.

If mixed-language synthesis proves unworkable the example is pure SystemVerilog
(no .vhd files); the rows that need VHDL are then skipped, for this example only.
"""

import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest

from detect_buses import group_ports
from extract_block import (
    extract_generics_vhdl,
    extract_interface_instances_sv,
    extract_params_sv,
    extract_ports_sv,
    extract_ports_vhdl,
)
from extract_processes import find_processes_sv, find_processes_vhdl
from generate_rst import extract_entities
from parse_build_info import parse_device_utilisation
from parse_hierarchy import build_hierarchy
from parse_testbenches import discover_testbenches
from parse_timing import parse_timing
from parse_utilization import parse_utilization
from sv_interfaces import collect_interfaces

EX = Path(__file__).parents[4] / "example_full"
SCRIPTS = Path(__file__).parents[1]
HDL_SUFFIXES = {".vhd", ".vhdl", ".sv", ".v", ".svh"}


@dataclass
class Project:
    hierarchy: dict
    files: dict[str, Path]            # module -> source file
    support: list[Path]
    pure_sv: bool
    extractions: dict[str, dict[str, str]]   # module -> {"fsm": rst, "cdc": rst, "reset": rst}

    def text(self, module: str) -> str:
        return self.files[module].read_text()

    def is_vhdl(self, module: str) -> bool:
        return self.files[module].suffix.lower() in (".vhd", ".vhdl")

    def vhdl_modules(self):
        return [m for m in self.files if self.is_vhdl(m)]

    def sv_modules(self):
        return [m for m in self.files if not self.is_vhdl(m)]


def _extract(script: str, source: Path, module: str, out: Path) -> None:
    subprocess.run([sys.executable, str(SCRIPTS / script), str(source), module, str(out)],
                   capture_output=True, text=True, check=True)


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    assert EX.is_dir(), "example_full/ does not exist yet"
    listed = [EX / l.strip() for l in (EX / "filelist.f").read_text().splitlines()
              if l.strip() and not l.strip().startswith("#")]
    hierarchy = build_hierarchy(listed)
    files = {name: Path(m["file"]) for name, m in hierarchy["modules"].items()}
    extractions = {}
    for name, source in files.items():
        out = tmp_path_factory.mktemp(name)
        for script in ("extract_fsm.py", "extract_cdc.py", "extract_reset.py"):
            _extract(script, source, name, out)
        read = lambda f: (out / f).read_text() if (out / f).exists() else ""
        extractions[name] = {"fsm": read(f"{name}.rst"), "cdc": read(f"{name}_cdc.rst"),
                             "reset": read(f"{name}_reset.rst")}
    pure_sv = not any(p.suffix.lower() in (".vhd", ".vhdl") for p in files.values())
    return Project(hierarchy, files, [Path(p) for p in hierarchy["support_files"]],
                   pure_sv, extractions)


def need_vhdl(project):
    if project.pure_sv:
        pytest.skip("pure-SystemVerilog example: VHDL rows are waived")


def mermaid_blocks(text: str) -> list[str]:
    """First diagram line of every `.. mermaid::` block in the comments of `text`.

    The block is the indented lines that follow the directive; the first line that is not
    indented ends it (an empty block yields "")."""
    blocks = []
    lines = [re.sub(r"^\s*(--|//)\s?", "", l) for l in text.splitlines() if re.match(r"^\s*(--|//)", l)]
    for i, line in enumerate(lines):
        if re.match(r"^\.\.\s+mermaid::\s*$", line):
            body = []
            for l in lines[i + 1:]:
                if l.strip() and not l[:1].isspace():
                    break
                body.append(l)
            body = [l.strip() for l in body if l.strip() and not l.strip().startswith(":")]
            blocks.append(body[0] if body else "")
    return blocks


# ── Hierarchy ────────────────────────────────────────────────────────────────

def test_hierarchy_has_three_levels_and_a_module_with_two_parents(project):
    mods = project.hierarchy["modules"]

    def depth(name):
        return 1 + max((depth(c) for c in mods[name]["children"]), default=0)

    assert depth(project.hierarchy["top"]) >= 3
    assert any(len(m["parents"]) >= 2 for m in mods.values()), "no shared component"


def test_the_design_mixes_vhdl_and_systemverilog(project):
    # Not waived by need_vhdl: this example is mixed-language, and losing a language fails.
    assert project.vhdl_modules() and project.sv_modules()


# ── SystemVerilog packages and interfaces ────────────────────────────────────

def test_support_files_include_a_package_and_two_interfaces(project):
    assert project.support, "no module-less SystemVerilog files"
    assert any(re.search(r"^\s*package\s+\w+", p.read_text(), re.M) for p in project.support)
    assert len(collect_interfaces(project.support)) >= 2


def test_interface_ports_and_an_internal_interface_instance_exist(project):
    names = set(collect_interfaces(project.support))
    ports = [p for m in project.sv_modules()
             for p in extract_ports_sv(project.text(m), names) if p.get("kind") == "interface"]
    assert ports, "no interface-typed ports"
    assert any(extract_interface_instances_sv(project.text(m), names) for m in project.sv_modules())


# ── Generics, parameters, headers ────────────────────────────────────────────

def test_vhdl_generics_with_defaults(project):
    need_vhdl(project)
    assert any(g["default"] for m in project.vhdl_modules()
               for g in extract_generics_vhdl(project.text(m)))


def test_systemverilog_parameters_with_defaults(project):
    assert any(g["default"] for m in project.sv_modules() for g in extract_params_sv(project.text(m)))


def test_every_module_has_a_header_description(project):
    for name, source in project.files.items():
        brief = next(e["brief"] for e in extract_entities(source) if e["name"].lower() == name)
        assert brief != f"{name} entity.", f"{name} has no header comment"


# ── FSMs, processes, waveforms ───────────────────────────────────────────────

def test_fsm_diagrams_in_vhdl_and_in_systemverilog(project):
    has_fsm = lambda m: "State Machine" in project.extractions[m]["fsm"]
    sv = [m for m in project.sv_modules() if has_fsm(m)]
    if project.pure_sv:
        assert len(sv) >= 2, "pure-SV example needs two SystemVerilog FSMs"
    else:
        assert [m for m in project.vhdl_modules() if has_fsm(m)], "no VHDL FSM"
        assert sv, "no SystemVerilog FSM"


def _tokens(project, module):
    text = project.text(module).splitlines()
    finder = find_processes_vhdl if project.is_vhdl(module) else find_processes_sv
    return [t["type"] for p in finder(text) for t in p["tokens"]]


def test_processes_with_wavedrom_waveforms(project):
    assert any("wavedrom" in _tokens(project, m) for m in project.files)


def test_a_process_comment_carries_a_mermaid_diagram(project):
    assert any("mermaid" in _tokens(project, m) for m in project.files)


# ── Mermaid ──────────────────────────────────────────────────────────────────

def test_header_mermaid_diagrams_in_systemverilog_and_vhdl(project):
    def in_header(module):
        text = project.text(module)
        marker = "--" if project.is_vhdl(module) else "//"
        head = re.split(r"^\s*(?:entity|module)\s+\w+", text, maxsplit=1, flags=re.M | re.I)[0]
        return re.search(rf"^\s*{re.escape(marker)}\s+\.\.\s+mermaid::", head, re.M) is not None

    assert any(in_header(m) for m in project.sv_modules()), "no SV header diagram"
    if not project.pure_sv:
        assert any(in_header(m) for m in project.vhdl_modules()), "no VHDL header diagram"


def test_mermaid_diagrams_include_a_sequence_a_state_and_a_flow(project):
    first = [b for m in project.files for b in mermaid_blocks(project.text(m))]
    assert len(first) >= 3
    assert any(b.startswith("sequenceDiagram") for b in first)
    assert any(b.startswith("stateDiagram") for b in first)
    assert any(b.startswith(("flowchart", "graph")) for b in first)


# ── CDC and resets ───────────────────────────────────────────────────────────

def test_cdc_analysis_finds_domains_a_synchroniser_and_a_dual_clock_structure(project):
    cdc = [e["cdc"] for e in project.extractions.values()]
    assert any("Clock Domains" in t for t in cdc), "no multi-clock module"
    assert any("Yes *(two-flop)*" in t for t in cdc), "no detected synchroniser"
    assert any("Dual-Clock Instances" in t for t in cdc), "no async FIFO / dual-clock instance"


def test_reset_analysis_finds_more_than_one_reset_domain_and_both_reset_styles(project):
    resets = [e["reset"] for e in project.extractions.values()]
    assert any("Reset Domains" in t for t in resets)
    assert any("- Async" in t for t in resets), "no asynchronous reset"
    assert any("- Sync" in t for t in resets), "no synchronous reset"
    need_vhdl(project)
    assert any("reset" in m.lower() and "sync" in m.lower() for m in project.vhdl_modules()), \
        "no reset synchroniser module"


# ── Buses and registers ──────────────────────────────────────────────────────

def test_flat_port_groups_are_recognised_and_a_custom_group_is_defined(project):
    names = set(collect_interfaces(project.support))
    toml_path = EX / "docs" / "hdl_autodoc" / "bus_groups.toml"
    assert toml_path.exists()
    custom = tomllib.loads(toml_path.read_text())
    assert custom, "bus_groups.toml is empty"
    types = set()
    for m in project.files:
        ports = (extract_ports_vhdl(project.text(m)) if project.is_vhdl(m)
                 else extract_ports_sv(project.text(m), names))
        groups, _ = group_ports([p for p in ports if p.get("kind") != "interface"], toml_path)
        types |= {g.bus_type for g in groups}
    joined = " | ".join(sorted(types))
    for expected in ("AXI4-Lite", "AXI4-Stream", "APB"):
        assert expected in joined, f"no {expected} group among: {joined}"


def test_a_register_map_describes_at_least_three_registers(project):
    maps = [EX / "registers" / f"regs_{m}.toml" for m in project.files
            if (EX / "registers" / f"regs_{m}.toml").exists()]
    assert maps, "no regs_<module>.toml for a module in the hierarchy"
    data = tomllib.loads(maps[0].read_text())
    assert sum(1 for v in data.values() if isinstance(v, dict) and "mode" in v) >= 3
    assert (EX / "registers" / "config.yml").exists()


# ── Schematics ───────────────────────────────────────────────────────────────

def test_a_vhdl_parent_instantiates_a_systemverilog_child(project):
    need_vhdl(project)
    mods = project.hierarchy["modules"]
    assert any(project.is_vhdl(p) and not project.is_vhdl(c)
               for p, m in mods.items() for c in m["children"])


# ── Testbenches ──────────────────────────────────────────────────────────────

def test_testbenches_in_all_three_frameworks_linked_with_one_skipped(project):
    tbs = discover_testbenches(EX / "tb", set(project.files))
    assert {t.framework for t in tbs} == {"vunit", "cocotb", "directed"}
    for framework in ("vunit", "cocotb", "directed"):
        assert any(t.dut for t in tbs if t.framework == framework), f"no linked {framework} bench"
    assert any(c.skipped for t in tbs for c in t.tests)
    assert any(t.dut for t in tbs) and any(not t.dut for t in tbs), "need linked and unlinked benches"
    suffixes = {Path(t.file).suffix for t in tbs}
    assert ".sv" in suffixes
    if not project.pure_sv:
        assert ".vhd" in suffixes


# ── Build reports ────────────────────────────────────────────────────────────

def test_real_ecp5_reports_parse(project):
    reports = EX / "reports" / "yosys"
    clocks, tool = parse_timing(reports / "nextpnr.log")
    assert tool == "nextpnr" and clocks
    assert {r.name: r for r in parse_device_utilisation((reports / "nextpnr.log").read_text())}["TRELLIS_FF"].used > 0
    assert "Yosys" in (reports / "yosys.log").read_text()
    assert (reports / "stat.txt").exists()


def test_vivado_sample_reports_give_a_hierarchical_utilization_table(project):
    modules, tool = parse_utilization(EX / "reports" / "vivado" / "utilization_placed.rpt")
    assert tool == "vivado" and len(modules) >= 3
    clocks, timing_tool = parse_timing(EX / "reports" / "vivado" / "timing_summary_routed.rpt")
    assert timing_tool == "vivado" and clocks


# ── Project files ────────────────────────────────────────────────────────────

def test_the_project_is_set_up_like_the_other_examples(project):
    makefile = (EX / "Makefile").read_text()
    assert "include ../src/autodoc.mk" in makefile and "ecp5-reports" in makefile
    readme = (EX / "README.md").read_text()
    assert "Synthesis strategy" in readme
    assert (EX / "ecp5.lpf").exists() and (EX / ".gitignore").exists()
