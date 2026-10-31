"""
parse_build_info.py
-------------------
Parse what an open-source (Yosys + nextpnr) build leaves in its logs into small
data models for the Build page.

Public API
----------
    parse_device_utilisation(nextpnr_log) -> list[ResourceUse]
    device_class(resources)               -> str | None
    parse_build_info(yosys_log, nextpnr_log, newest_mtime) -> BuildInfo
    summarise_warnings(*logs, top_n=5)    -> WarningSummary

Formats these were written against (nextpnr-ecp5 0.8, Yosys 0.56):

    Info: Device utilisation:
    Info: \t          TRELLIS_FF:      16/  24288     0%

    Yosys 0.56+186 (git sha1 ...)                       (log header)
    "nextpnr-ecp5" -- Next Generation Place and Route (Version nextpnr-0.8-108-g...)
        (printed to stdout, so absent from a --log file)

Everything here is tolerant: a missing or unfamiliar line gives None / an empty
list, never an exception.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ResourceUse:
    name: str
    used: int
    available: int
    percent: int


@dataclass
class BuildInfo:
    yosys_version: str | None
    nextpnr_version: str | None
    device: str | None
    report_time: datetime | None


@dataclass
class WarningSummary:
    total: int
    top: list[tuple[str, int]]


# ── Device utilisation ───────────────────────────────────────────────────────

_UTIL_HEADER_RE = re.compile(r"^Info:\s*Device utilisation:\s*$")
_UTIL_ROW_RE = re.compile(r"^Info:\s+(\w+):\s+(\d+)\s*/\s*(\d+)\s+(\d+)%\s*$")


def parse_device_utilisation(nextpnr_log: str) -> list[ResourceUse]:
    """
    Rows of nextpnr's `Device utilisation:` block, in order.  The block ends at the
    first line that is not a resource row; if it is printed more than once, the
    last one (after routing) is returned.
    """
    blocks: list[list[ResourceUse]] = []
    current: list[ResourceUse] | None = None
    for line in nextpnr_log.splitlines():
        if _UTIL_HEADER_RE.match(line):
            current = []
            blocks.append(current)
            continue
        if current is None:
            continue
        m = _UTIL_ROW_RE.match(line)
        if m:
            current.append(ResourceUse(m.group(1), int(m.group(2)),
                                       int(m.group(3)), int(m.group(4))))
        else:
            current = None
    return blocks[-1] if blocks else []


# Flip-flop capacity identifies the ECP5 size class (LFE5U-25/45/85 and variants).
_ECP5_BY_FF = {24288: "ECP5 25k class", 43848: "ECP5 45k class", 83640: "ECP5 85k class"}


def device_class(resources: list[ResourceUse]) -> str | None:
    """Device size class inferred from TRELLIS_FF capacity, or None if unrecognised."""
    for r in resources:
        if r.name == "TRELLIS_FF":
            return _ECP5_BY_FF.get(r.available)
    return None


# ── Tool versions and report time ────────────────────────────────────────────

def parse_build_info(yosys_log: str | None, nextpnr_log: str | None,
                     newest_mtime: float | None) -> BuildInfo:
    """Versions, device class and report time; anything not found is None."""
    yosys_version = None
    if yosys_log:
        m = re.search(r"\bYosys (\d+\.\d+\S*)", yosys_log)
        yosys_version = m.group(1) if m else None

    nextpnr_version = device = None
    if nextpnr_log:
        m = re.search(r"\(Version\s+([^)\s]+)\)", nextpnr_log)
        nextpnr_version = m.group(1) if m else None
        device = device_class(parse_device_utilisation(nextpnr_log))

    report_time = datetime.fromtimestamp(newest_mtime) if newest_mtime is not None else None
    return BuildInfo(yosys_version, nextpnr_version, device, report_time)


# ── Warnings ─────────────────────────────────────────────────────────────────

_WARNING_RE = re.compile(r"\b(?:Warning|WARNING):\s*(.*)$")
_QUOTED_RE = re.compile(r"[`'][^`'\n]*'")


def summarise_warnings(*logs: str, top_n: int = 5) -> WarningSummary:
    """
    Count `Warning:` / `WARNING:` lines across the logs and return the `top_n` most
    frequent messages.  Messages that differ only by a quoted name are one message,
    e.g. "IO 'q[3]' is unconstrained..." for every port becomes a single entry.
    """
    counts: dict[str, int] = {}
    total = 0
    for log in logs:
        for line in log.splitlines():
            m = _WARNING_RE.search(line)
            if not m:
                continue
            total += 1
            key = _QUOTED_RE.sub("'…'", m.group(1).strip())
            counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
    return WarningSummary(total, top)
