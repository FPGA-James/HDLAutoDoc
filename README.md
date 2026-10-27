# 📟 HDL AutoDoc

> **Turn your VHDL and SystemVerilog source into beautiful, navigable documentation — automatically.**

HDL AutoDoc is a zero-boilerplate documentation pipeline for hardware design projects. Drop your source files in, run `make doc-html`, and get a fully structured Sphinx site with block diagrams, FSM diagrams, timing waveforms, process pages, a hierarchy tree, a CDC analysis page per module, an embedded register map, and synthesis/place-and-route reports — all extracted directly from your HDL source and CI artifacts.

No separate doc files to maintain. No manual diagrams to draw. If it's in the source, it's in the docs.

---

## ✨ Features

| Feature | How it works |
|---|---|
| **Auto-discovered ports & entities** | Extracted from `entity`/`module` declarations |
| **Block diagrams** | TerosHDL-style port diagram (green generics box + yellow ports box) with bus widths, auto-generated per module |
| **RTL schematics** | Gate-level netlist diagram via `yosys`, inserted into each block diagram page — on by default (`SCHEMATICS=0` to skip) |
| **Generics / parameters table** | Name, type, default value, and description extracted from VHDL `generic` and SV `parameter`/`localparam` declarations |
| **FSM state diagrams** | Parsed from `case` blocks, rendered with [Graphviz](https://graphviz.org) |
| **Timing waveforms** | `.. wavedrom::` blocks in source comments, rendered with [WaveDrom](https://wavedrom.com) |
| **Per-process pages** | One page per labeled `process` / `always_ff` / `always_comb` block |
| **CDC analysis** | Clock domains, signal crossings, synchronizer detection, and async FIFO detection — one page per module with a Graphviz diagram |
| **Design hierarchy** | Driven by `filelist.f` — instantiation tree auto-detected, top-level auto-found |
| **Shared components** | Documented once, linked from every parent |
| **VHDL + SystemVerilog** | Mixed-language designs work out of the box |
| **Register map** | Auto-embeds `registers/generated/*.html` — any register builder output supported |
| **Synthesis reports** | Ingests Vivado and Yosys/nextpnr reports from CI — utilization per module (with hierarchy indent) and top-level timing/fmax |
| **Dark / light mode** | Built-in Furo toggle — persists across sessions, respects OS preference |
| **Ctrl+K search** | Keyboard shortcut focuses the sidebar search input |
| **PDF output** | Full LaTeX PDF via `make doc-pdf` |

---

## 📸 What you get

```
docs/
├── index.rst                       ← project root (Design + Implementation toctrees)
├── overview.rst                    ← module summary table
├── hierarchy.rst                   ← instantiation tree diagram + module list
├── synthesis/
│   └── index.rst                   ← Implementation page: timing + utilization tables
└── modules/
    └── top/
        ├── index.rst               ← module toctree + submodules
        ├── entity.rst              ← ports, generics, annotated source
        ├── block.rst               ← TerosHDL-style block diagram + port/generics tables
        ├── fsm.rst                 ← state diagram + transition table
        ├── timing.rst              ← all wavedrom diagrams for this module
        ├── cdc.rst                 ← clock domain crossing analysis + diagram
        ├── registers.rst           ← embedded register map (if present)
        ├── synthesis.rst           ← per-module utilization (if reports present)
        ├── processes/
        │   ├── index.rst           ← process summary table
        │   ├── p_state_reg.rst     ← per-process: description, waveform, source
        │   └── p_next_state.rst
        └── submodules/
            ├── → traffic_light/
            ├── → blinky/
            └── → pwm_controller/
```

---

## 📦 Dependencies

### Required

| Tool | Purpose | Install |
|---|---|---|
| **Python 3.11+** | Pipeline scripts and Sphinx | [python.org](https://python.org) or `brew install python` |
| **Graphviz** | Renders FSM, hierarchy, CDC, and block diagrams | `brew install graphviz` / `apt install graphviz` |
| Python packages | Sphinx, wavedrom, etc. | `make doc-install` (reads `requirements.txt`) |

### Optional — PDF output

| Tool | Purpose | Install |
|---|---|---|
| **TeX Live** / **MacTeX** | LaTeX PDF via `make doc-pdf` | [tug.org/texlive](https://tug.org/texlive/) or `brew install --cask mactex` |

### Optional — RTL schematics (on by default; `SCHEMATICS=0` to skip)

Gate-level netlists rendered inside each module's block diagram page. Enabled by default; if yosys is not installed they are skipped silently. Disable with `make doc-html SCHEMATICS=0`.

All modules require **netlistsvg** to render the schematic SVG:

```bash
npm install -g netlistsvg
```

**SystemVerilog modules** additionally need `yosys`:

```bash
# macOS
brew install yosys

# Debian/Ubuntu
apt install yosys
```

**VHDL modules** additionally need `ghdl` and the `ghdl-yosys-plugin`. The plugin is not available as a standalone package — the easiest way to get all three pre-built is the **OSS CAD Suite**:

1. Download the latest release for your platform from [github.com/YosysHQ/oss-cad-suite-build/releases](https://github.com/YosysHQ/oss-cad-suite-build/releases)
2. Extract and activate the environment:

```bash
tar -xf oss-cad-suite-<date>-<arch>.tgz
source oss-cad-suite/environment   # add to your shell profile to make permanent
```

This puts `yosys`, `ghdl`, and the plugin all on your PATH together.

Verify the GHDL plugin is wired up:
```bash
yosys -m ghdl -p "help" 2>&1 | head -3
```

If yosys or the GHDL plugin is absent, schematic generation is **skipped silently** — the rest of the build continues normally and the block diagram page simply omits the schematic section.

---

## 🚀 Getting started

### Install into your HDL project

The tool is **not copied into your project**. It lives in `third_party/hdl_autodoc/` (a git submodule) and your project's Makefile includes one file from it, so every documentation target has a single source. From a checkout of this repo:

```bash
git clone https://github.com/FPGA-James/files.git hdl-autodoc
./hdl-autodoc/install.sh /path/to/your/hdl-project            # git submodule
./hdl-autodoc/install.sh /path/to/your/hdl-project --vendor   # or copy src/ in (no git needed)
```

This places the tool at `third_party/hdl_autodoc` and appends one line to your `Makefile` (creating it if there is none):

```make
include third_party/hdl_autodoc/src/autodoc.mk
```

Re-running is safe. To update the tool, update the submodule (`git submodule update --remote third_party/hdl_autodoc`) — your Makefile, `conf.py` and generated files are never touched. Everything else (Sphinx config, theme, templates, scripts) is read from the submodule.

All targets are prefixed `doc-` so they cannot collide with your own targets. Run `make doc-help` for the list.

### Bootstrap your environment

```bash
cd /path/to/your/hdl-project
make doc-venv
```

This creates a `.venv/` virtualenv and installs all Python dependencies into it. Subsequent `make doc-*` commands automatically use `.venv/bin/python3`, keeping the project isolated from your system Python and any other tools (e.g. OSS CAD Suite) on your PATH.

> If you prefer to manage your own environment, `make doc-install` installs into whatever Python is currently active instead.

### Point it at your design

Create or edit `filelist.f` — list your source files, leaves first:

```
# filelist.f
src/alu.vhd
src/register_file.vhd
src/cpu_core.sv
src/top.vhd          ← top-level auto-detected
```

### Build

```bash
make doc-html   # → docs/hdl_autodoc/_build/html/index.html
make doc-pdf    # → docs/hdl_autodoc/_build/latex/<project>.pdf
```

Optionally set a project name:

```bash
make doc-html PROJECT="My FPGA Design"
```

### Try the example

A fully working example design (traffic light controller + PWM controller) lives in `example/`. It is a self-contained project with HDL sources, register definitions, and dummy synthesis reports:

```bash
cd example
make doc-venv && make doc-html
```

Then open `example/docs/hdl_autodoc/_build/html/index.html`.

---

## 🔧 How it works

The build runs in steps, all driven by a single `make doc-html`:

```
filelist.f
    │
    ▼
parse_hierarchy.py     Reads the filelist, extracts module names,
    │                  parses instantiations, detects the top-level,
    │                  writes docs/hdl_autodoc/hierarchy.json
    ▼
generate_rst.py        Scaffolds docs/modules/<n>/ for each module.
    │                  Always-regenerated: index, block, fsm, timing, cdc pages.
    │                  Write-if-missing: entity pages (safe to hand-edit).
    ▼
run_extract.py         Calls extract_fsm.py, extract_processes.py,
    │                  extract_cdc.py, and extract_block.py for every
    │                  module in hierarchy.json.
    ▼
include_registers.py   Checks registers/generated/*.html. Copies it
    │                  to _static/ and embeds via iframe if found.
    │                  Writes a placeholder page if not.
    ▼
generate_rst.py        Second pass: timing pages now aggregate all
    │                  wavedrom blocks from the extracted process files.
    │                  Detects synthesis.rst files and adds Implementation
    │                  toctree section if present.
    ▼
sphinx-build           Renders HTML (or PDF via latexpdf).
```

Synthesis reports are ingested separately with `make doc-reports` (see below) and picked up by the next `make doc-html`.

---

## 📝 Annotating your source

Everything lives in the source comments — no separate files ever needed.

### Entity / module documentation

```vhdl
-- Traffic light FSM controller.
-- Sequences RED → RED_AMBER → GREEN → AMBER with configurable timing.
entity traffic_light is
    port (
        clk       : in  std_logic;  -- System clock.
        rst       : in  std_logic;  -- Synchronous active-high reset.
        timer_exp : in  std_logic;  -- Timer expiry pulse.
        red_out   : out std_logic;  -- Red lamp drive.
        green_out : out std_logic   -- Green lamp drive.
    );
end entity traffic_light;
```

### Process documentation with waveforms

Wavedrom diagrams live right above the process they describe:

```vhdl
-- p_next_state: Combinational next-state logic.
--
-- Advances the FSM on each timer expiry pulse.
--
-- .. wavedrom::
--
--    { "signal": [
--      { "name": "clk",       "wave": "P........." },
--      { "name": "timer_exp", "wave": "0.1.1.1.1." },
--      { "name": "state",     "wave": "=.=.=.=.=.",
--        "data": ["RED","RED_AMB","GREEN","AMBER","RED"] }
--    ]}
p_next_state : process(state, timer_exp) is
begin
    ...
end process p_next_state;
```

Same convention for SystemVerilog using `//` comments:

```systemverilog
// p_pwm: PWM output logic.
//
// // wavedrom::
//
//    { "signal": [
//      { "name": "clk", "wave": "P......." }
//    ]}
always_comb begin : p_pwm
    ...
end
```

---

## 🔀 CDC analysis

Each module gets a `cdc.rst` page generated automatically. The extractor:

1. **Identifies clock domains** from `rising_edge(clk)` / `always_ff @(posedge clk)` patterns in labeled processes.
2. **Finds crossing signals** — any signal driven in one clock domain and read in another.
3. **Detects two-flop synchronizers** — marks a crossing as *synchronized* if the signal feeds a two-register chain in the destination domain.
4. **Detects async FIFOs and dual-clock instances** — any instantiation where two or more clock-named ports (`*clk*`, `*clock*`, `*ck*`) connect to different signals.

The page includes a **Graphviz diagram** of the clock domains with color-coded edges:

- **Green solid** — crossing is synchronized (two-flop chain detected)
- **Red dashed** — crossing has no detected synchronizer (warning raised)

Modules with a single clock domain show a "No CDC" note. Purely combinational modules are also noted.

### Known limitations

- Static analysis only — cannot verify CDC in black-box instances or generated code.
- Clock identity is name-based: two ports carrying the same physical clock under different names will be reported as a crossing.
- Only the classic two-flop back-to-back chain is detected as synchronized. Handshake, gray-code, and FIFO-based CDC are not automatically marked as synchronized.
- Reset domain crossings are not covered.

---

## 📊 Synthesis reports

HDL AutoDoc can ingest post-synthesis and post-route reports from CI and publish them as an **Implementation** section in the sidebar.

### Supported tools

| Toolchain | Utilization file | Timing file |
|---|---|---|
| **Vivado** (Xilinx) | `utilization_placed.rpt` (falls back to `utilization_synth.rpt`) | `timing_summary_routed.rpt` |
| **Yosys + nextpnr** (Lattice ECP5, iCE40) | `stat.txt` | `nextpnr.log` |

### Setup

Drop report files from CI into a `reports/` directory at the project root:

```
reports/
├── vivado/
│   ├── utilization_placed.rpt
│   └── timing_summary_routed.rpt
└── yosys/
    ├── stat.txt
    └── nextpnr.log
```

Then run:

```bash
make doc-reports   # ingest reports → writes synthesis RST files
make doc-html      # build docs (picks up the new RST)
```

### What you get

**Top-level Implementation page** (`synthesis/index.rst`):

- *Timing table* — clock name, target frequency, achieved fmax, constraint period, WNS (Vivado) or PASS/FAIL status (nextpnr)
- *Utilization table* — LUTs, FFs, BRAMs, DSPs per module with hierarchy indentation and available resource counts (Vivado)

**Per-module synthesis page** — LUT/FF/BRAM/DSP counts for that instance.

If no report files are present, a placeholder page is still shown so the Implementation section is always visible in the sidebar.

---

## 🗺 Register map integration

Place your register map HTML export under `registers/generated/`:

```
registers/
└── generated/
    ├── index.html              ← entry point (required)
    ├── index2.html
    ├── index_registers.html
    ├── style.css
    └── Registers/
        ├── reg_ctrl.html
        └── reg_status.html
```

Run `make doc-html`. The entire directory is copied to `docs/_static/registers/` and embedded as a full-screen iframe, preserving all internal links and CSS. If no export is found a clear placeholder page is shown instead with instructions.

Override the entry point filename if your tool produces a different name:

```bash
make doc-html AUTODOC_REG_ENTRY=regmap.html
```

---

## 🎨 Theme

HDL AutoDoc uses the [Furo](https://pradyunsg.me/furo/) Sphinx theme:

- **Dark / light toggle** — top-right button, `localStorage` persistence, respects OS `prefers-color-scheme` on first visit
- **Ctrl+K / Cmd+K** — focuses the sidebar search input
- **Responsive layout** — sidebar collapses on mobile; content column fills available width

### Customising the theme

The theme lives in the tool (`src/docs/hdl_autodoc/_static/custom.css` and `conf.py`) and is shared by every project, including a sticky sidebar scroll position and page breadcrumbs. Furo exposes CSS variable hooks for colour theming via `html_theme_options` in `conf.py`:

```python
html_theme_options = {
    "light_css_variables": { "--color-brand-primary": "#1e66f5" },
    "dark_css_variables":  { "--color-brand-primary": "#89b4fa" },
}
```

---

## 🛠 Make targets

| Target | Description |
|---|---|
| `make doc-help` | List all targets |
| `make doc-venv` | Create `.venv` and install Python dependencies |
| `make doc-install` | Install Python dependencies into the active environment |
| `make doc-hierarchy` | Parse `filelist.f` → `hierarchy.json` |
| `make doc-scaffold` | Generate RST shells (runs hierarchy first) |
| `make doc-extract` | Extract FSM + process + CDC + block docs (runs scaffold first) |
| `make doc-reports` | Ingest synthesis/PnR reports from `reports/` → writes synthesis RST files |
| `make doc-regs` | Generate register artifacts from `registers/regs_*.toml` |
| `make doc-html` | Full build → `docs/hdl_autodoc/_build/html/` |
| `make doc-html SCHEMATICS=0` | Full build without RTL schematics (they are on by default and need yosys) |
| `make doc-pdf` | Full build → LaTeX PDF |
| `make doc-all` | Run `doc-regs` + `doc-html` + `doc-pdf` |
| `make doc-clean` | Remove Sphinx build output only |
| `make doc-clean-generated` | Remove all auto-generated RST + static files |
| `make doc-clean-all` | ⚠️ Nuclear reset — removes everything including hand-editable shells |

---

## 📦 Python packages

Installed automatically by `make doc-install`:

| Package | Purpose |
|---|---|
| [Sphinx](https://www.sphinx-doc.org) | Documentation engine |
| [furo](https://pradyunsg.me/furo/) | Modern Sphinx theme with dark/light toggle and Ctrl+K search |
| [sphinx-vhdl](https://pypi.org/project/sphinx-vhdl/) | VHDL entity autodoc domain |
| [sphinxcontrib-wavedrom](https://sphinxcontrib-wavedrom.readthedocs.io) | `.. wavedrom::` directive |
| [Graphviz](https://graphviz.org) | FSM, hierarchy, CDC, and block diagram renderer |
| [docutils](https://docutils.sourceforge.io) | RST parser (pinned `>=0.18,<0.21` for sphinx-vhdl compat) |
| [hdl-registers](https://hdl-registers.com) | Register map generation from TOML/YAML |

---

## 📁 Repository layout

This repository is the **tool** — it lives in `src/`, is consumed by projects through `third_party/hdl_autodoc` (see `install.sh`), and a working demo lives in `example/`.

### Template (`src/`)

```
src/
├── autodoc.mk                  ← all make targets; included from your project Makefile
├── requirements.txt
├── scripts/
│   ├── hdl_autodoc/            ← drop-in pipeline, reusable across projects
│   │   ├── __init__.py
│   │   ├── parse_hierarchy.py   ← reads filelist.f → hierarchy.json
│   │   ├── generate_rst.py      ← scaffolds RST structure
│   │   ├── extract_fsm.py       ← extracts FSM case blocks → dot + rst
│   │   ├── extract_processes.py ← extracts labeled processes → rst pages
│   │   ├── extract_cdc.py       ← extracts CDC analysis → dot + rst
│   │   ├── extract_block.py     ← extracts block diagram + port/generics tables → dot + rst
│   │   ├── extract_reports.py   ← ingests synthesis reports → synthesis rst pages
│   │   ├── parse_utilization.py ← Vivado + Yosys utilization parser
│   │   ├── parse_timing.py      ← Vivado timing summary + nextpnr log parser
│   │   ├── generate_schematic.py← generates RTL schematic via yosys (optional, on by default)
│   │   ├── run_extract.py       ← orchestrates extraction for all modules
│   │   └── include_registers.py ← copies register map + writes rst page
│   └── registers/
│       └── generate.py         ← generates VHDL, C header, and HTML from register TOML
└── docs/
    └── hdl_autodoc/
        ├── conf.py             ← Sphinx config (read in place via `sphinx -c`; metadata comes from make variables)
        ├── _static/
        │   ├── custom.css      ← layout overrides
        │   ├── search-hotkey.js← Ctrl+K sidebar search shortcut
        │   └── logo.svg        ← replace with your own logo
        └── _templates/
            └── page.html       ← footer attribution override
```

### In your project (after `./install.sh`)

```
your-project/
├── Makefile                    ← your own; one line: include third_party/hdl_autodoc/src/autodoc.mk
├── filelist.f                  ← your source file list
├── src/                        ← your HDL source files
├── third_party/hdl_autodoc/    ← this repository (git submodule, or --vendor copy)
├── registers/                  ← optional: register definitions
│   ├── config.yml
│   ├── regs_<name>.toml
│   └── generated/
├── reports/                    ← optional: CI synthesis report drop zone
│   ├── vivado/
│   └── yosys/
└── docs/
    └── hdl_autodoc/            ← generated RST + build output only
        └── _build/html/        ← build output (gitignored)
```

Nothing from the tool is copied into the project tree, so there are no stale copies to drift.

---

## ✏️ What to hand-edit vs what to leave alone

| File | Status | Notes |
|---|---|---|
| `filelist.f` | ✍️ Edit freely | Your source manifest |
| `src/*.vhd`, `src/*.sv` | ✍️ Edit freely | Your HDL — single source of truth |
| `Makefile` | ✍️ Edit freely | Set `PROJECT`, `AUTODOC_AUTHOR`, `AUTODOC_RELEASE` before the `include` |
| `third_party/hdl_autodoc/` | 🔒 Tool | Update via the submodule; do not edit in place |
| `docs/hdl_autodoc/modules/<n>/entity.rst` | ✍️ Safe to edit | Written once, never overwritten |
| `docs/hdl_autodoc/modules/<n>/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/fsm.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/timing.rst` | 🔄 Auto-generated | Aggregated from process wavedrom blocks |
| `docs/hdl_autodoc/modules/<n>/block.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/cdc.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/processes/` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/registers.rst` | 🔄 Auto-generated | Written by `include_registers.py` |
| `docs/hdl_autodoc/_static/registers/` | 🔄 Auto-generated | Copied from `registers/generated/` |
| `docs/hdl_autodoc/hierarchy.json` | 🔄 Auto-generated | Do not edit |
| `docs/hdl_autodoc/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/overview.rst` | 🔄 Auto-generated | Regenerated every build |

---

## 🧩 Adding a new module

1. Add your source file (e.g. `src/my_module.vhd`)
2. Add it to `filelist.f` (dependency-first order)
3. Run `make doc-html`

Done. The new module appears in the hierarchy, navigation, overview table, hierarchy diagram, and gets its own block diagram and CDC analysis page automatically.

---

## 🐛 Known limitations

### FSM extraction

- Requires a labeled `case` block that assigns `next_state`. Complex FSMs split across multiple processes may not be fully captured.
- Only the first matching `case` block per module is extracted — multi-process FSMs are partially captured at best.

### CDC analysis

- Static analysis only — cannot verify CDC in black-box instances or generated code.
- Clock identity is name-based: two ports carrying the same physical clock under different names will be reported as a crossing.
- Only the classic two-flop back-to-back chain is detected as synchronized. Handshake, gray-code, and FIFO-based CDC are not automatically marked as synchronized.
- Reset domain crossings are not covered by the CDC page (see the reset domain page instead).

### Block diagrams

- VHDL `component`-style instantiation (without `entity work.` prefix) is matched by name — ambiguous names in large designs may need verification.
- SV named parameter overrides (`#(.PARAM(val))` style) are not extracted; use positional style or inline comments.
- Generics with no default value show a blank default in the table.

### RTL schematics (on by default)

- **Mixed-language top levels** — if a VHDL module instantiates SystemVerilog submodules, ghdl cannot elaborate it. The schematic for that module is skipped cleanly; leaf-level schematics are unaffected.
- **Unconnected ports** — ghdl is stricter than synthesis tools and will fail if any port is left unconnected in the design under test. The schematic is skipped for that module.
- **Non-synthesisable constructs** — `wait` statements, file I/O, or other simulation-only VHDL will cause yosys/ghdl to fail. Affected modules are skipped.
- **Tool availability** — requires yosys and netlistsvg (all modules) plus ghdl + ghdl-yosys-plugin for VHDL. Missing tools produce a warning and the build continues without schematics.

### Entity documentation

- `vhdl:autoentity` only works for VHDL. SystemVerilog modules get the `//` comment block above `module` as their description, followed by a `literalinclude` source listing. `/* ... */` header comments are not picked up.

### Output formats

- **Wavedrom in PDF** — may not render identically to HTML output depending on the wavedrom CLI version.
- **Register map in PDF** — the iframe embed is HTML-only. The PDF build skips the register page content.

---

## 📋 Release notes

### v3.6.1

#### Fixes

- **SystemVerilog descriptions on existing projects** — an unedited `entity.rst` from an older version is now upgraded automatically so the module description appears; hand-edited pages are left untouched.

### v3.6.0

#### Breaking changes

- **Single-source Makefile** — `src/Makefile` is now `src/autodoc.mk`, included from your own Makefile instead of copied. All targets are prefixed `doc-` (`doc-html`, `doc-pdf`, `doc-regs`, `doc-clean`, …) so they cannot clash with host targets; `make doc` is now `make doc-all`. Run `make doc-help` for the list.
- **`install.sh` rewritten** — adds the tool as a git submodule at `third_party/hdl_autodoc` (or copies `src/` with `--vendor`) and appends the `include` line to your Makefile. Scripts and Sphinx config are no longer copied into the project. Existing projects: delete their copied `scripts/` and `docs/hdl_autodoc/{conf.py,_static,_templates}`, then re-run the installer.
- Project metadata (`PROJECT`, `AUTODOC_AUTHOR`, `AUTODOC_RELEASE`) now comes from make variables instead of editing `conf.py`.
- `SCHEMATICS` now defaults to `0`, as documented.

#### New features

- **SystemVerilog module descriptions** — the `//` comment block directly above `module <name>` is rendered as the description on the entity page, matching what `vhdl:autoentity` does for VHDL. Unedited `entity.rst` shells from older versions are upgraded automatically.
- **Breadcrumbs** on every page, and the **sidebar keeps its scroll position** between pages.

#### Improvements

- `Sphinx` reads `conf.py`, static files and templates from the tool via `-c`; the project's own `docs/hdl_autodoc/_static` is added for generated register pages.
- Remaining bare `python` calls use `$(PYTHON)`, so the `.venv` is honoured everywhere.
- `scripts/registers/generate.py` resolves `registers/` from the working directory, so it works from a shared checkout.
- `example/` is now just a Makefile include plus sources, replacing its stale copy of the tool.

### v3.5.0

#### Breaking changes

- **Template repo restructure** — the pipeline scripts and Sphinx config have moved to `src/`. Use `./install.sh <target>` to drop the tool into your HDL project. An `example/` directory provides a fully working demo (traffic light + PWM controller).

### v3.4.0

#### New features

- **Synthesis reports** — `make reports` ingests Vivado (`utilization_placed.rpt`, `timing_summary_routed.rpt`) and Yosys/nextpnr (`stat.txt`, `nextpnr.log`) report files from a `reports/` directory. Writes an **Implementation** toctree section with a top-level timing + utilization page and a per-module synthesis page. Utilization tables show hierarchy indentation (`└─ submodule`) and available resource counts. Timing tables show target frequency alongside achieved fmax. A placeholder page is always present so the Implementation sidebar section never disappears.
- **Furo theme** — migrated from `sphinx-rtd-theme` to [Furo](https://pradyunsg.me/furo/) for a modern two-column layout with a built-in dark/light toggle and responsive sidebar. `Ctrl+K` / `Cmd+K` focuses the sidebar search input.

### v3.3.0

#### New features

- **RTL schematics** — new `generate_schematic.py` script synthesises each module with `yosys` (JSON netlist) and renders a clean gate-level schematic SVG with `netlistsvg`. The schematic is embedded as an *RTL Schematic* section at the bottom of each module's block diagram page. Enabled with `make html SCHEMATICS=1`; off by default. VHDL modules require `ghdl` + `ghdl-yosys-plugin` via the OSS CAD Suite; SystemVerilog modules only need `yosys` + `netlistsvg`.
- **`make venv` target** — creates a `.venv/` virtualenv and installs all Python dependencies into it in one step. The Makefile auto-detects `.venv/bin/python3` and uses it for all subsequent targets, keeping the project isolated from system Python and other tools (e.g. OSS CAD Suite) on `PATH`.

#### Improvements

- Sphinx is now invoked via `$(PYTHON) -m sphinx` rather than the `sphinx-build` binary, preventing PATH shadowing issues when tools like OSS CAD Suite install their own broken `sphinx-build` wrapper.
- Mixed-language top-level modules (VHDL instantiating SystemVerilog submodules) are detected before synthesis and skipped with a single clear warning rather than dumping a full ghdl error trace.
- All source files from `hierarchy.json` are passed to ghdl when synthesising any VHDL module, allowing cross-unit references to resolve correctly.
- Expanded dependency documentation in README: required, optional PDF, and optional schematic tool groups with per-platform install commands and OSS CAD Suite setup instructions.

### v3.2.0

#### New features

- **Block diagrams** — `extract_block.py` generates a `block.rst` page per module. The diagram uses a TerosHDL-inspired style: a green box for generics/parameters (with default values) stacked above a yellow box for ports (inputs left with `►`, outputs right with `◄`, bus widths annotated). Both VHDL `generic` and SV `parameter`/`localparam` declarations are extracted.
- **Port and generics/parameters tables** — the block page includes a full port table (name, direction, type, description) and a generics/parameters table (name, type, default, description). Comments from preceding lines and same-line inline comments are both captured.

### v3.1.0

#### New features

- **Test suite** — pytest suite covering all pipeline scripts under `scripts/hdl_autodoc/tests/`. 119 tests across 6 test files.
- **VS Code test runner config** — `pytest.ini`, `.python-version`, and `.vscode/settings.json` added so the VS Code Python extension discovers tests correctly.

### v3.0.0

#### New features

- **CDC analysis** — `extract_cdc.py` generates a `cdc.rst` page per module with a Graphviz diagram. Detects clock domains, signal crossings (synchronized vs unsynchronized), two-flop synchronizer chains, and dual-clock instances (async FIFOs etc.).
- **Register generation** — `scripts/registers/generate.py` generates VHDL packages, AXI-Lite wrappers, C headers, and HTML documentation from TOML/YAML register definitions using [hdl-registers](https://hdl-registers.com). `make regs` runs generation; `make doc` runs registers + full doc build.

#### Improvements

- Makefile variables prefixed: `AUTODOC_` for Sphinx pipeline variables, `REGS_` for register generation variables.
- `make doc` target added: runs `regs` + `html` + `pdf` in sequence.
- `scripts/` reorganised: `hdl_autodoc/` and `registers/` as separate subdirectories.

### v2.0.0

#### New features

- **Register map integration** — `include_registers.py` auto-detects `registers/generated/*.html` and embeds it as a full-screen iframe page nested under the top module. If no file is found a placeholder page with instructions is shown instead. The register page is listed above Submodules in the top module's navigation.
- **Dark mode** — floating toggle pill fixed to the bottom-right of every page. Saves preference to `localStorage`. Respects OS `prefers-color-scheme` on first visit.
- **Catppuccin theming** — light mode uses [Catppuccin Latte](https://catppuccin.com), dark mode uses [Catppuccin Mocha](https://catppuccin.com), both following the official style guide semantic mappings.
- **Fluid layout** — content area scales to viewport using `clamp()` rather than a fixed pixel cap. Removes the RTD theme's default ~800px content limit.
- **`PROJECT` variable** — set the documentation title from the command line: `make html PROJECT="My FPGA Design"`. Falls back to the parent directory name if not set.
- **`theme.js`** — standalone JS file handles all dark mode logic via DOM injection, independent of Sphinx template block availability.

#### Improvements

- Table styling overhauled — transparent backgrounds, single-rule headers, minimal row dividers. RTD theme's white even-row override is explicitly reset.
- Admonitions use Catppuccin semantic colours: Mauve for notes, Yellow for warnings, Red for errors, Teal for tips.
- Sidebar uses Catppuccin Crust as background in both modes for consistent contrast regardless of light/dark mode.
- Code blocks use Catppuccin Crust as background with an accent-coloured left border.
- `include_registers.py` warns if multiple HTML files are found in `registers/generated/` and states which is used.
- `clean-generated` target now also removes `docs/registers.rst` and `docs/_static/registers.html`.

### v1.0.0

- Initial release
- VHDL and SystemVerilog support
- FSM extraction (Graphviz dot diagrams)
- Per-process pages with WaveDrom waveforms
- Design hierarchy via `filelist.f`
- Shared component support
- Mixed VHDL + SV projects
- HTML and PDF output

---

## 🤝 Contributing

Pull requests welcome. The scripts are intentionally small and single-purpose:

```
scripts/hdl_autodoc/
├── parse_hierarchy.py    filelist.f         → hierarchy.json
├── generate_rst.py       src/ + hierarchy   → docs/modules/**/
├── extract_fsm.py        <file.vhd|sv>      → <module>.dot + <module>.rst
├── extract_processes.py  <file.vhd|sv>      → p_*.rst + index.rst
├── extract_cdc.py        <file.vhd|sv>      → <module>_cdc.dot + <module>_cdc.rst
├── extract_block.py      <file.vhd|sv>      → <module>_block.dot + <module>_block.rst
├── extract_reports.py    reports/           → synthesis/index.rst + modules/*/synthesis.rst
├── parse_utilization.py  util report        → list[ModuleUtilization]
├── parse_timing.py       timing report      → list[ClockTiming]
├── generate_schematic.py <file.vhd|sv>      → <module>_schematic.svg  (optional, on by default)
├── run_extract.py        hierarchy.json     → orchestrates above
└── include_registers.py  registers/         → docs/registers.rst + _static/
```

---

## 📄 License

MIT — do whatever you like, just don't blame us if your FSM has too many states.

---

<p align="center">
  Built with
  <a href="https://www.sphinx-doc.org">Sphinx</a> ·
  <a href="https://wavedrom.com">WaveDrom</a> ·
  <a href="https://graphviz.org">Graphviz</a> ·
  <a href="https://catppuccin.com">Catppuccin</a> ·
  ☕ and too much time staring at VHDL
</p>

---

<p align="center">
  🤖 Created by <a href="https://claude.ai">Claude</a> — Anthropic's AI assistant
</p>
