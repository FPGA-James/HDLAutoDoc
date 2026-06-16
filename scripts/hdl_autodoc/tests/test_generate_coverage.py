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

def test_cdc_detected_when_cdc_rst_contains_signal_crossings(tmp_path):
    mod_dir = _make_mod(tmp_path, "mymod")
    (mod_dir / "mymod_cdc.rst").write_text(
        "Signal Crossings\n----------------\n\n* clk_a to clk_b"
    )
    result = detect_coverage("mymod", tmp_path)
    assert result.cdc is True


def test_cdc_not_detected_when_cdc_rst_has_no_signal_crossings(tmp_path):
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
     - Description

   * - ``clk``
     - ``in``
     - ``std_logic``
     - System clock.

   * - ``rst``
     - ``in``
     - ``std_logic``
     - Synchronous reset.

Signals
-------

.. list-table::
   :header-rows: 1

   * - Signal
     - Type
     - Description

   * - ``state``
     - ``t_state``
     - Current state register.

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
    # top has process_count=0, all others > 0 → 4/5 have processes
    assert "4/5" in out


def test_terminal_table_separator_lines():
    out = format_terminal_table(_sample_results())
    assert "─" in out
    assert "Coverage Report" in out
