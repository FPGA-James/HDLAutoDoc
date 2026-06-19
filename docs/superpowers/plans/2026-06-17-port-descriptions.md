# Port Descriptions & Bus Interface Grouping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect standard bus interfaces from port name prefixes and collapse them into expandable `<details>` rows on each module's block diagram page.

**Architecture:** New `detect_buses.py` groups a flat port list by shared `<prefix>_` prefix and matches against built-in AXI/APB/Wishbone signal sets plus a project-level TOML for custom groups. `extract_block.py` calls it before rendering and switches from `.. list-table::` to `.. raw:: html` when any groups are found. `run_extract.py` passes the TOML path through; `custom.css` gains four new rules.

**Tech Stack:** Python 3.11+ stdlib (`tomllib`, `dataclasses`), HTML `<details>`/`<summary>`, Catppuccin CSS tokens, pytest.

---

### Task 1: detect_buses.py — bus detection module and tests

**Files:**
- Create: `scripts/hdl_autodoc/detect_buses.py`
- Create: `scripts/hdl_autodoc/tests/test_detect_buses.py`

- [ ] **Step 1: Write the failing tests**

Create `scripts/hdl_autodoc/tests/test_detect_buses.py`:

```python
"""
test_detect_buses.py
--------------------
Tests for detect_buses.py.

Covers all 11 cases from the spec:
  1.  AXI4-Full Subordinate detected from s_axi_ prefix
  2.  AXI4-Lite Subordinate detected when burst signals absent
  3.  AXI4-Stream detected from axis_ prefix
  4.  APB Subordinate detected from apb_ prefix
  5.  Wishbone detected from wb_ prefix
  6.  Custom group matched by prefix from TOML
  7.  Prefix with < 3 ports not grouped
  8.  Prefix with < 50% signal match not grouped
  9.  group_ports preserves order of remaining ports
  10. Missing TOML path → no custom groups (no error)
  11. Malformed TOML → no custom groups (no error)
"""

import pytest
from pathlib import Path

from detect_buses import BusGroup, group_ports


def _port(name: str, dir_: str = "in", type_: str = "std_logic") -> dict:
    return {"name": name, "dir": dir_, "type": type_, "range": None, "comment": ""}


# ── Test 1: AXI4-Full Subordinate ────────────────────────────────────────────

def test_axi4_full_subordinate():
    ports = [_port(f"s_axi_{sig}") for sig in [
        "awvalid", "awready", "awaddr", "awlen", "awsize", "awburst",
        "wvalid", "wready", "wdata", "wstrb", "wlast",
        "bvalid", "bready", "bresp",
        "arvalid", "arready", "araddr", "arlen", "arsize", "arburst",
        "rvalid", "rready", "rdata", "rresp", "rlast",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "s_axi"
    assert groups[0].bus_type == "AXI4-Full Subordinate"
    assert remaining == []


# ── Test 2: AXI4-Lite Subordinate (no burst signals) ─────────────────────────

def test_axi4_lite_subordinate():
    ports = [_port(f"s_axi_{sig}") for sig in [
        "awvalid", "awready", "awaddr",
        "wvalid", "wready", "wdata", "wstrb",
        "bvalid", "bready", "bresp",
        "arvalid", "arready", "araddr",
        "rvalid", "rready", "rdata", "rresp",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "s_axi"
    assert groups[0].bus_type == "AXI4-Lite Subordinate"
    assert remaining == []


# ── Test 3: AXI4-Stream ───────────────────────────────────────────────────────

def test_axi4_stream():
    ports = [_port(f"axis_{sig}") for sig in [
        "tvalid", "tready", "tdata", "tlast",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "axis"
    assert groups[0].bus_type == "AXI4-Stream"
    assert remaining == []


def test_axi4_stream_manager():
    ports = [_port(f"m_axis_{sig}") for sig in [
        "tvalid", "tready", "tdata", "tlast",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].bus_type == "AXI4-Stream Manager"


def test_axi4_stream_subordinate():
    ports = [_port(f"s_axis_{sig}") for sig in [
        "tvalid", "tready", "tdata", "tlast",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].bus_type == "AXI4-Stream Subordinate"


# ── Test 4: APB Subordinate ───────────────────────────────────────────────────

def test_apb_subordinate():
    ports = [_port(f"apb_{sig}") for sig in [
        "psel", "penable", "paddr", "pwdata", "prdata", "pwrite", "pready",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "apb"
    assert groups[0].bus_type == "APB Subordinate"
    assert remaining == []


# ── Test 5: Wishbone ──────────────────────────────────────────────────────────

def test_wishbone():
    ports = [_port(f"wb_{sig}") for sig in [
        "cyc", "stb", "ack", "adr", "dat_i", "dat_o", "we",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "wb"
    assert groups[0].bus_type == "Wishbone"
    assert remaining == []


# ── Test 6: Custom group from TOML ────────────────────────────────────────────

def test_custom_group_from_toml(tmp_path):
    toml_file = tmp_path / "bus_groups.toml"
    toml_file.write_text('[[group]]\nprefix = "dma"\nlabel = "DMA Write Master"\n')
    ports = [_port(f"dma_{sig}") for sig in ["addr", "data", "valid"]]
    groups, remaining = group_ports(ports, toml_path=toml_file)
    assert len(groups) == 1
    assert groups[0].prefix == "dma"
    assert groups[0].bus_type == "DMA Write Master"
    assert remaining == []


# ── Test 7: Prefix with < 3 ports not grouped ────────────────────────────────

def test_fewer_than_three_ports_not_grouped():
    ports = [_port("clk"), _port("s_axi_awvalid"), _port("s_axi_awready")]
    groups, remaining = group_ports(ports)
    assert groups == []
    assert len(remaining) == 3


# ── Test 8: < 50% signal match not grouped ───────────────────────────────────

def test_low_signal_match_not_grouped():
    # Only 2 of 17 AXI4-Lite signals — below 50% threshold
    ports = [_port(f"s_axi_{sig}") for sig in ["awvalid", "wdata", "rresp"]]
    groups, remaining = group_ports(ports)
    assert groups == []
    assert len(remaining) == 3


# ── Test 9: Remaining ports preserve original order ──────────────────────────

def test_remaining_ports_preserve_order():
    ports = [_port("clk"), _port("rst"), _port("en")]
    _, remaining = group_ports(ports)
    assert [p["name"] for p in remaining] == ["clk", "rst", "en"]


# ── Test 10: Missing TOML path → no error ────────────────────────────────────

def test_missing_toml_path_no_error():
    ports = [_port("clk"), _port("rst"), _port("en")]
    groups, remaining = group_ports(ports, toml_path=None)
    assert groups == []
    assert len(remaining) == 3


def test_missing_toml_file_no_error(tmp_path):
    absent = tmp_path / "bus_groups.toml"
    ports = [_port("clk"), _port("rst"), _port("en")]
    groups, remaining = group_ports(ports, toml_path=absent)
    assert groups == []


# ── Test 11: Malformed TOML → no error ───────────────────────────────────────

def test_malformed_toml_no_error(tmp_path):
    bad_toml = tmp_path / "bus_groups.toml"
    bad_toml.write_text("[[group\nthis is not valid toml!!!")
    ports = [_port("clk"), _port("rst"), _port("en")]
    groups, remaining = group_ports(ports, toml_path=bad_toml)
    assert groups == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/james/Workspace/files
pytest scripts/hdl_autodoc/tests/test_detect_buses.py -v
```

Expected: `ModuleNotFoundError: No module named 'detect_buses'`

- [ ] **Step 3: Implement detect_buses.py**

Create `scripts/hdl_autodoc/detect_buses.py`:

```python
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
    """Return {prefix: [port, ...]} for all shared prefix_ groups with ≥ 3 ports."""
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

    # AXI4-Full: ≥50% of full signal set AND at least one burst-specific signal
    # (burst check distinguishes Full from Lite, since all Lite signals are in Full)
    if (len(stripped & _AXI4_FULL_SIGNALS) >= len(_AXI4_FULL_SIGNALS) * 0.5
            and stripped & _AXI4_FULL_BURST_SIGNALS):
        return f"AXI4-Full{_role_suffix(prefix)}"

    # AXI4-Lite: ≥50% of lite signal set
    if len(stripped & _AXI4_LITE_SIGNALS) >= len(_AXI4_LITE_SIGNALS) * 0.5:
        return f"AXI4-Lite{_role_suffix(prefix)}"

    # AXI4-Stream: all four minimum signals present
    if _AXI4_STREAM_MIN.issubset(stripped):
        return f"AXI4-Stream{_role_suffix(prefix)}"

    # APB: ≥50% of APB signal set
    if len(stripped & _APB_SIGNALS) >= len(_APB_SIGNALS) * 0.5:
        return "APB Subordinate"

    # Wishbone: ≥50% of Wishbone signal set
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
            bus_groups.append(BusGroup(
                prefix=prefix,
                bus_type=custom_match["label"],
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_detect_buses.py -v
```

Expected output (all 13 tests pass — 11 spec tests plus 2 AXI4-Stream role tests):
```
test_detect_buses.py::test_axi4_full_subordinate PASSED
test_detect_buses.py::test_axi4_lite_subordinate PASSED
test_detect_buses.py::test_axi4_stream PASSED
test_detect_buses.py::test_axi4_stream_manager PASSED
test_detect_buses.py::test_axi4_stream_subordinate PASSED
test_detect_buses.py::test_apb_subordinate PASSED
test_detect_buses.py::test_wishbone PASSED
test_detect_buses.py::test_custom_group_from_toml PASSED
test_detect_buses.py::test_fewer_than_three_ports_not_grouped PASSED
test_detect_buses.py::test_low_signal_match_not_grouped PASSED
test_detect_buses.py::test_remaining_ports_preserve_order PASSED
test_detect_buses.py::test_missing_toml_path_no_error PASSED
test_detect_buses.py::test_missing_toml_file_no_error PASSED
test_detect_buses.py::test_malformed_toml_no_error PASSED
```

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/detect_buses.py scripts/hdl_autodoc/tests/test_detect_buses.py
git commit -m "feat: add detect_buses module with AXI/APB/Wishbone/custom group detection"
```

---

### Task 2: extract_block.py — HTML port table and CLI arg

**Files:**
- Modify: `scripts/hdl_autodoc/extract_block.py:517-541` (port table section of `write_rst_block`)
- Modify: `scripts/hdl_autodoc/extract_block.py:600-635` (`__main__` block)
- Modify: `scripts/hdl_autodoc/tests/test_extract_block.py` (add 2 tests at end)

- [ ] **Step 1: Write the failing tests**

Add these two tests at the bottom of `scripts/hdl_autodoc/tests/test_extract_block.py`:

```python
# ── Bus interface tests ───────────────────────────────────────────────────────

def test_bus_group_produces_details_html():
    """Bus-detected ports render as .. raw:: html with <details> rows."""
    ports = [
        {"name": f"s_axi_{sig}", "dir": "in", "type": "std_logic",
         "range": None, "comment": f"{sig} signal"}
        for sig in [
            "awvalid", "awready", "awaddr",
            "wvalid",  "wready",  "wdata",  "wstrb",
            "bvalid",  "bready",  "bresp",
            "arvalid", "arready", "araddr",
            "rvalid",  "rready",  "rdata",  "rresp",
        ]
    ]
    rst = write_rst_block("mymod", "mymod.vhd", ports, [], [])
    assert ".. raw:: html" in rst
    assert "<details>" in rst
    assert "s_axi" in rst
    assert "AXI4-Lite Subordinate" in rst
    assert ".. list-table::" not in rst


def test_no_bus_groups_uses_list_table():
    """Without bus groups the port section stays as .. list-table::."""
    ports = [
        {"name": "clk",  "dir": "in",  "type": "std_logic", "range": None, "comment": "Clock"},
        {"name": "rst",  "dir": "in",  "type": "std_logic", "range": None, "comment": "Reset"},
        {"name": "data", "dir": "out", "type": "std_logic", "range": None, "comment": "Data"},
    ]
    rst = write_rst_block("mymod", "mymod.vhd", ports, [], [])
    assert ".. list-table::" in rst
    assert ".. raw:: html" not in rst
    assert "<details>" not in rst
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_extract_block.py::test_bus_group_produces_details_html \
       scripts/hdl_autodoc/tests/test_extract_block.py::test_no_bus_groups_uses_list_table -v
```

Expected: both FAIL (function signatures don't yet call `group_ports`)

- [ ] **Step 3: Add `_html_port_table` function and `html` import to extract_block.py**

In `extract_block.py`, the top-level imports already include `import html as _html`. If not present, add it. Then add the `_html_port_table` function directly before `write_rst_block` (around line 494):

```python
# ─────────────────────────────────────────────────────────────────────────────
# HTML port table (used when bus groups are detected)
# ─────────────────────────────────────────────────────────────────────────────

def _html_port_table(bus_groups: list, remaining: list[dict]) -> str:
    """
    Render port table as an indented HTML block for use inside ``.. raw:: html``.
    Bus groups get a <details>/<summary> collapsible row; individual ports get
    plain <tr> rows.
    """
    import html as _h

    rows: list[str] = []
    rows.append('<table class="port-table">')
    rows.append("  <thead>")
    rows.append("    <tr><th>Port</th><th>Direction</th>"
                "<th>Type</th><th>Description</th></tr>")
    rows.append("  </thead>")
    rows.append("  <tbody>")

    for bg in bus_groups:
        n = bg.ports.__len__()
        plural = "s" if n != 1 else ""
        rows.append('    <tr class="bus-group-row">')
        rows.append("      <td colspan=\"4\">")
        rows.append("        <details>")
        rows.append(
            f"          <summary><strong>{_h.escape(bg.prefix)}</strong>"
            f" \u2014 {_h.escape(bg.bus_type)} ({n} port{plural})</summary>"
        )
        rows.append('          <table class="bus-ports-inner">')
        for p in bg.ports:
            type_text = _type_str(p).replace("`", "")
            rows.append("            <tr>")
            rows.append(f'              <td><code>{_h.escape(p["name"])}</code></td>')
            rows.append(f'              <td><code>{_h.escape(p["dir"])}</code></td>')
            rows.append(f'              <td><code>{_h.escape(type_text)}</code></td>')
            rows.append(f'              <td>{_h.escape(p["comment"] or "")}</td>')
            rows.append("            </tr>")
        rows.append("          </table>")
        rows.append("        </details>")
        rows.append("      </td>")
        rows.append("    </tr>")

    for p in remaining:
        type_text = _type_str(p).replace("`", "")
        rows.append("    <tr>")
        rows.append(f'      <td><code>{_h.escape(p["name"])}</code></td>')
        rows.append(f'      <td><code>{_h.escape(p["dir"])}</code></td>')
        rows.append(f'      <td><code>{_h.escape(type_text)}</code></td>')
        rows.append(f'      <td>{_h.escape(p["comment"] or "")}</td>')
        rows.append("    </tr>")

    rows.append("  </tbody>")
    rows.append("</table>")

    # Each line is indented 3 spaces to satisfy RST's ``.. raw:: html`` block
    return "\n".join("   " + line for line in rows)
```

- [ ] **Step 4: Update `write_rst_block` signature and port table section**

Change the `write_rst_block` function signature (line 517) and its port table section (lines 527–541):

Old signature:
```python
def write_rst_block(module_name: str, src_filename: str,
                    ports: list[dict], generics: list[dict],
                    signals: list[dict],
                    include_schematic: bool = False) -> str:
```

New signature (add `toml_path` at end, before `include_schematic` is already last, so append):
```python
def write_rst_block(module_name: str, src_filename: str,
                    ports: list[dict], generics: list[dict],
                    signals: list[dict],
                    include_schematic: bool = False,
                    toml_path: "Path | None" = None) -> str:
```

Old port table section (lines 527–541):
```python
    # ── Port table ──────────────────────────────────────────────────────────
    if ports:
        lines += [
            "Ports", "-----", "",
            ".. list-table::", "   :header-rows: 1", "",
            "   * - Port", "     - Direction", "     - Type", "     - Description", "",
        ]
        for p in ports:
            lines += [
                f'   * - ``{p["name"]}``',
                f'     - {_DIR_RST.get(p["dir"], p["dir"])}',
                f'     - {_type_str(p)}',
                f'     - {p["comment"] or "—"}',
                "",
            ]
```

New port table section:
```python
    # ── Port table ──────────────────────────────────────────────────────────
    if ports:
        from detect_buses import group_ports
        bus_groups, remaining = group_ports(ports, toml_path)
        if bus_groups:
            lines += ["Ports", "-----", "", ".. raw:: html", ""]
            lines.append(_html_port_table(bus_groups, remaining))
            lines.append("")
        else:
            lines += [
                "Ports", "-----", "",
                ".. list-table::", "   :header-rows: 1", "",
                "   * - Port", "     - Direction", "     - Type", "     - Description", "",
            ]
            for p in ports:
                lines += [
                    f'   * - ``{p["name"]}``',
                    f'     - {_DIR_RST.get(p["dir"], p["dir"])}',
                    f'     - {_type_str(p)}',
                    f'     - {p["comment"] or "—"}',
                    "",
                ]
```

- [ ] **Step 5: Update `__main__` block to parse `--bus-groups`**

Replace the existing `__main__` block (lines 600–635) with:

```python
if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Usage: extract_block.py <file.vhd|file.sv> <module_name> <output_dir> "
                 "[--bus-groups <path>]")

    src_path    = Path(sys.argv[1])
    module_name = sys.argv[2]
    output_dir  = Path(sys.argv[3])
    output_dir.mkdir(parents=True, exist_ok=True)

    args = sys.argv[4:]
    toml_path: Path | None = None
    if "--bus-groups" in args:
        idx = args.index("--bus-groups")
        toml_path = Path(args[idx + 1])

    text = src_path.read_text()
    ext  = src_path.suffix.lower()

    if ext in (".vhd", ".vhdl"):
        ports    = extract_ports_vhdl(text)
        generics = extract_generics_vhdl(text)
        signals  = extract_signals_vhdl(text)
    elif ext in (".sv", ".svh"):
        ports    = extract_ports_sv(text)
        generics = extract_params_sv(text)
        signals  = extract_signals_sv(text)
    else:
        sys.exit(f"ERROR: Unsupported file type '{ext}'")

    dot_path = output_dir / f"{module_name}_block.dot"
    rst_path = output_dir / f"{module_name}_block.rst"

    # Include RTL schematic section if generate_schematic.py already wrote the SVG.
    schematic_svg = output_dir / f"{module_name}_schematic.svg"
    include_schematic = schematic_svg.exists()

    dot_path.write_text(write_dot_block(module_name, ports, generics))
    print(f"  → {dot_path}")

    rst_path.write_text(write_rst_block(module_name, src_path.name, ports, generics, signals,
                                        include_schematic, toml_path))
    print(f"  → {rst_path}")
```

- [ ] **Step 6: Run all extract_block tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_extract_block.py -v
```

Expected: all existing tests still pass, plus the 2 new ones.

- [ ] **Step 7: Commit**

```bash
git add scripts/hdl_autodoc/extract_block.py scripts/hdl_autodoc/tests/test_extract_block.py
git commit -m "feat: add HTML bus-group port table to extract_block with --bus-groups arg"
```

---

### Task 3: run_extract.py wiring + CSS

**Files:**
- Modify: `scripts/hdl_autodoc/run_extract.py:86-87` (extract_block subprocess call)
- Modify: `docs/hdl_autodoc/_static/custom.css` (append 4 new rules at end of file)

- [ ] **Step 1: Update run_extract.py to pass --bus-groups**

In `run_extract.py`, replace the extract_block subprocess call (lines 86–87):

Old:
```python
        run(["python", str(scripts_dir / "extract_block.py"),
             src_file, name, str(module_dir)])
```

New:
```python
        run(["python", str(scripts_dir / "extract_block.py"),
             src_file, name, str(module_dir),
             "--bus-groups", str(docs_dir / "bus_groups.toml")])
```

`extract_block.py` silently ignores the TOML path if the file is absent, so no conditional needed here.

- [ ] **Step 2: Verify the full test suite still passes**

```bash
pytest scripts/hdl_autodoc/tests/ -v
```

Expected: all tests pass (the new `--bus-groups` arg is accepted by the updated `__main__` block).

- [ ] **Step 3: Append CSS rules to custom.css**

At the very end of `docs/hdl_autodoc/_static/custom.css`, append:

```css

/* ── Bus-group port table ─────────────────────────────────────────────────── */

.port-table {
  border-collapse: collapse;
  width: 100%;
  margin: 1.5rem 0;
  font-family: var(--f-body);
  font-size: 0.9em;
}

.port-table th,
.port-table td {
  padding: 0.45rem 0.8rem;
  border: 1px solid var(--surface-0);
  text-align: left;
}

.port-table thead tr {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--subtext-1);
}

.bus-group-row td {
  background: var(--surface-1);
  padding: 0;
}

.bus-group-row summary {
  cursor: pointer;
  padding: 0.45rem 0.8rem;
  font-family: var(--f-mono);
}

.bus-ports-inner {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
  margin: 0.25rem 0 0.25rem 1.5rem;
}

.bus-ports-inner td {
  padding: 0.3rem 0.6rem;
  border: none;
  border-bottom: 1px solid var(--surface-0);
}
```

- [ ] **Step 4: Run full test suite one final time**

```bash
pytest scripts/hdl_autodoc/tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/run_extract.py docs/hdl_autodoc/_static/custom.css
git commit -m "feat: wire --bus-groups into run_extract and add port-table CSS"
```
