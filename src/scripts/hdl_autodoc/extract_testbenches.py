"""
extract_testbenches.py
----------------------
Write the Testbenches page: every testbench under a testbench directory, what it
is for, which module it tests, and the tests it contains (counted from source).

Writes:
  docs/hdl_autodoc/testbenches/index.rst

With no testbenches (directory missing or empty) nothing is written and a stale
page from an earlier run is removed, so the sidebar entry disappears too.

Usage:
    python scripts/hdl_autodoc/extract_testbenches.py \\
        docs/hdl_autodoc/hierarchy.json \\
        docs/hdl_autodoc \\
        tb
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from parse_testbenches import FRAMEWORKS, Testbench, discover_testbenches
from rst_escape import escape_rst as _esc

_LABELS = {"vunit": "VUnit", "cocotb": "cocotb", "directed": "Directed"}


def _count(tests: list) -> str:
    skipped = sum(1 for t in tests if t.skipped)
    return f"{len(tests)} ({skipped} skipped)" if skipped else str(len(tests))


def _testbench_rst(tb: Testbench) -> list[str]:
    dut = f":doc:`/modules/{tb.dut}/index`" if tb.dut else "—"
    skipped = sum(1 for t in tb.tests if t.skipped)
    if not tb.tests:
        tests = "no tests found"
    else:
        tests = f"{len(tb.tests)} test{'s' if len(tb.tests) != 1 else ''}"
        tests += f", {skipped} skipped" if skipped else ""
    lines = [
        tb.name, "~" * len(tb.name), "",
        f":File: ``{tb.file}``",
        f":Tests module: {dut}",
        f":Purpose: {_esc(tb.purpose) if tb.purpose else '—'}",
        f":Tests: {tests}",
        "",
    ]
    if tb.tests:
        lines += [".. list-table::", "   :header-rows: 1", "",
                  "   * - Test", "     - Purpose", ""]
        for t in tb.tests:
            name = f"``{t.name}``" + (" *(skipped)*" if t.skipped else "")
            lines += [f"   * - {name}",
                      f"     - {_esc(t.purpose) if t.purpose else '—'}", ""]
    return lines


def testbenches_rst(tbs: list[Testbench]) -> str:
    """The Testbenches page: summary table, then one section per framework."""
    by_framework = {fw: [t for t in tbs if t.framework == fw] for fw in FRAMEWORKS}
    title = "Testbenches"
    lines = [title, "=" * len(title), "",
             ".. list-table::", "   :header-rows: 1", "",
             "   * - Framework", "     - Testbenches", "     - Tests", ""]
    for fw in FRAMEWORKS:
        group = by_framework[fw]
        if group:
            tests = [t for tb in group for t in tb.tests]
            lines += [f"   * - {_LABELS[fw]}", f"     - {len(group)}",
                      f"     - {_count(tests)}", ""]
    all_tests = [t for tb in tbs for t in tb.tests]
    lines += ["   * - **Total**", f"     - {len(tbs)}", f"     - {_count(all_tests)}", ""]

    for fw in FRAMEWORKS:
        if not by_framework[fw]:
            continue
        label = _LABELS[fw]
        lines += [label, "-" * len(label), ""]
        for tb in by_framework[fw]:
            lines += _testbench_rst(tb)
    return "\n".join(lines)


def main(hierarchy_path: Path, docs_dir: Path, tb_dir: Path) -> bool:
    """Write docs_dir/testbenches/index.rst.  True if a page was written."""
    try:
        modules = set(json.loads(Path(hierarchy_path).read_text())["modules"])
    except (OSError, ValueError, KeyError) as exc:
        print(f"  WARNING: cannot read {hierarchy_path} ({exc}); testbenches will not be linked "
              f"to modules", file=sys.stderr)
        modules = set()

    tbs = discover_testbenches(Path(tb_dir), modules)
    out_dir = Path(docs_dir) / "testbenches"
    if not tbs:
        shutil.rmtree(out_dir, ignore_errors=True)
        print(f"  Testbenches: none found in {tb_dir} — section skipped")
        return False

    out_dir.mkdir(parents=True, exist_ok=True)
    page = out_dir / "index.rst"
    page.write_text(testbenches_rst(tbs))
    print(f"  → {page}")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: extract_testbenches.py <hierarchy.json> <docs_dir> <tb_dir>")
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
