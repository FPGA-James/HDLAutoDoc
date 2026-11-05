# 📟 HDL AutoDoc

[![CI](https://github.com/FPGA-James/HDLAutoDoc/actions/workflows/ci.yml/badge.svg)](https://github.com/FPGA-James/HDLAutoDoc/actions/workflows/ci.yml)

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
| **Mermaid diagrams** | `.. mermaid::` blocks in module headers and process comments — sequence, state, flow and other diagrams — rendered in the browser, and in the PDF if `mermaid-cli` is installed |
| **Per-process pages** | One page per labeled `process` / `always_ff` / `always_comb` block |
| **CDC analysis** | Clock domains, signal crossings, synchronizer detection, and async FIFO detection — one page per module with a Graphviz diagram |
| **Design hierarchy** | Driven by `filelist.f` — instantiation tree auto-detected, top-level auto-found |
| **Shared components** | Documented once, linked from every parent |
| **VHDL + SystemVerilog** | Mixed-language designs work out of the box |
| **Register map** | Auto-embeds `registers/generated/*.html` — any register builder output supported |
| **Testbenches** | Lists VUnit, cocotb, pyuvm and directed testbenches with their purpose and test counts, read from source — on by default (`TESTBENCHES=0` to skip) |
| **Build reports** | Ingests Yosys/nextpnr (ECP5) and Vivado reports — summary, utilization, timing and warnings — on by default (`BUILD=0` to skip) |
| **VS Code preview** | A live per-file preview in the editor from the same extractors — ports, FSM, processes with WaveDrom and Mermaid, CDC and reset — installed from a `.vsix` (see [VS Code extension](#vs-code-extension)) |
| **Dark / light mode** | Built-in Furo toggle — persists across sessions, respects OS preference |
| **Ctrl+K search** | Keyboard shortcut focuses the sidebar search input |
| **PDF output** | Full LaTeX PDF via `make doc-pdf` |

---

## 📸 What you get

```
docs/
├── index.rst                       ← project root (Design, Verification and Build toctrees)
├── overview.rst                    ← instantiation tree, shared components, module table
├── synthesis/
│   └── index.rst                   ← Build page: summary, utilization, timing, warnings
├── testbenches/
│   └── index.rst                   ← Testbenches page: frameworks, tests, linked modules
└── modules/
    └── top/
        ├── index.rst               ← module toctree + submodules
        ├── entity.rst              ← ports, generics, annotated source
        ├── block.rst               ← TerosHDL-style block diagram + port/generics tables
        ├── fsm.rst                 ← state diagram + transition table
        ├── timing.rst              ← all wavedrom diagrams for this module
        ├── cdc.rst                 ← clock domain crossing analysis + diagram
        ├── registers.rst           ← embedded register map (if present)
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

**Live:** the example project, built from `main`, is at [fpga-james.github.io/HDLAutoDoc](https://fpga-james.github.io/HDLAutoDoc/) (without the RTL schematics, which need Yosys). Its built HTML is also in the repository, so after cloning you can open `example_full/docs/hdl_autodoc/_build/html/index.html` without building anything.

The example, `example_full/`, shows **every feature at once** — a mixed VHDL / SystemVerilog sampler for ECP5 (`make doc-venv && make doc-html` from that directory; the PDF shows its Mermaid diagrams when `mmdc` is installed):

- a three-level hierarchy with a shared module (`stream_filter` has two parents), VHDL parents of SystemVerilog children and the reverse;
- a VHDL FSM (`sample_ctrl`) and a SystemVerilog FSM (`stream_filter`) with generated diagrams, processes with WaveDrom waveforms, and a process-level Mermaid state diagram;
- Mermaid flow, sequence and state diagrams written in module headers and process comments;
- clock-domain analysis (two domains, a two-flop synchroniser, an asynchronous FIFO) and reset analysis (synchronous and asynchronous resets, several reset domains);
- generics and parameters, a package, two interfaces, interface ports and an internal interface instance, flat AXI4-Lite / AXI4-Stream / APB port groups and a custom group in `bus_groups.toml`;
- a register map (`registers/regs_axil_regs.toml`), RTL schematics, testbenches in all three frameworks (one skipped test), and real Yosys/nextpnr reports plus sample Vivado reports.

### VS Code extension

`vscode/` holds an extension that shows the documentation of the file you are editing, live, in a panel beside it: header, generics, ports, instances, the state machine, processes with their WaveDrom and Mermaid diagrams, and clock- and reset-domain analysis. It reads the source with the same extractors as the site build (through the new `autodoc_json.py`, which prints one JSON document per file), works on unsaved text, follows the editor theme, and exports the documentation as HTML, Markdown or PDF (the PDF needs Chrome, Edge, Brave or Chromium installed).

```bash
make -C vscode vsix                                      # builds vscode/hdl-autodoc-<version>.vsix
code --install-extension vscode/hdl-autodoc-*.vsix       # then: "HDL AutoDoc: Show documentation"
```

It needs Python 3.11+ on the `PATH` (nothing to `pip install`: the `.vsix` carries its own copy of the scripts) and is not published to the Marketplace; CI builds the `.vsix` on every push and keeps it as a build artifact. See [`vscode/README.md`](vscode/README.md) for settings and limits.

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
    │                  extract_cdc.py, extract_block.py and
    │                  extract_registers.py for every module in
    │                  hierarchy.json.
    ▼
extract_testbenches.py Lists the testbenches under tb/ (TESTBENCHES=1).
    ▼
extract_reports.py     Reads Yosys/nextpnr/Vivado reports under reports/
    │                  (BUILD=1; skipped if there are none).
    ▼
generate_rst.py        Second pass: timing pages now aggregate all
    │                  wavedrom blocks from the extracted process files.
    │                  Adds the Verification and Build toctree sections
    │                  for whichever generated pages exist.
    ▼
sphinx-build           Renders HTML (or PDF via latexpdf).
```

The testbench and build-report steps run only when their switch is on (`TESTBENCHES`, `BUILD`) and there is something to show; `make doc-reports` still runs the report step on its own.

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

### Mermaid diagrams

Write a [Mermaid](https://mermaid.js.org) diagram as a `.. mermaid::` block in the comments you already write. It works in a **module header** and in the **comment block above a process** (`always_ff`, `process`, ...). The block is indented under the directive, like a wavedrom block; `:caption:` and the extension's other options go first.

```vhdl
-- Master side of a write handshake.
--
-- .. mermaid::
--    :caption: Write handshake
--
--    sequenceDiagram
--      Master->>Slave: valid
--      Slave-->>Master: ready
entity master is
```

```systemverilog
// p_state: Controller state machine.
//
// .. mermaid::
//    :caption: States
//
//    stateDiagram-v2
//      [*] --> IDLE
//      IDLE --> BUSY: start
always_ff @(posedge clk) begin : p_state
```

- **Where it appears:** a header diagram on the module's *Entity* page; a process diagram under the process's *Description*, in the order you wrote it. The process index gets a *Mermaid* column next to *WaveDrom* when a process in that module has a diagram.
- **Indentation is kept**, since Mermaid depends on it (`subgraph`, nested `state`, `mindmap`). Write `-->` freely inside VHDL comments; only the leading `--` is removed. In a VHDL header, write the comment marker as `-- ` (with a space): the VHDL header reader ignores `--.. mermaid::` and a tab after `--`, and the comment above a process loses a tab after `--` too.
- **The overview description** (the one line in the overview table) stops at the first directive, so a diagram never leaks into it.
- **Generated diagrams are unchanged.** The FSM, hierarchy, CDC and block diagrams still use Graphviz; Mermaid is only for diagrams you write.
- **Dark mode** follows the Furo toggle automatically.

**HTML** needs nothing installed: the browser draws the diagram. By default it loads Mermaid from a CDN, so viewing needs internet access. Pages without a diagram do not load Mermaid.

For HTML that works **offline**, serve Mermaid from your own docs. The loader `mermaid.esm.min.mjs` imports its parts from a `chunks/` folder (about 24 MB), so both are needed, kept in this layout under the project's `docs/hdl_autodoc/_static/`:

```bash
npm pack mermaid && tar xzf mermaid-*.tgz
mkdir -p docs/hdl_autodoc/_static/mermaid/chunks
cp package/dist/mermaid.esm.min.mjs docs/hdl_autodoc/_static/mermaid/
cp -r package/dist/chunks/mermaid.esm.min docs/hdl_autodoc/_static/mermaid/chunks/
make doc-html AUTODOC_MERMAID_JS=mermaid/mermaid.esm.min.mjs
```

`AUTODOC_MERMAID_JS` is a path **relative to `_static/`** (or a full `https://` URL for a copy you host yourself), not a filesystem path.

The local copy is loaded as an ES module, which browsers refuse to load from a `file://` page, so the site must be **served** (for example `python3 -m http.server -d docs/hdl_autodoc/_build/html`) rather than opened from disk. The default CDN setup works when the page is opened from disk (it needs a network connection).

**PDF** needs each diagram rendered to an image, which only [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) can do:

```bash
npm install -g @mermaid-js/mermaid-cli        # provides `mmdc` (it downloads a headless Chromium)
make doc-pdf
# or, to use an existing Chrome instead:
make doc-pdf AUTODOC_MERMAID_PARAMS="-p puppeteer.json"
```

`puppeteer.json` is `{"executablePath": "/path/to/chrome", "args": ["--no-sandbox"]}`. Without `mmdc` the PDF still builds, with no warnings: each diagram is replaced by a one-line note and a single message says how many were left out.

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

## 🧪 Testbenches

HDL AutoDoc lists your testbenches, what each is for, which module it tests, and how many tests it contains — read from the source, without running a simulator. The section appears in the sidebar under **Verification**.

### Layout

One subdirectory per framework under `tb/`:

```
tb/
├── vunit/       VUnit testbenches (VHDL or SystemVerilog)
├── cocotb/      cocotb test modules (Python)
├── pyuvm/       pyuvm test modules (Python, UVM on top of cocotb)
└── directed/    plain HDL testbenches
```

The subdirectory name is the framework (case-insensitive). HDL files directly in `tb/`, or in any other subdirectory, are treated as `directed`. Use `AUTODOC_TB_DIR` for a different location. Testbench files must **not** be listed in `filelist.f`: the hierarchy treats every module nothing instantiates as a top level, so a listed testbench would become a second one.

### What counts as a test

| Framework | A test is | Its purpose comes from |
|---|---|---|
| VUnit (VHDL) | each `run("name")` | the comment directly above it, or on the same line |
| VUnit (SystemVerilog) | each `` `TEST_CASE("name") `` | the comment directly above it, or on the same line |
| cocotb | each `@cocotb.test(...)` function | the first line of its docstring; `skip=True` tests are listed and marked *skipped* |
| pyuvm | each class decorated with `@pyuvm.test(...)` | the first line of its docstring; `skip=True` tests are listed and marked *skipped* |
| directed | each `TEST:` marker (below) | the text after the marker |

A testbench's own purpose is the comment block directly above its `entity` / `module` (or, if there is none, the comment block at the top of the file); for cocotb and pyuvm it is the module docstring.

### Marking tests in directed testbenches

Directed testbenches have no framework to name their tests, so mark each scenario with a comment, in the file's own comment style, before it:

```vhdl
-- TEST: reset_clears_fifo — FIFO is empty after reset
```

```systemverilog
// TEST: wrap_around — pointers wrap at the last address
```

- The name is one word (letters, digits, underscore). After it, `—`, `-` or `:` separates the purpose, which may be left out.
- Only line comments count: a marker inside a string or a `/* ... */` block is ignored.
- A directed file with **no** markers counts as one test, named after the testbench, with the header comment as its purpose.

### Linking to a module

A testbench is shown next to the module it tests. It is linked by name — `tb_fifo`, `test_fifo`, `fifo_tb` and `fifo_test` all link to `fifo` — or, for HDL, by the module it instantiates. A testbench that matches neither is listed without a link.

### Switching it off

`make doc-html TESTBENCHES=0` removes the section. With no `tb/` directory (or no testbenches in it) there is no section and no sidebar entry. See [Make variables](#make-variables). Pages already built stay in `_build/html` until you run `make doc-clean`; the sidebar no longer links to them.

---

## 📊 Build reports

HDL AutoDoc reads the reports your synthesis and place-and-route flow leaves behind and shows them as a **Build** section in the sidebar: a summary of the tools and device, utilization, timing and warnings.

### Supported tools

| Toolchain | Files |
|---|---|
| **Yosys + nextpnr** (Lattice ECP5) | `yosys/stat.txt`, `yosys/nextpnr.log`, optionally `yosys/yosys.log` |
| **Vivado** (Xilinx) | `vivado/utilization_placed.rpt` (falls back to `utilization_synth.rpt`), `vivado/timing_summary_routed.rpt` |

Vivado support covers utilization and timing today; its power, DRC and other reports come later.

### Setup

Put the files in a `reports/` directory at the project root (or point `AUTODOC_REPORTS_DIR` at another one):

```
reports/
├── vivado/
│   ├── utilization_placed.rpt
│   └── timing_summary_routed.rpt
└── yosys/
    ├── stat.txt
    ├── nextpnr.log
    └── yosys.log
```

The reports are picked up by the normal `make doc-html`. With no report files — or none that could be read — there is **no Build section**, and a warning names each file that was binary, not UTF-8, or in an unrecognised format; `make doc-reports` still writes the explicit placeholder page. `make doc-html BUILD=0` removes the section (run `make doc-clean` to also drop the HTML from an earlier build).

### What you get

**Build page** (`synthesis/index.rst`), in this order:

- *Summary* — Yosys and nextpnr versions, device size class, when the reports were produced, and the git revision of the docs. Only what is found is shown (nextpnr prints its version to stdout, so it is absent when you save only a `--log` file).
- *Utilization* — nextpnr's device utilisation (resources in use, with counts and percentages) and a per-module table from Yosys or Vivado with hierarchy indentation.
- *Timing* — one row per clock with target and achieved fmax and PASS/FAIL (nextpnr) or WNS (Vivado). nextpnr prints each clock after placement and again after routing; the routed value is shown.
- *Warnings* — the total, and the most frequent messages (messages that differ only by a quoted name are grouped).

---

## 🗺 Register map integration

Describe a module's registers in `registers/regs_<module>.toml` (the [hdl-registers](https://hdl-registers.com) format, with `registers/config.yml` for the bus width), where `<module>` is a module in your hierarchy:

```
registers/
├── config.yml
└── regs_axil_regs.toml
```

`make doc-html` gives that module a **Registers** page: one table row per register with its address offset, access mode and description, and a field table for each register that has fields. A module with no `regs_<module>.toml` gets no page. Use `AUTODOC_REGISTERS_DIR` if the directory is not called `registers/` (see [Make variables](#make-variables)).

`make doc-regs` also runs hdl-registers to generate VHDL packages, an AXI-Lite wrapper, a C header and HTML register documentation into `registers/generated/`. Those files are for your design and tools; the site does not embed them.

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
| `make doc-check-env` | Check the Sphinx packages are importable (run automatically before `doc-html` / `doc-pdf`; tells you to run `make doc-venv` if not) |
| `make doc-hierarchy` | Parse `filelist.f` → `hierarchy.json` |
| `make doc-scaffold` | Generate RST shells (runs hierarchy first) |
| `make doc-extract` | Extract FSM + process + CDC + block docs (runs scaffold first) |
| `make doc-reports` | Ingest build reports from `reports/` (or `$AUTODOC_REPORTS_DIR`) on their own; writes a placeholder page if there are none |
| `make doc-regs` | Generate register artifacts from `registers/regs_*.toml` (or `$AUTODOC_REGISTERS_DIR`) |
| `make doc-html` | Full build → `docs/hdl_autodoc/_build/html/` |
| `make doc-html ANNOTATED_SOURCE=0` | Omit the "Annotated Source" listing from entity pages (on by default) |
| `make doc-html TESTBENCHES=0` | Omit the Testbenches section (on by default) |
| `make doc-html BUILD=0` | Omit the Build section (on by default) |
| `make doc-html SCHEMATICS=0` | Full build without RTL schematics (they are on by default and need yosys) |
| `make doc-pdf` | Full build → LaTeX PDF |
| `make doc-all` | Run `doc-regs` + `doc-html` + `doc-pdf` |
| `make doc-clean` | Remove Sphinx build output only |
| `make doc-clean-generated` | Remove all auto-generated RST + static files |
| `make doc-clean-all` | ⚠️ Nuclear reset — removes everything including hand-editable shells |

### Make variables

Set these on the command line (`make doc-html SCHEMATICS=0`) or in your Makefile **before** the `include` line.

| Variable | Default | Effect |
|---|---|---|
| `PROJECT` | parent directory name | Documentation title |
| `AUTODOC_AUTHOR`, `AUTODOC_RELEASE` | `HDL Team`, `1.0.0` | Author and release shown in the docs |
| `SCHEMATICS` | `1` | `0` skips RTL schematics |
| `ANNOTATED_SOURCE` | `1` | `0` omits the "Annotated Source" listing from entity pages |
| `AUTODOC_MERMAID_CMD` | `mmdc` | Command that renders Mermaid diagrams for the PDF; it may carry arguments (`npx -y @mermaid-js/mermaid-cli`), and a space in a path is written `\ ` |
| `AUTODOC_MERMAID_PARAMS` | *(none)* | Extra arguments for it, e.g. `-p puppeteer.json` |
| `AUTODOC_MERMAID_JS` | *(CDN)* | Where to load Mermaid from: a path relative to `docs/hdl_autodoc/_static/` (e.g. `mermaid/mermaid.esm.min.mjs`) or an `https://` URL, for HTML that works offline (serve the site; see above) |
| `TESTBENCHES` | `1` | `0` removes the Testbenches section |
| `AUTODOC_TB_DIR` | `tb` | Root of the testbenches, with one subdirectory per framework (`vunit/`, `cocotb/`, `pyuvm/`, `directed/`) |
| `BUILD` | `1` | `0` removes the Build section |
| `AUTODOC_REPORTS_DIR` | `reports` | Root of the build report files (`yosys/`, `vivado/`). Relative paths are taken from the project root. |
| `AUTODOC_YOSYS_STAT` | *(`<reports>/yosys/stat.txt`)* | Path to the Yosys `stat` output, if it does not follow the layout above. Relative paths are taken from the project root. |
| `AUTODOC_YOSYS_LOG` | *(`<reports>/yosys/yosys.log`)* | Path to the Yosys log |
| `AUTODOC_NEXTPNR_LOG` | *(`<reports>/yosys/nextpnr.log`)* | Path to the nextpnr log |
| `AUTODOC_VIVADO_UTILIZATION` | *(`<reports>/vivado/utilization_placed.rpt`)* | Path to the Vivado utilization report |
| `AUTODOC_VIVADO_TIMING` | *(`<reports>/vivado/timing_summary_routed.rpt`)* | Path to the Vivado timing summary |
| `AUTODOC_REGISTERS_DIR` | `registers` | Directory holding `regs_*.toml`, `config.yml` and the generated `generated/` and `out/` output. Relocate it, e.g. `AUTODOC_REGISTERS_DIR=out/registers`. Relative paths are taken from the project root. |

---

## 📦 Python packages

Installed automatically by `make doc-install`:

| Package | Purpose |
|---|---|
| [Sphinx](https://www.sphinx-doc.org) | Documentation engine |
| [furo](https://pradyunsg.me/furo/) | Modern Sphinx theme with dark/light toggle and Ctrl+K search |
| [sphinx-vhdl](https://pypi.org/project/sphinx-vhdl/) | VHDL entity autodoc domain |
| [sphinxcontrib-wavedrom](https://sphinxcontrib-wavedrom.readthedocs.io) | `.. wavedrom::` directive |
| [sphinxcontrib-mermaid](https://sphinxcontrib-mermaid-demo.readthedocs.io) | `.. mermaid::` directive (the optional [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) renders them for the PDF) |
| [Graphviz](https://graphviz.org) | FSM, hierarchy, CDC, and block diagram renderer |
| [docutils](https://docutils.sourceforge.io) | RST parser (pinned `>=0.18,<0.21` for sphinx-vhdl compat) |
| [hdl-registers](https://hdl-registers.com) | Register map generation from TOML/YAML |

---

## 📁 Repository layout

This repository is the **tool** — it lives in `src/`, is consumed by projects through `third_party/hdl_autodoc` (see `install.sh`), and a working demo lives in `example_full/`.

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
│   │   ├── extract_reports.py   ← ingests build reports → Build page
│   │   ├── extract_testbenches.py ← lists testbenches → Testbenches page
│   │   ├── parse_testbenches.py ← finds testbenches; counts VUnit / cocotb / pyuvm / directed tests
│   │   ├── parse_build_info.py  ← nextpnr utilisation block, tool versions, warning summary
│   │   ├── sv_interfaces.py     ← SystemVerilog interface definitions and interface ports
│   │   ├── rst_escape.py        ← escapes comment text for reStructuredText
│   │   ├── parse_utilization.py ← Vivado + Yosys utilization parser
│   │   ├── parse_timing.py      ← Vivado timing summary + nextpnr log parser
│   │   ├── generate_schematic.py← generates RTL schematic via yosys (optional, on by default)
│   │   ├── run_extract.py       ← orchestrates extraction for all modules
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
├── registers/                  ← optional: register definitions (location set by AUTODOC_REGISTERS_DIR)
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
| `docs/hdl_autodoc/modules/<n>/entity.rst` | ✍️ Safe to edit | Written once, never overwritten (keep its `.. include:: <n>_source.rst` line to honour `ANNOTATED_SOURCE`) |
| `docs/hdl_autodoc/modules/<n>/<n>_source.rst` | 🔄 Auto-generated | The annotated source section; empty when `ANNOTATED_SOURCE=0` |
| `docs/hdl_autodoc/modules/<n>/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/fsm.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/timing.rst` | 🔄 Auto-generated | Aggregated from process wavedrom blocks |
| `docs/hdl_autodoc/modules/<n>/block.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/cdc.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/modules/<n>/processes/` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/registers.rst` | 🔄 Auto-generated | Written by `generate_rst.py` (lists the modules that have a register map) |
| `docs/hdl_autodoc/_static/registers/` | 🔄 Auto-generated | Copied from `registers/generated/` |
| `docs/hdl_autodoc/testbenches/index.rst` | 🔄 Auto-generated | The Testbenches page, from `tb/` |
| `docs/hdl_autodoc/synthesis/index.rst` | 🔄 Auto-generated | The Build page, from `reports/` |
| `docs/hdl_autodoc/hierarchy.json` | 🔄 Auto-generated | Do not edit |
| `docs/hdl_autodoc/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/hdl_autodoc/overview.rst` | 🔄 Auto-generated | Regenerated every build |

---

## 🧩 Adding a new module

1. Add your source file (e.g. `src/my_module.vhd`)
2. Add it to `filelist.f` (dependency-first order)
3. Run `make doc-html`

Done. The new module appears in the overview (tree and table), navigation, and gets its own block diagram and CDC analysis page automatically.

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
- **SystemVerilog interface ports** are listed only when the interface is defined in a support file (a file with no module, listed in `filelist.f`) or in the module's own file, and only in one-port-per-line headers. Parameters in member widths are shown as written, not evaluated.

### RTL schematics (on by default)

- **Mixed-language top levels** — ghdl cannot read SystemVerilog, so a VHDL module that instantiates SystemVerilog submodules is elaborated with a generated port-only VHDL stub standing in for each SV child (outputs tied low). The child is drawn as a black-box instance; its internals are not shown. Headers the stub generator cannot convert (e.g. multi-dimensional packed ports) fall back to skipping that module's schematic.
- **SystemVerilog packages and interfaces** — files that define no module (packages, interfaces) are listed as `support_files` in `hierarchy.json` and read before every SystemVerilog schematic, in filelist order — so list a package before the files that use it. yosys' own frontend limits still apply: no `return` in functions, no `import` inside a module body (use the module header or `pkg::name`), and only basic interfaces with modports. After editing a package or interface run `make doc-extract FORCE=1`, since support files are not part of a module's extraction cache key.
- **Unconnected ports** — ghdl is stricter than synthesis tools and will fail if any port is left unconnected in the design under test. The schematic is skipped for that module.
- **Non-synthesisable constructs** — `wait` statements, file I/O, or other simulation-only VHDL will cause yosys/ghdl to fail. Affected modules are skipped.
- **Tool availability** — requires yosys and netlistsvg (all modules) plus ghdl + ghdl-yosys-plugin for VHDL. Missing tools produce a warning and the build continues without schematics.

### Testbenches

- Tests are counted from source, not from a run: a VUnit `run("...")` whose name is built at run time, or a cocotb test created in a loop, is not seen. Only top-level `@cocotb.test` functions and `@pyuvm.test` classes are found.
- Directed tests need the `TEST:` marker comments (see Testbenches); a directed file without them counts as one test.
- Purposes come from comments and docstrings. No results (pass/fail, coverage) are shown.
- A testbench is linked to a module by name or by the module it instantiates; with several instantiated modules the first alphabetically is used.

### Build reports

- Open-source support is ECP5 (Yosys + nextpnr-ecp5). The device class is inferred from the flip-flop capacity in nextpnr's utilisation block and is shown only for the 25k, 45k and 85k parts.
- nextpnr prints its version to stdout, so it is shown only if the banner is in your saved log. nextpnr and Yosys wording changes between versions; unrecognised lines are skipped, not reported.
- Power, DRC and CDC reports and build-to-build comparison are not yet supported.

### Entity documentation

- `vhdl:autoentity` only works for VHDL. SystemVerilog modules get the `//` comment block above `module` as their description, followed by a `literalinclude` source listing. `/* ... */` header comments are not picked up.

### Output formats

- **Wavedrom in PDF** — may not render identically to HTML output depending on the wavedrom CLI version.

---

## 📋 Release notes

Each release's notes are in [RELEASE.md](RELEASE.md) and on the [releases page](https://github.com/FPGA-James/HDLAutoDoc/releases).

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
├── extract_reports.py    reports/           → synthesis/index.rst
├── parse_utilization.py  util report        → list[ModuleUtilization]
├── parse_timing.py       timing report      → list[ClockTiming]
├── generate_schematic.py <file.vhd|sv>      → <module>_schematic.svg  (optional, on by default)
├── run_extract.py        hierarchy.json     → orchestrates above
└── extract_registers.py  registers/regs_<m>.toml → modules/<m>/registers.rst
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
