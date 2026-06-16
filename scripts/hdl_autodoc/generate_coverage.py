#!/usr/bin/env python3
"""
generate_coverage.py
--------------------
Inspects extraction output for each module and produces:
  1. A compact terminal coverage table (stdout)
  2. docs/hdl_autodoc/coverage.rst (Sphinx HTML page)

Usage:
    python scripts/hdl_autodoc/generate_coverage.py \\
        docs/hdl_autodoc/hierarchy.json docs/hdl_autodoc
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CoverageResult:
    name: str
    fsm: bool
    process_count: int
    cdc: bool
    reset: bool
    port_count: int


_PORT_SECTION_RE = re.compile(r"^Ports\n[-]+", re.MULTILINE)
_DATA_ROW_RE = re.compile(r"^\s+\* - ``", re.MULTILINE)
_NEXT_SECTION_RE = re.compile(r"\n\n[^\n]+\n[-=]+")


def _count_ports(content: str) -> int:
    """Count port data rows in the Ports section of a _block.rst file."""
    m = _PORT_SECTION_RE.search(content)
    if not m:
        return 0
    section = content[m.end():]
    nxt = _NEXT_SECTION_RE.search(section)
    if nxt:
        section = section[:nxt.start()]
    return len(_DATA_ROW_RE.findall(section))


def detect_coverage(name: str, docs_dir: Path) -> CoverageResult:
    """Inspect a module's extraction output directory and return coverage signals."""
    mod_dir = docs_dir / "modules" / name

    fsm = (mod_dir / f"{name}.dot").exists()

    procs_dir = mod_dir / "processes"
    process_count = len(list(procs_dir.glob("p_*.rst"))) if procs_dir.exists() else 0

    cdc_rst = mod_dir / f"{name}_cdc.rst"
    cdc = cdc_rst.exists() and "Signal Crossings" in cdc_rst.read_text()

    reset_rst = mod_dir / f"{name}_reset.rst"
    reset = reset_rst.exists() and bool(
        re.search(r"crossing", reset_rst.read_text(), re.IGNORECASE)
    )

    block_rst = mod_dir / f"{name}_block.rst"
    port_count = _count_ports(block_rst.read_text()) if block_rst.exists() else 0

    return CoverageResult(
        name=name,
        fsm=fsm,
        process_count=process_count,
        cdc=cdc,
        reset=reset,
        port_count=port_count,
    )


def format_terminal_table(results: list[CoverageResult]) -> str:
    """Format a compact terminal coverage table from a list of results."""
    n = len(results)
    if not results:
        return "Coverage Report\nNo modules found.\n"

    name_w = max(len(r.name) for r in results)
    name_w = max(name_w, 6)  # minimum width of "Module" header

    # Column widths: FSM=5, Processes=11, CDC=5, Reset=7, Ports=9
    total_w = name_w + 2 + 5 + 2 + 11 + 2 + 5 + 2 + 7 + 2 + 9
    sep = "─" * total_w

    def fmt_bool(v: bool) -> str:
        return "✓" if v else "–"

    def fmt_proc(count: int) -> str:
        return f"{count} procs" if count > 0 else "–"

    def fmt_port(count: int) -> str:
        return f"{count} ports" if count > 0 else "–"

    def row(name: str, fsm: str, proc: str, cdc: str, rst: str, port: str) -> str:
        return (
            f"{name:<{name_w}}  {fsm:>5}  {proc:>11}  "
            f"{cdc:>5}  {rst:>7}  {port:>9}"
        )

    lines = [
        "Coverage Report",
        sep,
        row("Module", "FSM", "Processes", "CDC", "Reset", "Ports"),
        sep,
    ]

    for r in results:
        lines.append(row(
            r.name,
            fmt_bool(r.fsm),
            fmt_proc(r.process_count),
            fmt_bool(r.cdc),
            fmt_bool(r.reset),
            fmt_port(r.port_count),
        ))

    fsm_tot   = sum(1 for r in results if r.fsm)
    proc_tot  = sum(1 for r in results if r.process_count > 0)
    cdc_tot   = sum(1 for r in results if r.cdc)
    reset_tot = sum(1 for r in results if r.reset)
    port_tot  = sum(1 for r in results if r.port_count > 0)

    lines.append(sep)
    lines.append(row(
        "Totals",
        f"{fsm_tot}/{n}",
        f"{proc_tot}/{n}",
        f"{cdc_tot}/{n}",
        f"{reset_tot}/{n}",
        f"{port_tot}/{n}",
    ))

    return "\n".join(lines)
