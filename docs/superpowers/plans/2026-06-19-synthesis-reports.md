# Synthesis Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ingest Vivado and Yosys/nextpnr synthesis reports from a `reports/` directory and publish an Implementation section in the Sphinx docs with per-module utilization and top-level timing.

**Architecture:** Two new parser modules (`parse_utilization.py`, `parse_timing.py`) produce a shared data model. `extract_reports.py` orchestrates them and writes per-module `synthesis.rst` and a top-level `synthesis/index.rst`. `generate_rst.py` detects these files and adds an Implementation toctree section to the main index; a `make reports` Makefile target drives the whole pipeline. Reports are optional — a placeholder page is always emitted so the Implementation section is never missing from the ToC.

**Tech Stack:** Python 3.11+ stdlib (`re`, `dataclasses`, `json`, `pathlib`), pytest, Sphinx RST.

## Global Constraints

- Reports directory layout: `reports/vivado/utilization_placed.rpt`, `reports/vivado/timing_summary_routed.rpt`, `reports/yosys/stat.txt`, `reports/yosys/nextpnr.log` — filenames are fixed; the parser must match exactly these names.
- Fallback for missing Vivado placed report: check `reports/vivado/utilization_synth.rpt`.
- The Implementation section is **always** included in the main ToC — show a placeholder when no reports are present.
- All generated RST files (`synthesis/index.rst`, `modules/*/synthesis.rst`) are always-regenerated — never hand-editable.
- `make reports` is a standalone target (does not run automatically as part of `make html`); `make html` picks up synthesis RST files if they were already written by `make reports`.
- Python import path: tests use `conftest.py` which inserts `scripts/hdl_autodoc/` into `sys.path`, so all imports are bare (e.g. `from parse_utilization import ...`).
- Module name normalisation for Vivado hierarchical rows: strip leading `u_` or `i_` prefix and lowercase — `u_blinky` → `blinky`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scripts/hdl_autodoc/parse_utilization.py` | **Create** | `ModuleUtilization` dataclass; Vivado ASCII-table parser; Yosys `stat` text parser; `parse_utilization(path)` public API |
| `scripts/hdl_autodoc/parse_timing.py` | **Create** | `ClockTiming` dataclass; Vivado timing-summary parser; nextpnr log parser; `parse_timing(path)` public API |
| `scripts/hdl_autodoc/extract_reports.py` | **Create** | `synthesis_index_rst()`, `module_synthesis_rst()`, `main()` — reads hierarchy.json, calls parsers, writes RST files |
| `scripts/hdl_autodoc/tests/test_parse_utilization.py` | **Create** | 8 tests for parse_utilization |
| `scripts/hdl_autodoc/tests/test_parse_timing.py` | **Create** | 7 tests for parse_timing |
| `scripts/hdl_autodoc/tests/test_extract_reports.py` | **Create** | 7 tests for extract_reports |
| `scripts/hdl_autodoc/generate_rst.py` | **Modify** | Add `has_synthesis` param to `module_index_rst` and `index_rst`; detect synthesis files in `main()` |
| `scripts/hdl_autodoc/tests/test_generate_rst.py` | **Modify** | Add 4 tests for the `has_synthesis` parameters |
| `Makefile` | **Modify** | Add `reports` target; add `reports` to `.PHONY`; add synthesis files to `clean-generated` |

---

### Task 1: parse_utilization.py — utilization report parser

**Files:**
- Create: `scripts/hdl_autodoc/parse_utilization.py`
- Create: `scripts/hdl_autodoc/tests/test_parse_utilization.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass
  class ModuleUtilization:
      module_name: str
      luts: int = 0
      ffs: int = 0
      brams: int = 0
      dsps: int = 0
      luts_available: int | None = None   # Vivado only
      ffs_available: int | None = None    # Vivado only

  def parse_utilization(path: Path) -> tuple[list[ModuleUtilization], str | None]:
      """
      Returns (modules, tool).
      tool is "vivado", "yosys", or None (file absent / unrecognised).
      modules[0] is always top-level totals.
      modules[1:] are per-instance rows when hierarchical data is present.
      Returns ([], None) when file is absent or format unrecognised.
      """
  ```

- [ ] **Step 1: Write the failing tests**

Create `scripts/hdl_autodoc/tests/test_parse_utilization.py`:

```python
"""
test_parse_utilization.py
--------------------------
Tests for parse_utilization.py.

Covers:
  1.  Vivado top-level: LUTs, FFs, BRAMs, DSPs parsed from Slice Logic table
  2.  Vivado: luts_available populated from Available column
  3.  Vivado hierarchical: per-module entries returned with u_ prefix stripped
  4.  Yosys ECP5: TRELLIS_COMB → LUTs, TRELLIS_FF → FFs, TRELLIS_BRAM → BRAMs
  5.  Yosys iCE40: SB_LUT4 → LUTs, SB_DFF → FFs
  6.  Yosys multiple modules: one ModuleUtilization per === section ===
  7.  Missing file → ([], None)
  8.  Unrecognised text → ([], None)
"""

import pytest
from pathlib import Path

from parse_utilization import ModuleUtilization, parse_utilization


# ── Sample report text ────────────────────────────────────────────────────────

_VIVADO_UTIL = """\
1. Slice Logic
--------------

+----------------------------+------+-------+------------+-----------+-------+
|          Site Type         | Used | Fixed | Prohibited | Available | Util% |
+----------------------------+------+-------+------------+-----------+-------+
| Slice LUTs                 |  142 |     0 |          0 |    134600 |  0.11 |
|   LUT as Logic             |  134 |     0 |          0 |    134600 |  0.10 |
| Slice Registers            |   89 |     0 |          0 |    269200 |  0.03 |
| Block RAM Tile             |    2 |     0 |          0 |       365 |  0.55 |
| DSPs                       |    4 |     0 |          0 |       740 |  0.54 |
+----------------------------+------+-------+------------+-----------+-------+
"""

_VIVADO_HIER = _VIVADO_UTIL + """\
Hierarchical LUT Usage
----------------------

+----------------------------+------+-----+-------+------+
|          Instance          | LUTs | FFs | BRAMs | DSPs |
+----------------------------+------+-----+-------+------+
| top                        |  142 |  89 |     2 |    4 |
|   (top)                    |   18 |   4 |     0 |    0 |
|   u_blinky                 |   12 |   8 |     0 |    0 |
+----------------------------+------+-----+-------+------+
"""

_YOSYS_ECP5 = """\
2. Printing statistics.

=== top ===

   Number of cells:               142
     TRELLIS_COMB                  47
     TRELLIS_FF                    89
     TRELLIS_BRAM                   6

=== blinky ===

   Number of cells:                12
     TRELLIS_COMB                   8
     TRELLIS_FF                     4
"""

_YOSYS_ICE40 = """\
=== blinky ===

   Number of cells:                10
     SB_LUT4                        6
     SB_DFF                         4
"""


# ── Test 1: Vivado top-level resource counts ──────────────────────────────────

def test_vivado_top_level_luts_ffs_brams_dsps(tmp_path):
    rpt = tmp_path / "util.rpt"
    rpt.write_text(_VIVADO_UTIL)
    modules, tool = parse_utilization(rpt)
    assert tool == "vivado"
    assert len(modules) >= 1
    top = modules[0]
    assert top.luts == 142
    assert top.ffs == 89
    assert top.brams == 2
    assert top.dsps == 4


# ── Test 2: Vivado luts_available ─────────────────────────────────────────────

def test_vivado_luts_available(tmp_path):
    rpt = tmp_path / "util.rpt"
    rpt.write_text(_VIVADO_UTIL)
    modules, _ = parse_utilization(rpt)
    assert modules[0].luts_available == 134600


# ── Test 3: Vivado hierarchical breakdown ─────────────────────────────────────

def test_vivado_hierarchical_per_module(tmp_path):
    rpt = tmp_path / "util.rpt"
    rpt.write_text(_VIVADO_HIER)
    modules, tool = parse_utilization(rpt)
    assert tool == "vivado"
    names = [m.module_name for m in modules]
    assert "top" in names
    assert "blinky" in names   # u_blinky → blinky
    blinky = next(m for m in modules if m.module_name == "blinky")
    assert blinky.luts == 12
    assert blinky.ffs == 8


# ── Test 4: Yosys ECP5 cell mapping ──────────────────────────────────────────

def test_yosys_ecp5_trellis(tmp_path):
    rpt = tmp_path / "stat.txt"
    rpt.write_text(_YOSYS_ECP5)
    modules, tool = parse_utilization(rpt)
    assert tool == "yosys"
    top = next(m for m in modules if m.module_name == "top")
    assert top.luts == 47    # TRELLIS_COMB
    assert top.ffs == 89     # TRELLIS_FF
    assert top.brams == 6    # TRELLIS_BRAM (6 half-BRAMs counted here)


# ── Test 5: Yosys iCE40 cell mapping ─────────────────────────────────────────

def test_yosys_ice40_sb(tmp_path):
    rpt = tmp_path / "stat.txt"
    rpt.write_text(_YOSYS_ICE40)
    modules, tool = parse_utilization(rpt)
    assert tool == "yosys"
    assert len(modules) == 1
    assert modules[0].module_name == "blinky"
    assert modules[0].luts == 6   # SB_LUT4
    assert modules[0].ffs == 4    # SB_DFF


# ── Test 6: Yosys multiple modules ───────────────────────────────────────────

def test_yosys_multiple_modules(tmp_path):
    rpt = tmp_path / "stat.txt"
    rpt.write_text(_YOSYS_ECP5)
    modules, _ = parse_utilization(rpt)
    names = [m.module_name for m in modules]
    assert "top" in names
    assert "blinky" in names
    assert len(modules) == 2


# ── Test 7: Missing file → ([], None) ────────────────────────────────────────

def test_missing_file_returns_empty(tmp_path):
    modules, tool = parse_utilization(tmp_path / "absent.rpt")
    assert modules == []
    assert tool is None


# ── Test 8: Unrecognised format → ([], None) ─────────────────────────────────

def test_unrecognised_format_returns_empty(tmp_path):
    rpt = tmp_path / "garbage.txt"
    rpt.write_text("hello world\nthis is not a report\n")
    modules, tool = parse_utilization(rpt)
    assert modules == []
    assert tool is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/james/Workspace/files
pytest scripts/hdl_autodoc/tests/test_parse_utilization.py -v
```

Expected: `ModuleNotFoundError: No module named 'parse_utilization'`

- [ ] **Step 3: Implement parse_utilization.py**

Create `scripts/hdl_autodoc/parse_utilization.py`:

```python
"""
parse_utilization.py
--------------------
Parse synthesis utilization reports from Vivado and Yosys into a common
data model.

Public API
----------
    from parse_utilization import ModuleUtilization, parse_utilization

    modules, tool = parse_utilization(Path("reports/vivado/utilization_placed.rpt"))
    # tool  → "vivado" | "yosys" | None
    # modules[0]  → top-level totals
    # modules[1:] → per-instance breakdown (only when hierarchical data present)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModuleUtilization:
    module_name: str
    luts: int = 0
    ffs: int = 0
    brams: int = 0
    dsps: int = 0
    luts_available: int | None = None   # Vivado only
    ffs_available: int | None = None    # Vivado only


# ── Yosys cell-name → resource category ──────────────────────────────────────
# Cell names are lower-cased before matching.
_LUT_CELLS = frozenset({
    "$lut", "lut4", "sb_lut4", "trellis_comb", "ice_lc",
})
_FF_CELLS = frozenset({
    "$dff", "$dffe", "$adff", "$adffe", "$sdff", "$sdffe",
    "dff", "dffe", "fdre", "fdce", "fdpe", "fdse",
    "sb_dff", "sb_dffe", "sb_dffr", "sb_dffs", "sb_dffsr",
    "trellis_ff",
})
_BRAM_CELLS = frozenset({
    "sb_ram40_4k", "sb_ram40_4knr", "sb_ram40_4knrnw",
    "trellis_bram", "dp16kd", "pdp16kd",
    "ramb18e1", "ramb18e2", "ramb36e1", "ramb36e2",
})
_DSP_CELLS = frozenset({
    "sb_mac16", "mult18x18d", "alu24b",
    "dsp48e1", "dsp48e2",
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_int(s: str) -> int:
    return int(s.replace(",", "").strip())


def _vivado_row(text: str, label_re: str) -> tuple[int, int | None]:
    """
    Extract (Used, Available) from a Vivado ASCII table row.
    Row format: | label | Used | Fixed | Prohibited | Available | Util% |
    Returns (0, None) when the row is absent.
    """
    m = re.search(
        r'\|\s*' + label_re + r'\s*\|'
        r'\s*(\d[\d,]*)\s*\|'    # Used
        r'[^|]*\|'               # Fixed
        r'[^|]*\|'               # Prohibited
        r'\s*(\d[\d,]*)\s*\|',   # Available
        text,
        re.IGNORECASE,
    )
    if m:
        return _parse_int(m.group(1)), _parse_int(m.group(2))
    m2 = re.search(
        r'\|\s*' + label_re + r'\s*\|\s*(\d[\d,]*)\s*\|',
        text,
        re.IGNORECASE,
    )
    if m2:
        return _parse_int(m2.group(1)), None
    return 0, None


def _normalise_instance(name: str) -> str:
    """Strip common instance prefixes and lowercase: u_blinky → blinky."""
    return re.sub(r'^[ui]_', '', name.strip()).lower()


# ── Vivado parser ─────────────────────────────────────────────────────────────

def _parse_vivado(text: str) -> list[ModuleUtilization]:
    # Top-level summary from the Slice Logic table
    top = ModuleUtilization(module_name="top")
    luts, luts_av = _vivado_row(text, r"Slice LUTs\*?")
    if luts == 0:
        luts, luts_av = _vivado_row(text, r"LUT as Logic")
    top.luts, top.luts_available = luts, luts_av

    ffs, ffs_av = _vivado_row(text, r"Slice Registers")
    if ffs == 0:
        ffs, ffs_av = _vivado_row(text, r"Register as Flip Flop")
    top.ffs, top.ffs_available = ffs, ffs_av

    top.brams, _ = _vivado_row(text, r"Block RAM Tile")
    top.dsps,  _ = _vivado_row(text, r"DSPs?")

    # Hierarchical section — detect by "| Instance |" header row
    hdr = re.search(r'\|\s*Instance\s*\|[^\n]*\n', text, re.IGNORECASE)
    if not hdr:
        return [top]

    hdr_cols = [c.strip().lower() for c in hdr.group(0).split("|")]
    col: dict[str, int] = {}
    for i, h in enumerate(hdr_cols):
        if re.match(r"lut", h):    col["luts"]  = i
        elif re.match(r"ff", h):   col["ffs"]   = i
        elif re.match(r"bram", h): col["brams"] = i
        elif re.match(r"dsp", h):  col["dsps"]  = i
    if "luts" not in col or "ffs" not in col:
        return [top]

    # Data rows live between the two +---+ separators that bracket the table body
    sep_re = re.compile(r'^\+[-+]+\+\s*$', re.MULTILINE)
    hier_results: list[ModuleUtilization] = []
    for sep_match in sep_re.finditer(text, hdr.end()):
        row_start = sep_match.end()
        end_match = sep_re.search(text, row_start)
        if not end_match:
            break
        for line in text[row_start:end_match.start()].split("\n"):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")]
            if len(cells) < max(col.values()) + 1:
                continue
            inst = cells[1]
            if not inst or inst.startswith("("):
                continue
            clean = _normalise_instance(inst)
            if not clean:
                continue
            try:
                hier_results.append(ModuleUtilization(
                    module_name=clean,
                    luts  = _parse_int(cells[col["luts"]]),
                    ffs   = _parse_int(cells[col["ffs"]]),
                    brams = _parse_int(cells[col["brams"]]) if "brams" in col else 0,
                    dsps  = _parse_int(cells[col["dsps"]])  if "dsps"  in col else 0,
                ))
            except (ValueError, IndexError):
                continue
        break  # only the first hierarchical table

    return hier_results if hier_results else [top]


# ── Yosys stat parser ─────────────────────────────────────────────────────────

def _parse_yosys(text: str) -> list[ModuleUtilization]:
    results: list[ModuleUtilization] = []
    sections = re.split(r'^=== (.+?) ===$', text, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        name = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""
        if name.lower() == "aggregate":
            continue
        mu = ModuleUtilization(module_name=name.lower())
        for line in body.split("\n"):
            m = re.match(r'\s+(\S+)\s+(\d+)', line)
            if not m:
                continue
            cell  = m.group(1).lower()
            count = int(m.group(2))
            if cell in _LUT_CELLS:   mu.luts   += count
            elif cell in _FF_CELLS:  mu.ffs    += count
            elif cell in _BRAM_CELLS: mu.brams += count
            elif cell in _DSP_CELLS:  mu.dsps  += count
        results.append(mu)
    return results


# ── Public API ────────────────────────────────────────────────────────────────

def parse_utilization(path: Path) -> tuple[list[ModuleUtilization], str | None]:
    """
    Parse a utilization report file.

    Returns (modules, tool) where tool is "vivado", "yosys", or None.
    Returns ([], None) if the file does not exist or format is unrecognised.
    """
    if not path.exists():
        return [], None
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return [], None

    if re.search(r'\|\s*Site Type\s*\|', text) or "Slice LUTs" in text:
        return _parse_vivado(text), "vivado"
    if re.search(r'^=== .+ ===$', text, re.MULTILINE):
        return _parse_yosys(text), "yosys"
    return [], None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_parse_utilization.py -v
```

Expected output:
```
test_parse_utilization.py::test_vivado_top_level_luts_ffs_brams_dsps PASSED
test_parse_utilization.py::test_vivado_luts_available PASSED
test_parse_utilization.py::test_vivado_hierarchical_per_module PASSED
test_parse_utilization.py::test_yosys_ecp5_trellis PASSED
test_parse_utilization.py::test_yosys_ice40_sb PASSED
test_parse_utilization.py::test_yosys_multiple_modules PASSED
test_parse_utilization.py::test_missing_file_returns_empty PASSED
test_parse_utilization.py::test_unrecognised_format_returns_empty PASSED

8 passed
```

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/parse_utilization.py \
        scripts/hdl_autodoc/tests/test_parse_utilization.py
git commit -m "feat: add parse_utilization — Vivado and Yosys utilization report parser"
```

---

### Task 2: parse_timing.py — timing report parser

**Files:**
- Create: `scripts/hdl_autodoc/parse_timing.py`
- Create: `scripts/hdl_autodoc/tests/test_parse_timing.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass
  class ClockTiming:
      clock_name: str
      fmax_mhz: float
      wns_ns: float | None = None          # Vivado: worst negative slack
      period_ns: float | None = None       # Vivado: constraint period
      constraint_mhz: float | None = None  # nextpnr: requested frequency
      passing: bool | None = None          # nextpnr: True = PASS, False = FAIL

  def parse_timing(path: Path) -> tuple[list[ClockTiming], str | None]:
      """
      Returns (clocks, tool) where tool is "vivado", "nextpnr", or None.
      Returns ([], None) if the file does not exist or format is unrecognised.
      """
  ```

- [ ] **Step 1: Write the failing tests**

Create `scripts/hdl_autodoc/tests/test_parse_timing.py`:

```python
"""
test_parse_timing.py
---------------------
Tests for parse_timing.py.

Covers:
  1.  Vivado: WNS parsed correctly
  2.  Vivado: fmax = 1000 / (period - WNS), rounded to 2 dp
  3.  Vivado: multiple clocks produce multiple ClockTiming entries
  4.  nextpnr: fmax extracted directly from log line
  5.  nextpnr: PASS → passing=True; FAIL → passing=False
  6.  nextpnr: ugly clock name ($glbnet$clk$TRELLIS_IO_IN) cleaned to 'clk'
  7.  Missing file → ([], None)
"""

import pytest
from pathlib import Path

from parse_timing import ClockTiming, parse_timing


# ── Sample report text ────────────────────────────────────────────────────────

_VIVADO_TIMING = """\
------------------------------------------------------------------------------------------------
| Design Timing Summary
| ---------------------
------------------------------------------------------------------------------------------------

    WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints
      1.234        0.000                      0                   42

Clock Summary
| Clock | Waveform(ns)       | Period(ns) | Frequency(MHz) |
| clk   | {0.000 5.000}      | 10.000     | 100.000        |
"""

_VIVADO_TWO_CLOCKS = """\
    WNS(ns)      TNS(ns)  TNS Failing Endpoints  TNS Total Endpoints
      0.500        0.000                      0                   10

Clock Summary
| Clock  | Waveform(ns)       | Period(ns) | Frequency(MHz) |
| clk    | {0.000 5.000}      | 10.000     | 100.000        |
| clk_2x | {0.000 2.500}      |  5.000     | 200.000        |
"""

_NEXTPNR_PASS = """\
Info: Target frequency: 50.00 MHz
Info: Max frequency for clock 'clk': 87.23 MHz (PASS at 50.00 MHz)
"""

_NEXTPNR_FAIL = """\
Info: Max frequency for clock 'clk': 43.15 MHz (FAIL at 50.00 MHz)
"""

_NEXTPNR_UGLY_NAME = """\
Info: Max frequency for clock '$glbnet$clk$TRELLIS_IO_IN': 87.23 MHz (PASS at 50.00 MHz)
"""


# ── Test 1: Vivado WNS ────────────────────────────────────────────────────────

def test_vivado_wns_parsed(tmp_path):
    rpt = tmp_path / "timing.rpt"
    rpt.write_text(_VIVADO_TIMING)
    clocks, tool = parse_timing(rpt)
    assert tool == "vivado"
    assert len(clocks) == 1
    assert clocks[0].wns_ns == pytest.approx(1.234)


# ── Test 2: Vivado fmax derivation ────────────────────────────────────────────

def test_vivado_fmax_computed(tmp_path):
    # fmax = 1000 / (10.000 - 1.234) = 1000 / 8.766 ≈ 114.09 MHz
    rpt = tmp_path / "timing.rpt"
    rpt.write_text(_VIVADO_TIMING)
    clocks, _ = parse_timing(rpt)
    assert clocks[0].fmax_mhz == pytest.approx(1000.0 / (10.0 - 1.234), rel=1e-3)
    assert clocks[0].period_ns == pytest.approx(10.0)
    assert clocks[0].clock_name == "clk"


# ── Test 3: Vivado multiple clocks ────────────────────────────────────────────

def test_vivado_multiple_clocks(tmp_path):
    rpt = tmp_path / "timing.rpt"
    rpt.write_text(_VIVADO_TWO_CLOCKS)
    clocks, tool = parse_timing(rpt)
    assert tool == "vivado"
    assert len(clocks) == 2
    names = {c.clock_name for c in clocks}
    assert "clk" in names
    assert "clk_2x" in names


# ── Test 4: nextpnr fmax ──────────────────────────────────────────────────────

def test_nextpnr_fmax(tmp_path):
    rpt = tmp_path / "nextpnr.log"
    rpt.write_text(_NEXTPNR_PASS)
    clocks, tool = parse_timing(rpt)
    assert tool == "nextpnr"
    assert len(clocks) == 1
    assert clocks[0].fmax_mhz == pytest.approx(87.23)
    assert clocks[0].constraint_mhz == pytest.approx(50.0)


# ── Test 5: nextpnr PASS / FAIL ───────────────────────────────────────────────

def test_nextpnr_pass_sets_passing_true(tmp_path):
    rpt = tmp_path / "nextpnr.log"
    rpt.write_text(_NEXTPNR_PASS)
    clocks, _ = parse_timing(rpt)
    assert clocks[0].passing is True


def test_nextpnr_fail_sets_passing_false(tmp_path):
    rpt = tmp_path / "nextpnr.log"
    rpt.write_text(_NEXTPNR_FAIL)
    clocks, _ = parse_timing(rpt)
    assert clocks[0].passing is False


# ── Test 6: nextpnr ugly clock name cleaned ────────────────────────────────────

def test_nextpnr_ugly_clock_name_cleaned(tmp_path):
    rpt = tmp_path / "nextpnr.log"
    rpt.write_text(_NEXTPNR_UGLY_NAME)
    clocks, _ = parse_timing(rpt)
    # $glbnet$clk$TRELLIS_IO_IN → clk
    assert clocks[0].clock_name == "clk"


# ── Test 7: Missing file ──────────────────────────────────────────────────────

def test_missing_file_returns_empty(tmp_path):
    clocks, tool = parse_timing(tmp_path / "absent.rpt")
    assert clocks == []
    assert tool is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_parse_timing.py -v
```

Expected: `ModuleNotFoundError: No module named 'parse_timing'`

- [ ] **Step 3: Implement parse_timing.py**

Create `scripts/hdl_autodoc/parse_timing.py`:

```python
"""
parse_timing.py
---------------
Parse timing reports from Vivado (report_timing_summary) and nextpnr
(--log output) into a common data model.

Public API
----------
    from parse_timing import ClockTiming, parse_timing

    clocks, tool = parse_timing(Path("reports/vivado/timing_summary_routed.rpt"))
    # tool  → "vivado" | "nextpnr" | None
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClockTiming:
    clock_name: str
    fmax_mhz: float
    wns_ns: float | None = None          # Vivado: worst negative slack
    period_ns: float | None = None       # Vivado: constraint period (ns)
    constraint_mhz: float | None = None  # nextpnr: requested frequency
    passing: bool | None = None          # nextpnr: True = PASS, False = FAIL


def _clean_clock_name(name: str) -> str:
    """
    Normalise a clock name.
    nextpnr emits names like '$glbnet$clk$TRELLIS_IO_IN' — extract the
    first non-empty, non-all-uppercase segment between '$' delimiters.
    Plain names (no '$') are returned unchanged.
    """
    if "$" not in name:
        return name
    parts = [p for p in name.split("$") if p and not p.isupper()]
    return parts[0] if parts else name


def _parse_vivado(text: str) -> list[ClockTiming]:
    """Parse Vivado report_timing_summary output."""
    # WNS from the Design Timing Summary data row
    # Header:  WNS(ns)      TNS(ns)  ...
    # Data:      1.234        0.000  ...
    wns: float | None = None
    m = re.search(r'WNS\(ns\)[^\n]*\n\s*([-\d.]+)', text)
    if m:
        try:
            wns = float(m.group(1))
        except ValueError:
            pass

    # Clock Summary table rows
    # | Clock | Waveform(ns)  | Period(ns) | Frequency(MHz) |
    # | clk   | {0.000 5.000} | 10.000     | 100.000        |
    clocks: list[ClockTiming] = []
    for cm in re.finditer(
        r'\|\s*(\S+)\s*\|\s*\{[^}]+\}\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|',
        text,
    ):
        name   = cm.group(1)
        period = float(cm.group(2))
        if wns is not None and period > wns:
            fmax = round(1000.0 / (period - wns), 2)
        else:
            fmax = round(1000.0 / period, 2)
        clocks.append(ClockTiming(
            clock_name=_clean_clock_name(name),
            fmax_mhz=fmax,
            wns_ns=wns,
            period_ns=period,
        ))
    return clocks


def _parse_nextpnr(text: str) -> list[ClockTiming]:
    """Parse nextpnr --log output for 'Max frequency for clock' lines."""
    clocks: list[ClockTiming] = []
    for m in re.finditer(
        r"Max frequency for clock '([^']+)':\s*([\d.]+)\s*MHz\s*"
        r"\((PASS|FAIL)\s+at\s*([\d.]+)\s*MHz\)",
        text,
        re.IGNORECASE,
    ):
        clocks.append(ClockTiming(
            clock_name=_clean_clock_name(m.group(1)),
            fmax_mhz=float(m.group(2)),
            passing=(m.group(3).upper() == "PASS"),
            constraint_mhz=float(m.group(4)),
        ))
    return clocks


def parse_timing(path: Path) -> tuple[list[ClockTiming], str | None]:
    """
    Parse a timing report file.

    Returns (clocks, tool) where tool is "vivado", "nextpnr", or None.
    Returns ([], None) if the file does not exist or format is unrecognised.
    """
    if not path.exists():
        return [], None
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return [], None

    if "WNS(ns)" in text or "Design Timing Summary" in text:
        return _parse_vivado(text), "vivado"
    if "Max frequency for clock" in text:
        return _parse_nextpnr(text), "nextpnr"
    return [], None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_parse_timing.py -v
```

Expected output:
```
test_parse_timing.py::test_vivado_wns_parsed PASSED
test_parse_timing.py::test_vivado_fmax_computed PASSED
test_parse_timing.py::test_vivado_multiple_clocks PASSED
test_parse_timing.py::test_nextpnr_fmax PASSED
test_parse_timing.py::test_nextpnr_pass_sets_passing_true PASSED
test_parse_timing.py::test_nextpnr_fail_sets_passing_false PASSED
test_parse_timing.py::test_nextpnr_ugly_clock_name_cleaned PASSED
test_parse_timing.py::test_missing_file_returns_empty PASSED

8 passed
```

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/parse_timing.py \
        scripts/hdl_autodoc/tests/test_parse_timing.py
git commit -m "feat: add parse_timing — Vivado timing summary and nextpnr log parser"
```

---

### Task 3: extract_reports.py — RST generator and orchestrator

**Files:**
- Create: `scripts/hdl_autodoc/extract_reports.py`
- Create: `scripts/hdl_autodoc/tests/test_extract_reports.py`

**Interfaces:**
- Consumes from Task 1: `ModuleUtilization`, `parse_utilization(path)`
- Consumes from Task 2: `ClockTiming`, `parse_timing(path)`
- Produces (callable from tests and from `main()`):
  ```python
  def synthesis_index_rst(
      util_modules: list[ModuleUtilization],
      util_tool: str | None,
      clocks: list[ClockTiming],
      timing_tool: str | None,
  ) -> str: ...

  def module_synthesis_rst(
      module_name: str,
      util: ModuleUtilization | None,
  ) -> str: ...

  def main(hierarchy_path: Path, docs_dir: Path, reports_dir: Path) -> None:
      """Writes synthesis/index.rst and modules/*/synthesis.rst."""
  ```

- [ ] **Step 1: Write the failing tests**

Create `scripts/hdl_autodoc/tests/test_extract_reports.py`:

```python
"""
test_extract_reports.py
------------------------
Tests for extract_reports.py.

Covers:
  1.  synthesis_index_rst with no reports → placeholder text present
  2.  synthesis_index_rst with timing → Timing section with fmax
  3.  synthesis_index_rst with utilization → Utilization table with module name
  4.  module_synthesis_rst with no util → placeholder text present
  5.  module_synthesis_rst with util → LUT/FF/BRAM/DSP counts in RST
  6.  main() with no report files → synthesis/index.rst written with placeholder
  7.  main() with no report files → synthesis.rst written for each module
"""

import json
import pytest
from pathlib import Path

from parse_utilization import ModuleUtilization
from parse_timing import ClockTiming
from extract_reports import (
    synthesis_index_rst,
    module_synthesis_rst,
    main,
)


# ── Test 1: placeholder when no reports ──────────────────────────────────────

def test_synthesis_index_placeholder_when_no_reports():
    rst = synthesis_index_rst([], None, [], None)
    assert "No synthesis reports available" in rst
    assert "make reports" in rst


# ── Test 2: timing section present when clocks provided ──────────────────────

def test_synthesis_index_with_timing():
    clocks = [ClockTiming(clock_name="clk", fmax_mhz=87.23,
                          constraint_mhz=50.0, passing=True)]
    rst = synthesis_index_rst([], None, clocks, "nextpnr")
    assert "Timing" in rst
    assert "87.23" in rst
    assert "clk" in rst


# ── Test 3: utilization table present when modules provided ───────────────────

def test_synthesis_index_with_utilization():
    modules = [ModuleUtilization(module_name="top", luts=142, ffs=89)]
    rst = synthesis_index_rst(modules, "vivado", [], None)
    assert "Utilization" in rst
    assert "top" in rst
    assert "142" in rst


# ── Test 4: per-module placeholder when no util ───────────────────────────────

def test_module_synthesis_placeholder_when_no_util():
    rst = module_synthesis_rst("blinky", None)
    assert "No synthesis data available" in rst


# ── Test 5: per-module RST with util data ────────────────────────────────────

def test_module_synthesis_with_util():
    util = ModuleUtilization(module_name="blinky", luts=12, ffs=8, brams=0, dsps=0)
    rst = module_synthesis_rst("blinky", util)
    assert "12" in rst
    assert "8" in rst
    assert "LUTs" in rst
    assert "FFs" in rst


# ── Test 6: main() writes synthesis/index.rst ────────────────────────────────

def test_main_writes_synthesis_index(tmp_path):
    hierarchy = {
        "top": "top",
        "modules": {
            "top": {"file": "src/top.vhd", "children": [], "shared": False},
        },
    }
    hier_path = tmp_path / "hierarchy.json"
    hier_path.write_text(json.dumps(hierarchy))
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    main(hier_path, docs_dir, reports_dir)

    synth_index = docs_dir / "synthesis" / "index.rst"
    assert synth_index.exists()
    assert "No synthesis reports available" in synth_index.read_text()


# ── Test 7: main() writes synthesis.rst for each module ──────────────────────

def test_main_writes_per_module_synthesis(tmp_path):
    hierarchy = {
        "top": "top",
        "modules": {
            "top":    {"file": "src/top.vhd",    "children": ["blinky"], "shared": False},
            "blinky": {"file": "src/blinky.vhd", "children": [],         "shared": False},
        },
    }
    hier_path = tmp_path / "hierarchy.json"
    hier_path.write_text(json.dumps(hierarchy))
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    main(hier_path, docs_dir, reports_dir)

    assert (docs_dir / "modules" / "top"    / "synthesis.rst").exists()
    assert (docs_dir / "modules" / "blinky" / "synthesis.rst").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_extract_reports.py -v
```

Expected: `ModuleNotFoundError: No module named 'extract_reports'`

- [ ] **Step 3: Implement extract_reports.py**

Create `scripts/hdl_autodoc/extract_reports.py`:

```python
"""
extract_reports.py
------------------
Orchestrate utilization and timing parsers, then write implementation RST.

Writes:
  docs/hdl_autodoc/synthesis/index.rst        — top-level Implementation page
  docs/hdl_autodoc/modules/<n>/synthesis.rst  — per-module utilization

Usage:
    python scripts/hdl_autodoc/extract_reports.py \\
        docs/hdl_autodoc/hierarchy.json \\
        docs/hdl_autodoc \\
        reports
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from parse_utilization import ModuleUtilization, parse_utilization
from parse_timing import ClockTiming, parse_timing


# ── RST rendering ─────────────────────────────────────────────────────────────

_PLACEHOLDER = """\
Implementation
==============

No synthesis reports available.

Run ``make reports`` after completing synthesis and place-and-route
to populate this page. Place report files in::

    reports/vivado/utilization_placed.rpt
    reports/vivado/timing_summary_routed.rpt

or::

    reports/yosys/stat.txt
    reports/yosys/nextpnr.log
"""

_MODULE_PLACEHOLDER = """\
Synthesis Results
=================

*No synthesis data available for this module.*
"""


def _timing_table_rst(clocks: list[ClockTiming], tool: str) -> str:
    if tool == "vivado":
        lines = [
            ".. list-table::",
            "   :header-rows: 1",
            "",
            "   * - Clock",
            "     - Fmax (MHz)",
            "     - Period (ns)",
            "     - WNS (ns)",
            "",
        ]
        for c in clocks:
            lines += [
                f"   * - {c.clock_name}",
                f"     - {c.fmax_mhz:.1f}",
                f"     - {c.period_ns:.3f}" if c.period_ns is not None else "     - —",
                f"     - {c.wns_ns:+.3f}"   if c.wns_ns  is not None  else "     - —",
                "",
            ]
    else:  # nextpnr
        lines = [
            ".. list-table::",
            "   :header-rows: 1",
            "",
            "   * - Clock",
            "     - Fmax (MHz)",
            "     - Target (MHz)",
            "     - Status",
            "",
        ]
        for c in clocks:
            status = ("✔ PASS" if c.passing else "✘ FAIL") if c.passing is not None else "—"
            lines += [
                f"   * - {c.clock_name}",
                f"     - {c.fmax_mhz:.1f}",
                f"     - {c.constraint_mhz:.1f}" if c.constraint_mhz is not None else "     - —",
                f"     - {status}",
                "",
            ]
    return "\n".join(lines)


def _utilization_table_rst(modules: list[ModuleUtilization], vivado: bool) -> str:
    avail_luts = modules[0].luts_available if vivado and modules else None
    avail_ffs  = modules[0].ffs_available  if vivado and modules else None
    lut_header = f"LUTs / {avail_luts:,}" if avail_luts else "LUTs"
    ff_header  = f"FFs / {avail_ffs:,}"   if avail_ffs  else "FFs"
    lines = [
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Module",
        f"     - {lut_header}",
        f"     - {ff_header}",
        "     - BRAMs",
        "     - DSPs",
        "",
    ]
    for m in modules:
        lines += [
            f"   * - {m.module_name}",
            f"     - {m.luts:,}",
            f"     - {m.ffs:,}",
            f"     - {m.brams:,}",
            f"     - {m.dsps:,}",
            "",
        ]
    return "\n".join(lines)


def synthesis_index_rst(
    util_modules: list[ModuleUtilization],
    util_tool: str | None,
    clocks: list[ClockTiming],
    timing_tool: str | None,
) -> str:
    """Return RST string for synthesis/index.rst."""
    if not util_modules and not clocks:
        return _PLACEHOLDER

    lines = ["Implementation", "==============", ""]

    if clocks and timing_tool:
        label = "Vivado" if timing_tool == "vivado" else "nextpnr"
        lines += [f"Timing — {label}", "-" * (9 + len(label)), ""]
        lines.append(_timing_table_rst(clocks, timing_tool))

    if util_modules and util_tool:
        label = "Vivado" if util_tool == "vivado" else "Yosys"
        lines += [f"Utilization — {label}", "-" * (15 + len(label)), ""]
        lines.append(_utilization_table_rst(util_modules, util_tool == "vivado"))

    return "\n".join(lines)


def module_synthesis_rst(module_name: str, util: ModuleUtilization | None) -> str:
    """Return RST string for a per-module synthesis.rst."""
    if util is None:
        return _MODULE_PLACEHOLDER
    return "\n".join([
        "Synthesis Results",
        "=================",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Resource",
        "     - Used",
        "",
        "   * - LUTs",
        f"     - {util.luts:,}",
        "",
        "   * - FFs",
        f"     - {util.ffs:,}",
        "",
        "   * - BRAMs",
        f"     - {util.brams:,}",
        "",
        "   * - DSPs",
        f"     - {util.dsps:,}",
        "",
    ])


# ── Orchestration ─────────────────────────────────────────────────────────────

def main(hierarchy_path: Path, docs_dir: Path, reports_dir: Path) -> None:
    hierarchy    = json.loads(hierarchy_path.read_text())
    module_names = list(hierarchy["modules"].keys())

    # Locate report files (prefer placed over synth for Vivado utilization)
    vivado_util  = reports_dir / "vivado" / "utilization_placed.rpt"
    if not vivado_util.exists():
        vivado_util  = reports_dir / "vivado" / "utilization_synth.rpt"
    yosys_util   = reports_dir / "yosys"  / "stat.txt"
    vivado_time  = reports_dir / "vivado" / "timing_summary_routed.rpt"
    nextpnr_time = reports_dir / "yosys"  / "nextpnr.log"

    util_modules, util_tool = parse_utilization(vivado_util)
    if not util_modules:
        util_modules, util_tool = parse_utilization(yosys_util)

    clocks, timing_tool = parse_timing(vivado_time)
    if not clocks:
        clocks, timing_tool = parse_timing(nextpnr_time)

    # Write synthesis/index.rst
    synth_dir = docs_dir / "synthesis"
    synth_dir.mkdir(parents=True, exist_ok=True)
    index_path = synth_dir / "index.rst"
    index_path.write_text(synthesis_index_rst(util_modules, util_tool, clocks, timing_tool))
    print(f"  → {index_path}")

    # Write per-module synthesis.rst
    util_by_name = {m.module_name: m for m in util_modules}
    for name in module_names:
        mod_dir = docs_dir / "modules" / name
        mod_dir.mkdir(parents=True, exist_ok=True)
        rst_path = mod_dir / "synthesis.rst"
        rst_path.write_text(module_synthesis_rst(name, util_by_name.get(name)))
        print(f"  → {rst_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: extract_reports.py <hierarchy.json> <docs_dir> <reports_dir>")
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_extract_reports.py -v
```

Expected output:
```
test_extract_reports.py::test_synthesis_index_placeholder_when_no_reports PASSED
test_extract_reports.py::test_synthesis_index_with_timing PASSED
test_extract_reports.py::test_synthesis_index_with_utilization PASSED
test_extract_reports.py::test_module_synthesis_placeholder_when_no_util PASSED
test_extract_reports.py::test_module_synthesis_with_util PASSED
test_extract_reports.py::test_main_writes_synthesis_index PASSED
test_extract_reports.py::test_main_writes_per_module_synthesis PASSED

7 passed
```

- [ ] **Step 5: Run the full test suite to confirm no regressions**

```bash
pytest scripts/hdl_autodoc/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all pre-existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/hdl_autodoc/extract_reports.py \
        scripts/hdl_autodoc/tests/test_extract_reports.py
git commit -m "feat: add extract_reports — synthesis RST generator for Vivado/Yosys reports"
```

---

### Task 4: generate_rst.py toctree wiring + Makefile target

**Files:**
- Modify: `scripts/hdl_autodoc/generate_rst.py` (functions `module_index_rst`, `index_rst`, and `main`)
- Modify: `scripts/hdl_autodoc/tests/test_generate_rst.py` (append 4 tests)
- Modify: `Makefile`

**Interfaces:**
- Consumes from Task 3: `synthesis/index.rst` and `modules/*/synthesis.rst` files on disk (detected by `.exists()` check)
- `module_index_rst` new signature:
  ```python
  def module_index_rst(entity, children, shared_children,
                       has_processes=True, has_registers=False,
                       has_synthesis=False) -> str
  ```
- `index_rst` new signature:
  ```python
  def index_rst(entities, project_name, hierarchy=None,
                has_coverage=False, modules_with_regs=None,
                has_synthesis=False) -> str
  ```

- [ ] **Step 1: Write the failing tests**

Append these four tests to the end of `scripts/hdl_autodoc/tests/test_generate_rst.py`:

```python
# ─────────────────────────────────────────────────────────────────────────────
# has_synthesis — module_index_rst
# ─────────────────────────────────────────────────────────────────────────────

def test_module_index_includes_synthesis_when_has_synthesis_true():
    """synthesis is added to the module toctree when has_synthesis=True."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set(),
                           has_synthesis=True)
    assert "synthesis" in rst


def test_module_index_omits_synthesis_when_has_synthesis_false():
    """synthesis is NOT added to the module toctree when has_synthesis=False."""
    rst = module_index_rst(_make_entity(), children=[], shared_children=set(),
                           has_synthesis=False)
    assert "synthesis" not in rst


# ─────────────────────────────────────────────────────────────────────────────
# has_synthesis — index_rst (top-level)
# ─────────────────────────────────────────────────────────────────────────────

def test_top_index_has_implementation_section_when_has_synthesis_true():
    """synthesis/index is included and 'Implementation' caption present."""
    rst = index_rst([_make_entity()], "MyProject", has_synthesis=True)
    assert "synthesis/index" in rst
    assert "Implementation" in rst


def test_top_index_no_implementation_section_when_has_synthesis_false():
    """synthesis/index is NOT present when has_synthesis=False."""
    rst = index_rst([_make_entity()], "MyProject", has_synthesis=False)
    assert "synthesis/index" not in rst
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_rst.py \
    -k "synthesis" -v
```

Expected: all 4 FAIL — `module_index_rst` and `index_rst` don't yet accept `has_synthesis`.

- [ ] **Step 3: Update module_index_rst in generate_rst.py**

Find the function `module_index_rst` (around line 155). Change its signature and add the `has_synthesis` entry after `has_registers`:

Old signature:
```python
def module_index_rst(entity: dict, children: list[str],
                     shared_children: set[str],
                     has_processes: bool = True,
                     has_registers: bool = False) -> str:
```

New signature:
```python
def module_index_rst(entity: dict, children: list[str],
                     shared_children: set[str],
                     has_processes: bool = True,
                     has_registers: bool = False,
                     has_synthesis: bool = False) -> str:
```

Find the block where `has_registers` is used (around line 176–178):

Old:
```python
    if has_registers:
        lines.append("   registers")
    lines.append("")
```

New:
```python
    if has_registers:
        lines.append("   registers")
    if has_synthesis:
        lines.append("   synthesis")
    lines.append("")
```

- [ ] **Step 4: Update index_rst in generate_rst.py**

Find the function `index_rst` (around line 448). Change its signature:

Old signature:
```python
def index_rst(entities: list[dict], project_name: str,
              hierarchy: dict = None, has_coverage: bool = False,
              modules_with_regs: list[str] | None = None) -> str:
```

New signature:
```python
def index_rst(entities: list[dict], project_name: str,
              hierarchy: dict = None, has_coverage: bool = False,
              modules_with_regs: list[str] | None = None,
              has_synthesis: bool = False) -> str:
```

Find the `:caption: Contents` line in the function body and change it to `:caption: Design`:

Old:
```python
    lines = [
        project_name, "=" * len(project_name), "",
        ".. toctree::",
        "   :maxdepth: 4",
        "   :caption: Contents",
        "",
        "   overview",
    ]
```

New:
```python
    lines = [
        project_name, "=" * len(project_name), "",
        ".. toctree::",
        "   :maxdepth: 4",
        "   :caption: Design",
        "",
        "   overview",
    ]
```

Find the `if has_coverage:` block (around line 474) and add the Implementation toctree block after it:

Old:
```python
    if has_coverage:
        lines.append("   coverage")

    lines += [
        "",
        "Indices", "-------", "",
```

New:
```python
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
```

- [ ] **Step 5: Update main() in generate_rst.py to detect synthesis files**

In `generate_rst.py`'s `main()`, find the loop over entities where `has_registers` is detected (around line 584). Add `has_synthesis` detection on the next line:

Old:
```python
        has_processes = (mod_dir / "processes" / "index.rst").exists()
        has_registers = (mod_dir / "registers.rst").exists()
        if has_registers:
            modules_with_regs.append(name)
        results.append(write_always(
            mod_dir / "index.rst",
            module_index_rst(entity, children, shared_names,
                             has_processes=has_processes,
                             has_registers=has_registers)
        ))
```

New:
```python
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
```

In the same `main()`, find where `index_rst` is called (around line 631–634):

Old:
```python
    results.append(write_always(
        docs_dir / "index.rst",
        index_rst(entities, project_name, hierarchy, has_coverage=has_coverage,
                  modules_with_regs=modules_with_regs or None)
    ))
```

New:
```python
    has_synthesis_index = (docs_dir / "synthesis" / "index.rst").exists()
    results.append(write_always(
        docs_dir / "index.rst",
        index_rst(entities, project_name, hierarchy, has_coverage=has_coverage,
                  modules_with_regs=modules_with_regs or None,
                  has_synthesis=has_synthesis_index)
    ))
```

- [ ] **Step 6: Run all generate_rst tests**

```bash
pytest scripts/hdl_autodoc/tests/test_generate_rst.py -v
```

Expected: all existing tests still pass, plus the 4 new synthesis tests.

- [ ] **Step 7: Update Makefile**

Make three changes to the `Makefile`:

**Change 1** — add `reports` to `.PHONY` line (line 51–52):

Old:
```makefile
.PHONY: help venv install hierarchy scaffold extract html pdf \
        coverage clean clean-generated clean-all
```

New:
```makefile
.PHONY: help venv install hierarchy scaffold extract reports html pdf \
        coverage clean clean-generated clean-all
```

**Change 2** — add `reports` target after the `coverage` target (after line 104):

Old:
```makefile
# ── Step 3b: coverage report (opt-in, runs independently after extract) ──────
coverage: hierarchy
	python $(AUTODOC_SCRIPTDIR)/generate_coverage.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR)
```

New:
```makefile
# ── Step 3b: coverage report (opt-in, runs independently after extract) ──────
coverage: hierarchy
	python $(AUTODOC_SCRIPTDIR)/generate_coverage.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR)

# ── Step 3c: synthesis/PnR report ingestion (opt-in, after CI generates reports/) ──
reports: hierarchy
	@echo "Ingesting synthesis reports..."
	python $(AUTODOC_SCRIPTDIR)/extract_reports.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) reports
	@echo "Regenerating RST for implementation pages..."
	python $(AUTODOC_SCRIPTDIR)/generate_rst.py src $(AUTODOC_SOURCEDIR) "$(PROJECT)"
```

**Change 3** — add synthesis files to `clean-generated` (after the `coverage.rst` line at line 142):

Old:
```makefile
	rm -f  $(AUTODOC_SOURCEDIR)/coverage.rst
	rm -f  $(AUTODOC_SOURCEDIR)/.extract_cache.json
```

New:
```makefile
	rm -f  $(AUTODOC_SOURCEDIR)/coverage.rst
	rm -f  $(AUTODOC_SOURCEDIR)/synthesis/index.rst
	rm -rf $(AUTODOC_SOURCEDIR)/synthesis
	rm -f  $(AUTODOC_SOURCEDIR)/.extract_cache.json
```

Also add `synthesis.rst` to the per-module `find` command (around line 153):

Old (the find command in clean-generated):
```makefile
	     -o -name "registers.rst" \
	     -o -name "*.dot"  -o -name "*.rst" -path "*/processes/*" \
```

New:
```makefile
	     -o -name "registers.rst" \
	     -o -name "synthesis.rst" \
	     -o -name "*.dot"  -o -name "*.rst" -path "*/processes/*" \
```

- [ ] **Step 8: Run the full test suite**

```bash
pytest scripts/hdl_autodoc/tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass (pre-existing + new).

- [ ] **Step 9: Smoke-test make reports**

```bash
make reports 2>&1 | tail -10
```

Expected output (no reports dir exists yet — the placeholder path):
```
Ingesting synthesis reports...
  → docs/hdl_autodoc/synthesis/index.rst
  → docs/hdl_autodoc/modules/top/synthesis.rst
  → docs/hdl_autodoc/modules/blinky/synthesis.rst
  ...
Regenerating RST for implementation pages...
```

- [ ] **Step 10: Smoke-test make html**

```bash
make html 2>&1 | tail -5
```

Expected: `build succeeded.` — the Implementation section appears in the ToC from the `synthesis/index.rst` placeholder.

- [ ] **Step 11: Commit**

```bash
git add scripts/hdl_autodoc/generate_rst.py \
        scripts/hdl_autodoc/tests/test_generate_rst.py \
        Makefile
git commit -m "feat: wire synthesis toctree into generate_rst and add make reports target"
```
