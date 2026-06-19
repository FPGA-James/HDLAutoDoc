"""
extract_reports.py
------------------
Orchestrate utilization and timing parsers, then write implementation RST.

Writes:
  docs/hdl_autodoc/synthesis/index.rst        — top-level Implementation page
  docs/hdl_autodoc/modules/<n>/synthesis.rst  — per-module utilization

Usage:
    python scripts/hdl_autodoc/extract_reports.py \\
        docs/hdl_autodoc/hierarchy.json \\
        docs/hdl_autodoc \\
        reports
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from parse_utilization import ModuleUtilization, parse_utilization
from parse_timing import ClockTiming, parse_timing


# ── RST rendering ─────────────────────────────────────────────────────────────

_PLACEHOLDER = """\
Implementation
==============

No synthesis reports available.

Run ``make reports`` after completing synthesis and place-and-route
to populate this page. Place report files in::

    reports/vivado/utilization_placed.rpt
    reports/vivado/timing_summary_routed.rpt

or::

    reports/yosys/stat.txt
    reports/yosys/nextpnr.log
"""

_MODULE_PLACEHOLDER = """\
Synthesis Results
=================

*No synthesis data available for this module.*
"""


def _timing_table_rst(clocks: list[ClockTiming], tool: str) -> str:
    if tool == "vivado":
        lines = [
            ".. list-table::",
            "   :header-rows: 1",
            "",
            "   * - Clock",
            "     - Fmax (MHz)",
            "     - Period (ns)",
            "     - WNS (ns)",
            "",
        ]
        for c in clocks:
            lines += [
                f"   * - {c.clock_name}",
                f"     - {c.fmax_mhz:.2f}",
                f"     - {c.period_ns:.3f}" if c.period_ns is not None else "     - —",
                f"     - {c.wns_ns:+.3f}"   if c.wns_ns  is not None  else "     - —",
                "",
            ]
    else:  # nextpnr
        lines = [
            ".. list-table::",
            "   :header-rows: 1",
            "",
            "   * - Clock",
            "     - Fmax (MHz)",
            "     - Target (MHz)",
            "     - Status",
            "",
        ]
        for c in clocks:
            status = ("✔ PASS" if c.passing else "✘ FAIL") if c.passing is not None else "—"
            lines += [
                f"   * - {c.clock_name}",
                f"     - {c.fmax_mhz:.2f}",
                f"     - {c.constraint_mhz:.1f}" if c.constraint_mhz is not None else "     - —",
                f"     - {status}",
                "",
            ]
    return "\n".join(lines)


def _utilization_table_rst(modules: list[ModuleUtilization], vivado: bool) -> str:
    avail_luts = modules[0].luts_available if vivado and modules else None
    avail_ffs  = modules[0].ffs_available  if vivado and modules else None
    lut_header = f"LUTs / {avail_luts:,}" if avail_luts else "LUTs"
    ff_header  = f"FFs / {avail_ffs:,}"   if avail_ffs  else "FFs"
    lines = [
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Module",
        f"     - {lut_header}",
        f"     - {ff_header}",
        "     - BRAMs",
        "     - DSPs",
        "",
    ]
    for m in modules:
        lines += [
            f"   * - {m.module_name}",
            f"     - {m.luts:,}",
            f"     - {m.ffs:,}",
            f"     - {m.brams:,}",
            f"     - {m.dsps:,}",
            "",
        ]
    return "\n".join(lines)


def synthesis_index_rst(
    util_modules: list[ModuleUtilization],
    util_tool: str | None,
    clocks: list[ClockTiming],
    timing_tool: str | None,
) -> str:
    """Return RST string for synthesis/index.rst."""
    if not util_modules and not clocks:
        return _PLACEHOLDER

    lines = ["Implementation", "==============", ""]

    if clocks and timing_tool:
        label = "Vivado" if timing_tool == "vivado" else "nextpnr"
        lines += [f"Timing — {label}", "-" * (9 + len(label)), ""]
        lines.append(_timing_table_rst(clocks, timing_tool))

    if util_modules and util_tool:
        label = "Vivado" if util_tool == "vivado" else "Yosys"
        lines += [f"Utilization — {label}", "-" * (15 + len(label)), ""]
        lines.append(_utilization_table_rst(util_modules, util_tool == "vivado"))

    return "\n".join(lines)


def module_synthesis_rst(module_name: str, util: ModuleUtilization | None) -> str:
    """Return RST string for a per-module synthesis.rst."""
    if util is None:
        return _MODULE_PLACEHOLDER
    return "\n".join([
        "Synthesis Results",
        "=================",
        "",
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Resource",
        "     - Used",
        "",
        "   * - LUTs",
        f"     - {util.luts:,}",
        "",
        "   * - FFs",
        f"     - {util.ffs:,}",
        "",
        "   * - BRAMs",
        f"     - {util.brams:,}",
        "",
        "   * - DSPs",
        f"     - {util.dsps:,}",
        "",
    ])


# ── Orchestration ─────────────────────────────────────────────────────────────

def main(hierarchy_path: Path, docs_dir: Path, reports_dir: Path) -> None:
    hierarchy    = json.loads(hierarchy_path.read_text())
    module_names = list(hierarchy["modules"].keys())

    # Locate report files (prefer placed over synth for Vivado utilization)
    vivado_util  = reports_dir / "vivado" / "utilization_placed.rpt"
    if not vivado_util.exists():
        vivado_util  = reports_dir / "vivado" / "utilization_synth.rpt"
    yosys_util   = reports_dir / "yosys"  / "stat.txt"
    vivado_time  = reports_dir / "vivado" / "timing_summary_routed.rpt"
    nextpnr_time = reports_dir / "yosys"  / "nextpnr.log"

    util_modules, util_tool = parse_utilization(vivado_util)
    if not util_modules:
        util_modules, util_tool = parse_utilization(yosys_util)

    clocks, timing_tool = parse_timing(vivado_time)
    if not clocks:
        clocks, timing_tool = parse_timing(nextpnr_time)

    # Write synthesis/index.rst
    synth_dir = docs_dir / "synthesis"
    synth_dir.mkdir(parents=True, exist_ok=True)
    index_path = synth_dir / "index.rst"
    index_path.write_text(synthesis_index_rst(util_modules, util_tool, clocks, timing_tool))
    print(f"  → {index_path}")

    # Write per-module synthesis.rst
    util_by_name = {m.module_name: m for m in util_modules}
    for name in module_names:
        mod_dir = docs_dir / "modules" / name
        mod_dir.mkdir(parents=True, exist_ok=True)
        rst_path = mod_dir / "synthesis.rst"
        rst_path.write_text(module_synthesis_rst(name, util_by_name.get(name)))
        print(f"  → {rst_path}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: extract_reports.py <hierarchy.json> <docs_dir> <reports_dir>")
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
