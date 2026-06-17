# Port Descriptions & Bus Interface Grouping — Design Spec

**Date:** 2026-06-17
**Status:** Approved

---

## Overview

Enhance the block diagram page (`_block.rst`) so that:

1. Port descriptions are surfaced clearly for every port (already extracted from source comments; this feature improves display).
2. Ports that form a recognisable bus interface (AXI4-Lite, APB, Wishbone, or user-declared custom) are collapsed into a single expandable row in the port table.
3. Users can declare custom bus groups in a project-level TOML file without touching HDL source.

---

## Architecture & Data Flow

Two new components, one modified file:

**`detect_buses.py`** — knows about bus standards; groups a flat port list into `(bus_groups, remaining_ports)`. Loads project-level `bus_groups.toml` for custom groups. No rendering concern.

**`extract_block.py`** (updated) — calls `detect_buses.group_ports(ports, toml_path)` before writing output. If any groups are found, the port table switches from `.. list-table::` to `.. raw:: html` — a single HTML table where bus groups get a `<details>` collapsed row and remaining individual ports get plain `<tr>` rows. If no groups are found, the output is unchanged.

**`docs/hdl_autodoc/bus_groups.toml`** (optional, user-created) — custom group definitions. Not auto-generated; `extract_block.py` silently skips it if absent.

**No new Makefile target.** Bus detection runs as part of `make extract`. The TOML path is passed to `extract_block.py` as a new optional CLI arg `--bus-groups <path>`. `run_extract.py` passes `$(AUTODOC_SOURCEDIR)/bus_groups.toml` if the file exists.

---

## `detect_buses.py` Module

### Data Model

```python
@dataclass
class BusGroup:
    prefix: str        # e.g. "s_axi"
    bus_type: str      # e.g. "AXI4-Lite Subordinate"
    ports: list[dict]  # the matched port dicts (full, unstripped)

def group_ports(
    ports: list[dict],
    toml_path: Path | None = None,
) -> tuple[list[BusGroup], list[dict]]:
    ...
    # Returns (bus_groups, remaining_ports)
    # remaining_ports preserves original order minus grouped ports
```

### Detection Algorithm

1. **Find common prefixes** — scan port names for a shared `<prefix>_` prefix. Require ≥ 3 ports per candidate prefix to form a group.
2. **Match against custom TOML first** — if the prefix matches a `[[group]]` entry, create a `BusGroup` with the user-supplied label (no signal-set check required).
3. **Match against built-in patterns** — strip the prefix from signal names, then check the stripped names against each built-in bus signal set. A match requires ≥ 50% of the canonical signal set to be present.
4. **Unmatched prefix groups** — if a prefix group has ≥ 3 ports but does not match any bus pattern, the ports remain as individual rows.

### Built-in Bus Patterns

Patterns are checked in order — AXI4-Full before AXI4-Lite to avoid a burst interface being mis-labelled as Lite.

| Type | Key signals (stripped names) |
|---|---|
| AXI4-Full Subordinate | `awvalid awready awaddr awlen awsize awburst wvalid wready wdata wstrb wlast bvalid bready bresp arvalid arready araddr arlen arsize arburst rvalid rready rdata rresp rlast` — prefix hint: contains `s_` or `slv_` |
| AXI4-Full Manager | same signal set — prefix hint: contains `m_` or `mst_` |
| AXI4-Lite Subordinate | `awvalid awready awaddr wvalid wready wdata wstrb bvalid bready bresp arvalid arready araddr rvalid rready rdata rresp` — prefix hint: contains `s_` or `slv_` |
| AXI4-Lite Manager | same signal set — prefix hint: contains `m_` or `mst_` |
| AXI4-Stream Manager | `tvalid tready tdata tlast` (minimum required set; `tstrb tkeep tid tdest tuser` optional) — prefix hint: contains `m_` or `mst_` |
| AXI4-Stream Subordinate | same signal set — prefix hint: contains `s_` or `slv_` |
| AXI4-Stream | same signal set — no Manager/Subordinate prefix hint present |
| APB Subordinate | `psel penable paddr pwdata prdata pwrite pready` |
| Wishbone | `cyc stb ack adr dat_i dat_o we` |

When a prefix group matches an AXI4 or AXI4-Stream signal set, the Manager vs. Subordinate label is chosen based on prefix hint (`m_`/`mst_` → Manager, `s_`/`slv_` → Subordinate); if neither hint is present, the label defaults to "AXI4-Full", "AXI4-Lite", or "AXI4-Stream" without a role qualifier.

---

## TOML Config

**Path:** `docs/hdl_autodoc/bus_groups.toml` (optional, user-created)

```toml
[[group]]
prefix = "dma"
label  = "DMA Write Master"

[[group]]
prefix = "cfg"
label  = "Config Interface"
```

Only `prefix` and `label` are required fields. Custom groups match purely by prefix — no signal-set check. If the file is absent or malformed, bus detection continues with built-in patterns only (no error raised).

---

## HTML Output Format

When bus groups are detected, the entire Ports section is rendered as `.. raw:: html`. The outer table preserves the existing 4-column layout (Port, Direction, Type, Description).

**Bus group row** — a `<details>` element spanning all 4 columns:

```html
<table class="port-table">
  <thead>
    <tr>
      <th>Port</th><th>Direction</th><th>Type</th><th>Description</th>
    </tr>
  </thead>
  <tbody>
    <!-- Bus group row -->
    <tr class="bus-group-row">
      <td colspan="4">
        <details>
          <summary>
            <strong>s_axi</strong> — AXI4-Lite Subordinate (9 ports)
          </summary>
          <table class="bus-ports-inner">
            <tr>
              <td><code>s_axi_awvalid</code></td>
              <td><code>in</code></td>
              <td><code>std_logic</code></td>
              <td>AXI write address valid.</td>
            </tr>
            <!-- ... remaining bus ports ... -->
          </table>
        </details>
      </td>
    </tr>
    <!-- Individual (non-bus) port row -->
    <tr>
      <td><code>clk</code></td>
      <td><code>in</code></td>
      <td><code>std_logic</code></td>
      <td>System clock, rising-edge triggered.</td>
    </tr>
  </tbody>
</table>
```

No JavaScript — `<details>`/`<summary>` is native HTML. When no bus groups are detected, the port section remains as `.. list-table::` exactly as today.

---

## `extract_block.py` Changes

- New optional CLI arg: `--bus-groups <path>` (path to `bus_groups.toml`; silently ignored if absent)
- Before rendering, call `detect_buses.group_ports(ports, toml_path)` → `(bus_groups, remaining)`
- If `bus_groups` is non-empty: render the Ports section using `_html_port_table(bus_groups, remaining)` → `.. raw:: html`
- If `bus_groups` is empty: render as before with `.. list-table::` (no change to existing output)

`run_extract.py` — always passes `--bus-groups $(AUTODOC_SOURCEDIR)/bus_groups.toml` to `extract_block.py`. Since `extract_block.py` already silently skips an absent TOML, no conditional is needed in either `run_extract.py` or the Makefile.

---

## CSS Additions (`custom.css`)

Four new rules using existing Catppuccin Latte/Mocha tokens:

- `.port-table` — table layout, full width, border-collapse, consistent with existing `.coverage-table`
- `.bus-group-row` — subtle tinted background (surface1 token) to distinguish bus rows
- `.bus-group-row summary` — cursor pointer; `▶` indicator replaced by browser-native `<details>` triangle
- `.bus-ports-inner` — compact inner table: smaller font size (0.9em), tighter cell padding, indented left margin

---

## Testing

New file: `scripts/hdl_autodoc/tests/test_detect_buses.py`

| # | Test |
|---|---|
| 1 | AXI4-Full Subordinate detected from `s_axi_` prefix with ≥50% signal match (has `awlen`, `wlast`, etc.) |
| 2 | AXI4-Lite Subordinate detected from `s_axi_` prefix when burst signals absent |
| 3 | AXI4-Stream detected from `axis_` prefix with tvalid/tready/tdata/tlast present |
| 4 | APB detected from `apb_` prefix with ≥50% signal match |
| 5 | Wishbone detected from `wb_` prefix with ≥50% signal match |
| 6 | Custom group matched by prefix from TOML |
| 7 | Prefix with < 3 ports not grouped |
| 8 | Prefix with < 50% signal match not grouped as known bus (ports remain individual) |
| 9 | `group_ports` preserves order of remaining ports |
| 10 | Missing TOML path → silently returns no custom groups |
| 11 | Malformed TOML → silently returns no custom groups (no exception) |

`scripts/hdl_autodoc/tests/test_extract_block.py` — 2 new tests:

| # | Test |
|---|---|
| 12 | Bus group produces `<details>` HTML and `.. raw:: html` in RST output |
| 13 | No bus groups → port section uses `.. list-table::` (unchanged) |

---

## What Does Not Change

- The `.. list-table::` Signals and Generics/Parameters sections are unaffected.
- `entity.rst` (hand-editable) is untouched.
- `generate_coverage.py` port count logic is unaffected — it counts `list-table` data rows for individual ports; bus-grouped ports in HTML are not counted. This is acceptable: the coverage signal reflects individually documented ports, not bus groups.
- No changes to `hierarchy.json`, `generate_rst.py`, or Sphinx config.
