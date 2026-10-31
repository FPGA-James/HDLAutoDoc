# Testbenches and Build Sections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a switchable *Testbenches* section (tests counted from source) and widen *Implementation* into a switchable *Build* section (ECP5 open-source reports first), plus an ECP5 example that shows both.

**Architecture:** New pure parsers (`parse_testbenches.py`, `parse_build_info.py`) feed two orchestrators (`extract_testbenches.py`, extended `extract_reports.py`) that write RST under the docs dir. `autodoc.mk` runs them from `doc-extract` behind `TESTBENCHES` / `BUILD`; `generate_rst.py` builds the sidebar from which generated files exist and, when a switch is off, deletes that section's stale files.

**Tech Stack:** Python 3.13 stdlib only (pytest for tests), GNU make, Sphinx/Furo (existing). Example flow: Yosys `synth_ecp5` + `nextpnr-ecp5`.

**Spec:** `docs/superpowers/specs/2026-10-28-testbenches-and-build-sections-design.md`

## Global Constraints

- Variables in `src/autodoc.mk`, `?=` defaults: `TESTBENCHES ?= 1`, `AUTODOC_TB_DIR ?= tb`, `BUILD ?= 1`, `AUTODOC_REPORTS_DIR ?= reports`.
- Testbench framework = subdirectory of `AUTODOC_TB_DIR`: `vunit`, `cocotb`, `directed`, case-insensitive; any other subdirectory, or HDL directly in `tb/`, is `directed` (console note).
- Directed-test marker, in the file's own comment style: `-- TEST: name — purpose` (VHDL), `// TEST: name — purpose` (SV/V). Separator after the name: `—`, `-` or `:`. A directed file with no markers = one test, named after the testbench, purpose = header comment.
- VUnit test = `run("name")` (VHDL) or `` `TEST_CASE("name") `` (SV); cocotb test = `@cocotb.test(...)` function, purpose = first line of its docstring, `skip=True` → listed and counted as skipped.
- Testbench files must not be in `filelist.f`. Missing or empty `AUTODOC_TB_DIR` → no section, no sidebar entry, one console line.
- Sidebar captions: `Design`, `Verification` (testbenches page), `Build` (replaces `Implementation`; file paths `synthesis/index.rst` and `modules/<n>/synthesis.rst` and target `doc-reports` unchanged).
- `BUILD=1` with no reports directory → no section (as today). `make doc-reports` run explicitly still writes its placeholder.
- A parse failure on any tb or report file prints a warning and skips that file; it never aborts the build.
- Standard library only. With no `tb/`, no reports, or both switches off, output is byte-identical to today.
- Paths passed to scripts as command-line arguments, relative to the project root (as `extract_reports.py` does).

## Review Focus

- nextpnr prints `Max frequency for clock` twice per clock (after place, after route): the page shows one row per clock, the last (routed) value. *(Task 4)*
- A directed marker whose separator is `—`, `-` or `:`, or has no purpose, or sits in a VHDL string/block comment, gives the right name and no phantom test. *(Task 2)*
- A cocotb decorator spread over lines, or `@cocotb.test` inside a comment or docstring, is counted correctly (once, or not at all). *(Task 2)*
- A tb or report file that is empty, binary or not valid UTF-8 produces a warning and the rest of the page, not a traceback. *(Tasks 2, 4)*
- Switching a section off after it was on removes its pages and sidebar entry; both off reproduces today's output exactly; `AUTODOC_REPORTS_DIR` works as absolute path, relative path, or with a trailing slash. *(Tasks 1, 5, 7)*

## File Structure

| File | Responsibility |
|---|---|
| `src/autodoc.mk` (modify) | Variables, `doc-extract` steps, flags, clean, help |
| `src/scripts/hdl_autodoc/generate_rst.py` (modify) | Sidebar captions; `--no-testbenches` / `--no-build`; stale-file removal |
| `src/scripts/hdl_autodoc/parse_testbenches.py` (create) | Find testbench files, classify, extract purpose/tests/DUT |
| `src/scripts/hdl_autodoc/extract_testbenches.py` (create) | Render `testbenches/index.rst`, CLI |
| `src/scripts/hdl_autodoc/parse_build_info.py` (create) | Device utilisation block, tool versions, warning summary |
| `src/scripts/hdl_autodoc/parse_timing.py` (modify) | One row per clock for nextpnr |
| `src/scripts/hdl_autodoc/extract_reports.py` (modify) | Build page: summary, utilization, timing, warnings; `--if-present` |
| `example_ecp5/` (create) | SV design (AXI-Stream + AXI-Lite interfaces, registers), `tb/`, real ECP5 reports |
| Tests under `src/scripts/hdl_autodoc/tests/` | One file per new module, plus additions to existing ones |

---

### Task 1: Switches, plumbing and stale-file removal

**Files:**
- Modify: `src/autodoc.mk`, `src/scripts/hdl_autodoc/generate_rst.py`
- Test: `src/scripts/hdl_autodoc/tests/test_generate_rst.py`, create `src/scripts/hdl_autodoc/tests/test_autodoc_mk.py`

**Interfaces:**
- Consumes: existing `index_rst(entities, project_name, hierarchy, has_coverage, modules_with_regs, has_synthesis)`.
- Produces: `index_rst(..., has_synthesis: bool = False, has_testbenches: bool = False) -> str`; generate_rst CLI flags `--no-testbenches`, `--no-build`; `autodoc.mk` variables above plus `AUTODOC_GENRST_FLAGS` extended.

- [ ] **Step 1: Write failing tests.** `test_generate_rst.py`: `test_index_rst_verification_caption_between_design_and_build` (has_testbenches and has_synthesis → captions appear in order `Design`, `Verification`, `Build`; `testbenches/index` and `synthesis/index` listed; `Implementation` no longer appears); update the existing assertion at line ~275 to `"Build"`. `test_no_testbenches_flag_removes_stale_page`: run `generate_rst.py` as a subprocess on a tmp docs dir containing `testbenches/index.rst` with `--no-testbenches` → file gone and `index.rst` has no `Verification`; same for `--no-build` removing `synthesis/index.rst` and `modules/*/synthesis.rst`. `test_autodoc_mk.py`: in a tmp project whose Makefile is `include <abs path to src/autodoc.mk>`, `make -n doc-extract TESTBENCHES=0 BUILD=0` output contains `--no-testbenches` and `--no-build`; with defaults it contains neither and contains `extract_testbenches.py` and `extract_reports.py ... --if-present`; `make -n doc-reports` never contains `--no-build`; `make -n doc-extract AUTODOC_TB_DIR=x/ AUTODOC_REPORTS_DIR=/abs/r` shows both values.
- [ ] **Step 2: Run** `pytest scripts/hdl_autodoc/tests/test_generate_rst.py scripts/hdl_autodoc/tests/test_autodoc_mk.py -q` → FAIL.
- [ ] **Step 3: Implement.** `index_rst` gains `has_testbenches`; `main` of generate_rst parses `--no-testbenches` / `--no-build` (same filtering as `--no-source`), deletes `docs_dir/testbenches/`, or `docs_dir/synthesis/` plus each `modules/*/synthesis.rst`, when the flag is given, *before* computing `has_*`. In `autodoc.mk`: add the four variables; `AUTODOC_GENRST_FLAGS` appends the two flags via `$(if $(filter 0,$(X)),--flag)`; change `doc-reports` to use `$(AUTODOC_REPORTS_DIR)` and not add `--no-build`; in `doc-extract`, before the final `generate_rst.py` call, add `$(if $(filter 1,$(TESTBENCHES)),$(PYTHON) .../extract_testbenches.py $(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) $(AUTODOC_TB_DIR))` and the `extract_reports.py ... $(AUTODOC_REPORTS_DIR) --if-present` equivalent for `BUILD`; add `testbenches/` to `doc-clean-generated`; add help lines.
- [ ] **Step 4: Run** the same tests → PASS; `pytest -q` whole suite → PASS.
- [ ] **Step 5: Commit** `feat: TESTBENCHES/BUILD switches, tb and reports directory variables`.

### Task 2: Testbench parsers

**Files:**
- Create: `src/scripts/hdl_autodoc/parse_testbenches.py`
- Test: `src/scripts/hdl_autodoc/tests/test_parse_testbenches.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) TestCase(name: str, purpose: str = "", skipped: bool = False)`
  - `@dataclass Testbench(name: str, file: str, framework: str, purpose: str, tests: list[TestCase], dut: str | None)`
  - `framework_for_dir(dirname: str) -> str`
  - `parse_vunit_hdl(text: str, suffix: str) -> list[TestCase]`
  - `parse_cocotb(text: str) -> tuple[str, list[TestCase]]` (module purpose, tests)
  - `parse_directed(text: str, suffix: str) -> list[TestCase]` (empty if no markers)
  - `header_purpose(text: str, suffix: str) -> str` (comment block directly above the first `entity`/`module`)
  - `link_dut(tb_name: str, text: str, suffix: str, module_names: set[str]) -> str | None`
  - `discover_testbenches(tb_dir: Path, module_names: set[str]) -> list[Testbench]`

- [ ] **Step 1: Write failing tests** (fixtures as inline strings): VUnit VHDL `if run("reset") then ... elsif run("wrap") then` → two tests, purposes from the comment above each; VUnit SV with `` `TEST_CASE("a") `` ×2; cocotb with `@cocotb.test()`, a multi-line `@cocotb.test(\n timeout_time=10,\n timeout_unit="ns")`, a `skip=True` test, docstring purposes, and a commented-out `# @cocotb.test()` plus one inside a docstring → counted exactly the real ones; directed markers with `—`, `-`, `:`, a marker with no purpose, one inside a VHDL string and one inside `/* */` → only real markers; directed file without markers → `parse_directed` returns `[]` and `discover_testbenches` yields one test named after the testbench with the header purpose; `framework_for_dir("VUnit") == "vunit"`, `"unit_tests"` → `"directed"`; `link_dut`: `tb_fifo`/`fifo_tb`/`test_fifo` link to `fifo`; a file instantiating `fifo` links even if named `bench`; no match → `None`; `discover_testbenches` on a tmp tree skips packages, `run.py`, Makefiles, an empty file, a binary file and a non-UTF-8 file (no exception; a warning on stderr), and returns testbenches sorted by framework then name.
- [ ] **Step 2: Run** `pytest scripts/hdl_autodoc/tests/test_parse_testbenches.py -q` → FAIL (module missing).
- [ ] **Step 3: Implement** the functions above. Read files with `errors="replace"` and skip files containing NUL; strip comments/strings before searching for `run(` / `` `TEST_CASE `` / decorators but search the *raw* text for `TEST:` markers line by line, ignoring lines whose comment start sits inside a string or block comment. Reuse `parse_hierarchy.extract_instantiations` for DUT rule 2 and `generate_rst.sv_module_description`-style logic for the header block.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: testbench parsers for VUnit, cocotb and directed`.

### Task 3: Testbenches page and wiring

**Files:**
- Create: `src/scripts/hdl_autodoc/extract_testbenches.py`
- Test: `src/scripts/hdl_autodoc/tests/test_extract_testbenches.py`

**Interfaces:**
- Consumes: Task 2's `discover_testbenches`, `Testbench`, `TestCase`; Task 1's `index_rst` caption and `autodoc.mk` call `extract_testbenches.py <hierarchy.json> <docs_dir> <tb_dir>`.
- Produces: `testbenches_rst(tbs: list[Testbench]) -> str`; `main(hierarchy_path: Path, docs_dir: Path, tb_dir: Path) -> bool` (True when a page was written).

- [ ] **Step 1: Write failing tests:** `testbenches_rst` contains a summary table (framework | testbenches | tests, plus Total row), a section per framework, per testbench its file, linked module as `:doc:` link (or "—" when `dut` is None), purpose, test count, and a test table (name | purpose; skipped tests marked "skipped"); a testbench with 0 tests shows "no tests found"; `main` returns False and writes nothing when `tb_dir` is missing or has no testbench files (and prints one line), writes `docs_dir/testbenches/index.rst` otherwise; a second run with the directory emptied removes the stale page; a parse warning from one bad file does not stop the others.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `testbenches_rst` and `main` (module names from `hierarchy["modules"]`); CLI usage line like `extract_reports.py`; exit 0 always.
- [ ] **Step 4: Run** new tests and full suite → PASS.
- [ ] **Step 5: Commit** `feat: Testbenches page`.

### Task 4: Build data: device utilisation, versions, warnings, timing dedupe

**Files:**
- Create: `src/scripts/hdl_autodoc/parse_build_info.py`
- Modify: `src/scripts/hdl_autodoc/parse_timing.py` (`_parse_nextpnr`)
- Test: `src/scripts/hdl_autodoc/tests/test_parse_build_info.py`, `src/scripts/hdl_autodoc/tests/test_parse_timing.py`

**Interfaces:**
- Produces:
  - `@dataclass ResourceUse(name: str, used: int, available: int, percent: int)`
  - `@dataclass BuildInfo(yosys_version: str | None, nextpnr_version: str | None, device: str | None, report_time: datetime | None)`
  - `@dataclass WarningSummary(total: int, top: list[tuple[str, int]])`
  - `parse_device_utilisation(nextpnr_log: str) -> list[ResourceUse]`
  - `parse_build_info(yosys_log: str | None, nextpnr_log: str | None, newest_mtime: float | None) -> BuildInfo`
  - `summarise_warnings(*logs: str, top_n: int = 5) -> WarningSummary`
  - `device_class(resources: list[ResourceUse]) -> str | None`

Real formats (captured from `nextpnr-0.8-108` and Yosys 0.56): `Info: \t          TRELLIS_FF:      16/  24288     0%` inside a block starting `Info: Device utilisation:`; `Info: Max frequency for clock '$glbnet$clk$TRELLIS_IO_IN': 346.86 MHz (PASS at 100.00 MHz)` printed after placement and again after routing; `Warning: IO 'q[15]' is unconstrained in LPF and will be automatically placed`; Yosys log header `Yosys 0.56+186 (git sha1 ...)`; the nextpnr banner `"nextpnr-ecp5" -- Next Generation Place and Route (Version nextpnr-0.8-108-gca4f727f)` is on stdout and **absent** from a `--log` file.

- [ ] **Step 1: Write failing tests:** utilisation block → rows in order, zero-use rows kept, parsing stops at the first non-block line; `parse_timing` test: a log containing both lines for one clock → one `ClockTiming` with the *second* (routed) fmax, and two clocks stay two rows (put the real two-line excerpt above in the test); `parse_build_info` reads Yosys version, nextpnr version when the banner is present and `None` when absent; `summarise_warnings` groups messages that differ only by quoted names/digits (`IO 'q[15]'…` ×18 → one entry with count 18), counts `Warning:`/`WARNING:` lines, returns `top` sorted by count then text, handles empty input; `device_class` maps `TRELLIS_FF` available `24288` → `"ECP5 25k class"` (also 43848→45k, 83640→85k) and returns `None` otherwise.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** with `re`; for `_parse_nextpnr` keep a dict keyed by cleaned clock name, later matches overwrite earlier ones, preserve first-seen order.
- [ ] **Step 4: Run** → PASS (existing timing tests unchanged).
- [ ] **Step 5: Commit** `feat: parse nextpnr utilisation, versions and warnings; one timing row per clock`.

### Task 5: Build page

**Files:**
- Modify: `src/scripts/hdl_autodoc/extract_reports.py`
- Test: `src/scripts/hdl_autodoc/tests/test_extract_reports.py`

**Interfaces:**
- Consumes: Task 4 functions; existing `parse_utilization`, `parse_timing`, `synthesis_index_rst(util_modules, util_tool, clocks, timing_tool)`.
- Produces: `synthesis_index_rst(..., build_info: BuildInfo | None = None, resources: list[ResourceUse] | None = None, warnings: WarningSummary | None = None) -> str` (title `Build`; old call shape still valid); `main(hierarchy_path, docs_dir, reports_dir, if_present: bool = False) -> bool`; CLI `extract_reports.py <hierarchy.json> <docs_dir> <reports_dir> [--if-present]`.

- [ ] **Step 1: Write failing tests:** page order is Build summary → Utilization → Timing → Warnings; summary lists only the facts found (no "None"); a "device utilisation" table appears when nextpnr resources exist and the Yosys per-module table is kept; warnings table shows count and top messages; `--if-present` with a missing or empty reports dir writes nothing and returns False, without the flag the placeholder is still written; reports dir given as absolute path, relative path and with trailing slash all work; only `stat.txt` present, or only `nextpnr.log`, or an empty file, or a non-UTF-8 log → renders what exists, no traceback; placeholder text says Build.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Read logs from `reports_dir/yosys/{stat.txt,nextpnr.log,yosys.log}` (existing `vivado/` handling untouched); `report_time` = newest mtime of files read; "documented at" = `git describe --always --dirty` run in the docs dir's repo, omitted if git is unavailable.
- [ ] **Step 4: Run** → PASS; full suite → PASS.
- [ ] **Step 5: Commit** `feat: Build page with summary, nextpnr utilisation and warnings`.

### Task 6: ECP5 example (design, registers, testbenches, real reports)

**Files:**
- Create: `example_ecp5/Makefile`, `filelist.f`, `README.md`, `src/{axis_if,axil_if,axil_regs,stream_filter,top}.sv`, `registers/regs_axil_regs.toml`, `tb/vunit/tb_stream_filter.sv`, `tb/cocotb/test_axil_regs.py`, `tb/directed/tb_top.sv`, `reports/yosys/{stat.txt,nextpnr.log,yosys.log}`, `example_ecp5/ecp5.lpf`
- Test: `src/scripts/hdl_autodoc/tests/test_example_ecp5.py`

**Interfaces:** consumes everything above; produces the demo project.

Design: `axis_if` and `axil_if` interfaces with `master`/`slave` modports; `axil_regs` (`axil_if.slave s_axil`, four registers: `ctrl` with `enable`/`clear`, `status` read-only, `threshold`, `scratch`) described by `registers/regs_axil_regs.toml` in the same hdl-registers format as `example/registers/regs_cfg_sync.toml`; `stream_filter` (`axis_if.slave s_axis`, `axis_if.master m_axis`, forwards bytes at or above the threshold); `top` instantiates both and wires the interfaces. Comments on every module and port (headers, preceding-line, inline). Testbenches: VUnit SV with three `` `TEST_CASE `` blocks, cocotb with three tests (one `skip=True`, one multi-line decorator), directed with two `// TEST:` markers. Example `Makefile` = `include ../src/autodoc.mk` plus an `ecp5-reports` target running `yosys -l ... synth_ecp5 -json`, `tee -o stat.txt stat`, and `nextpnr-ecp5 --25k --package CABGA256 --lpf ecp5.lpf --log ...`; the generated reports are committed, produced by running that target (not hand-written).

- [ ] **Step 1: Write failing test** `test_example_ecp5.py`: `discover_testbenches(example_ecp5/tb, {...modules...})` returns 3 testbenches / 8 tests (1 skipped) with `dut` set for each; `parse_device_utilisation` on the committed `nextpnr.log` returns a non-empty list including `TRELLIS_FF`; `parse_timing` returns exactly one row per clock; `extract_ports_sv` with the interface names finds `s_axil`, `s_axis`, `m_axis`.
- [ ] **Step 2: Run** → FAIL (files missing).
- [ ] **Step 3: Create the files; run** `make ecp5-reports` (PATH must include the OSS CAD Suite `bin`) and commit its output.
- [ ] **Step 4: Run** the test → PASS; then `make doc-venv && make doc-html` from `example_ecp5/`: build succeeds with no warnings; the HTML has **Verification** (3 testbenches, 8 tests), **Build** (summary, utilization, one timing row, warnings), the block pages show interface ports and the interfaces box, and the register page lists the four registers. Remove generated `docs/` before committing.
- [ ] **Step 5: Commit** `feat: example_ecp5 with AXI-Stream, AXI-Lite, registers, testbenches and reports`.

### Task 7: Documentation and release

**Files:** Modify `README.md`, `RELEASE.md`; test none (verified by reading and by the build above).

- [ ] **Step 1: README:** a Testbenches section **documenting the directed-test marker convention exactly as in Global Constraints**, the `tb/<framework>/` layout and the rule that testbenches stay out of `filelist.f`; a Build section (expected files under `AUTODOC_REPORTS_DIR`, what each part shows, Vivado coming); four rows added to the Make variables table; `example_ecp5` mentioned under "Try the example"; note that "Implementation" is now "Build".
- [ ] **Step 2: Release notes** for one minor version, v3.12.0, in `RELEASE.md` and the README, covering both sections, the four variables, the `Implementation` → `Build` rename, and backwards compatibility. (The spec suggested two releases; one is simpler because the example needs both sections.)
- [ ] **Step 3: Verify:** full suite passes; `make doc-html` in `example/`, `example_sv/` and `example_ecp5/` succeed; for `example/` the generated block and entity RST is byte-identical to the previous release (the `cmp.sh` approach used for earlier releases).
- [ ] **Step 4: Commit** `docs: testbenches and build sections`. **Tagging, pushing and creating GitHub releases happen only on the owner's go-ahead.**
