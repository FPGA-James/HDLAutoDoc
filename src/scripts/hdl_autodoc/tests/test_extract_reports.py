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


# ═════════════════════════════════════════════════════════════════════════════
# Build page (ECP5: Yosys + nextpnr)
# ═════════════════════════════════════════════════════════════════════════════

import os
import shutil
import subprocess
from datetime import datetime

from parse_build_info import BuildInfo, ResourceUse, WarningSummary

_YOSYS_STAT = """\
=== cnt ===

        +----------Local Count, excluding submodules.
        | 
        8   CCU2C
        1   LUT4
       16   TRELLIS_FF
"""

_NEXTPNR_LOG = """\
Warning: IO 'rst' is unconstrained in LPF and will be automatically placed
Warning: IO 'q[15]' is unconstrained in LPF and will be automatically placed
Info: Device utilisation:
Info: \t          TRELLIS_IO:      18/    197     9%
Info: \t          TRELLIS_FF:      16/  24288     0%
Info: \t        TRELLIS_COMB:      23/  24288     0%

Info: Max frequency for clock 'clk': 398.09 MHz (PASS at 100.00 MHz)
Info: Max frequency for clock 'clk': 346.86 MHz (PASS at 100.00 MHz)
"""

_YOSYS_LOG = " Yosys 0.56+186 (git sha1 83d953e95)\nABC: Warning: The network is combinational.\n"


def _reports(tmp_path, **files):
    """Create reports/yosys/<name> files; returns (hierarchy.json, docs_dir, reports_dir)."""
    h = tmp_path / "hierarchy.json"
    h.write_text(json.dumps({"top": "cnt", "modules": {"cnt": {}}}))
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    rep = tmp_path / "reports"
    (rep / "yosys").mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        data = content if isinstance(content, bytes) else content.encode()
        (rep / "yosys" / name).write_bytes(data)
    return h, docs, rep


def _full_page_args():
    return dict(
        build_info=BuildInfo("0.56+186", "nextpnr-0.8-108", "ECP5 25k class",
                             datetime(2026, 10, 31, 14, 2)),
        resources=[ResourceUse("TRELLIS_FF", 16, 24288, 0),
                   ResourceUse("TRELLIS_COMB", 23, 24288, 0)],
        warnings=WarningSummary(18, [("IO '…' is unconstrained in LPF", 17),
                                     ("The network is combinational.", 1)]),
    )


def _full_page():
    modules = [ModuleUtilization(module_name="cnt", luts=1, ffs=16)]
    clocks = [ClockTiming(clock_name="clk", fmax_mhz=346.86, constraint_mhz=100.0, passing=True)]
    return synthesis_index_rst(modules, "yosys", clocks, "nextpnr", **_full_page_args())


def test_build_page_title_and_section_order():
    rst = _full_page()
    assert rst.startswith("Build\n=====")
    assert "Implementation" not in rst
    order = [rst.index(h) for h in ("\nSummary\n", "\nUtilization", "\nTiming", "\nWarnings\n")]
    assert order == sorted(order)


def test_build_summary_lists_only_the_facts_found():
    rst = _full_page()
    summary = rst[rst.index("\nSummary\n"):rst.index("\nUtilization")]
    for fact in ("0.56+186", "nextpnr-0.8-108", "ECP5 25k class", "2026-10-31 14:02"):
        assert fact in summary
    assert "None" not in rst

    sparse = synthesis_index_rst([ModuleUtilization(module_name="cnt", luts=1)], "yosys", [], None,
                                 build_info=BuildInfo("0.56+186", None, None, None))
    assert "0.56+186" in sparse and "nextpnr" not in sparse.split("Utilization")[0].lower()
    assert "None" not in sparse


def test_build_page_shows_the_device_utilisation_table_and_keeps_the_yosys_table():
    rst = _full_page()
    util = rst[rst.index("\nUtilization"):rst.index("\nTiming")]
    assert "TRELLIS_FF" in util and "24,288" in util and "TRELLIS_COMB" in util
    assert "cnt" in util                      # the per-module Yosys table is still there


def test_build_page_warnings_table_and_the_no_warnings_case():
    rst = _full_page()
    warnings = rst[rst.index("\nWarnings\n"):]
    assert "18" in warnings and "IO '…' is unconstrained in LPF" in warnings and "17" in warnings
    clean = synthesis_index_rst([ModuleUtilization(module_name="cnt", luts=1)], "yosys", [], None,
                                warnings=WarningSummary(0, []))
    assert "No warnings" in clean


def test_old_call_shape_still_renders_without_the_new_sections():
    rst = synthesis_index_rst([ModuleUtilization(module_name="top", luts=142)], "vivado", [], None)
    assert "142" in rst and "\nSummary\n" not in rst and "\nWarnings\n" not in rst


def test_placeholder_is_titled_build():
    assert synthesis_index_rst([], None, [], None).startswith("Build\n=====")


# ── main ─────────────────────────────────────────────────────────────────────

def test_main_builds_the_full_page_from_yosys_and_nextpnr_files(tmp_path):
    h, docs, rep = _reports(tmp_path, **{"stat.txt": _YOSYS_STAT, "nextpnr.log": _NEXTPNR_LOG,
                                         "yosys.log": _YOSYS_LOG})
    assert main(h, docs, rep) is True
    page = (docs / "synthesis" / "index.rst").read_text()
    assert "0.56+186" in page and "ECP5 25k class" in page and "Reports generated" in page
    assert "346.86" in page and "398.09" not in page          # one routed row per clock
    assert "TRELLIS_COMB" in page and "Warnings" in page
    assert page.count("clk") >= 1


def test_if_present_with_no_reports_writes_nothing_and_returns_false(tmp_path, capsys):
    h, docs, rep = _reports(tmp_path)                           # reports/yosys exists, empty
    assert main(h, docs, rep, if_present=True) is False
    assert not (docs / "synthesis").exists()
    assert "skipped" in capsys.readouterr().out
    assert main(h, docs, tmp_path / "missing", if_present=True) is False


def test_if_present_ignores_empty_files(tmp_path):
    h, docs, rep = _reports(tmp_path, **{"stat.txt": "", "nextpnr.log": ""})
    assert main(h, docs, rep, if_present=True) is False
    assert not (docs / "synthesis").exists()


def test_without_if_present_the_placeholder_is_still_written(tmp_path):
    h, docs, rep = _reports(tmp_path)
    assert main(h, docs, rep) is True
    assert "No synthesis reports available" in (docs / "synthesis" / "index.rst").read_text()


def test_if_present_removes_pages_from_an_earlier_run_when_reports_are_gone(tmp_path):
    h, docs, rep = _reports(tmp_path, **{"nextpnr.log": _NEXTPNR_LOG})
    assert main(h, docs, rep, if_present=True) is True
    (rep / "yosys" / "nextpnr.log").unlink()
    assert main(h, docs, rep, if_present=True) is False
    assert not (docs / "synthesis").exists()
    assert not (docs / "modules" / "cnt" / "synthesis.rst").exists()


def test_reports_directory_may_be_absolute_relative_or_have_a_trailing_slash(tmp_path, monkeypatch):
    h, docs, rep = _reports(tmp_path, **{"nextpnr.log": _NEXTPNR_LOG})
    assert main(h, docs, rep) is True                                         # absolute
    assert main(h, docs, Path(str(rep) + os.sep)) is True                     # trailing slash
    monkeypatch.chdir(tmp_path)
    assert main(h, docs, Path("reports")) is True                             # relative
    assert main(h, docs, Path("reports/")) is True
    assert "346.86" in (docs / "synthesis" / "index.rst").read_text()


def test_only_stat_txt_renders_utilization_without_timing(tmp_path):
    h, docs, rep = _reports(tmp_path, **{"stat.txt": _YOSYS_STAT})
    assert main(h, docs, rep, if_present=True) is True
    page = (docs / "synthesis" / "index.rst").read_text()
    assert "Utilization" in page and "\nTiming" not in page and "\nWarnings\n" not in page


def test_only_nextpnr_log_renders_timing_device_utilisation_and_warnings(tmp_path):
    h, docs, rep = _reports(tmp_path, **{"nextpnr.log": _NEXTPNR_LOG})
    assert main(h, docs, rep, if_present=True) is True
    page = (docs / "synthesis" / "index.rst").read_text()
    assert "TRELLIS_FF" in page and "346.86" in page and "unconstrained" in page


def test_a_non_utf8_log_renders_what_it_can(tmp_path):
    log = _NEXTPNR_LOG.encode() + "Warning: caf\xe9 is odd\n".encode("latin-1")
    h, docs, rep = _reports(tmp_path, **{"nextpnr.log": log, "stat.txt": _YOSYS_STAT})
    assert main(h, docs, rep) is True
    assert "346.86" in (docs / "synthesis" / "index.rst").read_text()


def test_documented_at_appears_only_inside_a_git_repository(tmp_path):
    h, docs, rep = _reports(tmp_path, **{"nextpnr.log": _NEXTPNR_LOG})
    main(h, docs, rep)
    assert "Documented at" not in (docs / "synthesis" / "index.rst").read_text()
    if shutil.which("git") is None:
        return
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-q", "-m", "x"]):
        subprocess.run(cmd, cwd=tmp_path, env=env, check=True, capture_output=True)
    main(h, docs, rep)
    assert "Documented at" in (docs / "synthesis" / "index.rst").read_text()


def test_main_still_writes_a_per_module_synthesis_page(tmp_path):
    h, docs, rep = _reports(tmp_path, **{"stat.txt": _YOSYS_STAT})
    main(h, docs, rep)
    assert "16" in (docs / "modules" / "cnt" / "synthesis.rst").read_text()


def test_cli_accepts_if_present(tmp_path):
    import sys
    h, docs, rep = _reports(tmp_path)
    script = Path(__file__).parents[1] / "extract_reports.py"
    out = subprocess.run([sys.executable, str(script), str(h), str(docs), str(rep), "--if-present"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert not (docs / "synthesis").exists()
