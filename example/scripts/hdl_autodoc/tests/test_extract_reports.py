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
