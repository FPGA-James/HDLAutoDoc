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
