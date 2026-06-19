# Coverage Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `make coverage` target that scans extraction output and produces a terminal table plus a Sphinx HTML coverage page.

**Architecture:** A single new script `generate_coverage.py` reads `hierarchy.json`, inspects each module's output directory, and writes `coverage.rst`. `generate_rst.py` gains a `has_coverage` guard that adds `coverage` to the index toctree only when the file exists. CSS classes are added to `custom.css` for coloured table cells.

**Tech Stack:** Python 3, pathlib, dataclasses, re, pytest with `tmp_path` fixtures

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scripts/hdl_autodoc/generate_coverage.py` | **Create** | CoverageResult dataclass, detect_coverage(), format_terminal_table(), coverage_rst(), main() |
| `scripts/hdl_autodoc/tests/test_generate_coverage.py` | **Create** | All 8 test groups for the new script |
| `docs/hdl_autodoc/_static/custom.css` | **Modify** | Add `.coverage-table`, `.cov-yes`, `.cov-no`, `.cov-count` |
| `scripts/hdl_autodoc/generate_rst.py` | **Modify** | Add `has_coverage` param to `index_rst()`, update `__main__` |
| `Makefile` | **Modify** | `coverage` target, `.PHONY`, `clean-generated`, `help` |

---

## Task 1: Data model and detection

**Files:**
- Create: `scripts/hdl_autodoc/generate_coverage.py`
- Create: `scripts/hdl_autodoc/tests/test_generate_coverage.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/hdl_autodoc/tests/test_generate_coverage.py`:

```python
"""Tests for generate_coverage.py — detection signals."""

from pathlib import Path
import pytest
from generate_coverage import CoverageResult, detect_coverage


def _make_mod(tmp_path: Path, name: str) -> Path:
    mod_dir = tmp_path / "modules" / name
    mod_dir.mkdir(parents=True)
    return mod_dir


# ── FSM ──────────────────────────────────────────────────────────────────────

def test_fsm_detected_when_dot_exists(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod.dot").write_text("digraph {}")
    result = detect_coverage("mymod", tmp_path)
    assert result.fsm is True


def test_fsm_not_detected_when_dot_absent(tmp_path):
    _make_mod(tmp_path, "mymod")
    result = detect_coverage("mymod", tmp_path)
    assert result.fsm is False


# ── Processes ─────────────────────────────────────────────────────────────────

def test_process_count_matches_p_rst_files(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    procs = mod_dir / "processes"
    procs.mkdir()
    (procs / "p_state_reg.rst").write_text("")
    (procs / "p_outputs.rst").write_text("")
    (procs / "p_next_state.rst").write_text("")
    result = detect_coverage("mymod", tmp_path)
    assert result.process_count == 3


def test_process_count_zero_when_no_processes_dir(tmp_path):
    _make_mod(tmp_path, "mymod")
    result = detect_coverage("mymod", tmp_path)
    assert result.process_count == 0


def test_process_count_zero_when_processes_dir_empty(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "processes").mkdir()
    result = detect_coverage("mymod", tmp_path)
    assert result.process_count == 0


# ── CDC ───────────────────────────────────────────────────────────────────────

def test_cdc_detected_when_cdc_rst_contains_arrow(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod_cdc.rst").write_text("clk_a → clk_b crossing detected")
    result = detect_coverage("mymod", tmp_path)
    assert result.cdc is True


def test_cdc_not_detected_when_cdc_rst_has_no_arrow(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod_cdc.rst").write_text("No clock domain crossings detected.")
    result = detect_coverage("mymod", tmp_path)
    assert result.cdc is False


def test_cdc_not_detected_when_cdc_rst_absent(tmp_path):
    _make_mod(tmp_path, "mymod")
    result = detect_coverage("mymod", tmp_path)
    assert result.cdc is False


# ── Reset ─────────────────────────────────────────────────────────────────────

def test_reset_detected_when_reset_rst_contains_crossing(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod_reset.rst").write_text("Reset domain Crossing detected on rst_n.")
    result = detect_coverage("mymod", tmp_path)
    assert result.reset is True


def test_reset_detected_case_insensitive(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod_reset.rst").write_text("CROSSING identified between domains.")
    result = detect_coverage("mymod", tmp_path)
    assert result.reset is True


def test_reset_not_detected_when_reset_rst_has_no_crossing(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod_reset.rst").write_text("Synchronous reset only. No domain issues.")
    result = detect_coverage("mymod", tmp_path)
    assert result.reset is False


def test_reset_not_detected_when_reset_rst_absent(tmp_path):
    _make_mod(tmp_path, "mymod")
    result = detect_coverage("mymod", tmp_path)
    assert result.reset is False


# ── Ports ─────────────────────────────────────────────────────────────────────

_BLOCK_RST_2_PORTS = """\
mymod — Block Diagram
=====================

Ports
-----

.. list-table::
   :header-rows: 1

   * - Port
     - Direction
     - Type

   * - ``clk``
     - ``in``
     - ``std_logic``

   * - ``rst``
     - ``in``
     - ``std_logic``

Signals
-------

.. list-table::
   :header-rows: 1

   * - Signal
     - Type

   * - ``state``
     - ``t_state``

"""


def test_port_count_returns_ports_only(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod_block.rst").write_text(_BLOCK_RST_2_PORTS)
    result = detect_coverage("mymod", tmp_path)
    assert result.port_count == 2  # signals section not counted


def test_port_count_zero_when_block_rst_absent(tmp_path):
    _make_mod(tmp_path, "mymod")
    result = detect_coverage("mymod", tmp_path)
    assert result.port_count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py -v
```

Expected: all tests fail with `ModuleNotFoundError: No module named 'generate_coverage'`

- [ ] **Step 3: Write the minimal implementation**

Create `scripts/hdl_autodoc/generate_coverage.py`:

```python
#!/usr/bin/env python3
"""
generate_coverage.py
--------------------
Inspects extraction output for each module and produces:
  1. A compact terminal coverage table (stdout)
  2. docs/hdl_autodoc/coverage.rst (Sphinx HTML page)

Usage:
    python scripts/hdl_autodoc/generate_coverage.py \\
        docs/hdl_autodoc/hierarchy.json docs/hdl_autodoc
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CoverageResult:
    name: str
    fsm: bool
    process_count: int
    cdc: bool
    reset: bool
    port_count: int


_PORT_SECTION_RE = re.compile(r"^Ports\n[-]+", re.MULTILINE)
_DATA_ROW_RE = re.compile(r"^\s+\* - ``", re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r"\n\n[^\n]+\n[-=]+")


def _count_ports(content: str) -> int:
    """Count port data rows in the Ports section of a _block.rst file."""
    m = _PORT_SECTION_RE.search(content)
    if not m:
        return 0
    section = content[m.end():]
    nxt = _NEXT_SECTION_RE.search(section)
    if nxt:
        section = section[:nxt.start()]
    return len(_DATA_ROW_RE.findall(section))


def detect_coverage(name: str, docs_dir: Path) -> CoverageResult:
    """Inspect a module's extraction output directory and return coverage signals."""
    mod_dir = docs_dir / "modules" / name

    fsm = (mod_dir / f"{name}.dot").exists()

    procs_dir = mod_dir / "processes"
    process_count = len(list(procs_dir.glob("p_*.rst"))) if procs_dir.exists() else 0

    cdc_rst = mod_dir / f"{name}_cdc.rst"
    cdc = cdc_rst.exists() and "\u2192" in cdc_rst.read_text()

    reset_rst = mod_dir / f"{name}_reset.rst"
    reset = reset_rst.exists() and bool(
        re.search(r"crossing", reset_rst.read_text(), re.IGNORECASE)
    )

    block_rst = mod_dir / f"{name}_block.rst"
    port_count = _count_ports(block_rst.read_text()) if block_rst.exists() else 0

    return CoverageResult(
        name=name,
        fsm=fsm,
        process_count=process_count,
        cdc=cdc,
        reset=reset,
        port_count=port_count,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py -v
```

Expected: all 14 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/generate_coverage.py \
        scripts/hdl_autodoc/tests/test_generate_coverage.py
git commit -m "feat: add CoverageResult dataclass and detect_coverage() with full signal tests"
```

---

## Task 2: Terminal formatter

**Files:**
- Modify: `scripts/hdl_autodoc/generate_coverage.py`
- Modify: `scripts/hdl_autodoc/tests/test_generate_coverage.py`

- [ ] **Step 1: Write the failing tests**

Append to `scripts/hdl_autodoc/tests/test_generate_coverage.py`:

```python
from generate_coverage import format_terminal_table


# ── Terminal formatter ────────────────────────────────────────────────────────

def _sample_results():
    return [
        CoverageResult("blinky",         fsm=True,  process_count=3, cdc=False, reset=True,  port_count=7),
        CoverageResult("cfg_sync",        fsm=False, process_count=3, cdc=True,  reset=True,  port_count=8),
        CoverageResult("pwm_controller",  fsm=True,  process_count=3, cdc=False, reset=False, port_count=6),
        CoverageResult("top",             fsm=False, process_count=0, cdc=False, reset=False, port_count=4),
        CoverageResult("traffic_light",   fsm=True,  process_count=4, cdc=False, reset=True,  port_count=7),
    ]


def test_terminal_table_contains_all_module_names():
    out = format_terminal_table(_sample_results())
    for name in ("blinky", "cfg_sync", "pwm_controller", "top", "traffic_light"):
        assert name in out


def test_terminal_table_checkmark_for_true_fsm():
    out = format_terminal_table(_sample_results())
    lines = out.splitlines()
    blinky_line = next(l for l in lines if l.startswith("blinky"))
    assert "✓" in blinky_line


def test_terminal_table_dash_for_false_fsm():
    out = format_terminal_table(_sample_results())
    lines = out.splitlines()
    cfg_line = next(l for l in lines if l.startswith("cfg_sync"))
    # First field after name is FSM — cfg_sync has fsm=False
    assert "–" in cfg_line


def test_terminal_table_proc_count_format():
    out = format_terminal_table(_sample_results())
    assert "3 procs" in out
    assert "4 procs" in out


def test_terminal_table_dash_for_zero_proc_count():
    results = [CoverageResult("top", fsm=False, process_count=0, cdc=False, reset=False, port_count=4)]
    out = format_terminal_table(results)
    lines = out.splitlines()
    top_line = next(l for l in lines if l.startswith("top"))
    assert "procs" not in top_line


def test_terminal_table_port_count_format():
    out = format_terminal_table(_sample_results())
    assert "7 ports" in out
    assert "8 ports" in out


def test_terminal_table_totals_row_present():
    out = format_terminal_table(_sample_results())
    assert "Totals" in out


def test_terminal_table_totals_boolean_fraction():
    out = format_terminal_table(_sample_results())
    # 3 modules have fsm=True out of 5
    assert "3/5" in out


def test_terminal_table_totals_count_fraction():
    out = format_terminal_table(_sample_results())
    # All 5 have process_count > 0 (top has 0 — so 4/5)
    assert "4/5" in out


def test_terminal_table_separator_lines():
    out = format_terminal_table(_sample_results())
    assert "─" in out
    assert "Coverage Report" in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py::test_terminal_table_contains_all_module_names -v
```

Expected: FAIL with `ImportError: cannot import name 'format_terminal_table'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/hdl_autodoc/generate_coverage.py` (before the `_depth_first_order` placeholder):

```python
def format_terminal_table(results: list[CoverageResult]) -> str:
    """Format a compact terminal coverage table from a list of results."""
    n = len(results)
    if not results:
        return "Coverage Report\nNo modules found.\n"

    name_w = max(len(r.name) for r in results)
    name_w = max(name_w, 6)  # minimum width of "Module" header

    # Column widths: FSM=5, Processes=11, CDC=5, Reset=7, Ports=9
    total_w = name_w + 2 + 5 + 2 + 11 + 2 + 5 + 2 + 7 + 2 + 9
    sep = "─" * total_w

    def fmt_bool(v: bool) -> str:
        return "✓" if v else "–"

    def fmt_proc(count: int) -> str:
        return f"{count} procs" if count > 0 else "–"

    def fmt_port(count: int) -> str:
        return f"{count} ports" if count > 0 else "–"

    def row(name: str, fsm: str, proc: str, cdc: str, rst: str, port: str) -> str:
        return (
            f"{name:<{name_w}}  {fsm:>5}  {proc:>11}  "
            f"{cdc:>5}  {rst:>7}  {port:>9}"
        )

    lines = [
        "Coverage Report",
        sep,
        row("Module", "FSM", "Processes", "CDC", "Reset", "Ports"),
        sep,
    ]

    for r in results:
        lines.append(row(
            r.name,
            fmt_bool(r.fsm),
            fmt_proc(r.process_count),
            fmt_bool(r.cdc),
            fmt_bool(r.reset),
            fmt_port(r.port_count),
        ))

    fsm_tot   = sum(1 for r in results if r.fsm)
    proc_tot  = sum(1 for r in results if r.process_count > 0)
    cdc_tot   = sum(1 for r in results if r.cdc)
    reset_tot = sum(1 for r in results if r.reset)
    port_tot  = sum(1 for r in results if r.port_count > 0)

    lines.append(sep)
    lines.append(row(
        "Totals",
        f"{fsm_tot}/{n}",
        f"{proc_tot}/{n}",
        f"{cdc_tot}/{n}",
        f"{reset_tot}/{n}",
        f"{port_tot}/{n}",
    ))

    return "\n".join(lines)
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py -v
```

Expected: all tests PASS (14 detection + 10 formatter = 24 total)

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/generate_coverage.py \
        scripts/hdl_autodoc/tests/test_generate_coverage.py
git commit -m "feat: add format_terminal_table() with coverage column formatting and totals row"
```

---

## Task 3: RST generator

**Files:**
- Modify: `scripts/hdl_autodoc/generate_coverage.py`
- Modify: `scripts/hdl_autodoc/tests/test_generate_coverage.py`

- [ ] **Step 1: Write the failing tests**

Append to `scripts/hdl_autodoc/tests/test_generate_coverage.py`:

```python
from generate_coverage import coverage_rst


# ── RST generator ─────────────────────────────────────────────────────────────

def _one_result(fsm=True, process_count=3, cdc=False, reset=True, port_count=6):
    return [CoverageResult("blinky", fsm=fsm, process_count=process_count,
                           cdc=cdc, reset=reset, port_count=port_count)]


def test_coverage_rst_has_title():
    rst = coverage_rst(_one_result())
    assert "Documentation Coverage" in rst
    assert "======================" in rst


def test_coverage_rst_has_raw_html_directive():
    rst = coverage_rst(_one_result())
    assert ".. raw:: html" in rst


def test_coverage_rst_has_coverage_table_class():
    rst = coverage_rst(_one_result())
    assert 'class="coverage-table"' in rst


def test_coverage_rst_module_link():
    rst = coverage_rst(_one_result())
    assert 'href="modules/blinky/index.html"' in rst
    assert ">blinky<" in rst


def test_coverage_rst_cov_yes_for_true_fsm():
    rst = coverage_rst(_one_result(fsm=True))
    assert 'class="cov-yes"' in rst
    assert ">✓<" in rst


def test_coverage_rst_cov_no_for_false_cdc():
    rst = coverage_rst(_one_result(cdc=False))
    # CDC is False → cov-no class
    lines = rst.splitlines()
    # Find the CDC cell — it follows the Processes cell
    assert 'class="cov-no"' in rst


def test_coverage_rst_cov_count_for_process_count():
    rst = coverage_rst(_one_result(process_count=3))
    assert 'class="cov-count"' in rst
    assert ">3<" in rst


def test_coverage_rst_cov_count_for_port_count():
    rst = coverage_rst(_one_result(port_count=6))
    assert ">6<" in rst


def test_coverage_rst_cov_no_for_zero_process_count():
    rst = coverage_rst(_one_result(process_count=0))
    # All non-count fields are bool. Zero count → cov-no with –
    assert ">–<" in rst


def test_coverage_rst_tfoot_present():
    rst = coverage_rst(_one_result())
    assert "<tfoot>" in rst


def test_coverage_rst_tfoot_totals():
    results = [
        CoverageResult("a", fsm=True,  process_count=2, cdc=True,  reset=False, port_count=3),
        CoverageResult("b", fsm=False, process_count=0, cdc=False, reset=False, port_count=0),
    ]
    rst = coverage_rst(results)
    assert ">1/2<" in rst   # fsm: 1 out of 2
    assert ">2/2<" in rst   # ports: both > 0? No — b has 0. Check: port_tot=1
    # a: port_count=3 (>0) → counted; b: port_count=0 → not counted → 1/2
    assert ">0/2<" in rst   # reset: 0 out of 2


def test_coverage_rst_multiple_rows():
    results = [
        CoverageResult("mod_a", fsm=True,  process_count=2, cdc=False, reset=True,  port_count=4),
        CoverageResult("mod_b", fsm=False, process_count=0, cdc=True,  reset=False, port_count=0),
    ]
    rst = coverage_rst(results)
    assert "mod_a" in rst
    assert "mod_b" in rst
    assert rst.count("<tr>") >= 3  # header + 2 data rows (+ tfoot row)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py::test_coverage_rst_has_title -v
```

Expected: FAIL with `ImportError: cannot import name 'coverage_rst'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/hdl_autodoc/generate_coverage.py`:

```python
def coverage_rst(results: list[CoverageResult]) -> str:
    """Generate a coverage.rst Sphinx page with a coloured HTML table."""
    n = len(results)

    def bool_cell(v: bool) -> str:
        cls = "cov-yes" if v else "cov-no"
        txt = "✓" if v else "–"
        return f'        <td class="{cls}">{txt}</td>'

    def count_cell(v: int) -> str:
        cls = "cov-count" if v > 0 else "cov-no"
        txt = str(v) if v > 0 else "–"
        return f'        <td class="{cls}">{txt}</td>'

    rows = []
    for r in results:
        rows.append(
            "      <tr>\n"
            f'        <td><a href="modules/{r.name}/index.html">{r.name}</a></td>\n'
            + bool_cell(r.fsm) + "\n"
            + count_cell(r.process_count) + "\n"
            + bool_cell(r.cdc) + "\n"
            + bool_cell(r.reset) + "\n"
            + count_cell(r.port_count) + "\n"
            "      </tr>"
        )

    fsm_tot   = sum(1 for r in results if r.fsm)
    proc_tot  = sum(1 for r in results if r.process_count > 0)
    cdc_tot   = sum(1 for r in results if r.cdc)
    reset_tot = sum(1 for r in results if r.reset)
    port_tot  = sum(1 for r in results if r.port_count > 0)

    body = "\n".join(rows)

    return (
        "Documentation Coverage\n"
        "======================\n"
        "\n"
        ".. raw:: html\n"
        "\n"
        '   <table class="coverage-table">\n'
        "     <thead>\n"
        "       <tr>\n"
        "         <th>Module</th><th>FSM</th><th>Processes</th>\n"
        "         <th>CDC</th><th>Reset</th><th>Ports</th>\n"
        "       </tr>\n"
        "     </thead>\n"
        "     <tbody>\n"
        f"{body}\n"
        "     </tbody>\n"
        "     <tfoot>\n"
        "       <tr>\n"
        "         <td>Totals</td>\n"
        f"         <td>{fsm_tot}/{n}</td>\n"
        f"         <td>{proc_tot}/{n}</td>\n"
        f"         <td>{cdc_tot}/{n}</td>\n"
        f"         <td>{reset_tot}/{n}</td>\n"
        f"         <td>{port_tot}/{n}</td>\n"
        "       </tr>\n"
        "     </tfoot>\n"
        "   </table>\n"
    )
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py -v
```

Expected: all tests PASS (24 + 13 = 37 total)

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/generate_coverage.py \
        scripts/hdl_autodoc/tests/test_generate_coverage.py
git commit -m "feat: add coverage_rst() generating coloured HTML table with tfoot totals"
```

---

## Task 4: Main entry point and hierarchy ordering

**Files:**
- Modify: `scripts/hdl_autodoc/generate_coverage.py`
- Modify: `scripts/hdl_autodoc/tests/test_generate_coverage.py`

- [ ] **Step 1: Write the failing tests**

Append to `scripts/hdl_autodoc/tests/test_generate_coverage.py`:

```python
import json
from generate_coverage import _depth_first_order, main


# ── Hierarchy ordering ────────────────────────────────────────────────────────

def _make_hierarchy(top: str, children: dict[str, list[str]]) -> dict:
    """Build a minimal hierarchy.json structure."""
    modules = {}
    for name, kids in children.items():
        modules[name] = {"file": f"src/{name}.vhd", "children": kids, "parents": []}
    # Fix up parents
    for name, kids in children.items():
        for kid in kids:
            modules[kid]["parents"] = [name]
    return {"top": top, "modules": modules}


def test_depth_first_order_top_first():
    h = _make_hierarchy("top", {
        "top": ["child_a", "child_b"],
        "child_a": [],
        "child_b": [],
    })
    order = _depth_first_order(h)
    assert order[0] == "top"


def test_depth_first_order_children_after_parent():
    h = _make_hierarchy("top", {
        "top": ["child_a", "child_b"],
        "child_a": [],
        "child_b": [],
    })
    order = _depth_first_order(h)
    assert order == ["top", "child_a", "child_b"]


def test_depth_first_order_nested():
    h = _make_hierarchy("top", {
        "top": ["mid"],
        "mid": ["leaf"],
        "leaf": [],
    })
    order = _depth_first_order(h)
    assert order == ["top", "mid", "leaf"]


def test_depth_first_order_includes_unreachable_modules():
    h = _make_hierarchy("top", {
        "top": [],
        "orphan": [],
    })
    order = _depth_first_order(h)
    assert "top" in order
    assert "orphan" in order


# ── main() integration ────────────────────────────────────────────────────────

def _write_hierarchy(path: Path, hierarchy: dict) -> None:
    path.write_text(json.dumps(hierarchy))


def _make_full_module(docs_dir: Path, name: str, *, fsm=False, procs=0,
                      cdc_arrow=False, reset_cross=False, ports=0) -> None:
    mod_dir = docs_dir / "modules" / name
    mod_dir.mkdir(parents=True, exist_ok=True)

    if fsm:
        (mod_dir / f"{name}.dot").write_text("digraph {}")

    if procs > 0:
        p_dir = mod_dir / "processes"
        p_dir.mkdir(exist_ok=True)
        for i in range(procs):
            (p_dir / f"p_proc{i}.rst").write_text("")

    cdc_content = "clk_a \u2192 clk_b" if cdc_arrow else "No crossings."
    (mod_dir / f"{name}_cdc.rst").write_text(cdc_content)

    reset_content = "Reset crossing detected." if reset_cross else "Synchronous reset only."
    (mod_dir / f"{name}_reset.rst").write_text(reset_content)

    if ports > 0:
        port_rows = "\n".join(
            f"   * - ``port{i}``\n     - ``in``\n     - ``std_logic``\n"
            for i in range(ports)
        )
        block = (
            f"{name} — Block Diagram\n"
            f"{'=' * (len(name) + 16)}\n\n"
            "Ports\n-----\n\n"
            ".. list-table::\n"
            "   :header-rows: 1\n\n"
            "   * - Port\n     - Direction\n     - Type\n\n"
            + port_rows
        )
        (mod_dir / f"{name}_block.rst").write_text(block)


def test_main_writes_coverage_rst(tmp_path):
    h = _make_hierarchy("top", {"top": ["child_a"], "child_a": []})
    hjson = tmp_path / "hierarchy.json"
    _write_hierarchy(hjson, h)
    _make_full_module(tmp_path, "top",     fsm=False, procs=0, ports=2)
    _make_full_module(tmp_path, "child_a", fsm=True,  procs=2, ports=3)

    main(hjson, tmp_path)

    out = tmp_path / "coverage.rst"
    assert out.exists()
    content = out.read_text()
    assert "Documentation Coverage" in content
    assert "child_a" in content


def test_main_preserves_depth_first_order_in_rst(tmp_path):
    h = _make_hierarchy("top", {"top": ["child_a", "child_b"],
                                 "child_a": [], "child_b": []})
    hjson = tmp_path / "hierarchy.json"
    _write_hierarchy(hjson, h)
    for name in ("top", "child_a", "child_b"):
        _make_full_module(tmp_path, name, ports=1)

    main(hjson, tmp_path)

    content = (tmp_path / "coverage.rst").read_text()
    pos_top     = content.index(">top<")
    pos_child_a = content.index(">child_a<")
    pos_child_b = content.index(">child_b<")
    assert pos_top < pos_child_a < pos_child_b
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py::test_depth_first_order_top_first -v
```

Expected: FAIL with `ImportError: cannot import name '_depth_first_order'`

- [ ] **Step 3: Write the implementation**

Append to `scripts/hdl_autodoc/generate_coverage.py`:

```python
def _depth_first_order(hierarchy: dict) -> list[str]:
    """Return module names in depth-first order starting from the top module."""
    top = hierarchy["top"]
    modules = hierarchy["modules"]
    visited: list[str] = []

    def visit(name: str) -> None:
        if name not in visited:
            visited.append(name)
            for child in modules[name]["children"]:
                visit(child)

    visit(top)
    for name in modules:
        if name not in visited:
            visited.append(name)
    return visited


def main(hierarchy_json: Path, docs_dir: Path) -> None:
    """Run coverage detection and write terminal output + coverage.rst."""
    with open(hierarchy_json) as f:
        hierarchy = json.load(f)

    names = _depth_first_order(hierarchy)
    results = [detect_coverage(name, docs_dir) for name in names]

    print(format_terminal_table(results))

    rst = coverage_rst(results)
    out = docs_dir / "coverage.rst"
    out.write_text(rst)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: generate_coverage.py <hierarchy.json> <docs_dir>")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_coverage.py -v
```

Expected: all tests PASS (37 + 9 = 46 total)

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/generate_coverage.py \
        scripts/hdl_autodoc/tests/test_generate_coverage.py
git commit -m "feat: add _depth_first_order() and main() entry point, complete generate_coverage.py"
```

---

## Task 5: CSS additions

**Files:**
- Modify: `docs/hdl_autodoc/_static/custom.css`

No TDD here — CSS is visual. Add the four coverage classes at the end of the file (before any final comment block if present).

- [ ] **Step 1: Append coverage CSS to custom.css**

Add at the end of `docs/hdl_autodoc/_static/custom.css`:

```css
/* ── Coverage table ──────────────────────────────────────────────────────── */

.coverage-table {
  border-collapse: collapse;
  width: 100%;
  margin: 1.5rem 0;
  font-family: var(--f-body);
  font-size: 0.9em;
}

.coverage-table th,
.coverage-table td {
  padding: 0.45rem 0.8rem;
  border: 1px solid var(--surface-0);
  text-align: center;
}

.coverage-table th:first-child,
.coverage-table td:first-child {
  text-align: left;
}

.coverage-table thead tr {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--subtext-1);
}

.coverage-table tfoot tr {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--subtext-1);
}

.cov-yes {
  background: color-mix(in srgb, var(--ctp-green) 18%, transparent);
  color: var(--success);
  font-weight: 600;
}

.cov-no {
  background: color-mix(in srgb, var(--surface-0) 60%, transparent);
  color: var(--overlay-1);
}

.cov-count {
  background: color-mix(in srgb, var(--ctp-blue) 12%, transparent);
  color: var(--accent);
  font-weight: 500;
}
```

- [ ] **Step 2: Verify no CSS syntax errors**

```bash
python3 -c "
import re, sys
with open('docs/hdl_autodoc/_static/custom.css') as f:
    css = f.read()
# Check all braces balance
opens = css.count('{')
closes = css.count('}')
if opens != closes:
    sys.exit(f'Unbalanced braces: {opens} open, {closes} close')
print('CSS brace balance OK')
"
```

Expected: `CSS brace balance OK`

- [ ] **Step 3: Commit**

```bash
git add docs/hdl_autodoc/_static/custom.css
git commit -m "feat: add coverage table CSS classes (cov-yes, cov-no, cov-count) to Catppuccin theme"
```

---

## Task 6: generate_rst.py — has_coverage guard

**Files:**
- Modify: `scripts/hdl_autodoc/generate_rst.py`

- [ ] **Step 1: Write the failing test**

Create `scripts/hdl_autodoc/tests/test_generate_rst_coverage.py`:

```python
"""Tests for the has_coverage guard in generate_rst.index_rst()."""

from generate_rst import index_rst

_ENTITIES = [{"name": "blinky", "file": "src/blinky.vhd", "brief": ""}]
_HIERARCHY = {"top": "blinky", "modules": {"blinky": {"children": [], "parents": []}}}


def test_coverage_not_in_toctree_by_default():
    rst = index_rst(_ENTITIES, "TestProject", _HIERARCHY)
    assert "coverage" not in rst


def test_coverage_in_toctree_when_has_coverage_true():
    rst = index_rst(_ENTITIES, "TestProject", _HIERARCHY, has_coverage=True)
    assert "   coverage" in rst


def test_coverage_entry_position_after_hierarchy():
    rst = index_rst(_ENTITIES, "TestProject", _HIERARCHY, has_coverage=True)
    pos_hierarchy = rst.index("   hierarchy")
    pos_coverage  = rst.index("   coverage")
    assert pos_coverage > pos_hierarchy
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_rst_coverage.py -v
```

Expected: `test_coverage_not_in_toctree_by_default` PASS (coverage isn't there yet), the other two FAIL with `TypeError: index_rst() got an unexpected keyword argument 'has_coverage'`

- [ ] **Step 3: Update `index_rst` in generate_rst.py**

In `scripts/hdl_autodoc/generate_rst.py`, change the `index_rst` signature and body:

**Old** (line 434–464):
```python
def index_rst(entities: list[dict], project_name: str,
              hierarchy: dict = None) -> str:
    lines = [
        project_name, "=" * len(project_name), "",
        ".. toctree::",
        "   :maxdepth: 4",
        "   :caption: Contents",
        "",
        "   overview",
    ]

    if hierarchy:
        # Only list the top-level module — it contains submodule toctrees
        top = hierarchy["top"]
        lines += [
            f"   modules/{top}/index",
            "   hierarchy",
        ]
    else:
        for e in entities:
            lines.append(f"   modules/{e['name']}/index")
        lines.append("   registers")

    lines += [
        "",
        "Indices", "-------", "",
        "* :ref:`genindex`",
        "* :ref:`search`",
        "",
    ]
    return "\n".join(lines)
```

**New**:
```python
def index_rst(entities: list[dict], project_name: str,
              hierarchy: dict = None, has_coverage: bool = False) -> str:
    lines = [
        project_name, "=" * len(project_name), "",
        ".. toctree::",
        "   :maxdepth: 4",
        "   :caption: Contents",
        "",
        "   overview",
    ]

    if hierarchy:
        # Only list the top-level module — it contains submodule toctrees
        top = hierarchy["top"]
        lines += [
            f"   modules/{top}/index",
            "   hierarchy",
        ]
    else:
        for e in entities:
            lines.append(f"   modules/{e['name']}/index")
        lines.append("   registers")

    if has_coverage:
        lines.append("   coverage")

    lines += [
        "",
        "Indices", "-------", "",
        "* :ref:`genindex`",
        "* :ref:`search`",
        "",
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Update the `__main__` call site in generate_rst.py**

Find this block near line 601 in `scripts/hdl_autodoc/generate_rst.py`:

```python
    results.append(write_always(
        docs_dir / "index.rst",
        index_rst(entities, project_name, hierarchy)
    ))
```

Replace with:

```python
    has_coverage = (docs_dir / "coverage.rst").exists()
    results.append(write_always(
        docs_dir / "index.rst",
        index_rst(entities, project_name, hierarchy, has_coverage=has_coverage)
    ))
```

- [ ] **Step 5: Run all tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_rst_coverage.py \
       scripts/hdl_autodoc/tests/test_generate_coverage.py -v
```

Expected: all tests PASS

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
pytest scripts/hdl_autodoc/tests/ -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add scripts/hdl_autodoc/generate_rst.py \
        scripts/hdl_autodoc/tests/test_generate_rst_coverage.py
git commit -m "feat: add has_coverage guard to index_rst() toctree"
```

---

## Task 7: Makefile additions

**Files:**
- Modify: `Makefile`

No tests for Makefile targets. Manual verification is the check.

- [ ] **Step 1: Add `coverage` to `.PHONY`**

In `Makefile`, change:

```makefile
.PHONY: help venv install hierarchy scaffold extract html pdf \
        clean clean-generated clean-all
```

To:

```makefile
.PHONY: help venv install hierarchy scaffold extract html pdf \
        coverage clean clean-generated clean-all
```

- [ ] **Step 2: Add `coverage` help line**

In the `help` target, after the `make extract` line, add:

```makefile
	@echo "  make coverage              Generate documentation coverage report"
```

- [ ] **Step 3: Add `coverage` target**

After the `extract` target block (around line 98), add:

```makefile
# ── Step 3b: coverage report (opt-in, runs independently after extract) ──────
coverage: hierarchy
	python $(AUTODOC_SCRIPTDIR)/generate_coverage.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR)
```

- [ ] **Step 4: Add `coverage.rst` to `clean-generated`**

In the `clean-generated` target, after the `registers.rst` line:

```makefile
	rm -f  $(AUTODOC_SOURCEDIR)/coverage.rst
```

- [ ] **Step 5: Verify the Makefile parses correctly**

```bash
make help
```

Expected: help output includes `make coverage              Generate documentation coverage report`

- [ ] **Step 6: Run `make coverage` against the real project**

```bash
make coverage
```

Expected:
- Terminal table printed with all 5 modules
- `docs/hdl_autodoc/coverage.rst` created

- [ ] **Step 7: Verify coverage page appears in Sphinx build**

```bash
make html
```

Expected: build succeeds, `coverage` entry appears in the sidebar toctree

- [ ] **Step 8: Commit**

```bash
git add Makefile
git commit -m "feat: add make coverage target with clean-generated support"
```

---

## Self-Review Against Spec

**Spec coverage check:**

| Spec requirement | Covered by |
|---|---|
| `generate_coverage.py` script | Tasks 1–4 |
| Reads `hierarchy.json` for module list | Task 4 (main + _depth_first_order) |
| 5 coverage signals (FSM, processes, CDC, reset, ports) | Task 1 |
| Terminal table with ✓/– and counts | Task 2 |
| Totals row (boolean = count-True, count = count->0) | Task 2 |
| Sphinx `coverage.rst` with `.. raw:: html` | Task 3 |
| `.cov-yes`, `.cov-no`, `.cov-count` CSS classes | Tasks 3 + 5 |
| Module name links to `modules/<name>/index.html` | Task 3 |
| `<tfoot>` totals row | Task 3 |
| `.coverage-table` CSS with Catppuccin tokens | Task 5 |
| `index_rst` has_coverage guard | Task 6 |
| `make coverage` target depending on `hierarchy` | Task 7 |
| `make html` does NOT depend on `coverage` | Task 7 (coverage is standalone) |
| `clean-generated` removes `coverage.rst` | Task 7 |
| Depth-first ordering | Task 4 |

**No placeholders found.**

**Type consistency check:** `CoverageResult` defined in Task 1, used by `format_terminal_table` (Task 2), `coverage_rst` (Task 3), `main` (Task 4) — all consistent.
