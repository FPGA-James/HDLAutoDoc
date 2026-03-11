# Release Notes — v3.0.0

## CDC Analysis

Each module now gets a **Clock Domain Crossing (CDC) analysis page** generated automatically as part of `make html`.

`extract_cdc.py` performs static analysis on every HDL source file:

- **Clock domain identification** — detects clocked processes from `rising_edge(clk)` (VHDL) and `always_ff @(posedge clk)` (SystemVerilog) patterns.
- **Signal crossing detection** — identifies signals driven in one clock domain and read in another.
- **Two-flop synchronizer detection** — marks a crossing as *synchronized* when the signal feeds a back-to-back register chain in the destination domain.
- **Dual-clock instance detection** — flags instantiations where two or more clock-named ports (`*clk*`, `*clock*`, `*ck*`) connect to different signals, indicating an async FIFO or similar CDC structure.

The `cdc.rst` page for each module includes:

- A **Graphviz diagram** with clock domains as color-coded clusters, crossing signals as labeled edges (green solid = synchronized, red dashed = unsynchronized).
- A clock domains table listing all clocked processes per domain.
- A signal crossings table with synchronized status.
- A dual-clock instances table when async FIFOs or equivalent structures are detected.
- Modules with a single clock domain display a "No CDC" note. Purely combinational modules are also noted.

### Known limitations

- Static analysis only — CDC in black-box instances or generated code is not detected.
- Clock identity is name-based; aliased clocks may produce false positives.
- Only the two-flop back-to-back register pattern is recognised as a synchronizer. Handshake, gray-code, and FIFO-based CDC are not automatically marked as synchronized.
- Reset domain crossings are not covered.

---

## Register Generation

A register generation pipeline is now included alongside the documentation pipeline.

- Register maps are defined in `registers/regs_<name>.toml` (or `.yml`) using [hdl-registers](https://hdl-registers.com) format.
- `scripts/registers/generate.py` produces VHDL register packages, an AXI-Lite wrapper, a C header, and HTML documentation into `registers/generated/`.
- `make regs` runs generation. `make doc` runs registers + HTML + PDF in sequence.
- Bus configuration (width, address width, protocol) lives in `registers/config.yml`.

---

## Makefile Variable Renaming

All Makefile variables have been prefixed to clarify which part of the pipeline they belong to:

| Old name | New name | Belongs to |
|---|---|---|
| `SPHINXOPTS` | `AUTODOC_SPHINXOPTS` | Sphinx pipeline |
| `SPHINXBUILD` | `AUTODOC_SPHINXBUILD` | Sphinx pipeline |
| `SOURCEDIR` | `AUTODOC_SOURCEDIR` | Sphinx pipeline |
| `BUILDDIR` | `AUTODOC_BUILDDIR` | Sphinx pipeline |
| `SCRIPTDIR` | `AUTODOC_SCRIPTDIR` | Sphinx pipeline |
| `FILELIST` | `AUTODOC_FILELIST` | Sphinx pipeline |
| `HIERARCHY_JSON` | `AUTODOC_HIERARCHY_JSON` | Sphinx pipeline |
| `REG_ENTRY` | `AUTODOC_REG_ENTRY` | Sphinx pipeline |
| `REGGEN` | `AUTODOC_REGGEN` | Sphinx pipeline |
| `CONFIG` | `REGS_CONFIG` | Register generation |
| `REGMAP` | `REGS_REGMAP` | Register generation |
| `REG_OUT_DIR` | `REGS_GENERATED_DIR` | Register generation |
| `OUT_DIR` | `REGS_OUT_DIR` | Register generation |
| `PLUGINS` | `REGS_PLUGINS` | Register generation |

---

## New Make Targets

| Target | Description |
|---|---|
| `make regs` | Generate register artifacts from `registers/regs_*.toml` |
| `make doc` | Run `regs` + `html` + `pdf` in sequence |

---

## Test Suite

A pytest suite covering all pipeline scripts has been added under `scripts/hdl_autodoc/tests/`.

Run with:

```bash
pytest scripts/hdl_autodoc/tests/
```

| Test file | Coverage |
|---|---|
| `test_parse_hierarchy.py` | Module name extraction, instantiation detection, hierarchy building |
| `test_extract_fsm.py` | FSM transition extraction (VHDL + SV), dot and RST output |
| `test_extract_processes.py` | Process/always block discovery, comment tokens, RST rendering |
| `test_extract_cdc.py` | Clock domain identification, crossing detection, synchronizer detection, FIFO detection, dot output |
| `test_generate_rst.py` | Toctree generation, entity/FSM/CDC RST, file write helpers |
| `test_include_registers.py` | Entry point detection, placeholder vs iframe output, directory copy |

---

## Bug Fixes

- Fixed `cclean-generated` typo in Makefile (was a double `c`, target was unreachable).
- Fixed stray characters in `AUTODOC_REG_ENTRY` default value (`counter_regs.htmlP` → `counter_regs.html`).
- Fixed stray characters in `AUTODOC_REGGEN` comment (`diffePrent` → `different`).
