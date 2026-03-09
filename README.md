# 📟 HDL AutoDoc

> **Turn your VHDL and SystemVerilog source into beautiful, navigable documentation — automatically.**

HDL AutoDoc is a zero-boilerplate documentation pipeline for hardware design projects. Drop your source files in, run `make html`, and get a fully structured Sphinx site with FSM diagrams, timing waveforms, process pages, a hierarchy tree, and an embedded register map — all extracted directly from your HDL source.

No separate doc files to maintain. No manual diagrams to draw. If it's in the source, it's in the docs.

---

## ✨ Features

| Feature | How it works |
|---|---|
| **Auto-discovered ports & entities** | Extracted from `entity`/`module` declarations |
| **FSM state diagrams** | Parsed from `case` blocks, rendered with [Graphviz](https://graphviz.org) |
| **Timing waveforms** | `.. wavedrom::` blocks in source comments, rendered with [WaveDrom](https://wavedrom.com) |
| **Per-process pages** | One page per labeled `process` / `always_ff` / `always_comb` block |
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
        ├── fsm.rst                 ← state diagram + transition table
        ├── timing.rst              ← all wavedrom diagrams for this module
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
    │                  Always-regenerated: index, fsm, timing pages.
    │                  Write-if-missing: entity pages (safe to hand-edit).
    ▼
run_extract.py         Calls extract_fsm.py and extract_processes.py
    │                  for every module in hierarchy.json.
    │                  Extracts FSM dot+rst and per-process rst pages.
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

## 🗺 Register map integration

Place your register builder output anywhere under `registers/generated/`:

```
registers/
└── generated/
    └── my_chip_registers.html   ← any filename, any register tool
```

Run `make html`. The register map is automatically embedded as a full-screen page inside the top module's navigation, above the Submodules section. If no file is found, a clear placeholder is shown instead with instructions.

If your tool produces multiple HTML files, the first alphabetically is used and a warning is printed listing the others.

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
| `make extract` | Extract FSM + process docs (runs scaffold first) |
| `make html` | Full build → `docs/_build/html/` |
| `make pdf` | Full build → LaTeX PDF |
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
| [Graphviz](https://graphviz.org) | FSM and hierarchy diagram renderer |
| [docutils](https://docutils.sourceforge.io) | RST parser (pinned `>=0.18,<0.21` for sphinx-vhdl compat) |

---

## 📁 Project layout

```
hdl-autodoc/
├── filelist.f                  ← your source file list (edit this)
├── Makefile
├── requirements.txt
├── src/                        ← your HDL source files
├── registers/
│   └── generated/              ← place your register map HTML here
├── scripts/
│   ├── parse_hierarchy.py      ← reads filelist.f → hierarchy.json
│   ├── generate_rst.py         ← scaffolds RST structure
│   ├── extract_fsm.py          ← extracts FSM case blocks → dot + rst
│   ├── extract_processes.py    ← extracts labeled processes → rst pages
│   ├── run_extract.py          ← orchestrates extraction for all modules
│   └── include_registers.py   ← copies register map + writes rst page
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

Done. The new module appears in the hierarchy, navigation, overview table, and hierarchy diagram automatically.

---

## 🐛 Known limitations

- **FSM extraction** requires a labeled `case` block that assigns `next_state`. Complex FSMs split across multiple processes may not be fully captured.
- **Component instantiation** (VHDL `component` style without `entity work.` prefix) is matched by name — ambiguous names in large designs may need verification.
- **`vhdl:autoentity`** only works for VHDL. SystemVerilog modules get a `literalinclude` source listing instead.
- **Wavedrom in PDF** requires the `wavedrom` Python package and may not render identically to HTML output.
- **Register map in PDF** — the iframe embed is HTML-only. The PDF build skips the register page content.

---

## 📋 Release notes

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
- Sidebar uses Catppuccin Crust as background in both modes for consistent contrast regardless of light/light mode.
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
parse_hierarchy.py    filelist.f         → hierarchy.json
generate_rst.py       src/ + hierarchy   → docs/modules/**/
extract_fsm.py        <file.vhd|sv>      → <module>.dot + <module>.rst
extract_processes.py  <file.vhd|sv>      → p_*.rst + index.rst
run_extract.py        hierarchy.json     → orchestrates above two
include_registers.py  registers/         → docs/registers.rst + _static/
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