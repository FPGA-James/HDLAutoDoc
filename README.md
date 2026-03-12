# 📟 HDL AutoDoc

> **Turn your VHDL and SystemVerilog source into beautiful, navigable documentation — automatically.**

HDL AutoDoc is a zero-boilerplate documentation pipeline for hardware design projects. Drop your source files in, run `make html`, and get a fully structured Sphinx site with block diagrams, FSM diagrams, timing waveforms, process pages, a hierarchy tree, a CDC analysis page per module, and an embedded register map — all extracted directly from your HDL source.

No separate doc files to maintain. No manual diagrams to draw. If it's in the source, it's in the docs.

---

## ✨ Features

| Feature | How it works |
|---|---|
| **Auto-discovered ports & entities** | Extracted from `entity`/`module` declarations |
| **Block diagrams** | TerosHDL-style port diagram (green generics box + yellow ports box) with bus widths, auto-generated per module |
| **Generics / parameters table** | Name, type, default value, and description extracted from VHDL `generic` and SV `parameter`/`localparam` declarations |
| **FSM state diagrams** | Parsed from `case` blocks, rendered with [Graphviz](https://graphviz.org) |
| **Timing waveforms** | `.. wavedrom::` blocks in source comments, rendered with [WaveDrom](https://wavedrom.com) |
| **Per-process pages** | One page per labeled `process` / `always_ff` / `always_comb` block |
| **CDC analysis** | Clock domains, signal crossings, synchronizer detection, and async FIFO detection — one page per module with a Graphviz diagram |
| **Design hierarchy** | Driven by `filelist.f` — instantiation tree auto-detected, top-level auto-found |
| **Shared components** | Documented once, linked from every parent |
| **VHDL + SystemVerilog** | Mixed-language designs work out of the box |
| **Register map** | Auto-embeds `registers/generated/*.html` — any register builder output supported |
| **Dark / light mode** | Catppuccin Latte (light) and Mocha (dark) — toggle persists across sessions |
| **Fluid layout** | Scales to any screen width using `clamp()` — no hardcoded breakpoints |
| **PDF output** | Full LaTeX PDF via `make pdf` |

---

## 📸 What you get

```
docs/
├── index.rst                       ← project root
├── overview.rst                    ← module summary table
├── hierarchy.rst                   ← instantiation tree diagram + module list
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

## 🚀 Getting started

### Prerequisites

- Python 3.11+
- [Graphviz](https://graphviz.org/download/) (`dot` on your PATH)
- [TeX Live](https://tug.org/texlive/) or [MacTeX](https://tug.org/mactex/) *(PDF only)*

### Install

```bash
git clone https://github.com/your-org/hdl-autodoc.git
cd hdl-autodoc
make install
```

### Point it at your design

Edit `filelist.f` — list your source files, leaves first:

```
# filelist.f
src/alu.vhd
src/register_file.vhd
src/cpu_core.sv
src/top.vhd          ← top-level auto-detected
```

### Build

```bash
make html   # → docs/_build/html/index.html
make pdf    # → docs/_build/latex/<project>.pdf
```

Optionally set a project name:

```bash
make html PROJECT="My FPGA Design"
```

---

## 🔧 How it works

The build runs in four steps, all driven by a single `make html`:

```
filelist.f
    │
    ▼
parse_hierarchy.py     Reads the filelist, extracts module names,
    │                  parses instantiations, detects the top-level,
    │                  writes docs/hierarchy.json
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
    ▼
sphinx-build           Renders HTML (or PDF via latexpdf).
```

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

Run `make html`. The entire directory is copied to `docs/_static/registers/` and embedded as a full-screen iframe, preserving all internal links and CSS. If no export is found a clear placeholder page is shown instead with instructions.

Override the entry point filename if your tool produces a different name:

```bash
make html AUTODOC_REG_ENTRY=regmap.html
```

---

## 🎨 Theme

HDL AutoDoc ships with a custom [Catppuccin](https://catppuccin.com) theme:

| Mode | Flavour | Background | Accent |
|---|---|---|---|
| Light | Latte | `#eff1f5` warm white | `#1e66f5` blue |
| Dark | Mocha | `#1e1e2e` deep slate | `#89b4fa` blue |

Toggle between modes using the floating pill button fixed to the bottom-right of every page. Your preference is saved to `localStorage` and survives navigation and browser restarts. On first visit the OS `prefers-color-scheme` setting is respected automatically.

### Customising the theme

All design tokens live at the top of `docs/_static/custom.css`. To change the accent colour across the entire site, update one variable in each flavour block:

```css
:root               { --ctp-blue: #1e66f5; }   /* Latte  */
[data-theme="dark"] { --ctp-blue: #89b4fa; }   /* Mocha  */
```

Content width is fluid by default and scales to your screen:

```css
--content-max: clamp(640px, calc(100vw - 300px), 1800px);
```

---

## 🛠 Make targets

| Target | Description |
|---|---|
| `make install` | Install Python dependencies |
| `make hierarchy` | Parse `filelist.f` → `hierarchy.json` |
| `make scaffold` | Generate RST shells (runs hierarchy first) |
| `make extract` | Extract FSM + process + CDC + block docs (runs scaffold first) |
| `make regs` | Generate register artifacts from `registers/regs_*.toml` |
| `make html` | Full build → `docs/_build/html/` |
| `make pdf` | Full build → LaTeX PDF |
| `make doc` | Run `regs` + `html` + `pdf` |
| `make clean` | Remove Sphinx build output only |
| `make clean-generated` | Remove all auto-generated RST + static files |
| `make clean-all` | ⚠️ Nuclear reset — removes everything including hand-editable shells |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| [Sphinx](https://www.sphinx-doc.org) | Documentation engine |
| [sphinx-rtd-theme](https://sphinx-rtd-theme.readthedocs.io) | ReadTheDocs HTML theme |
| [sphinx-vhdl](https://pypi.org/project/sphinx-vhdl/) | VHDL entity autodoc domain |
| [sphinxcontrib-wavedrom](https://sphinxcontrib-wavedrom.readthedocs.io) | `.. wavedrom::` directive |
| [Graphviz](https://graphviz.org) | FSM, hierarchy, CDC, and block diagram renderer |
| [docutils](https://docutils.sourceforge.io) | RST parser (pinned `>=0.18,<0.21` for sphinx-vhdl compat) |
| [hdl-registers](https://hdl-registers.com) | Register map generation from TOML/YAML |

---

## 📁 Project layout

```
hdl-autodoc/
├── filelist.f                  ← your source file list (edit this)
├── Makefile
├── requirements.txt
├── src/                        ← your HDL source files
├── registers/
│   ├── config.yml              ← bus config (width, protocol)
│   ├── regs_<name>.toml        ← register definitions
│   └── generated/              ← register map HTML output (auto-generated)
├── scripts/
│   ├── hdl_autodoc/            ← drop-in pipeline, reusable across projects
│   │   ├── __init__.py
│   │   ├── parse_hierarchy.py  ← reads filelist.f → hierarchy.json
│   │   ├── generate_rst.py     ← scaffolds RST structure
│   │   ├── extract_fsm.py      ← extracts FSM case blocks → dot + rst
│   │   ├── extract_processes.py← extracts labeled processes → rst pages
│   │   ├── extract_cdc.py      ← extracts CDC analysis → dot + rst
│   │   ├── extract_block.py    ← extracts block diagram + port/generics tables → dot + rst
│   │   ├── run_extract.py      ← orchestrates extraction for all modules
│   │   └── include_registers.py← copies register map + writes rst page
│   └── registers/
│       └── generate.py         ← generates VHDL, C header, and HTML from register TOML
└── docs/
    ├── conf.py                 ← Sphinx config (edit project metadata here)
    ├── _static/
    │   ├── custom.css          ← Catppuccin Latte/Mocha theme
    │   ├── theme.js            ← dark mode toggle + OS preference detection
    │   └── logo.svg            ← replace with your own logo
    └── _templates/
        ├── layout.html         ← sidebar brand + footer
        └── breadcrumbs.html    ← version badge in breadcrumb bar
```

---

## ✏️ What to hand-edit vs what to leave alone

| File | Status | Notes |
|---|---|---|
| `filelist.f` | ✍️ Edit freely | Your source manifest |
| `src/*.vhd`, `src/*.sv` | ✍️ Edit freely | Your HDL — single source of truth |
| `docs/conf.py` | ✍️ Edit freely | Project name, author, version |
| `docs/_static/custom.css` | ✍️ Edit freely | Theme tokens and visual overrides |
| `docs/_static/logo.svg` | ✍️ Replace | Swap in your own logo |
| `docs/modules/<n>/entity.rst` | ✍️ Safe to edit | Written once, never overwritten |
| `docs/modules/<n>/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/modules/<n>/fsm.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/modules/<n>/timing.rst` | 🔄 Auto-generated | Aggregated from process wavedrom blocks |
| `docs/modules/<n>/block.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/modules/<n>/cdc.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/modules/<n>/processes/` | 🔄 Auto-generated | Regenerated every build |
| `docs/registers.rst` | 🔄 Auto-generated | Written by `include_registers.py` |
| `docs/_static/registers.html` | 🔄 Auto-generated | Copied from `registers/generated/` |
| `docs/hierarchy.json` | 🔄 Auto-generated | Do not edit |
| `docs/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/overview.rst` | 🔄 Auto-generated | Regenerated every build |

---

## 🧩 Adding a new module

1. Add your source file to `src/`
2. Add it to `filelist.f`
3. Run `make html`

Done. The new module appears in the hierarchy, navigation, overview table, hierarchy diagram, and gets its own block diagram and CDC analysis page automatically.

---

## 🐛 Known limitations

- **FSM extraction** requires a labeled `case` block that assigns `next_state`. Complex FSMs split across multiple processes may not be fully captured.
- **Component instantiation** (VHDL `component` style without `entity work.` prefix) is matched by name — ambiguous names in large designs may need verification.
- **`vhdl:autoentity`** only works for VHDL. SystemVerilog modules get a `literalinclude` source listing instead.
- **Wavedrom in PDF** requires the `wavedrom` Python package and may not render identically to HTML output.
- **Register map in PDF** — the iframe embed is HTML-only. The PDF build skips the register page content.
- **CDC analysis** is static only — see the CDC analysis section for full limitations.
- **Block diagram generics** — port comments on a preceding line are captured; inline comments on the same line are also captured. Generics with no default value will show no default in the table.
- **Block diagram SV named parameters** — `#(.PARAM(val))` style is not detected; use positional `#(val)` style.

---

## 📋 Release notes

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
├── run_extract.py        hierarchy.json     → orchestrates above four
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
