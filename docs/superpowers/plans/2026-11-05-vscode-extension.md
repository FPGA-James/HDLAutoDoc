# HDL AutoDoc VS Code Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A VS Code extension that shows a live, per-file documentation preview for the active VHDL/SystemVerilog file, packaged as a self-contained `.vsix`.

**Architecture:** A new stdlib-only Python command (`autodoc_json.py`) turns file text into one JSON document using the existing extractors. A TypeScript extension spawns it with `python3`, and a webview renders the JSON, bundling WaveDrom, Mermaid and viz-js locally. The `.vsix` embeds a copy of the Python scripts, so there is no `pip install`.

**Tech Stack:** Python 3.11+ (stdlib only) and pytest; TypeScript, esbuild, `@vscode/vsce`, `node:test`; wavedrom, mermaid, `@viz-js/viz` bundled into the webview; puppeteer-core + system Chrome only for visual checks, not as a dependency.

**Spec:** `docs/superpowers/specs/2026-11-05-vscode-extension-design.md`

## Global Constraints

- Existing output, make targets and variables do not change; every Python change is additive (new function, new dict key).
- The Python side uses only the standard library (no third-party import in `src/scripts/hdl_autodoc`); ruff (`ruff.toml`) must pass.
- Python 3.11+; Node 20+ for the extension build.
- Nothing in the webview is fetched from a network (CSP: no remote scripts or styles).
- The `.vsix` contains `src/scripts/hdl_autodoc` without `tests/` and without `__pycache__`.
- No publishing; the deliverable is a `.vsix`. Do not tag, push or release without the owner's go-ahead.
- Tests first: every behaviour change has a test watched failing before it passes. Python tests under `src/scripts/hdl_autodoc/tests/`; extension tests with `node:test` under `vscode/test/`.
- Extension version equals the tool version in `RELEASE.md` (a test enforces it).

## Review Focus

- A buffer with unsaved edits is documented, not the file on disk (text goes on stdin).
- A file that does not parse yields partial JSON plus `warnings`, never a crash or empty panel.
- An active editor that is not VHDL/SystemVerilog leaves the last panel content and says so; it does not error.
- Rapid typing: only the newest response is rendered; a slow older one never overwrites it.
- `python3` missing or older than 3.11: a message naming the `hdlAutodoc.pythonPath` setting and the version needed.
- CRLF line endings and non-ASCII text in comments give the same line numbers and no mojibake.
- A very large file (10k lines) refreshes without freezing the editor (spawn is async, with a timeout).
- Theme change (light/dark) re-renders diagrams with theme colours.
- Panel closed and reopened; two windows; a workspace with no `filelist.f` and no interface files.
- Webview content-security policy blocks inline script without the nonce.

---

### Task 1: line numbers on ports, generics and parameters

**Files:**
- Modify: `src/scripts/hdl_autodoc/extract_block.py`
- Test: `src/scripts/hdl_autodoc/tests/test_extract_block.py`

**Interfaces:**
- Consumes: existing `extract_ports_vhdl`, `extract_generics_vhdl`, `extract_ports_sv`, `extract_params_sv`.
- Produces: each returned dict gains `"line": int` (1-based line of the declaration in the text passed in); all existing keys unchanged.

- [ ] **Step 1: Write failing tests** `test_vhdl_ports_and_generics_carry_their_line_number`, `test_sv_ports_and_params_carry_their_line_number`, `test_line_numbers_count_from_the_start_of_the_file_not_the_port_list`, `test_crlf_source_gives_the_same_line_numbers`. Each uses a small source with a header comment and blank lines before the declarations and asserts exact line numbers.
- [ ] **Step 2: Run them and watch them fail** (`KeyError: 'line'`).
- [ ] **Step 3: Implement.** VHDL: add `_extract_paren_section_at(text, keyword) -> tuple[str, int]` returning the section and the 1-based line it starts on (`_extract_paren_section` stays and calls it); add `idx + first_line - 1`. SV: `idx + 1`. Interface-typed ports get `line` too.
- [ ] **Step 4: Run the new tests and the whole suite.** Expected: pass, no other test changes.
- [ ] **Step 5: Commit** `feat: line numbers on ports, generics and parameters`.

### Task 2: reusable CDC and reset analysis

**Files:**
- Modify: `src/scripts/hdl_autodoc/extract_cdc.py`, `src/scripts/hdl_autodoc/extract_reset.py`
- Test: `src/scripts/hdl_autodoc/tests/test_extract_cdc.py`, `src/scripts/hdl_autodoc/tests/test_extract_reset.py`

**Interfaces:**
- Produces: `analyse_cdc(text: str, is_vhdl: bool) -> dict` returning `{"domains": {clock: [process, ...]}, "crossings": [{signal, src_clock, dst_clock, synchronized}], "dual_clock_instances": [{instance, component, clocks}]}`; `analyse_reset(text: str, is_vhdl: bool) -> dict` returning `{"processes": [{label, clock, reset, style}], "domains": {reset_or___none__: [process labels]}, "crossings": [...]}` (crossing shape as `find_reset_crossings` returns today).
- The `__main__` blocks call these and write exactly the same files as before.

- [ ] **Step 1: Characterisation tests** (pass against current code): for the four example projects' source files, run each script's CLI into a temp directory and store the produced `.rst`/`.dot` text in the test as the expected output (a golden-file test over `example*/src/*`); name `test_cli_output_is_unchanged_by_the_refactor`.
- [ ] **Step 2: Write failing tests** for `analyse_cdc` and `analyse_reset` on `example_full/src/sample_capture.sv` (two domains, a two-flop synchronised crossing `capture_en`, one dual-clock instance) and a single-domain file (`domains` has one key, `crossings == []`).
- [ ] **Step 3: Run and watch fail** (`ImportError`).
- [ ] **Step 4: Implement** by moving the analysis code out of each `__main__` into the new functions; the mains keep only argument handling and writing.
- [ ] **Step 5: Run the golden tests and the whole suite.** Expected: pass unchanged.
- [ ] **Step 6: Commit** `refactor: analyse_cdc and analyse_reset as functions`.

### Task 3: `autodoc_json.py`

**Files:**
- Create: `src/scripts/hdl_autodoc/autodoc_json.py`
- Test: `src/scripts/hdl_autodoc/tests/test_autodoc_json.py`

**Interfaces:**
- Consumes: Task 1 `line` fields; Task 2 `analyse_cdc`/`analyse_reset`; `extract_block`, `extract_fsm`, `extract_processes`, `detect_buses.group_ports`, `sv_interfaces.collect_interfaces`, `hdl_scan.scan_*_instances`, `generate_rst.sv_module_description`.
- Produces: `build_document(text: str, language: str, support_files: list[Path] = (), bus_groups: Path | None = None) -> dict` following the JSON contract in the spec (`language`, `module`, `generics`, `ports`, `instances`, `fsm`, `processes`, `cdc`, `reset`, `warnings`), and a CLI: `python autodoc_json.py --language vhdl|systemverilog [--support FILE ...] [--bus-groups FILE]` reading the source from stdin and writing JSON to stdout. Exit status 0 even when warnings exist; non-zero only for usage errors. `ports[].group` is the bus-group label or `null`. `fsm.dot` is the Graphviz source the site would draw. `processes[].description` is the text blocks joined; `wavedrom` and `mermaid` are lists of the block texts.

- [ ] **Step 1: Write failing tests:**
  - `test_vhdl_document_has_module_ports_generics_with_lines` (a VHDL entity with header comment);
  - `test_systemverilog_document_with_interface_ports_and_support_file` (interface port appears with `kind == "interface"` only when `--support` names the interface file);
  - `test_ports_are_grouped_with_bus_groups_toml` (an AXI4-Stream flat group gets `group`);
  - `test_processes_carry_wavedrom_and_mermaid_blocks_and_their_line`;
  - `test_fsm_has_states_transitions_and_dot` (use `example/src/traffic_light.vhd`), `fsm is None` without an FSM;
  - `test_cdc_and_reset_sections_present_for_a_two_clock_file`;
  - `test_a_file_that_does_not_parse_returns_warnings_not_an_exception` (garbage text, truncated entity);
  - `test_cli_reads_stdin_and_writes_valid_json` (subprocess, with CRLF input and non-ASCII comment text);
  - `test_every_example_file_produces_a_serialisable_document` (all `example*/src/*.sv|vhd`; `json.dumps` succeeds; port count equals `len(extract_ports_*)`).
- [ ] **Step 2: Run and watch them fail** (`ModuleNotFoundError`).
- [ ] **Step 3: Implement** `build_document` by language, catching exceptions per section into `warnings` (a failing section is `null`/empty, the rest still returned); VHDL module description is the contiguous `--` block above `entity` up to the first RST directive; the CLI wrapper.
- [ ] **Step 4: Run the new tests and the whole suite; `ruff check`.** Expected: pass.
- [ ] **Step 5: Commit** `feat: autodoc_json - one JSON document per source file`.

### Task 4: extension scaffold and `.vsix` build

**Files:**
- Create: `vscode/package.json`, `vscode/tsconfig.json`, `vscode/esbuild.mjs`, `vscode/.vscodeignore`, `vscode/Makefile`, `vscode/src/extension.ts`, `vscode/README.md`, `vscode/test/vsix.test.mjs`, `vscode/test/version.test.mjs`
- Modify: `.gitignore` (`vscode/node_modules`, `vscode/dist`, `vscode/python`, `*.vsix`)

**Interfaces:**
- Produces: `npm test` (node:test), `npm run build` (bundles `src/extension.ts` to `dist/extension.js`, the webview to `dist/webview.js`), `make -C vscode vsix` producing `vscode/hdl-autodoc-<version>.vsix` that contains `python/hdl_autodoc/*.py` (copied from `src/scripts/hdl_autodoc`, excluding `tests/` and `__pycache__`), `dist/extension.js`, `dist/webview.js`, `package.json`. `package.json` declares the command `hdlAutodoc.showDocumentation`, activation on that command, settings `hdlAutodoc.pythonPath` (default `python3`) and `hdlAutodoc.refreshDelayMs` (default 400), `engines.vscode`, `publisher` (placeholder), `version`.

- [ ] **Step 1: Write failing tests:** `vsix.test.mjs` builds the vsix and asserts it is a zip listing the files above and none under `tests/`; `version.test.mjs` asserts `package.json` version equals the top version in `RELEASE.md`.
- [ ] **Step 2: Run them and watch them fail** (no project yet).
- [ ] **Step 3: Implement** the scaffold; `extension.ts` activates and registers the command with a placeholder message; `Makefile` target `vsix` copies the scripts then runs `vsce package --no-dependencies`.
- [ ] **Step 4: Run `npm ci && npm test` and `make vsix`.** Expected: pass; a `.vsix` is produced.
- [ ] **Step 5: Commit** `feat: vscode extension scaffold and vsix build`.

### Task 5: Python runner

**Files:**
- Create: `vscode/src/runner.ts`, `vscode/test/runner.test.mjs`, `vscode/test/fixtures/` (fake interpreters)

**Interfaces:**
- Produces: `runAutodocJson(opts: {python: string; script: string; language: 'vhdl'|'systemverilog'; text: string; support: string[]; busGroups?: string; timeoutMs: number; signal?: AbortSignal}): Promise<RunResult>` where `RunResult = {ok: true; doc: Document} | {ok: false; kind: 'no-python'|'old-python'|'timeout'|'aborted'|'failed'|'bad-json'; message: string}`; `Document` is the TypeScript type of the JSON contract (`vscode/src/types.ts`).

- [ ] **Step 1: Write failing tests** with fake interpreters (small scripts): success path returns the parsed document; missing interpreter gives `no-python` naming `hdlAutodoc.pythonPath`; an interpreter reporting 3.9 gives `old-python`; a hanging one gives `timeout`; an aborted signal kills the child and gives `aborted`; non-zero exit gives `failed` with stderr; non-JSON stdout gives `bad-json`; the source text reaches the child unchanged (CRLF, non-ASCII).
- [ ] **Step 2: Run and watch fail.**
- [ ] **Step 3: Implement** with `child_process.spawn`, stdin write, version probe (`python -c "import sys; print(sys.version_info[:2])"`, cached per interpreter), timeout and abort handling.
- [ ] **Step 4: Run `npm test`.** Expected: pass.
- [ ] **Step 5: Commit** `feat: python runner for the extension`.

### Task 6: panel renderer

**Files:**
- Create: `vscode/src/render.ts`, `vscode/src/panel.css`, `vscode/test/render.test.mjs`

**Interfaces:**
- Consumes: `Document` type.
- Produces: `renderDocument(doc: Document): string` (HTML fragment: sections Header, Generics, Ports (grouped), Instances, State machine, Processes, Clock domains, Reset domains, Warnings); `renderMessage(kind, text): string`; every element that maps to a source line carries `data-line="N"`; waveform and diagram placeholders are `<div class="wavedrom" data-source="...">`, `<pre class="mermaid">`, `<div class="fsm" data-dot="...">`. CSS uses only VS Code variables (`--vscode-*`).

- [ ] **Step 1: Write failing tests:** HTML-escapes every text field (a port named `<b>`), omits empty sections, renders bus groups as a heading with their ports, emits `data-line`, renders warnings, renders the FSM placeholder only when `fsm` is non-null, escapes quotes in `data-*` attributes, and snapshot-checks `example_full` `sample_capture` JSON (generated once by `autodoc_json.py` and stored under `test/fixtures/`).
- [ ] **Step 2: Run and watch fail.**
- [ ] **Step 3: Implement** the renderer as pure string building.
- [ ] **Step 4: Run `npm test`.** Expected: pass.
- [ ] **Step 5: Commit** `feat: render the documentation panel`.

### Task 7: webview client and bundled libraries

**Files:**
- Create: `vscode/webview/main.ts`; modify `vscode/esbuild.mjs`, `vscode/package.json`
- Test: `vscode/test/webview-visual.md` (procedure) and a node script `vscode/test/visual-check.mjs` (not part of `npm test`)

**Interfaces:**
- Produces: a webview bundle that, on a `render` message `{html}`, replaces the content, then renders WaveDrom (`wavedrom` package), Mermaid (`mermaid`, theme dark/default from `document.body.classList`) and the FSM (`@viz-js/viz` → inline SVG); posts `{type:'goto', line}` when an element with `data-line` is clicked; re-renders diagrams when the theme class changes.

- [ ] **Step 1: Write the visual check** `visual-check.mjs`: builds the bundle, loads a static page with the bundle and the `example_full` `sample_capture` and `sample_ctrl` JSON in headless Chrome (puppeteer-core; path from `CHROME`), and asserts the page has an `svg` for each waveform, Mermaid diagram and the FSM, and no console errors; saves screenshots.
- [ ] **Step 2: Run it and watch it fail** (no bundle).
- [ ] **Step 3: Implement** `main.ts` and the esbuild webview entry (IIFE, no remote URLs); install `wavedrom`, `mermaid`, `@viz-js/viz`.
- [ ] **Step 4: Run the visual check; read the screenshots** (light and dark). Expected: waveforms, both Mermaid diagrams and the FSM visible.
- [ ] **Step 5: Commit** `feat: webview client with bundled wavedrom, mermaid and viz-js`.

### Task 8: extension host

**Files:**
- Modify: `vscode/src/extension.ts`; create `vscode/src/session.ts`, `vscode/src/support.ts`, `vscode/test/session.test.mjs`, `vscode/test/support.test.mjs`

**Interfaces:**
- Consumes: Tasks 5-7.
- Produces: `Session` (pure logic, no `vscode` import): `class Session { constructor(deps: {run: RunFn; now: () => number; delayMs: number; post: (msg) => void}); update(snapshot: {uri: string; languageId: string; text: string}): void; dispose(): void }` implementing debounce, "newest result wins" (a stale response is dropped), abort of the previous run, and the messages sent to the panel (`render` with html, or a message for non-HDL files / runner errors). `findSupportFiles(readDir, readFile, root): Promise<string[]>` returns workspace `*.sv`/`*.svh` paths that define an `interface` (cached by path+mtime). `extension.ts` is thin glue: command opens one webview panel beside the editor (with CSP and nonce, `localResourceRoots` limited to `dist`), listens to `onDidChangeActiveTextEditor`, `onDidSaveTextDocument` and `onDidChangeTextDocument`, maps language ids (`vhdl`; `systemverilog`, `verilog`), passes `bus_groups.toml` if found at `docs/hdl_autodoc/bus_groups.toml`, and reveals the line for `goto` messages.

- [ ] **Step 1: Write failing tests** for `Session`: debounce collapses rapid updates into one run; a slow older response arriving after a newer one is ignored; the older run is aborted; a non-HDL snapshot posts the "not an HDL file" message and keeps the panel; a runner failure posts its message; `dispose` stops pending work. For `findSupportFiles`: finds interface files, skips others, reuses cache while mtime is unchanged.
- [ ] **Step 2: Run and watch fail.**
- [ ] **Step 3: Implement** `Session`, `findSupportFiles` and the glue.
- [ ] **Step 4: Run `npm test`, `make vsix`, then load the panel HTML produced by the real `autodoc_json.py` for `example_full/src/sample_capture.sv` through the visual check once more.** Expected: pass.
- [ ] **Step 5: Commit** `feat: extension host - live panel for the active file`.

### Task 9: CI, docs, release notes

**Files:**
- Modify: `.github/workflows/ci.yml`, `README.md`, `RELEASE.md`, `vscode/README.md`
- Test: existing `vscode/test/version.test.mjs`

**Interfaces:**
- Produces: a `vscode` CI job (Node 22: `npm ci`, `npm test`, `make vsix`, upload the `.vsix` as an artifact named `hdl-autodoc-vsix`); a README section "VS Code extension" (what it shows, install with `code --install-extension <file>`, settings, how to build, no-publish note, what is not included); release notes for the next minor version.

- [ ] **Step 1: Update version and notes** so the version test passes with the new release number.
- [ ] **Step 2: Write the docs and the CI job.**
- [ ] **Step 3: Run the whole Python suite, `ruff check`, `npm test`, `make vsix` locally.** Expected: all pass; the `.vsix` installs (`unzip -l` lists the expected files).
- [ ] **Step 4: Commit** `docs: vscode extension, release notes; ci builds the vsix`.
- [ ] **Step 5 (owner):** install the `.vsix` in VS Code, open `example_full/src/sample_capture.sv` and `sample_ctrl.vhd`, and confirm the panel as described in `vscode/test/webview-visual.md`. The assistant cannot run VS Code here and says so.
