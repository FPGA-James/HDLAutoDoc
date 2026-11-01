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
| **Mermaid diagrams** | `.. mermaid::` blocks in module headers and process comments — sequence, state, flow and other diagrams — rendered in the browser, and in the PDF if `mermaid-cli` is installed |
| **Per-process pages** | One page per labeled `process` / `always_ff` / `always_comb` block |
| **CDC analysis** | Clock domains, signal crossings, synchronizer detection, and async FIFO detection — one page per module with a Graphviz diagram |
| **Design hierarchy** | Driven by `filelist.f` — instantiation tree auto-detected, top-level auto-found |
| **Shared components** | Documented once, linked from every parent |
| **VHDL + SystemVerilog** | Mixed-language designs work out of the box |
| **Register map** | Auto-embeds `registers/generated/*.html` — any register builder output supported |
| **Testbenches** | Lists VUnit, cocotb, pyuvm and directed testbenches with their purpose and test counts, read from source — on by default (`TESTBENCHES=0` to skip) |
| **Build reports** | Ingests Yosys/nextpnr (ECP5) and Vivado reports — summary, utilization, timing and warnings — on by default (`BUILD=0` to skip) |
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

A fully working example design (traffic light controller + PWM controller) lives in `example/`. It is a self-contained project with HDL sources, register definitions, and dummy synthesis reports:

```bash
cd example
make doc-venv && make doc-html
```

Then open `example/docs/hdl_autodoc/_build/html/index.html`.

Two more examples live alongside it: `example_sv/` (a SystemVerilog package, interfaces and interface ports) and `example_ecp5/` (an AXI4-Stream filter with an AXI4-Lite register file for Lattice ECP5, with testbenches in all three frameworks and real Yosys/nextpnr reports — it shows the Verification and Build sections).

`example_full/` shows **every feature at once** — a mixed VHDL / SystemVerilog sampler for ECP5 (`make doc-venv && make doc-html` from that directory; the PDF shows its Mermaid diagrams when `mmdc` is installed):

- a three-level hierarchy with a shared module (`stream_filter` has two parents), VHDL parents of SystemVerilog children and the reverse;
- a VHDL FSM (`sample_ctrl`) and a SystemVerilog FSM (`stream_filter`) with generated diagrams, processes with WaveDrom waveforms, and a process-level Mermaid state diagram;
- Mermaid flow, sequence and state diagrams written in module headers and process comments;
- clock-domain analysis (two domains, a two-flop synchroniser, an asynchronous FIFO) and reset analysis (synchronous and asynchronous resets, several reset domains);
- generics and parameters, a package, two interfaces, interface ports and an internal interface instance, flat AXI4-Lite / AXI4-Stream / APB port groups and a custom group in `bus_groups.toml`;
- a register map (`registers/regs_axil_regs.toml`), RTL schematics, testbenches in all three frameworks (one skipped test), and real Yosys/nextpnr reports plus sample Vivado reports.

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

**Per-module synthesis page** — LUT/FF/BRAM/DSP counts for that instance.

---

## 🗺 Register map integration

Place your register map HTML export under `registers/generated/` (or `$AUTODOC_REGISTERS_DIR/generated/` if you have relocated the registers directory — see [Make variables](#make-variables)):

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
| `docs/hdl_autodoc/registers.rst` | 🔄 Auto-generated | Written by `include_registers.py` |
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
- **Register map in PDF** — the iframe embed is HTML-only. The PDF build skips the register page content.

---

## 📋 Release notes

### v3.14.0

#### New features

- **pyuvm testbenches** — the Testbenches section now lists [pyuvm](https://github.com/pyuvm/pyuvm) tests, from a `tb/pyuvm/` subdirectory. Each class decorated with `@pyuvm.test(...)` (or `@test(...)` imported from pyuvm) is a test; its purpose is the first line of the class docstring and `skip=True` tests are listed and marked skipped. The testbench is linked to the module it tests by file name, as for cocotb, and gets its own section and row in the summary table.
- `example_full/` gains a pyuvm environment for `axis_pipeline` (sequence, driver, monitor, scoreboard, two tests and one skipped).

#### Compatibility

- Backwards compatible. A project with no `tb/pyuvm/` directory gets the same Testbenches page as before.

---

### v3.13.0

#### New features

- **Mermaid diagrams** — write a `.. mermaid::` block in a source comment, the way `.. wavedrom::` blocks work. It is supported in a module or entity header (VHDL and SystemVerilog) and in the comment block above a process or `always` block; options such as `:caption:` work, and the diagram keeps its indentation (state diagrams nest). HTML pages render them in the browser (Mermaid is fetched from a CDN, or served locally — see the README; the local copy needs the site to be served over http, not opened from disk); the PDF includes them when `mermaid-cli` (`mmdc`) is installed, and otherwise shows a one-line note where each diagram would be and the build prints a single message. The generated FSM, hierarchy, CDC and block diagrams stay on Graphviz. There is no on/off switch: a project with no Mermaid block is unchanged.
- **Previous / Next links** at the bottom of every page, following the order of the sidebar (they had been lost to the page-footer override).
- **Process index** — when at least one process in a module has a diagram, its process table gains a "Mermaid" column next to "WaveDrom"; modules without a diagram keep the old table.
- New make variables: `AUTODOC_MERMAID_CMD` (default `mmdc`; it may carry arguments, and a space in a path is written `\ `), `AUTODOC_MERMAID_PARAMS` (for example a puppeteer config) and `AUTODOC_MERMAID_JS` (a local Mermaid script for offline pages). New dependency: `sphinxcontrib-mermaid>=2.1`.
- **`example_full/`** — a mixed VHDL / SystemVerilog sampler for ECP5 that shows every feature at once: a three-level hierarchy with a shared module, VHDL and SystemVerilog FSMs, Mermaid flow / sequence / state diagrams, CDC and reset analysis, generics and parameters, a package, interfaces and flat bus groups, a custom `bus_groups.toml` group, a register map, testbenches in all three frameworks, and real Yosys/nextpnr reports. A test (`test_example_full.py`) keeps it covering every feature.

#### Behaviour changes

- **Synthesis numbers are only in the Build section.** The per-module "Synthesis Results" page that every module had in the Design sidebar is gone (it was empty for most modules, and could disagree with the Build page); per-module numbers are in the Build page's "By module" table. A project without reports now has no synthesis entry anywhere in the Design section. Stale `modules/<n>/synthesis.rst` files are removed on the next build.

#### Fixes

- **Without `mmdc`, a captioned diagram leaves only the note in the PDF**, not an empty numbered figure.
- **`make doc-check-env` also checks `sphinxcontrib-mermaid`**, so an old environment is told to run `make doc-venv` instead of failing with a traceback.
- **The breadcrumb bar stays at the top of the page while you scroll.**
- A header comment line that merely starts with dots (`...wraps at N`) is no longer mistaken for a directive in the overview description.
- **A SystemVerilog or VHDL header with a directive in it no longer turns the directive into the overview description.** The description shown in the module overview table now stops at the first directive line (`.. mermaid::`, `.. wavedrom::`), instead of including it.

#### Compatibility

- Backwards compatible. Projects without Mermaid blocks build the same pages as before; the Mermaid script is added only to pages that contain a diagram.
- Install the new dependency with `make doc-venv` (or `pip install -r requirements.txt`).

---

### v3.12.0

#### New features

- **Testbenches section** — lists the testbenches under `tb/` (`vunit/`, `cocotb/`, `directed/` subdirectories), each with its purpose, the module it tests, and its tests, counted from the source with no simulator run: VUnit `run("...")` and `` `TEST_CASE("...") ``, cocotb `@cocotb.test` functions (`skip=True` marked skipped), and directed tests marked with a `-- TEST: name — purpose` / `// TEST: name — purpose` comment. A summary table gives counts per framework and in total. Appears in the sidebar under **Verification**. `TESTBENCHES=0` removes it; `AUTODOC_TB_DIR` relocates it. The marker convention is documented in the new Testbenches section.
- **Build section** — the Implementation section is now **Build**, and shows a summary (Yosys and nextpnr versions, device class, when the reports were produced, docs revision), utilization (nextpnr's device utilisation plus the per-module table), timing, and warnings (total and most frequent messages). Open-source ECP5 (Yosys + nextpnr) first; Vivado utilization and timing still work, with its power, DRC and other reports to follow. `BUILD=0` removes it; `AUTODOC_REPORTS_DIR` relocates the reports.
- **`example_ecp5/`** — an ECP5 design (AXI4-Stream threshold filter with an AXI4-Lite register file, four registers), with one testbench per framework and real Yosys and nextpnr reports produced by `make ecp5-reports`.

#### Behaviour changes

- **Reports are now part of the normal build.** `make doc-html` ingests `reports/` itself (it used to need a separate `make doc-reports`), so a project that already has a `reports/` directory gets a Build section automatically. With no report files there is no section, as before; `make doc-reports` still writes its placeholder page; `BUILD=0` switches it off.
- The sidebar caption and page title are **Build** (was Implementation). File paths (`synthesis/index.rst`, `modules/<n>/synthesis.rst`) and `make doc-reports` are unchanged.
- The Build page order is Summary, Utilization, Timing, Warnings (timing used to come first).

#### Fixes

- **nextpnr timing showed every clock twice.** nextpnr prints `Max frequency for clock` after placement and again after routing; there is now one row per clock, with the routed value.
- **Yosys utilization was all zeros on current Yosys.** Yosys now prints `stat` cell lines as `<count> <cell>`; the parser expected `<cell> <count>`. Both are read, and the `design hierarchy` total is no longer shown as a module.
- When a switch is off, that section's pages from an earlier run are deleted, so they cannot reappear in the sidebar.

#### Compatibility

- Backwards compatible. With no `tb/` directory and no report files the output is unchanged.
- Testbench files must not be listed in `filelist.f` (a listed testbench becomes a second top level).

### v3.11.0

#### New features

- **Interfaces a module instantiates are documented and drawn** — a module that wires interfaces together without having interface ports of its own (a typical top level) is no longer silent about them. The block page's "Interfaces" section now also covers interfaces declared in a module's body (`axis_if m_axis (.clk(clk));`), shown as "instantiated here as ...", with each interface's members and widths. For an interface used only internally, every modport it defines gets a direction column. On the diagram they appear in a separate blue **interfaces** box (`name : interface`, one row each) below the ports box, since they are internal rather than ports.
- **`make doc-check-env`** — `doc-html` and `doc-pdf` now first check that the Sphinx packages are importable and, if not, stop with "run `make doc-venv`" instead of a Sphinx `no theme named 'furo'` traceback.
- **`example_sv/`** — a small SystemVerilog example with a package, two interfaces, and a module with interface ports (`make doc-venv && make doc-html` from that directory).

#### Compatibility

- Backwards compatible. Modules that neither have interface ports nor instantiate interfaces produce byte-identical block pages and diagrams.

#### Notes

- Interface instances are found by the same rules as interface ports: the interface must be defined in a support file or the module's own file, and ordinary module instances are never read as interfaces.

### v3.10.0

#### New features

- **SystemVerilog interface ports in block diagrams and port tables** — ports typed as an interface (`axil_if.slave s_axil`, `axis_if.master m_axis`, or a bare `axis_if s_dbg`) are no longer skipped. A module with AXI-Lite / AXI-Stream interface ports now shows them next to `clk`/`rst`:
  - **Port table:** one row per interface port. *Direction* is the modport (`slave`, `master`, or — if there is none), *Type* is the interface name, and the description comes from the preceding or inline comment like any other port.
  - **Block diagram:** one bus-style port per interface, labelled `name (interface)`. Master-like modports (`master`, `manager`, `initiator`, `source`/`src`, `mst`, `tx`, `producer`, `driver`, `out`) are drawn on the right; every other port (`slave`, `subordinate`, `target`, `sink`/`snk`, `rx`, an unrecognised modport, or none) is on the left.
  - **Interfaces section:** a new "Interfaces" heading lists the members of each interface a module uses (type, width and description), with a direction column for each modport the module's ports use.
  - A type name counts as an interface only if an `interface ... endinterface` of that name is defined in one of the `support_files` (see v3.9.0) or in the module's own file, so an ordinary type name is never mistaken for one.
- `generate_rst.py`'s flat-mode port list recognises interface ports the same way (it finds interface definitions across the source tree).

#### Compatibility

- Backwards compatible. Modules without interface ports produce byte-identical block pages, and `extract_block.py`'s new `--support` option is optional.
- VHDL is unchanged: record-typed ports already appear as ordinary typed ports.

#### Notes

- Interface ports are read from the module header, one per line (the style the existing port extractor already assumes). An interface *instance* inside the module body is not a port. Interfaces defined in a file that also defines modules are found only for that file's own modules.
- Interface members and widths are shown as written (`logic[W-1:0]`); parameters are not evaluated.
- Support files are not part of a module's extraction cache key; after editing an interface run `make doc-extract FORCE=1`.
- A *modport-less* interface port (`axis_if s_dbg`) makes the RTL schematic fall back to yosys's own renderer, because yosys marks its members `inout` and netlistsvg accepts only `input`/`output`. The block page is unaffected.

### v3.9.0

#### New features

- **SystemVerilog packages and interfaces in schematics** — files that define no module (packages, interfaces) are now recorded in `hierarchy.json` as `support_files`, in filelist order, instead of only triggering a "could not extract module name" warning. RTL schematic generation reads them first, in that order (so a package precedes its users), then the module's dependencies, then the module itself, and runs `hierarchy -top <module>` before `proc; opt`. This fixes `Can't resolve function name pkg::...` and package-scoped syntax errors from yosys, and the netlistsvg failure on interface-typed ports (yosys now flattens the interface into plain signals).
- **Cleaner schematic labels** — interface members appear as `if_name_signal` instead of falling back to a generic `output` label, and yosys's per-interface copies (`producer$interfaces$stream_if`) are labelled with the module name.

#### Compatibility

- Backwards compatible. `support_files` is an addition to `hierarchy.json` (an older file without it still works), VHDL modules ignore it, and projects with no packages or interfaces get the same schematics as before. VHDL package files are unaffected.
- `generate_schematic.py` accepts `--support <file>` (repeatable) after its dependency arguments.

#### Notes

- yosys's native SystemVerilog frontend still applies: no `return` statements in functions, no `import` inside a module body (import in the module header or use `pkg::name`), and only basic interface/modport support. Modules that use unsupported constructs are skipped with a message, as before.
- Support files are not part of a module's extraction cache key (neither are its dependencies). After editing a package or interface, run `make doc-extract FORCE=1` to refresh the schematics.

### v3.8.0

#### New features

- **Configurable registers directory** — the register pipeline no longer assumes a top-level `registers/`. Set `AUTODOC_REGISTERS_DIR` (default `registers`) to relocate it, for example under `out/`: `make doc-html AUTODOC_REGISTERS_DIR=out/registers`. It moves `regs_*.toml` and `config.yml`, the `generated/` and `out/` output of `make doc-regs`, and the `generated/` export that `include_registers.py` looks for. `autodoc.mk` passes the variable to `run_extract.py` and `generate.py` as well as Sphinx.

#### Compatibility

- Backwards compatible. With the variable unset, every script keeps its previous default, including the `docs/hdl_autodoc`-relative fallback in `run_extract.py`. Through `make` the default resolves to `<project root>/registers`, which is the same directory for the standard layout.
- The "no register export found" notice now names the configured directory, and says `make doc-html` rather than `make html`.

### v3.7.0

#### Behaviour changes

- **Schematics are on by default** — `SCHEMATICS` now defaults to `1` (it was `0` in v3.6.x). They are skipped silently when yosys is not installed; `make doc-html SCHEMATICS=0` turns them off.
- **Design Hierarchy merged into Overview** — the instantiation tree, shared-component list and parent/child columns now live on the single Overview page; the separate `hierarchy.rst` page is gone (an old one is deleted automatically on the next build).

#### New features

- **`ANNOTATED_SOURCE` switch** — `make doc-html ANNOTATED_SOURCE=0` drops the full source listing from entity pages (default on, as before). The listing now lives in an always-regenerated `<module>_source.rst` that `entity.rst` includes, so the switch works on existing pages too. Unedited older `entity.rst` shells are upgraded automatically; a hand-edited one that still contains the listing inline keeps it until you replace it with `.. include:: <module>_source.rst`.
- **Black-box SystemVerilog children** — a VHDL module that instantiates SystemVerilog is no longer skipped as "mixed-language". A generated port-only VHDL stub stands in for each SV child, which is drawn as a black-box instance. ghdl's generic-value suffixes (`pwm_controller_8`) are stripped from box labels.
- **Restyled schematics** — a bundled netlistsvg skin (soft colours, sans-serif font, dark-mode palette, slightly wider layout spacing).
- **RTL Detail section** — the schematic sits under a collapsed "RTL Detail" disclosure on the block page in HTML, so the page leads with the block diagram. In the PDF each schematic gets its own landscape page, rotated 90° and fitted to the page.
- **Navigation** — breadcrumbs on every page, and the left sidebar now scrolls to the current page (it keeps its position after a click inside the sidebar).

#### Fixes

- VHDL modules in a project that also contains SystemVerilog files now get schematics: only a module's own dependencies are passed to ghdl, not every file in the project.
- netlistsvg drew the wrong module for hierarchical designs; the requested module is now moved to the front of the netlist.
- Incremental rebuilds after an HDL edit no longer warn "Entity … not found" and drop the ports and generics from VHDL entity pages (a sphinx-vhdl bug, worked around in `conf.py`).
- SystemVerilog descriptions now also appear on projects generated before v3.6.0 (unedited `entity.rst` shells are upgraded).

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

- **Synthesis reports** — `make reports` ingests Vivado (`utilization_placed.rpt`, `timing_summary_routed.rpt`) and Yosys/nextpnr (`stat.txt`, `nextpnr.log`) report files from a `reports/` directory. Writes an **Implementation** toctree section with a top-level timing + utilization page (per-module numbers are in its "By module" table). Utilization tables show hierarchy indentation (`└─ submodule`) and available resource counts. Timing tables show target frequency alongside achieved fmax. A placeholder page is always present so the Implementation sidebar section never disappears.
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

- **Block diagrams** — `extract_block.py` generates a `block.rst` page per module. The diagram uses a TerosHDL-inspired style: a green box for generics/parameters (with default values) stacked above a yellow box for ports (inputs left with `►`, outputs right with `◄`, bus widths annotated). Both VHDL `generic` and SV `parameter`/`localparam` declarations are extracted. SystemVerilog interface-typed ports (`axil_if.slave s_axil`) get one table row and one `name (interface)` port each — slave-style modports on the left, master-style on the right — and an "Interfaces" section lists each interface's members. Interfaces a module instantiates internally appear in a blue box under the ports.
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
├── extract_reports.py    reports/           → synthesis/index.rst
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
