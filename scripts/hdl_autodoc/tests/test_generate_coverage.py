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
