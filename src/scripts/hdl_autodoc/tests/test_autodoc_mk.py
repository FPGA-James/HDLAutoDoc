"""Tests for src/autodoc.mk wiring, using `make -n` (print the commands, run nothing)."""

import shutil
import subprocess
from pathlib import Path

import pytest

AUTODOC_MK = Path(__file__).parents[3] / "autodoc.mk"

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")


def _dry_run(tmp_path, target, *variables):
    (tmp_path / "Makefile").write_text(f"include {AUTODOC_MK}\n")
    out = subprocess.run(["make", "-n", target, *variables], cwd=tmp_path,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_defaults_run_testbench_and_report_extraction_without_off_flags(tmp_path):
    out = _dry_run(tmp_path, "doc-extract")
    assert "extract_testbenches.py" in out
    assert "extract_reports.py" in out and "--if-present" in out
    assert "--no-testbenches" not in out and "--no-build" not in out


def test_switching_testbenches_off_skips_the_script_and_passes_the_flag(tmp_path):
    out = _dry_run(tmp_path, "doc-extract", "TESTBENCHES=0")
    assert "extract_testbenches.py" not in out
    assert "--no-testbenches" in out and "--no-build" not in out


def test_switching_build_off_skips_the_script_and_passes_the_flag(tmp_path):
    out = _dry_run(tmp_path, "doc-extract", "BUILD=0")
    assert "extract_reports.py" not in out
    assert "--no-build" in out and "--no-testbenches" not in out


def test_directory_variables_reach_the_scripts(tmp_path):
    out = _dry_run(tmp_path, "doc-extract", "AUTODOC_TB_DIR=x/", "AUTODOC_REPORTS_DIR=/abs/r")
    tb_line = next(l for l in out.splitlines() if "extract_testbenches.py" in l)
    rep_line = next(l for l in out.splitlines() if "extract_reports.py" in l)
    assert tb_line.rstrip().endswith("x/")
    assert "/abs/r" in rep_line


def test_default_directories_are_tb_and_reports(tmp_path):
    out = _dry_run(tmp_path, "doc-extract")
    assert next(l for l in out.splitlines() if "extract_testbenches.py" in l).rstrip().endswith(" tb")
    assert " reports " in next(l for l in out.splitlines() if "extract_reports.py" in l) + " "


def test_explicit_doc_reports_uses_the_variable_and_never_passes_no_build(tmp_path):
    out = _dry_run(tmp_path, "doc-reports", "BUILD=0", "AUTODOC_REPORTS_DIR=out/r")
    assert "out/r" in out
    assert "--no-build" not in out
    assert "--if-present" not in out      # explicit target keeps its placeholder behaviour


def test_report_file_variables_reach_the_report_script(tmp_path):
    out = _dry_run(tmp_path, "doc-extract", "AUTODOC_YOSYS_STAT=build/s.txt",
                   "AUTODOC_NEXTPNR_LOG=build/p.log")
    line = next(l for l in out.splitlines() if "extract_reports.py" in l)
    assert 'AUTODOC_YOSYS_STAT="build/s.txt"' in line
    assert 'AUTODOC_NEXTPNR_LOG="build/p.log"' in line


def test_report_file_variables_reach_doc_reports_too(tmp_path):
    out = _dry_run(tmp_path, "doc-reports", "AUTODOC_VIVADO_TIMING=t.rpt")
    line = next(l for l in out.splitlines() if "extract_reports.py" in l)
    assert 'AUTODOC_VIVADO_TIMING="t.rpt"' in line
