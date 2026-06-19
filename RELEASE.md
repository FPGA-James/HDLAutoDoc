# Release Notes

## v3.5.0

### Template Repo Restructure

The repository has been reorganised into a reusable template layout:

| Directory | Contents |
|---|---|
| `src/` | Canonical tool — pipeline scripts, Sphinx config, Makefile, requirements.txt |
| `example/` | Self-contained working demo — traffic light + PWM controller HDL with registers and dummy synthesis reports |

**`install.sh`** — new helper script that copies the tool into any target HDL project:

```bash
./install.sh /path/to/your/hdl-project
```

Re-running is safe: `scripts/` and `docs/hdl_autodoc/` are always overwritten with the latest version; `Makefile` and `requirements.txt` are skipped if they already exist.

**`.gitignore`** has been updated to exclude all auto-generated Sphinx files (`modules/`, `synthesis/`, `hierarchy.json`, `_static/registers/`, `_build/`) under any nested `docs/hdl_autodoc/` tree.

#### Breaking changes

- `scripts/`, `docs/hdl_autodoc/`, `registers/`, `Makefile`, `requirements.txt`, and `filelist.f` no longer live at the repository root. Use `install.sh` to place them in your project.

---

## v3.4.0

### Synthesis Reports

`make reports` ingests post-synthesis and post-route report files from a `reports/` directory and writes an **Implementation** section into the documentation sidebar.

**Supported toolchains:**

| Toolchain | Utilization file | Timing file |
|---|---|---|
| Vivado (Xilinx) | `reports/vivado/utilization_placed.rpt` (falls back to `utilization_synth.rpt`) | `reports/vivado/timing_summary_routed.rpt` |
| Yosys + nextpnr (Lattice ECP5, iCE40) | `reports/yosys/stat.txt` | `reports/yosys/nextpnr.log` |

**New scripts:**

- `parse_utilization.py` — parses Vivado ASCII utilization tables (including hierarchical breakdown with depth tracking) and Yosys `stat.txt` cell counts into a common `ModuleUtilization` dataclass.
- `parse_timing.py` — parses Vivado `WNS` + `Period` into achieved fmax, and nextpnr `Max frequency` lines. Strips nextpnr infrastructure prefixes (`$glbnet$`, `gbuf`, `clkbuf`) from clock names.
- `extract_reports.py` — orchestrates both parsers and writes `docs/hdl_autodoc/synthesis/index.rst` (top-level timing + utilization tables) and `docs/hdl_autodoc/modules/<n>/synthesis.rst` (per-module resource counts).

**Utilization table** — modules shown with hierarchy indentation (`└─ submodule`) and available resource counts in column headers (Vivado only).

**Timing table** — clock name, target frequency (MHz), achieved fmax (MHz), constraint period (ns), and WNS (ns) for Vivado; clock name, fmax, target, and PASS/FAIL status for nextpnr.

`generate_rst.py` detects the presence of `synthesis/index.rst` and adds an **Implementation** toctree section to the top-level sidebar when reports are available. A placeholder page is always written so the section remains visible even when no reports are present.

**Test coverage:** `test_parse_utilization.py` (9 tests), `test_parse_timing.py` (8 tests), `test_extract_reports.py` (7 tests), 4 new tests in `test_generate_rst.py`.

### Furo Theme

Migrated from `sphinx-rtd-theme` to [Furo](https://pradyunsg.me/furo/):

- Built-in dark/light toggle — top-right button, `localStorage` persistence, respects OS `prefers-color-scheme` on first visit.
- `Ctrl+K` / `Cmd+K` keyboard shortcut focuses the sidebar search input (via `_static/search-hotkey.js`).
- Wider content column and responsive sidebar that collapses cleanly on mobile.
- `docutils` pinned to `>=0.18,<0.21` for `sphinx-vhdl` compatibility.

---

## v3.3.0

### RTL Schematics

Gate-level netlists rendered inside each module's block diagram page. Enabled with `make html SCHEMATICS=1`; off by default.

`generate_schematic.py` synthesises each module with `yosys` to a JSON netlist, then renders a clean SVG schematic with `netlistsvg`. The SVG is embedded as an *RTL Schematic* section at the bottom of the block diagram page.

**Tool requirements:**

| Module type | Required tools |
|---|---|
| SystemVerilog | `yosys`, `netlistsvg` |
| VHDL | `yosys`, `netlistsvg`, `ghdl`, `ghdl-yosys-plugin` (via OSS CAD Suite) |

Missing tools produce a warning and the build continues without schematics. Mixed-language top-level modules and modules with unconnected ports or non-synthesisable constructs are skipped cleanly.

### `make venv` Target

Creates a `.venv/` virtualenv and installs all Python dependencies in one step. Subsequent `make` commands auto-detect `.venv/bin/python3`, keeping the project isolated from system Python and tools like OSS CAD Suite on `PATH`.

### Sphinx Invocation Fix

Sphinx is now invoked as `$(PYTHON) -m sphinx` rather than the `sphinx-build` binary, preventing `PATH` shadowing issues when OSS CAD Suite installs its own `sphinx-build` wrapper.

---

## v3.2.0

### Block Diagrams

Each module now gets a **`block.rst` page** generated automatically, containing a TerosHDL-inspired block diagram and interface tables.

`extract_block.py` performs the following extraction:

- **Port extraction** — name, direction (`in`/`out`/`inout`), type, bus width range, and description from VHDL `port (...)` and SV module port lists. Comments on the preceding line or same line as the declaration are both captured.
- **Generics / parameters extraction** — name, type, default value, and description from VHDL `generic (...)` and SV `parameter`/`localparam` declarations.

The `block.rst` page includes:

- A **Graphviz block diagram** using a TerosHDL-inspired style:
  - **Green box** (top) — generics/parameters with name and default value, one row each.
  - **Yellow box** (below) — port interface; inputs left-aligned with `►`, outputs right-aligned with `◄`; bus widths annotated inline (e.g. `[8]`, `[WIDTH-1:0]`).
- A **port table** — name, direction, type, description.
- A **generics/parameters table** — name, type, default, description (omitted if the module has no generics).

**`test_extract_block.py`** — 36 tests covering VHDL/SV port and generic extraction, width label computation, dot output structure, and RST content.

### Known limitations

- Port comments are captured from the same line or the immediately preceding comment line only. Multi-line preceding comment blocks are not aggregated.
- SV named parameter syntax (`#(.PARAM(val))`) in instantiations is not detected by the hierarchy parser; positional syntax (`#(val)`) is supported.

---

## v3.1.0

### Test Suite

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
| `test_generate_rst.py` | Toctree generation, entity/FSM/CDC/block RST, file write helpers |
| `test_include_registers.py` | Entry point detection, placeholder vs iframe output, directory copy |

### VS Code test runner configuration

- `pytest.ini` — sets `testpaths` and `pythonpath` so VS Code discovers tests without manual path configuration.
- `.python-version` — pins pyenv to the project Python version.
- `.vscode/settings.json` — points the Python extension at the correct interpreter and enables pytest.

---

## v3.0.0

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
