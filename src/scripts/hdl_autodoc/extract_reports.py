"""
extract_reports.py
------------------
Orchestrate utilization and timing parsers, then write implementation RST.

Writes:
  docs/hdl_autodoc/synthesis/index.rst        — top-level Build page
  docs/hdl_autodoc/modules/<n>/synthesis.rst  — per-module utilization

Usage:
    python scripts/hdl_autodoc/extract_reports.py \\
        docs/hdl_autodoc/hierarchy.json \\
        docs/hdl_autodoc \\
        reports
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from parse_build_info import (
    BuildInfo,
    ResourceUse,
    WarningSummary,
    parse_build_info,
    parse_device_utilisation,
    summarise_warnings,
)
from parse_utilization import ModuleUtilization, parse_utilization_text
from parse_timing import ClockTiming, parse_timing_text
from rst_escape import escape_rst


# ── RST rendering ─────────────────────────────────────────────────────────────

_PLACEHOLDER = """\
Build
=====

No synthesis reports available.

Run ``make reports`` after completing synthesis and place-and-route
to populate this page. Place report files in::

    reports/vivado/utilization_placed.rpt
    reports/vivado/timing_summary_routed.rpt

or::

    reports/yosys/stat.txt
    reports/yosys/nextpnr.log
"""

def _timing_table_rst(clocks: list[ClockTiming], tool: str) -> str:
    if tool == "vivado":
        lines = [
            ".. list-table::",
            "   :header-rows: 1",
            "",
            "   * - Clock",
            "     - Target (MHz)",
            "     - Fmax (MHz)",
            "     - Period (ns)",
            "     - WNS (ns)",
            "",
        ]
        for c in clocks:
            target = f"     - {1000.0 / c.period_ns:.1f}" if c.period_ns is not None else "     - —"
            lines += [
                f"   * - {c.clock_name}",
                target,
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
        indent = "  " * (m.depth - 1) + "└─ " if m.depth > 0 else ""
        lines += [
            f"   * - {indent}{m.module_name}",
            f"     - {m.luts:,}",
            f"     - {m.ffs:,}",
            f"     - {m.brams:,}",
            f"     - {m.dsps:,}",
            "",
        ]
    return "\n".join(lines)


def _has_content(util_modules, clocks, resources, build_info, warnings) -> bool:
    """True if anything was actually parsed (file timestamps alone do not count)."""
    facts = build_info and (build_info.yosys_version or build_info.nextpnr_version
                            or build_info.device)
    return bool(util_modules or clocks or resources or facts
                or (warnings is not None and warnings.total))


def _summary_rst(info: BuildInfo | None, documented_at: str | None) -> list[str]:
    """Build summary table; only facts that were found, or [] if there are none."""
    rows: list[tuple[str, str]] = []
    if info:
        if info.yosys_version:
            rows.append(("Yosys", info.yosys_version))
        if info.nextpnr_version:
            rows.append(("nextpnr", info.nextpnr_version))
        if info.device:
            rows.append(("Device", info.device))
        if info.report_time:
            rows.append(("Reports generated", info.report_time.strftime("%Y-%m-%d %H:%M")))
    if documented_at:
        rows.append(("Documented at", documented_at))
    if not rows:
        return []
    lines = ["Summary", "-------", "", ".. list-table::", "   :widths: 30 70", ""]
    for key, value in rows:
        lines += [f"   * - {key}", f"     - {escape_rst(value)}", ""]
    return lines


def _device_table_rst(resources: list[ResourceUse]) -> list[str]:
    """nextpnr device utilisation: resources in use, with a note for the unused ones."""
    used = [r for r in resources if r.used > 0]
    unused = len(resources) - len(used)
    lines = ["Device utilisation (nextpnr)", "~" * len("Device utilisation (nextpnr)"), ""]
    if used:
        lines += [".. list-table::", "   :header-rows: 1", "",
                  "   * - Resource", "     - Used", "     - Available", "     - %", ""]
        for r in used:
            lines += [f"   * - ``{r.name}``", f"     - {r.used:,}",
                      f"     - {r.available:,}", f"     - {r.percent}", ""]
    if unused:
        lines += [f"{unused} other resource type{'s' if unused != 1 else ''} unused.", ""]
    return lines


def _warnings_rst(warnings: WarningSummary) -> list[str]:
    lines = ["Warnings", "--------", ""]
    if warnings.total == 0:
        return lines + ["No warnings reported.", ""]
    lines += [f"{warnings.total} warning{'s' if warnings.total != 1 else ''} in the build logs; "
              f"the most frequent:", "",
              ".. list-table::", "   :header-rows: 1", "",
              "   * - Message", "     - Count", ""]
    for message, count in warnings.top:
        lines += [f"   * - {escape_rst(message)}", f"     - {count}", ""]
    return lines


def synthesis_index_rst(
    util_modules: list[ModuleUtilization],
    util_tool: str | None,
    clocks: list[ClockTiming],
    timing_tool: str | None,
    build_info: BuildInfo | None = None,
    resources: list[ResourceUse] | None = None,
    warnings: WarningSummary | None = None,
    documented_at: str | None = None,
) -> str:
    """
    Return RST string for synthesis/index.rst (the Build page): summary,
    utilization, timing, warnings.  Called with only the first four arguments it
    behaves as before (minus the new title).
    """
    if not _has_content(util_modules, clocks, resources, build_info, warnings):
        return _PLACEHOLDER

    lines = ["Build", "=====", ""]
    lines += _summary_rst(build_info, documented_at)

    if util_modules or resources:
        lines += ["Utilization", "-----------", ""]
        if resources:
            lines += _device_table_rst(resources)
        if util_modules and util_tool:
            label = "Vivado" if util_tool == "vivado" else "Yosys"
            heading = f"By module ({label})"
            lines += [heading, "~" * len(heading), ""]
            lines.append(_utilization_table_rst(util_modules, util_tool == "vivado"))

    if clocks and timing_tool:
        label = "Vivado" if timing_tool == "vivado" else "nextpnr"
        lines += [f"Timing — {label}", "-" * (9 + len(label)), ""]
        lines.append(_timing_table_rst(clocks, timing_tool))

    if warnings is not None:
        lines += _warnings_rst(warnings)

    return "\n".join(lines)


# ── Orchestration ─────────────────────────────────────────────────────────────

def _warn(path: Path, message: str) -> None:
    print(f"  WARNING: report {path}: {message}", file=sys.stderr)


def _read_text(path: Path) -> str | None:
    """
    Text of a report, or None if it is missing, empty or binary.  A byte-order mark
    is dropped; undecodable bytes are replaced (with a warning).
    """
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if not data.strip():
        return None
    if b"\x00" in data:
        _warn(path, "binary file — ignored")
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        _warn(path, "not valid UTF-8 — decoded with replacement characters")
        return data.decode("utf-8-sig", errors="replace")


def _git(cwd: Path, *args: str) -> str | None:
    """Output of a git command run in `cwd`, or None if git is missing or it fails."""
    try:
        out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _git_describe(cwd: Path) -> str | None:
    """
    The checkout's revision for the "Documented at" row, or None if unavailable:
    `git describe --tags --always`, plus `-dirty` if tracked source files differ from
    HEAD.  Files under `cwd` (the docs directory) and under any `_build` directory are
    not source and are ignored.

    `--tags` matters: releases here are lightweight tags, which plain `git describe`
    skips.  Changes under the docs directory are ignored for "dirty" because generated
    docs are often tracked (and a repo may track several projects' output), and
    rebuilding them is not a change to the design.
    """
    described = (_git(cwd, "describe", "--tags", "--always") or "").strip()
    toplevel = (_git(cwd, "rev-parse", "--show-toplevel") or "").strip()
    if not described or not toplevel:
        return None
    docs = Path(cwd).resolve()
    status = _git(cwd, "status", "--porcelain", "--untracked-files=no") or ""
    for line in status.splitlines():
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        full = (Path(toplevel) / path).resolve()
        if not full.is_relative_to(docs) and "_build" not in full.parts:
            return described + "-dirty"
    return described


def _remove_build_pages(docs_dir: Path) -> None:
    """Delete the generated Build pages (the sidebar lists whatever exists)."""
    shutil.rmtree(docs_dir / "synthesis", ignore_errors=True)
    _remove_module_pages(docs_dir)


def _remove_module_pages(docs_dir: Path) -> None:
    """Delete modules/<n>/synthesis.rst written by versions that had one per module."""
    for page in (docs_dir / "modules").glob("*/synthesis.rst"):
        page.unlink()


def main(hierarchy_path: Path, docs_dir: Path, reports_dir: Path,
         if_present: bool = False) -> bool:
    """
    Write the Build pages from the report files under `reports_dir`.

    With `if_present`, nothing is written when no report file has any content
    (and pages from an earlier run are removed), so a project without reports
    gets no Build section.  Without it a placeholder page is written.
    Returns True if a page was written.
    """
    docs_dir     = Path(docs_dir)
    reports_dir  = Path(reports_dir)

    # Locate report files (prefer placed over synth for Vivado utilization)
    vivado_util  = reports_dir / "vivado" / "utilization_placed.rpt"
    if not vivado_util.exists():
        vivado_util  = reports_dir / "vivado" / "utilization_synth.rpt"
    yosys_util   = reports_dir / "yosys"  / "stat.txt"
    yosys_log    = reports_dir / "yosys"  / "yosys.log"
    vivado_time  = reports_dir / "vivado" / "timing_summary_routed.rpt"
    nextpnr_time = reports_dir / "yosys"  / "nextpnr.log"

    # Read every report once (warning about binary / non-UTF-8 files as we go).
    texts = {p: _read_text(p) for p in
             (vivado_util, yosys_util, yosys_log, vivado_time, nextpnr_time)}
    present = [p for p, t in texts.items() if t is not None]
    if if_present and not present:
        _remove_build_pages(docs_dir)
        print(f"  Build: no reports found in {reports_dir} — section skipped")
        return False

    def utilization(p: Path):
        return parse_utilization_text(texts[p]) if texts[p] else ([], None)

    def timing(p: Path):
        return parse_timing_text(texts[p]) if texts[p] else ([], None)

    util_modules, util_tool = utilization(vivado_util)
    if not util_modules:
        util_modules, util_tool = utilization(yosys_util)

    clocks, timing_tool = timing(vivado_time)
    if not clocks:
        clocks, timing_tool = timing(nextpnr_time)

    nextpnr_text = texts[nextpnr_time]
    yosys_text   = texts[yosys_log]
    resources    = parse_device_utilisation(nextpnr_text) if nextpnr_text else []
    log_texts    = [t for t in (yosys_text, nextpnr_text) if t is not None]
    warnings     = summarise_warnings(*log_texts) if log_texts else None

    newest = max((p.stat().st_mtime for p in present), default=None)
    build_info = parse_build_info(yosys_text, nextpnr_text, newest) if present else None

    # Say which report files contributed nothing.
    contributed = {
        vivado_util:  bool(utilization(vivado_util)[0]),
        yosys_util:   bool(utilization(yosys_util)[0]),
        vivado_time:  bool(timing(vivado_time)[0]),
        nextpnr_time: bool(timing(nextpnr_time)[0] or resources
                           or (nextpnr_text and summarise_warnings(nextpnr_text).total)),
        yosys_log:    bool(build_info and build_info.yosys_version
                           or (yosys_text and summarise_warnings(yosys_text).total)),
    }
    for p in present:
        if not contributed[p]:
            _warn(p, "unrecognised format — nothing could be read from it")

    content = _has_content(util_modules, clocks, resources, build_info, warnings)
    if if_present and not content:
        _remove_build_pages(docs_dir)
        print(f"  Build: nothing recognisable in the reports in {reports_dir} — section skipped")
        return False

    # Write synthesis/index.rst
    synth_dir = docs_dir / "synthesis"
    synth_dir.mkdir(parents=True, exist_ok=True)
    index_path = synth_dir / "index.rst"
    index_path.write_text(synthesis_index_rst(
        util_modules, util_tool, clocks, timing_tool,
        build_info=build_info, resources=resources, warnings=warnings,
        documented_at=_git_describe(docs_dir) if content else None))
    print(f"  → {index_path}")

    # Per-module numbers live in the Build page's "By module" table; older versions also
    # wrote modules/<n>/synthesis.rst into the Design section, which would now be orphans.
    _remove_module_pages(docs_dir)
    return True


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 3:
        sys.exit("Usage: extract_reports.py <hierarchy.json> <docs_dir> <reports_dir> [--if-present]")
    main(Path(args[0]), Path(args[1]), Path(args[2]), if_present="--if-present" in sys.argv[1:])
