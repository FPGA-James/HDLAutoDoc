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
