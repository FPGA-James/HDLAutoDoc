"""
parse_utilization.py
--------------------
Parse synthesis utilization reports from Vivado and Yosys into a common
data model.

Public API
----------
    from parse_utilization import ModuleUtilization, parse_utilization

    modules, tool = parse_utilization(Path("reports/vivado/utilization_placed.rpt"))
    # tool  → "vivado" | "yosys" | None
    # modules[0]  → top-level totals
    # modules[1:] → per-instance breakdown (only when hierarchical data present)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModuleUtilization:
    module_name: str
    luts: int = 0
    ffs: int = 0
    brams: int = 0
    dsps: int = 0
    luts_available: int | None = None   # Vivado only
    ffs_available: int | None = None    # Vivado only


# ── Yosys cell-name → resource category ──────────────────────────────────────
# Cell names are lower-cased before matching.
_LUT_CELLS = frozenset({
    "$lut", "lut4", "sb_lut4", "trellis_comb", "ice_lc",
})
_FF_CELLS = frozenset({
    "$dff", "$dffe", "$adff", "$adffe", "$sdff", "$sdffe",
    "dff", "dffe", "fdre", "fdce", "fdpe", "fdse",
    "sb_dff", "sb_dffe", "sb_dffr", "sb_dffs", "sb_dffsr",
    "trellis_ff",
})
_BRAM_CELLS = frozenset({
    "sb_ram40_4k", "sb_ram40_4knr", "sb_ram40_4knrnw",
    "trellis_bram", "dp16kd", "pdp16kd",
    "ramb18e1", "ramb18e2", "ramb36e1", "ramb36e2",
})
_DSP_CELLS = frozenset({
    "sb_mac16", "mult18x18d", "alu24b",
    "dsp48e1", "dsp48e2",
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_int(s: str) -> int:
    return int(s.replace(",", "").strip())


def _vivado_row(text: str, label_re: str) -> tuple[int, int | None]:
    """
    Extract (Used, Available) from a Vivado ASCII table row.
    Row format: | label | Used | Fixed | Prohibited | Available | Util% |
    Returns (0, None) when the row is absent.
    """
    m = re.search(
        r'\|\s*' + label_re + r'\s*\|'
        r'\s*(\d[\d,]*)\s*\|'    # Used
        r'[^|]*\|'               # Fixed
        r'[^|]*\|'               # Prohibited
        r'\s*(\d[\d,]*)\s*\|',   # Available
        text,
        re.IGNORECASE,
    )
    if m:
        return _parse_int(m.group(1)), _parse_int(m.group(2))
    m2 = re.search(
        r'\|\s*' + label_re + r'\s*\|\s*(\d[\d,]*)\s*\|',
        text,
        re.IGNORECASE,
    )
    if m2:
        return _parse_int(m2.group(1)), None
    return 0, None


def _normalise_instance(name: str) -> str:
    """Strip common instance prefixes and lowercase: u_blinky → blinky."""
    return re.sub(r'^[ui]_', '', name.strip()).lower()


# ── Vivado parser ─────────────────────────────────────────────────────────────

def _parse_vivado(text: str) -> list[ModuleUtilization]:
    # Top-level summary from the Slice Logic table
    top = ModuleUtilization(module_name="top")
    luts, luts_av = _vivado_row(text, r"Slice LUTs\*?")
    if luts == 0:
        luts, luts_av = _vivado_row(text, r"LUT as Logic")
    top.luts, top.luts_available = luts, luts_av

    ffs, ffs_av = _vivado_row(text, r"Slice Registers")
    if ffs == 0:
        ffs, ffs_av = _vivado_row(text, r"Register as Flip Flop")
    top.ffs, top.ffs_available = ffs, ffs_av

    top.brams, _ = _vivado_row(text, r"Block RAM Tile")
    top.dsps,  _ = _vivado_row(text, r"DSPs?")

    # Hierarchical section — detect by "| Instance |" header row
    hdr = re.search(r'\|\s*Instance\s*\|[^\n]*\n', text, re.IGNORECASE)
    if not hdr:
        return [top]

    hdr_cols = [c.strip().lower() for c in hdr.group(0).split("|")]
    col: dict[str, int] = {}
    for i, h in enumerate(hdr_cols):
        if re.match(r"lut", h):    col["luts"]  = i
        elif re.match(r"ff", h):   col["ffs"]   = i
        elif re.match(r"bram", h): col["brams"] = i
        elif re.match(r"dsp", h):  col["dsps"]  = i
    if "luts" not in col or "ffs" not in col:
        return [top]

    # Data rows live between the two +---+ separators that bracket the table body
    sep_re = re.compile(r'^\+[-+]+\+\s*$', re.MULTILINE)
    hier_results: list[ModuleUtilization] = []
    for sep_match in sep_re.finditer(text, hdr.end()):
        row_start = sep_match.end()
        end_match = sep_re.search(text, row_start)
        if not end_match:
            break
        for line in text[row_start:end_match.start()].split("\n"):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")]
            if len(cells) < max(col.values()) + 1:
                continue
            inst = cells[1]
            if not inst or inst.startswith("("):
                continue
            clean = _normalise_instance(inst)
            if not clean:
                continue
            try:
                hier_results.append(ModuleUtilization(
                    module_name=clean,
                    luts  = _parse_int(cells[col["luts"]]),
                    ffs   = _parse_int(cells[col["ffs"]]),
                    brams = _parse_int(cells[col["brams"]]) if "brams" in col else 0,
                    dsps  = _parse_int(cells[col["dsps"]])  if "dsps"  in col else 0,
                ))
            except (ValueError, IndexError):
                continue
        break  # only the first hierarchical table

    if hier_results:
        # Restore available counts from the summary onto the top-level hier entry
        for m in hier_results:
            if m.module_name == "top":
                m.luts_available = top.luts_available
                m.ffs_available  = top.ffs_available
                break
        return hier_results
    return [top]


# ── Yosys stat parser ─────────────────────────────────────────────────────────

def _parse_yosys(text: str) -> list[ModuleUtilization]:
    results: list[ModuleUtilization] = []
    sections = re.split(r'^=== (.+?) ===$', text, flags=re.MULTILINE)
    for i in range(1, len(sections), 2):
        name = sections[i].strip()
        body = sections[i + 1] if i + 1 < len(sections) else ""
        if name.lower() == "aggregate":
            continue
        mu = ModuleUtilization(module_name=name.lower())
        for line in body.split("\n"):
            m = re.match(r'\s+(\S+)\s+(\d+)', line)
            if not m:
                continue
            cell  = m.group(1).lower()
            count = int(m.group(2))
            if cell in _LUT_CELLS:   mu.luts   += count
            elif cell in _FF_CELLS:  mu.ffs    += count
            elif cell in _BRAM_CELLS: mu.brams += count
            elif cell in _DSP_CELLS:  mu.dsps  += count
        results.append(mu)
    return results


# ── Public API ────────────────────────────────────────────────────────────────

def parse_utilization(path: Path) -> tuple[list[ModuleUtilization], str | None]:
    """
    Parse a utilization report file.

    Returns (modules, tool) where tool is "vivado", "yosys", or None.
    Returns ([], None) if the file does not exist or format is unrecognised.
    """
    if not path.exists():
        return [], None
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return [], None

    if re.search(r'\|\s*Site Type\s*\|', text) or "Slice LUTs" in text:
        return _parse_vivado(text), "vivado"
    if re.search(r'^=== .+ ===$', text, re.MULTILINE):
        return _parse_yosys(text), "yosys"
    return [], None
