"""
parse_timing.py
---------------
Parse timing reports from Vivado (report_timing_summary) and nextpnr
(--log output) into a common data model.

Public API
----------
    from parse_timing import ClockTiming, parse_timing

    clocks, tool = parse_timing(Path("reports/vivado/timing_summary_routed.rpt"))
    # tool  → "vivado" | "nextpnr" | None
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ClockTiming:
    clock_name: str
    fmax_mhz: float
    wns_ns: float | None = None          # Vivado: worst negative slack
    period_ns: float | None = None       # Vivado: constraint period (ns)
    constraint_mhz: float | None = None  # nextpnr: requested frequency
    passing: bool | None = None          # nextpnr: True = PASS, False = FAIL


_NEXTPNR_INFRA_PREFIXES = {"glbnet", "gbuf", "clkbuf"}


def _clean_clock_name(name: str) -> str:
    """
    Normalise a clock name.
    nextpnr emits names like '$glbnet$clk$TRELLIS_IO_IN' — extract the
    shortest non-empty, non-all-uppercase, non-infrastructure segment.
    Plain names (no '$') are returned unchanged.
    """
    if "$" not in name:
        return name
    parts = [
        p for p in name.split("$")
        if p and not p.isupper() and p.lower() not in _NEXTPNR_INFRA_PREFIXES
    ]
    return parts[0] if parts else name


def _parse_vivado(text: str) -> list[ClockTiming]:
    """Parse Vivado report_timing_summary output."""
    # WNS from the Design Timing Summary data row
    # Header:  WNS(ns)      TNS(ns)  ...
    # Data:      1.234        0.000  ...
    wns: float | None = None
    m = re.search(r'WNS\(ns\)[^\n]*\n\s*([-\d.]+)', text)
    if m:
        try:
            wns = float(m.group(1))
        except ValueError:
            pass

    # Clock Summary table rows
    # | Clock | Waveform(ns)  | Period(ns) | Frequency(MHz) |
    # | clk   | {0.000 5.000} | 10.000     | 100.000        |
    clocks: list[ClockTiming] = []
    for cm in re.finditer(
        r'\|\s*(\S+)\s*\|\s*\{[^}]+\}\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|',
        text,
    ):
        name   = cm.group(1)
        period = float(cm.group(2))
        if wns is not None and period > wns:
            fmax = round(1000.0 / (period - wns), 2)
        else:
            fmax = round(1000.0 / period, 2)
        clocks.append(ClockTiming(
            clock_name=_clean_clock_name(name),
            fmax_mhz=fmax,
            wns_ns=wns,
            period_ns=period,
        ))
    return clocks


def _parse_nextpnr(text: str) -> list[ClockTiming]:
    """Parse nextpnr --log output for 'Max frequency for clock' lines."""
    clocks: list[ClockTiming] = []
    for m in re.finditer(
        r"Max frequency for clock '([^']+)':\s*([\d.]+)\s*MHz\s*"
        r"\((PASS|FAIL)\s+at\s*([\d.]+)\s*MHz\)",
        text,
        re.IGNORECASE,
    ):
        clocks.append(ClockTiming(
            clock_name=_clean_clock_name(m.group(1)),
            fmax_mhz=float(m.group(2)),
            passing=(m.group(3).upper() == "PASS"),
            constraint_mhz=float(m.group(4)),
        ))
    return clocks


def parse_timing(path: Path) -> tuple[list[ClockTiming], str | None]:
    """
    Parse a timing report file.

    Returns (clocks, tool) where tool is "vivado", "nextpnr", or None.
    Returns ([], None) if the file does not exist or format is unrecognised.
    """
    if not path.exists():
        return [], None
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return [], None

    if "WNS(ns)" in text or "Design Timing Summary" in text:
        return _parse_vivado(text), "vivado"
    if "Max frequency for clock" in text:
        return _parse_nextpnr(text), "nextpnr"
    return [], None
