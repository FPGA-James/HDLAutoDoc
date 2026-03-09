# 📟 HDL AutoDoc

> **Turn your VHDL and SystemVerilog source into beautiful, navigable documentation — automatically.**

HDL AutoDoc is a zero-boilerplate documentation pipeline for hardware design projects. Drop your source files in, run `make html`, and get a fully structured Sphinx site with FSM diagrams, timing waveforms, process pages, and a hierarchy tree — all extracted directly from your HDL source comments.

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
        ├── processes/
        │   ├── index.rst           ← process summary table
        │   ├── p_state_reg.rst     ← per-process: description, waveform, source
        │   └── p_next_state.rst
        └── submodules/             ← nav links to child modules
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

That's it.

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
generate_rst.py        Scaffolds docs/modules/<name>/ for each module.
    │                  Always-regenerated: index, fsm, timing pages.
    │                  Write-if-missing: entity pages (safe to hand-edit).
    ▼
run_extract.py         Calls extract_fsm.py and extract_processes.py
    │                  for every module in hierarchy.json.
    │                  Extracts FSM dot+rst and per-process rst pages.
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
// p_next_state: Combinational next-state logic.
//
// // wavedrom::
//
//    { "signal": [
//      { "name": "clk", "wave": "P......." }
//    ]}
always_comb begin : p_next_state
    ...
end
```

---

## 🗂 Design hierarchy

HDL AutoDoc reads a standard `filelist.f`. List files in any order — the hierarchy is detected by parsing instantiations, not by file order:

```
# VHDL direct instantiation style
u1 : entity work.alu port map (...);

# VHDL component instantiation style
u1 : alu port map (...);

# SystemVerilog module instantiation
alu #(.WIDTH(32)) u_alu (.clk(clk), ...);
```

Shared components (instantiated by multiple parents) are documented once and linked from each parent's Submodules section.

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
| `make clean` | Remove Sphinx build output |
| `make clean-generated` | Remove all auto-generated RST files |
| `make clean-all` | ⚠️ Nuclear reset — removes all generated files including hand-editable shells |

---

## 📦 Dependencies

| Package | Purpose | Link |
|---|---|---|
| [Sphinx](https://www.sphinx-doc.org) | Documentation engine | sphinx-doc.org |
| [sphinx-rtd-theme](https://sphinx-rtd-theme.readthedocs.io) | ReadTheDocs HTML theme | readthedocs.io |
| [sphinx-vhdl](https://pypi.org/project/sphinx-vhdl/) | VHDL entity autodoc domain | PyPI |
| [sphinxcontrib-wavedrom](https://sphinxcontrib-wavedrom.readthedocs.io) | `.. wavedrom::` directive | readthedocs.io |
| [WaveDrom](https://wavedrom.com) | Timing diagram renderer (JS + Python) | wavedrom.com |
| [Graphviz](https://graphviz.org) | FSM and hierarchy diagram renderer | graphviz.org |
| [docutils](https://docutils.sourceforge.io) | RST parser (pinned `<0.21` for sphinx-vhdl compat) | sourceforge.io |

---

## 📁 Project layout

```
hdl-autodoc/
├── filelist.f                  ← your source file list (edit this)
├── Makefile
├── requirements.txt
├── src/                        ← your HDL source files
│   ├── top.vhd
│   └── ...
├── scripts/
│   ├── parse_hierarchy.py      ← reads filelist.f, writes hierarchy.json
│   ├── generate_rst.py         ← scaffolds RST structure
│   ├── extract_fsm.py          ← extracts FSM case blocks → dot + rst
│   ├── extract_processes.py    ← extracts labeled processes → rst pages
│   └── run_extract.py          ← orchestrates extraction for all modules
└── docs/
    ├── conf.py                 ← Sphinx config (edit project metadata here)
    ├── _static/
    │   ├── custom.css          ← theme overrides
    │   └── logo.svg            ← replace with your logo
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
| `docs/_static/custom.css` | ✍️ Edit freely | Visual overrides |
| `docs/_static/logo.svg` | ✍️ Replace | Swap in your own logo |
| `docs/modules/<n>/entity.rst` | ✍️ Safe to edit | Written once, never overwritten |
| `docs/modules/<n>/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/modules/<n>/fsm.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/modules/<n>/timing.rst` | 🔄 Auto-generated | Aggregated from process wavedrom blocks |
| `docs/modules/<n>/processes/` | 🔄 Auto-generated | Regenerated every build |
| `docs/hierarchy.json` | 🔄 Auto-generated | Do not edit |
| `docs/index.rst` | 🔄 Auto-generated | Regenerated every build |
| `docs/overview.rst` | 🔄 Auto-generated | Regenerated every build |

---

## 🧩 Adding a new module

1. Add your source file to `src/`
2. Add it to `filelist.f`
3. Run `make html`

Done. The new module appears in the hierarchy, the navigation, the overview table, and the hierarchy diagram automatically.

---

## 🐛 Known limitations

- **FSM extraction** requires a labeled `case` block that assigns `next_state`. Complex FSMs using nested functions or split across multiple processes may not be fully captured.
- **Component instantiation** (VHDL `component` style without `entity work.` prefix) is matched by name against the known module list — ambiguous names in large designs may need verification.
- **`vhdl:autoentity`** only works for VHDL. SystemVerilog modules get a `literalinclude` source listing instead.
- **Wavedrom in PDF** requires the `wavedrom` Python package (`pip install wavedrom`) and may not render identically to the HTML output.

---

## 🤝 Contributing

Pull requests welcome. The scripts are intentionally small and single-purpose — each one does one thing and has a clear input/output contract.

```
parse_hierarchy.py   filelist.f          → hierarchy.json
generate_rst.py      src/ + hierarchy    → docs/modules/**/
extract_fsm.py       <file.vhd|sv>       → <module>.dot + <module>.rst
extract_processes.py <file.vhd|sv>       → p_*.rst + index.rst
run_extract.py       hierarchy.json      → orchestrates above two
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
  ☕ and too much time staring at VHDL
</p>

---

<p align="center">
  🤖 Created by <a href="https://claude.ai">Claude</a> — Anthropic's AI assistant
</p>