#!/usr/bin/env python3
"""
extract_registers.py
--------------------
Reads registers/regs_<module>.toml and writes registers.rst
to the module's doc directory.

Usage:
    python extract_registers.py <regs_toml> <module_name> <output_dir>
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


ACCESS_MAP = {"r_w": "r/w", "r": "r", "w": "w", "wpulse": "wpulse"}


def _access(mode: str) -> str:
    return ACCESS_MAP.get(mode, mode)


def _read_bus_width(regs_toml: Path) -> int:
    config = regs_toml.parent / "config.yml"
    if config.exists():
        m = re.search(r'bus_width:\s*(\d+)', config.read_text())
        if m:
            return int(m.group(1))
    return 32


def _render_field_type(fdata: dict) -> str:
    ftype = fdata.get("type", "")
    if ftype == "bit_vector":
        width = fdata.get("width", "")
        return f"bit_vector({width})" if width else "bit_vector"
    return ftype


def _render_enum_subtable(elements: dict[str, str]) -> list[str]:
    lines = [
        "",
        "       .. list-table::",
        "          :header-rows: 1",
        "          :widths: 50 50",
        "",
        "          * - Value",
        "            - Description",
    ]
    for val, desc in elements.items():
        lines.append(f"          * - ``{val}``")
        lines.append(f"            - {desc}")
    lines.append("")
    return lines


def _render_field_row(fname: str, fdata: dict) -> list[str]:
    ftype   = fdata.get("type", "")
    desc    = fdata.get("description", "")
    default = fdata.get("default_value", "")
    lines = [
        f"   * - ``{fname}``",
        f"     - {_render_field_type(fdata)}",
        f"     - {default}",
        f"     - {desc}",
    ]
    if ftype == "integer":
        mn = fdata.get("min_value")
        mx = fdata.get("max_value")
        if mn is not None and mx is not None:
            lines.append(f"       Range: {mn}–{mx}.")
    if ftype == "enumeration":
        elements = fdata.get("element", {})
        if elements:
            lines.extend(_render_enum_subtable(elements))
    return lines


def generate_registers_rst(regs_toml: Path, module_name: str) -> str:
    data      = tomllib.loads(regs_toml.read_text())
    bus_width = _read_bus_width(regs_toml)
    stride    = bus_width // 8

    registers = [(k, v) for k, v in data.items()
                 if isinstance(v, dict) and "mode" in v]

    title = f"{module_name} — Register Map"
    lines: list[str] = [title, "=" * len(title), ""]

    # Summary table
    lines += [
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 25 25 25 25",
        "",
        "   * - Register",
        "     - Offset",
        "     - Access",
        "     - Description",
    ]
    for i, (rname, rdata) in enumerate(registers):
        offset = f"0x{i * stride:02X}"
        lines += [
            f"   * - {rname}",
            f"     - {offset}",
            f"     - {_access(rdata.get('mode', ''))}",
            f"     - {rdata.get('description', '')}",
        ]
    lines.append("")

    # Per-register detail sections
    for i, (rname, rdata) in enumerate(registers):
        offset  = f"0x{i * stride:02X}"
        heading = f"{rname} ({offset})"
        lines += [heading, "-" * len(heading), ""]

        fields = [(k, v) for k, v in rdata.items()
                  if isinstance(v, dict) and "type" in v]
        if fields:
            lines += [
                ".. list-table::",
                "   :header-rows: 1",
                "   :widths: 25 25 25 25",
                "",
                "   * - Field",
                "     - Type",
                "     - Default",
                "     - Description",
            ]
            for fname, fdata in fields:
                lines.extend(_render_field_row(fname, fdata))
            lines.append("")
        else:
            lines += [f"No fields defined for ``{rname}``.", ""]

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: extract_registers.py <regs_toml> <module_name> <output_dir>")

    regs_toml   = Path(sys.argv[1])
    module_name = sys.argv[2]
    output_dir  = Path(sys.argv[3])

    rst = generate_registers_rst(regs_toml, module_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "registers.rst").write_text(rst)
    print(f"  → {output_dir / 'registers.rst'}")
