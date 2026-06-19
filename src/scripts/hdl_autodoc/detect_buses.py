"""
detect_buses.py
---------------
Groups a flat port list into recognised bus interfaces.

Supports built-in patterns (AXI4-Full, AXI4-Lite, AXI4-Stream, APB, Wishbone)
and user-defined custom groups loaded from a project-level bus_groups.toml.

Usage:
    from detect_buses import BusGroup, group_ports
    bus_groups, remaining = group_ports(ports, toml_path=Path("bus_groups.toml"))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BusGroup:
    prefix: str       # e.g. "s_axi"
    bus_type: str     # e.g. "AXI4-Lite Subordinate"
    ports: list[dict] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Built-in signal sets (stripped names, lowercase)
# ─────────────────────────────────────────────────────────────────────────────

_AXI4_FULL_SIGNALS = frozenset({
    "awvalid", "awready", "awaddr", "awlen", "awsize", "awburst",
    "wvalid",  "wready",  "wdata",  "wstrb", "wlast",
    "bvalid",  "bready",  "bresp",
    "arvalid", "arready", "araddr", "arlen", "arsize", "arburst",
    "rvalid",  "rready",  "rdata",  "rresp", "rlast",
})

# Signals present in Full but NOT in Lite — used to distinguish the two
_AXI4_FULL_BURST_SIGNALS = frozenset({"awlen", "awsize", "awburst", "wlast",
                                       "arlen", "arsize", "arburst", "rlast"})

_AXI4_LITE_SIGNALS = frozenset({
    "awvalid", "awready", "awaddr",
    "wvalid",  "wready",  "wdata",  "wstrb",
    "bvalid",  "bready",  "bresp",
    "arvalid", "arready", "araddr",
    "rvalid",  "rready",  "rdata",  "rresp",
})

# AXI4-Stream: minimum required set; tstrb/tkeep/tid/tdest/tuser are optional
_AXI4_STREAM_MIN = frozenset({"tvalid", "tready", "tdata", "tlast"})

_APB_SIGNALS = frozenset({
    "psel", "penable", "paddr", "pwdata", "prdata", "pwrite", "pready",
})

_WISHBONE_SIGNALS = frozenset({
    "cyc", "stb", "ack", "adr", "dat_i", "dat_o", "we",
})


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _role_suffix(prefix: str) -> str:
    """Return ' Manager', ' Subordinate', or '' based on prefix naming hint."""
    lp = prefix.lower()
    if lp.startswith("m_") or "_m_" in lp or lp.startswith("mst_") or "_mst_" in lp:
        return " Manager"
    if lp.startswith("s_") or "_s_" in lp or lp.startswith("slv_") or "_slv_" in lp:
        return " Subordinate"
    return ""


def _find_prefix_groups(ports: list[dict]) -> dict[str, list[dict]]:
    """Return {prefix: [port, ...]} for all shared prefix_ groups with >= 3 ports."""
    groups: dict[str, list[dict]] = {}
    for port in ports:
        name = port["name"]
        idx = 0
        while True:
            idx = name.find("_", idx)
            if idx <= 0:
                break
            prefix = name[:idx]
            groups.setdefault(prefix, []).append(port)
            idx += 1
    return {k: v for k, v in groups.items() if len(v) >= 3}


def _match_bus_type(prefix: str, port_names: list[str]) -> str | None:
    """Return bus type label string or None if no built-in pattern matches."""
    stripped = {n[len(prefix) + 1:].lower() for n in port_names}

    # AXI4-Full: >=50% of full signal set AND at least one burst-specific signal
    # (burst check distinguishes Full from Lite, since all Lite signals are in Full)
    if (len(stripped & _AXI4_FULL_SIGNALS) >= len(_AXI4_FULL_SIGNALS) * 0.5
            and stripped & _AXI4_FULL_BURST_SIGNALS):
        return f"AXI4-Full{_role_suffix(prefix)}"

    # AXI4-Lite: >=50% of lite signal set
    if len(stripped & _AXI4_LITE_SIGNALS) >= len(_AXI4_LITE_SIGNALS) * 0.5:
        return f"AXI4-Lite{_role_suffix(prefix)}"

    # AXI4-Stream: all four minimum signals present
    if _AXI4_STREAM_MIN.issubset(stripped):
        return f"AXI4-Stream{_role_suffix(prefix)}"

    # APB: >=50% of APB signal set
    if len(stripped & _APB_SIGNALS) >= len(_APB_SIGNALS) * 0.5:
        return "APB Subordinate"

    # Wishbone: >=50% of Wishbone signal set
    if len(stripped & _WISHBONE_SIGNALS) >= len(_WISHBONE_SIGNALS) * 0.5:
        return "Wishbone"

    return None


def _load_custom_groups(toml_path: Path | None) -> list[dict]:
    """Load [[group]] entries from bus_groups.toml. Returns [] on any error."""
    if toml_path is None or not toml_path.exists():
        return []
    try:
        import tomllib
        data = tomllib.loads(toml_path.read_text())
        return data.get("group", [])
    except Exception:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def group_ports(
    ports: list[dict],
    toml_path: Path | None = None,
) -> tuple[list[BusGroup], list[dict]]:
    """
    Group ports into bus interfaces.

    Returns (bus_groups, remaining_ports).
    remaining_ports preserves the original order of ports not assigned to a group.
    """
    custom        = _load_custom_groups(toml_path)
    prefix_groups = _find_prefix_groups(ports)
    grouped_names: set[str] = set()
    bus_groups: list[BusGroup] = []

    # Process longest (most specific) prefix first so s_axi wins over s
    for prefix in sorted(prefix_groups, key=len, reverse=True):
        candidates = [p for p in prefix_groups[prefix]
                      if p["name"] not in grouped_names]
        if len(candidates) < 3:
            continue

        # Custom TOML match takes priority over built-in patterns
        custom_match = next((c for c in custom if c.get("prefix") == prefix), None)
        if custom_match:
            label = custom_match.get("label")
            if not label:
                continue  # silently skip malformed group entry
            bus_groups.append(BusGroup(
                prefix=prefix,
                bus_type=label,
                ports=candidates,
            ))
            grouped_names.update(p["name"] for p in candidates)
            continue

        bus_type = _match_bus_type(prefix, [p["name"] for p in candidates])
        if bus_type:
            bus_groups.append(BusGroup(
                prefix=prefix,
                bus_type=bus_type,
                ports=candidates,
            ))
            grouped_names.update(p["name"] for p in candidates)

    remaining = [p for p in ports if p["name"] not in grouped_names]
    return bus_groups, remaining
