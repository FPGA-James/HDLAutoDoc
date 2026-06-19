"""Tests for generate_coverage.py — detection signals."""

import json
from pathlib import Path

import pytest

from generate_coverage import (
    CoverageResult,
    _depth_first_order,
    coverage_rst,
    detect_coverage,
    format_terminal_table,
    main,
)


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
    # fsm=1/2, processes=1/2, cdc=1/2, reset=0/2, ports=1/2
    assert rst.count(">1/2<") == 4   # fsm, processes, cdc, ports
    assert ">0/2<" in rst             # reset: 0 out of 2


def test_coverage_rst_multiple_rows():
    results = [
        CoverageResult("mod_a", fsm=True,  process_count=2, cdc=False, reset=True,  port_count=4),
        CoverageResult("mod_b", fsm=False, process_count=0, cdc=True,  reset=False, port_count=0),
    ]
    rst = coverage_rst(results)
    assert "mod_a" in rst
    assert "mod_b" in rst
    assert rst.count("<tr>") >= 3  # header + 2 data rows (+ tfoot row)


def test_coverage_rst_thead_has_column_headers():
    rst = coverage_rst(_one_result())
    assert "<thead>" in rst
    assert "<th>Module</th>" in rst
    assert "<th>FSM</th>" in rst
    assert "<th>Processes</th>" in rst


# ── Hierarchy ordering ────────────────────────────────────────────────────────

def _make_hierarchy(top: str, children: dict[str, list[str]]) -> dict:
    """Build a minimal hierarchy.json structure."""
    modules = {}
    for name, kids in children.items():
        modules[name] = {"file": f"src/{name}.vhd", "children": kids, "parents": []}
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
                      cdc_crossings=False, reset_cross=False, ports=0) -> None:
    mod_dir = docs_dir / "modules" / name
    mod_dir.mkdir(parents=True, exist_ok=True)

    if fsm:
        (mod_dir / f"{name}.dot").write_text("digraph {}")

    if procs > 0:
        p_dir = mod_dir / "processes"
        p_dir.mkdir(exist_ok=True)
        for i in range(procs):
            (p_dir / f"p_proc{i}.rst").write_text("")

    cdc_content = "Signal Crossings\n----------------\n\n* clk_a to clk_b" if cdc_crossings else "No crossings."
    (mod_dir / f"{name}_cdc.rst").write_text(cdc_content)

    reset_content = "Reset crossing detected." if reset_cross else "Synchronous reset only."
    (mod_dir / f"{name}_reset.rst").write_text(reset_content)

    if ports > 0:
        port_rows = "\n".join(
            f"   * - ``port{i}``\n     - ``in``\n     - ``std_logic``\n     - Port {i}.\n"
            for i in range(ports)
        )
        block = (
            f"{name} — Block Diagram\n"
            f"{'=' * (len(name) + 16)}\n\n"
            "Ports\n-----\n\n"
            ".. list-table::\n"
            "   :header-rows: 1\n\n"
            "   * - Port\n     - Direction\n     - Type\n     - Description\n\n"
            + port_rows
        )
        (mod_dir / f"{name}_block.rst").write_text(block)


def test_main_exits_if_hierarchy_missing_top_key(tmp_path):
    hjson = tmp_path / "hierarchy.json"
    hjson.write_text(json.dumps({"modules": {}}))
    with pytest.raises(SystemExit):
        main(hjson, tmp_path)


def test_main_exits_if_hierarchy_missing_modules_key(tmp_path):
    hjson = tmp_path / "hierarchy.json"
    hjson.write_text(json.dumps({"top": "foo"}))
    with pytest.raises(SystemExit):
        main(hjson, tmp_path)


def test_main_exits_if_top_module_not_in_modules(tmp_path):
    hjson = tmp_path / "hierarchy.json"
    hjson.write_text(json.dumps({"top": "missing", "modules": {"other": {"children": [], "parents": []}}}))
    with pytest.raises(SystemExit):
        main(hjson, tmp_path)


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


def test_main_prints_terminal_table(tmp_path, capsys):
    h = _make_hierarchy("top", {"top": []})
    hjson = tmp_path / "hierarchy.json"
    _write_hierarchy(hjson, h)
    _make_full_module(tmp_path, "top", ports=2)

    main(hjson, tmp_path)

    captured = capsys.readouterr()
    assert "Coverage Report" in captured.out
    assert "top" in captured.out
