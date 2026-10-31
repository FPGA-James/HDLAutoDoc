# Mermaid Support and the Showcase Example Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let authors put Mermaid diagrams in source comments (headers and process comments) and see them in HTML and, with `mmdc`, in the PDF; and add `example_full/`, an example that exercises every feature.

**Architecture:** `sphinxcontrib-mermaid` is always loaded. A small `mermaid_support.py` next to `conf.py` holds the testable pieces: settings from the environment and a LaTeX fallback that replaces diagrams with a note when `mmdc` is missing. `extract_processes.py` gains a `mermaid` comment token beside `wavedrom`. `example_full/` is a mixed VHDL/SV ECP5 design built against a feature-coverage test.

**Tech Stack:** Python 3.13 (pytest), Sphinx 8 + Furo, sphinxcontrib-mermaid 2.1, mermaid-cli (optional), GNU make, Yosys + ghdl + nextpnr-ecp5 for the example.

**Spec:** `docs/superpowers/specs/2026-10-31-mermaid-and-showcase-example-design.md`

## Global Constraints

- Branch `mermaid-support`; commit on the branch; **do not tag or push** without the owner's go-ahead.
- `sphinxcontrib.mermaid` is always loaded; there is **no** `MERMAID` switch. Add `sphinxcontrib-mermaid>=2.1` to `src/requirements.txt`.
- Environment variables set by `autodoc.mk` for `conf.py`: `AUTODOC_MERMAID_JS` (default empty → `mermaid_use_local`), `AUTODOC_MERMAID_CMD` (default `mmdc`), `AUTODOC_MERMAID_PARAMS` (extra `mmdc` arguments, whitespace separated).
- Process-level blocks keep **relative indentation**: remove the smallest common indent, re-indent by three spaces. Do not strip each line.
- Without `mmdc`, the LaTeX builder replaces each Mermaid node with the note "Diagram omitted from the PDF: install mermaid-cli (mmdc)." and logs **one** info message with the count; **no** warning, no empty figure.
- A project that writes no Mermaid block gets identical pages. The overview description stops at the first line beginning `..`.
- The sidebar, pages and PDF of every example build with **zero Sphinx warnings**.
- `example_full/` is mixed VHDL + SystemVerilog, ≥ 3 hierarchy levels, one module with two parents, real Yosys/nextpnr-ecp5 reports, ≥ 3 Mermaid diagrams (a sequence, a state, a flow), and satisfies the spec's feature-coverage matrix. Built output is committed from a clean revision.
- Standard library only in the tool's scripts; `mermaid-cli` stays an optional external tool.

## Review Focus

- A VHDL comment line inside a Mermaid block that begins with `-->` or contains `--` (arrows) survives both the process-level token and the entity-header path. *(Task 2)*
- Nested content (`subgraph`, nested `state`, `mindmap`), option lines and blank lines inside a block keep their relative indentation; a Mermaid block directly after a wavedrom block in one comment keeps token order. *(Task 2)*
- A short header followed by a directive gives an overview description without `..`; a header with prose only is unchanged. *(Task 3)*
- LaTeX with no `mmdc`: zero warnings and one message; with the command present the extension's own path is used; empty environment variables give the defaults. *(Task 1)*
- A project with no Mermaid block builds identical content to v3.12.0 for the existing examples. *(Task 5)*

## File Structure

| File | Responsibility |
|---|---|
| `src/docs/hdl_autodoc/mermaid_support.py` (create) | Settings from the environment; LaTeX fallback handler |
| `src/docs/hdl_autodoc/conf.py` (modify) | Load the extension, apply settings, connect the handler |
| `src/autodoc.mk`, `src/requirements.txt` (modify) | Variables, dependency |
| `src/scripts/hdl_autodoc/extract_processes.py` (modify) | `mermaid` token, rendering, summary column |
| `src/scripts/hdl_autodoc/generate_rst.py` (modify) | Overview description stops at a directive |
| `example_full/` (create) | The showcase example |
| tests under `src/scripts/hdl_autodoc/tests/` | One file per concern |

---

### Task 1: Extension, settings and the PDF fallback

**Files:**
- Create: `src/docs/hdl_autodoc/mermaid_support.py`; test `src/scripts/hdl_autodoc/tests/test_mermaid_support.py`
- Modify: `src/docs/hdl_autodoc/conf.py`, `src/autodoc.mk`, `src/requirements.txt`

**Interfaces:**
- Produces: `mermaid_settings(environ: Mapping[str, str]) -> dict` returning `mermaid_cmd`, `mermaid_params` (list), `mermaid_use_local`; `omit_unrendered_diagrams(app, doctree, docname) -> None` (the `doctree-resolved` handler); `setup_mermaid(app) -> None`.

- [ ] **Step 1: Install the dependency** into the dev venv: `example/.venv/bin/pip install 'sphinxcontrib-mermaid>=2.1'`; add it to `src/requirements.txt`.
- [ ] **Step 2: Write failing tests** (load `mermaid_support` from `src/docs/hdl_autodoc` via `sys.path`): `mermaid_settings({})` → `mmdc`, `[]`, `""`; with `AUTODOC_MERMAID_CMD="/x/mmdc"`, `AUTODOC_MERMAID_PARAMS="-p /x/p.json"`, `AUTODOC_MERMAID_JS="/x/m.js"` → those values, params split on whitespace; blank values give defaults. `omit_unrendered_diagrams`: a doctree with two `sphinxcontrib.mermaid.mermaid` nodes, a fake app whose builder name is `latex` and `config.mermaid_cmd` names a missing command → nodes replaced by the note paragraph, one `logger.info` call mentioning `2`; the same doctree with builder `html` is untouched; with a command that exists (`sys.executable`) it is untouched. Integration: build a two-diagram tmp Sphinx project with the `latex` builder using `setup_mermaid` and a missing command → `warning` stream empty, `.tex` contains the note and no `\caption{}` for an empty figure.
- [ ] **Step 3: Run** `pytest scripts/hdl_autodoc/tests/test_mermaid_support.py -q` → FAIL (module missing).
- [ ] **Step 4: Implement** the three functions (`shutil.which` for the command check; replace nodes with `docutils.nodes.paragraph`); in `conf.py` add the extension, `globals().update(mermaid_settings(os.environ))`, and `setup_mermaid(app)` inside the existing `setup`; in `autodoc.mk` add the three variables (default `AUTODOC_MERMAID_CMD ?= mmdc`) to `AUTODOC_ENV`.
- [ ] **Step 5: Run** the new tests and the full suite → PASS; a real `make doc-html` in `example/` still reports no warnings.
- [ ] **Step 6: Commit** `feat: Mermaid extension, settings and PDF fallback`.

### Task 2: Process-level Mermaid blocks

**Files:**
- Modify: `src/scripts/hdl_autodoc/extract_processes.py`
- Test: `src/scripts/hdl_autodoc/tests/test_extract_processes.py` (add)

**Interfaces:**
- Produces: tokens of `{"type": "mermaid", "lines": list[str]}` from `extract_comment_tokens`; `render_mermaid_block(lines: list[str]) -> list[str]`; the process index summary gains a `Mermaid` column after `WaveDrom`.

- [ ] **Step 1: Write failing tests:** a VHDL process comment with `-- .. mermaid::`, `--    :caption: Flow`, blank, and a nested `subgraph` body gives one `mermaid` token whose lines keep relative indentation (the nested line is two spaces deeper than its parent) and contain the `:caption:` line; a body line `-->` style (`--      A --> B`) is intact; an SV `//` block likewise; text before and after the block stays as `text` tokens in order; a wavedrom block immediately followed by a mermaid block gives `wavedrom` then `mermaid`; `render_mermaid_block` returns `[".. mermaid::", "   :caption: Flow", "", "   flowchart LR", ...]` with the blank line preserved; the rendered process page contains the block under *Description*; the summary table has a `Mermaid` header and `✔` for the process that has a block, `—` otherwise; an existing wavedrom-only process is unchanged except the new column.
- [ ] **Step 2: Run** the new tests → FAIL.
- [ ] **Step 3: Implement** the token in `extract_comment_tokens` using the same recognition as wavedrom (`^\s*(?:\.\.|//|#)\s+mermaid\s*::\s*$` after the prefix is stripped) but collecting indented lines with their indentation, then dedenting by the common indent; `render_process_page` and the index table handle the new type and column. Update the existing tests that assert the table columns.
- [ ] **Step 4: Run** → PASS; full suite → PASS.
- [ ] **Step 5: Commit** `feat: Mermaid blocks in process comments`.

### Task 3: Overview description stops at a directive

**Files:**
- Modify: `src/scripts/hdl_autodoc/generate_rst.py` (`extract_entities`, where `brief` is built)
- Test: `src/scripts/hdl_autodoc/tests/test_generate_rst.py` (add)

- [ ] **Step 1: Write failing tests:** header `// Stream filter.\n//\n// .. mermaid::\n//    flowchart LR` over `module m` → `brief == "Stream filter."`; same for a VHDL `--` header; a header whose first two lines are prose and then a directive keeps both prose lines (unchanged); a header that *starts* with a directive falls back to `"<name> module."` / `"<name> entity."`; a prose-only header is unchanged.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement:** while collecting the comment lines, discard everything from the first line beginning `..` onward before taking the first two.
- [ ] **Step 4: Run** → PASS; full suite → PASS.
- [ ] **Step 5: Commit** `fix: overview descriptions stop at the first directive`.

### Task 4: Header diagrams render through the real pipeline

**Files:** Test only: `src/scripts/hdl_autodoc/tests/test_mermaid_pipeline.py` (create)

**Interfaces:** Consumes Tasks 1–3 and `generate_rst.entity_rst` / `sv_module_description`, `extract_processes`.

- [ ] **Step 1: Write the tests** (they should pass once Tasks 1–3 exist; if one fails, the failure is the bug): build tiny Sphinx HTML projects in `tmp_path` from (a) a VHDL file with a header `.. mermaid::` rendered via `vhdl:autoentity` (absolute `vhdl_autodoc_source_path`), (b) the RST that `entity_rst` and `sv_module_description` produce for an SV module header, (c) a process page produced by `render_process_page` — each HTML page contains a `class="mermaid"` element holding the diagram source and its caption; a page with no block has no mermaid element and no mermaid script; the caption survives.
- [ ] **Step 2: Run** `pytest scripts/hdl_autodoc/tests/test_mermaid_pipeline.py -q` → PASS (if any fails, fix the cause in the owning module and note it in the ledger).
- [ ] **Step 3: Commit** `test: Mermaid diagrams render from headers and process comments`.

### Task 5: Documentation, regression check and Mermaid-aware existing examples

**Files:** Modify `README.md`; verify the existing examples.

- [ ] **Step 1: README:** a *Mermaid diagrams* section (how to write a block in VHDL and SV with the examples from the spec; where it is supported; `AUTODOC_MERMAID_JS`, `AUTODOC_MERMAID_CMD`, `AUTODOC_MERMAID_PARAMS` in the Make variables table; the PDF requirements and what happens without `mmdc`; a note that diagrams load Mermaid from a CDN by default); add it to the feature table.
- [ ] **Step 2: Regression check against v3.12.0:** generate `example/`, `example_sv/` and `example_ecp5/` with the tag in a worktree and with this branch (same `PROJECT`, `PYTHONHASHSEED=0`, `SCHEMATICS=0`) and diff every file under `docs/hdl_autodoc/modules` and the top-level pages → identical except the new `Mermaid` column in the process index tables.
- [ ] **Step 3: Verify** full suite and zero-warning HTML builds of the three examples.
- [ ] **Step 4: Commit** `docs: Mermaid support`.

### Task 6: `example_full` — coverage test and a mixed-language flow spike

**Files:** Create `src/scripts/hdl_autodoc/tests/test_example_full.py`, `example_full/Makefile`, `filelist.f`, `ecp5.lpf`, `.gitignore`, `README.md` (stubs)

**Interfaces:** Produces the coverage test every later task turns green; records the synthesis strategy in the ledger and `example_full/README.md`.

- [ ] **Step 1: Write the coverage test** with one assertion group per row of the spec's matrix, parsing `example_full` with the existing parsers (hierarchy: ≥ 3 levels, one module with two parents, support files; ports/generics of VHDL and SV; FSM extraction on a VHDL and an SV module; processes with wavedrom and with mermaid; CDC output has a synchroniser and an async FIFO; reset output; bus groups found among flat ports and `bus_groups.toml` valid; interface ports and an internal interface instance; a `regs_<module>.toml`; testbenches in all three frameworks, linked, one skipped; reports parse with ≥ 1 timing row; ≥ 3 Mermaid blocks across a sequence, a state and a flow diagram). Use `pytest.mark.parametrize` per row so each failure names its feature. Run → FAIL (directory missing).
- [ ] **Step 2: Spike mixed-language synthesis** in the scratchpad with a toy VHDL leaf and SV top and the reverse: load SV with `read_verilog -sv`, elaborate each VHDL unit with `ghdl --std=08 <files> -e <unit>` into the same design, `hierarchy -top`, `synth_ecp5`, `nextpnr-ecp5`. Record which of the spec's three strategies works.
- [ ] **Step 3: Create** the Makefile (`include ../src/autodoc.mk`, an `ecp5-reports` target using the working strategy), `filelist.f` skeleton, `ecp5.lpf`, `.gitignore`, and a README stub stating the strategy.
- [ ] **Step 4: Commit** `test: coverage test for example_full; synthesis strategy`.

### Task 7: `example_full` — clocking, CDC and reset

**Files:** Create under `example_full/src/`: reset synchroniser (VHDL), a second-clock-domain capture module (SV, with parameters), an asynchronous FIFO (VHDL, with generics), and the shared package and interfaces (`*_pkg.sv`, `axis_if.sv`, `axil_if.sv`).

- [ ] **Step 1:** Run the coverage test's CDC, reset, generics/parameters and support-file groups → FAIL.
- [ ] **Step 2:** Write the modules: header comments on every module and port; a 2-flop synchroniser and the FIFO's pointer synchronisers so `extract_cdc` finds domains, crossings and an async FIFO; sync and async resets; at least one `.. mermaid::` header diagram (a flow) in the SV module.
- [ ] **Step 3:** Run the groups → PASS; every file lints/elaborates (`ghdl -a --std=08`, `verilator --lint-only`).
- [ ] **Step 4: Commit** `feat: example_full clocking, CDC and reset`.

### Task 8: `example_full` — control path, registers and bus grouping

**Files:** Create: a VHDL sample controller with a labelled-`case` FSM and wavedrom + process-level Mermaid (`stateDiagram-v2`); an SV AXI4-Lite register block with an `axil_if.slave` port and `registers/regs_<module>.toml`; an SV stream filter with `axis_if` ports, used by two parents; a VHDL APB bridge with flat APB ports; an SV module with flat AXI-Stream ports; `bus_groups.toml` with a custom group.

- [ ] **Step 1:** Run the coverage groups for FSM, processes, wavedrom, mermaid-process, bus grouping, interfaces and registers → FAIL.
- [ ] **Step 2:** Write the modules (header comment on each; a header sequence diagram on the register block showing an AXI-Lite write; the FSM in both languages — add a small SV FSM if the VHDL one is the only one); the stream filter is instantiated from two different parents.
- [ ] **Step 3:** Run the groups → PASS; lint/elaborate each file.
- [ ] **Step 4: Commit** `feat: example_full control path, registers and bus grouping`.

### Task 9: `example_full` — top level and integration

**Files:** Create the VHDL top (with generics, a header flow diagram, and an SV child to exercise the black-box schematic) and complete `filelist.f` in dependency order.

- [ ] **Step 1:** Run the hierarchy group (≥ 3 levels, two-parent module, top detection, mixed language) → FAIL.
- [ ] **Step 2:** Write the top level instantiating the clocking, control and stream modules; connect all ports (ghdl rejects unconnected inputs).
- [ ] **Step 3:** Run the group → PASS; `make doc-hierarchy` prints the expected tree.
- [ ] **Step 4: Commit** `feat: example_full top level`.

### Task 10: `example_full` — testbenches and build reports

**Files:** Create `tb/vunit/` (a VHDL and an SV bench), `tb/cocotb/` (one module, one `skip=True`, one multi-line decorator), `tb/directed/` (a VHDL and an SV bench with `TEST:` markers); `reports/yosys/{yosys.log,stat.txt,nextpnr.log}` from `make ecp5-reports`; `reports/vivado/` sample reports copied from `example/reports/vivado` and adapted only in module names.

- [ ] **Step 1:** Run the testbench and reports coverage groups → FAIL.
- [ ] **Step 2:** Write the testbenches (illustrative, headers on each, a mix of linked and unlinked); run `make ecp5-reports` (OSS CAD Suite on `PATH`) and commit its real output; do not hand-edit the Yosys/nextpnr logs.
- [ ] **Step 3:** Run the groups → PASS.
- [ ] **Step 4: Commit** `feat: example_full testbenches and reports`.

### Task 11: Build everything, verify and release notes

**Files:** Modify `README.md`, `RELEASE.md`; commit generated output for all four examples.

- [ ] **Step 1:** `make doc-coverage` then `make doc-html` and `make doc-pdf` in `example_full/` with zero Sphinx warnings; check the site: all matrix rows visible, Mermaid diagrams present in HTML; with `mmdc` and a puppeteer config the PDF contains the diagram labels; without `mmdc` the PDF build prints no warning.
- [ ] **Step 2:** README: `example_full` under "Try the example" with a one-line description per feature it shows; release notes for the next minor version (Mermaid support, new variables, overview-description fix, the new example, no behaviour change for projects without Mermaid blocks).
- [ ] **Step 3:** Rebuild `example`, `example_sv`, `example_ecp5` and `example_full` (HTML and PDF) from a clean revision; commit the four `_build` trees; full suite → PASS.
- [ ] **Step 4: Commit** `docs: example_full output, release notes`. **Do not tag, push or release without the owner's go-ahead.**
