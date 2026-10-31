# Mermaid diagrams and a full-feature showcase example — design

Status: draft for review. Nothing here is built yet. Work happens on branch `mermaid-support`.

Marked **[decided]** = said by the project owner. **[call]** = a default chosen while
writing this; change it freely. **[verified]** = checked by a throwaway spike against
`sphinxcontrib-mermaid` 2.1.1, Sphinx 8.2.3, Furo, sphinx-vhdl 0.2.2 and mermaid-cli.

## Intent

Authors should be able to put **Mermaid diagrams** (sequence, state, flow and similar) in
the comments they already write, and see them rendered in the generated HTML and, where the
tooling is installed, in the PDF. Alongside it, one **example project that exercises every
feature** of the tool, so users have a single place to see all the output.

## Decisions

- Diagrams are **written by the author in source comments**, as `.. wavedrom::` blocks are
  today. The tool does **not** generate Mermaid; the generated FSM, hierarchy, CDC and block
  diagrams stay on Graphviz. **[decided]**
- **PDF rendering is optional.** HTML always works; the PDF gets diagrams only if
  `mermaid-cli` (`mmdc`) is installed. **[decided]**
- Work is done on a branch. **[decided]**
- The example is extensive enough to cover all features. **[decided]**

## Goals

- A `.. mermaid::` block in a module header, or in the comment block above a process /
  `always` block, renders as a diagram on the corresponding page (VHDL and SystemVerilog).
- Works in light and dark mode, offline if the user supplies a local copy of the JavaScript,
  and in the PDF when `mmdc` is available.
- A project that never writes a Mermaid block sees no change at all.
- `example_full/` demonstrates every feature listed in the coverage matrix below, and a test
  keeps it honest.

## Non-goals

- Generating Mermaid from the design (FSM as `stateDiagram`, hierarchy as a graph).
  Possible later; not now.
- A per-module "Diagrams" page aggregating every diagram (the way Timing aggregates
  waveforms). Diagrams appear where they are written.
- A `MERMAID=0` switch: nothing appears unless an author writes a block, so there is nothing
  to switch off. **[call]**
- Bundling mermaid-cli, or making it a required dependency.

## Anti-goals (a failure even if it "works")

- A page without a diagram starts loading Mermaid JavaScript, or any existing page changes.
  **[verified: the script is only added to pages that contain a diagram]**
- The PDF build fails, or prints one warning per diagram, just because `mmdc` is missing.
- `mmdc` or a browser becomes a hard dependency.
- A diagram's indentation is destroyed (Mermaid `mindmap`, nested `subgraph` and `state`
  blocks depend on it).

## How authors write a diagram

The same shape as wavedrom: an RST directive inside the comment block. The first block is
in a VHDL entity header, the second above a SystemVerilog `always_ff`.

```vhdl
-- Handshake master.
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
// .. mermaid::
//    :caption: State machine
//
//    stateDiagram-v2
//      [*] --> IDLE
//      IDLE --> BUSY: start
always_ff @(posedge clk) begin : p_state
```

Directive options (`:caption:`, `:alt:`, `:align:`) are the extension's own and pass through.

## Where diagrams are supported

| Location | Today | Needed |
|---|---|---|
| VHDL entity header comment | works, via `vhdl:autoentity` **[verified]** | tests, docs |
| SystemVerilog module header comment | works, via `sv_module_description`, indentation kept **[verified]** | tests, docs |
| Comment block above a process / `always` block | not supported | **new token** in `extract_processes.py`, rendered on the process page |
| Anywhere else in the body | not supported | non-goal |

### Process-level blocks (new)

`extract_comment_tokens` gains a `mermaid` token beside `wavedrom`, recognised by the same
rule (`.. mermaid::` after the comment prefix is stripped). Differences from wavedrom:

- The block's lines are the indented lines that follow, including option lines such as
  `:caption:` and the blank line after them. They are emitted **with their relative
  indentation preserved**: remove the smallest common indent, then re-indent by three spaces.
  (`wavedrom` strips every line, which is fine for JSON and wrong for Mermaid.)
- It is rendered on the process page under *Description*, in source order with the surrounding
  text.
- A page with a Mermaid block shows it in the process summary's feature column the way a
  waveform does (`✔`). **[call]**

### Fix: overview descriptions

`generate_rst.extract_entities` builds the one-line description in the overview table from
the first two comment lines above the module. A short header followed by a directive would
put `.. mermaid::` into that table. The description stops at the first directive line (any
line beginning `..`). This applies to every directive, not only Mermaid.

## Configuration

In `src/docs/hdl_autodoc/conf.py`, always loaded:

- Add `sphinxcontrib.mermaid` to `extensions`; add `sphinxcontrib-mermaid>=2.1` to
  `src/requirements.txt`.
- **Offline HTML:** by default the extension loads Mermaid from a CDN, so a viewer needs
  internet access. A Makefile variable `AUTODOC_MERMAID_JS` (default empty) points at a local
  copy and is passed to `mermaid_use_local`. **[call]**
- **Light/dark:** follows Furo's theme toggle and the OS preference with no configuration
  **[verified]**; the defaults are kept.
- **PDF:** two Makefile variables passed through the environment like the others:
  `AUTODOC_MERMAID_CMD` (default `mmdc`) and `AUTODOC_MERMAID_PARAMS` (extra arguments, for
  example `-p puppeteer.json` to use an installed Chrome). **[call]**
  **[verified: with `mmdc` plus system Chrome the LaTeX build embeds each diagram as a vector
  PDF and the PDF text contains the diagram's labels; current `mmdc` fits the PDF to the
  diagram, so no `--pdfFit` flag is passed]**

### PDF without `mmdc`

**[verified]** Without `mmdc` the extension leaves an *empty captioned figure* and prints one
`WARNING: command 'mmdc' cannot be run` **per diagram**. The build still succeeds. The
configuration replaces this: for the LaTeX builder, if the command is not found, each Mermaid
node is replaced by a one-line note ("Diagram omitted from the PDF: install mermaid-cli") and
**one** informational message states how many diagrams were omitted and how to enable them.
No warning, no empty figure. **[call]** HTML is unaffected.

## The showcase example: `example_full/`

A Lattice ECP5 **sensor data logger**: a sampled input crosses from its own clock into the
system clock, is filtered and framed on an AXI4-Stream path, and is controlled and read back
over AXI4-Lite and a UART/APB path. The theme exists to give every feature a natural home; the
RTL itself is the builder's to design.

Constraints on the design, so the example is real and stays maintainable:

- Mixed **VHDL and SystemVerilog**, with at least three levels of hierarchy and one module
  instantiated by two different parents (a shared component).
- Synthesises with Yosys and nextpnr-ecp5 so the build reports are **real output** (see
  "Mixed-language synthesis" below).
- It is a *documentation* example: correct and readable matters more than being a good
  logger. Testbenches are illustrative and are not run by the docs build.

### Feature coverage matrix

Every row must be demonstrable in the built site; a test checks the source-level ones.

| Feature | Where `example_full` shows it |
|---|---|
| VHDL entities, SystemVerilog modules, mixed hierarchy, shared component | the module set as a whole |
| Generics (VHDL) and parameters (SV), with defaults | at least one module of each |
| FSM diagrams | a VHDL FSM and an SV FSM |
| Per-process pages, wavedrom waveforms | labelled processes with `.. wavedrom::` blocks |
| **Mermaid** (new) | header diagram in a VHDL entity and in an SV module; process-level diagram; at least a sequence, a state and a flow diagram |
| CDC analysis | a second clock domain, a 2-flop synchroniser, an asynchronous FIFO |
| Reset-domain analysis | a reset synchroniser and a mix of sync and async resets |
| Bus grouping (flat ports) | flat AXI4-Lite, AXI4-Stream and APB port groups, plus a `bus_groups.toml` for a custom group |
| SV interfaces and packages | `axis_if`, `axil_if` (support files), a package, interface ports, and an internal interface instance |
| Register map | an AXI4-Lite register block with a `regs_<module>.toml` |
| RTL schematics | VHDL modules, SV modules, and a VHDL parent with an SV child (black box) |
| Block diagrams with generics, interface ports, internal-interface box | across the modules above |
| Annotated source and entity descriptions | every module has a header comment |
| Testbenches | VUnit (VHDL and SV), cocotb, directed (VHDL and SV), each linked to a module, one skipped test |
| Build reports | real Yosys + nextpnr-ecp5 reports, plus Vivado sample reports for the hierarchical utilization table |
| Documentation coverage | `make doc-coverage` output included |
| PDF output | built with landscape schematics |

### Mixed-language synthesis (the known risk)

Yosys' Verilog frontend and the ghdl plugin elaborate separately, and neither sees the other's
modules. The builder starts with a **spike**: load the SystemVerilog modules, elaborate each
VHDL unit with `ghdl ... -e <unit>` into the same Yosys design, then `hierarchy -top`. If that
works, the reports cover the whole design. **If it does not**, fall back to: synthesise the
design with the SystemVerilog top level as the reported top and the VHDL units it instantiates
elaborated one by one; and if even that fails, report on the part that does synthesise and say
so in the example's README. The VHDL schematics use the existing stub mechanism either way.
**[call]**

### Layout

```
example_full/
├── Makefile  filelist.f  bus_groups.toml  ecp5.lpf  README.md  .gitignore
├── src/            VHDL, SV, package and interface files
├── registers/      config.yml, regs_<module>.toml
├── tb/             vunit/  cocotb/  directed/
├── reports/        yosys/ (real)  vivado/ (sample)
└── docs/hdl_autodoc/_build/   committed output, built from a clean revision
```

The built output is committed like the other examples. **[decided: outputs are kept in the
repo]**

## Compatibility

- Projects that write no Mermaid block see identical pages **[verified for page content;
  the extension adds no script to pages without a diagram]**.
- `sphinxcontrib-mermaid` becomes a Python dependency (pure Python; no browser needed for
  HTML).
- A header that contains a directive now gets a one-line overview description that stops
  before it; previously it could include the directive text.

## Testing and docs

- Unit tests: the new `mermaid` token (with indentation and options), the overview
  description stopping at a directive, the LaTeX no-`mmdc` path (nodes replaced, one message,
  no warning), the new environment variables reaching `conf.py`.
- A test over `example_full/` for the source-level rows of the matrix (modules exist, FSMs
  found, testbenches linked, interface ports found, registers parsed, reports parse).
- Build checks: HTML and PDF of every example with zero warnings; PDF with and without `mmdc`.
- README: a Mermaid section (how to write a diagram, where it is supported, offline and PDF
  setup, what happens without `mmdc`), the new variables, and `example_full` under "Try the
  example". Release notes for the next minor version.

## Phasing

1. **Mermaid support:** the extension, process-level token, overview fix, PDF fallback, the
   new variables, tests, README.
2. **`example_full`:** design and RTL, registers, testbenches, a real flow for the reports,
   Mermaid diagrams in it, the coverage test.
3. **Build, verify and release:** all examples built from a clean revision with output
   committed, release notes, version bump. Tagging and pushing only on the owner's go-ahead.

## Left to the builder

- All RTL, names and sizes inside `example_full`, within the matrix and constraints above.
- The exact wording of the PDF note and the log message.
- The shape of the Mermaid diagrams in the example, provided there are at least a sequence,
  a state and a flow diagram.

## Needs input

None. The calls above (no `MERMAID` switch, the new variables, the PDF note, the example's
name and fallback plan) are marked so they can be changed in review.
