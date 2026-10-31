"""Tests for extract_testbenches.py: the Testbenches page."""

import json
import subprocess
import sys
from pathlib import Path

# pytest would collect a bare `testbenches_rst` import as a test (name starts with 'test').
from extract_testbenches import main, testbenches_rst as render_page
from parse_testbenches import TestCase, Testbench

SCRIPT = Path(__file__).parents[1] / "extract_testbenches.py"


def _tbs():
    return [
        Testbench("tb_fifo", "tb/vunit/tb_fifo.vhd", "vunit", "Testbench for the FIFO.",
                  [TestCase("reset", "Reset empties the FIFO."), TestCase("wrap")], "fifo"),
        Testbench("test_regs", "tb/cocotb/test_regs.py", "cocotb", "Register tests.",
                  [TestCase("a", "First."), TestCase("b", "Second.", skipped=True)], None),
        Testbench("tb_top", "tb/directed/tb_top.vhd", "directed", "", [], "top"),
    ]


def test_page_title_and_summary_table_with_totals():
    rst = render_page(_tbs())
    assert rst.startswith("Testbenches\n===========")
    assert "Framework" in rst and "Testbenches" in rst
    summary = rst[:rst.index("\nVUnit\n")]
    assert "VUnit" in summary and "cocotb" in summary and "Directed" in summary
    assert "Total" in summary
    # 4 tests overall (one skipped), 3 testbenches.
    total_row = summary[summary.index("Total"):]
    assert "3" in total_row and "4" in total_row and "1 skipped" in total_row


def test_a_section_per_framework_and_per_testbench_details():
    rst = render_page(_tbs())
    for heading in ("\nVUnit\n-----", "\ncocotb\n------", "\nDirected\n--------"):
        assert heading in rst
    assert "``tb/vunit/tb_fifo.vhd``" in rst
    assert "Testbench for the FIFO." in rst
    assert ":doc:`/modules/fifo/index`" in rst            # linked module
    assert "``reset``" in rst and "Reset empties the FIFO." in rst


def test_unlinked_testbench_shows_a_dash_and_skipped_tests_are_marked():
    rst = render_page(_tbs())
    cocotb = rst[rst.index("\ncocotb\n"):rst.index("\nDirected\n")]
    assert "Tests module" in cocotb and "—" in cocotb
    assert "``b`` *(skipped)*" in cocotb
    assert "2 tests, 1 skipped" in cocotb


def test_testbench_with_no_tests_says_so_and_empty_purpose_is_a_dash():
    rst = render_page(_tbs())
    directed = rst[rst.index("\nDirected\n"):]
    assert "no tests found" in directed


def test_purpose_text_is_escaped_for_restructuredtext():
    tb = Testbench("tb_x", "tb/directed/tb_x.vhd", "directed", "Checks a*b and `c` and x_ | y",
                   [TestCase("t", "uses * and trailing_ and |bars|")], None)
    rst = render_page([tb])
    assert "a\\*b" in rst and "\\`c\\`" in rst and "x\\_ " in rst and "\\|" in rst
    assert "trailing\\_ " in rst


def test_a_framework_with_no_testbenches_is_left_out():
    rst = render_page([_tbs()[0]])
    assert "\ncocotb\n" not in rst and "\nDirected\n" not in rst


# ── main ─────────────────────────────────────────────────────────────────────

def _project(tmp_path):
    h = tmp_path / "hierarchy.json"
    h.write_text(json.dumps({"top": "top", "modules": {"fifo": {}, "top": {}}}))
    docs = tmp_path / "docs"
    docs.mkdir()
    tb = tmp_path / "tb"
    (tb / "vunit").mkdir(parents=True)
    (tb / "vunit" / "tb_fifo.vhd").write_text(
        '-- FIFO bench.\nentity tb_fifo is end entity;\n'
        'architecture a of tb_fifo is begin\n  process begin\n'
        '    if run("reset") then null; end if;\n  end process;\nend;\n')
    return h, docs, tb


def test_main_writes_the_page_and_returns_true(tmp_path, capsys):
    h, docs, tb = _project(tmp_path)
    assert main(h, docs, tb) is True
    page = docs / "testbenches" / "index.rst"
    assert page.exists()
    text = page.read_text()
    assert "tb_fifo" in text and ":doc:`/modules/fifo/index`" in text
    assert str(page) in capsys.readouterr().out


def test_main_with_missing_directory_writes_nothing_and_says_so(tmp_path, capsys):
    h, docs, _ = _project(tmp_path)
    assert main(h, docs, tmp_path / "nope") is False
    assert not (docs / "testbenches").exists()
    out = capsys.readouterr().out
    assert len(out.strip().splitlines()) == 1 and "testbench" in out.lower()


def test_main_with_empty_directory_writes_nothing(tmp_path):
    h, docs, _ = _project(tmp_path)
    (tmp_path / "empty").mkdir()
    assert main(h, docs, tmp_path / "empty") is False
    assert not (docs / "testbenches").exists()


def test_main_removes_a_stale_page_when_there_is_nothing_left(tmp_path):
    h, docs, tb = _project(tmp_path)
    assert main(h, docs, tb) is True
    (tb / "vunit" / "tb_fifo.vhd").unlink()
    assert main(h, docs, tb) is False
    assert not (docs / "testbenches").exists()


def test_main_survives_one_bad_file_and_still_lists_the_rest(tmp_path, capsys):
    h, docs, tb = _project(tmp_path)
    (tb / "cocotb").mkdir()
    (tb / "cocotb" / "test_bad.py").write_text("def broken(:\n")
    assert main(h, docs, tb) is True
    assert "tb_fifo" in (docs / "testbenches" / "index.rst").read_text()
    assert "test_bad.py" in capsys.readouterr().err


def test_main_tolerates_a_missing_hierarchy_file(tmp_path):
    _, docs, tb = _project(tmp_path)
    assert main(tmp_path / "missing.json", docs, tb) is True
    assert ":doc:" not in (docs / "testbenches" / "index.rst").read_text()   # nothing to link


def test_cli_always_exits_zero(tmp_path):
    h, docs, tb = _project(tmp_path)
    ok = subprocess.run([sys.executable, str(SCRIPT), str(h), str(docs), str(tb)],
                        capture_output=True, text=True)
    missing = subprocess.run([sys.executable, str(SCRIPT), str(h), str(docs), str(tmp_path / "x")],
                             capture_output=True, text=True)
    assert ok.returncode == 0 and missing.returncode == 0
