# Testbenches and Build sections — design

Status: draft for review. Nothing here is built yet.

Marked **[decided]** = said by the project owner. Marked **[call]** = a default chosen
while writing this; change it freely. Marked **[needs input]** = only the owner can supply it.

## Intent

Two new sections in the generated documentation, each switchable from the Makefile the same
way `SCHEMATICS` is:

1. **Testbenches** — a list of the project's testbenches, each with its purpose (taken from
   its header comment or the comments in the code), and a summary of how many tests it
   contains.
2. **Build** — a readable view of what the build leaves behind: utilization, timing and
   other generated reports. It grows the existing *Implementation* section; it is not a
   second, parallel one.

The point: a reader of the docs can see *what is verified* and *what the design costs and
achieves in hardware* without opening a simulator or a report file.

## Goals

- Testbenches are found and described from source only. No simulator run is needed.
- Handles several frameworks in one project: **VUnit**, **cocotb** and **directed**
  (plain HDL) testbenches, each with many files and many tests per file. **[decided]**
- Directed testbenches use a small, documented comment convention to mark individual
  tests. **[decided]**
- Build reads open-source (Yosys + nextpnr, target **Lattice ECP5**) reports first;
  Vivado (Artix UltraScale) follows. **[decided]**
- Where the reports live is a Makefile variable. **[decided]**
- Where the testbenches live is a Makefile variable, default `tb/`, with one subdirectory
  per framework. **[decided]**
- Both sections can be switched off from the Makefile. **[decided]**
- Switched off, or with nothing to show, the docs build exactly as it does today.

## Non-goals (for this design)

- Running simulations, or showing pass/fail, coverage or timing of test runs. (Later,
  optionally, from the JUnit XML that VUnit and cocotb already write.)
- Vivado parsing: power, DRC/methodology, CDC reports, build history. (Phase 2 of Build.)
- Power for the ECP5 flow: there is no mainstream open-source estimator.
- A per-module testbench page. v1 is one top-level page. **[call]**
- Frameworks other than the three above (UVM, OSVVM, etc.).

## Anti-goals (a failure even if it "works")

- A malformed report or testbench file breaks the documentation build. It must warn and
  skip instead.
- A project with no `tb/` and no reports sees new empty pages or sidebar entries.
- New required Python dependencies. Standard library only.
- Existing projects change output when they upgrade without setting anything.

## Makefile interface

All in `src/autodoc.mk`, following the existing pattern (`?=` defaults, overridable on the
command line or before the `include`).

| Variable | Default | Meaning |
|---|---|---|
| `TESTBENCHES` | `1` | `0` removes the Testbenches section |
| `AUTODOC_TB_DIR` | `tb` | Root of the testbenches; one subdirectory per framework |
| `BUILD` | `1` | `0` removes the Build section |
| `AUTODOC_REPORTS_DIR` | `reports` | Root of the report files |

Names follow the existing `AUTODOC_*` / bare-switch split (`SCHEMATICS`,
`ANNOTATED_SOURCE`, `AUTODOC_REGISTERS_DIR`). **[call]**

Wiring:

- **Today** `doc-reports` is a separate, opt-in target and `doc-html` never ingests reports.
  With `BUILD=1` by default, ingestion must run as part of `doc-extract`, so the normal
  `make doc-html` picks it up. `doc-reports` stays as an explicit target for compatibility
  (it still writes its placeholder page when nothing is found). **[call]**
- The reports path is currently hard-coded as `reports` inside the `doc-reports` recipe;
  it becomes `$(AUTODOC_REPORTS_DIR)`.
- Directory values are passed to the scripts as command-line arguments, like the existing
  `extract_reports.py` call. Relative paths are relative to the project root.
- `generate_rst.py` gets `--no-testbenches` and `--no-build` flags (the `--no-source`
  pattern). When a switch is off it **deletes that section's stale generated files** and
  omits its toctree entry, because the toctree is built from "does the generated file
  exist", so leftovers from an earlier run would otherwise reappear.
- `doc-clean-generated` removes the new generated files.

## Testbenches section

### Discovery

```
tb/
├── vunit/      VUnit testbenches (VHDL/SV) — framework from the directory name
├── cocotb/     cocotb tests (Python)
└── directed/   plain HDL testbenches
```

- The framework is taken from the subdirectory name, case-insensitive. No content
  sniffing. **[decided: subdirectory per framework]**
- A subdirectory with another name, or HDL files directly in `tb/`, are treated as
  `directed`, with a console note. **[call]**
- Which files count:
  - `vunit`, `directed`: `.vhd .vhdl .sv .v` files that define an entity or module.
    Files that define none (packages, helpers) are skipped.
  - `cocotb`: `.py` files containing `@cocotb.test`. `run.py`, Makefiles and helpers
    are skipped.
- A missing or empty `AUTODOC_TB_DIR`: **no section, no sidebar entry**, one console
  line. **[call]**
- Testbench files must **not** be listed in `filelist.f`. The hierarchy treats every listed
  module that nothing instantiates as a root, so a listed testbench would become a second
  top level. The README states this; extraction does not try to repair it. **[call]**

### Purpose

- HDL: the comment block directly above the `entity` / `module` (the same rule the
  module descriptions use today; `sv_module_description` already does this for SV).
- cocotb: the module docstring, else the leading comment block.
- No header: the purpose cell shows "—".

### Tests and counting

| Framework | A test is | Purpose from |
|---|---|---|
| VUnit (VHDL) | each `run("name")` in `if/elsif run(...)` | comment directly above, or inline |
| VUnit (SV) | each `` `TEST_CASE("name") `` | comment directly above, or inline |
| cocotb | each `@cocotb.test(...)` function | first line of the function docstring |
| directed | each `TEST:` marker (below) | the text after the marker |

**Directed-test convention (to be documented in the README):** put one comment line before
each scenario, in the file's own comment style:

```vhdl
-- TEST: reset_clears_fifo — FIFO is empty after reset
```
```systemverilog
// TEST: wrap_around — pointers wrap at the last address
```

The separator after the name may be `—`, `-` or `:`. A directed file with no markers counts
as **one test**, named after the testbench, with the header comment as its purpose.
A cocotb test marked `skip=True` is listed and counted as skipped. **[call]**

### Linking to the design

A testbench is linked to the module it exercises so the page can show it next to that
module. **[call]** Two rules, in order: (1) the name matches a module after stripping a
`tb_` / `test_` prefix or `_tb` / `_test` suffix; (2) for HDL files, the module it
instantiates (reusing the instantiation scan in `parse_hierarchy.py`). Otherwise the
testbench is listed as unlinked. cocotb is linked by rule (1) only.

### Output

One generated page, `testbenches/index.rst`, in a new sidebar section **Verification**
(sibling of Design and Implementation/Build). **[call]**

- Summary table: framework | testbenches | tests. Total row.
- One section per framework; per testbench: file, linked module, purpose, test count,
  and a table of tests (name | purpose).

## Build section

### Relationship to Implementation **[call]**

Build **extends** the current Implementation section; it is not a second one. In v1 only
the visible heading and sidebar caption change from "Implementation" to "Build". The file
paths (`synthesis/index.rst`, `modules/<n>/synthesis.rst`) and the `doc-reports` target
stay, so nothing existing breaks. A later cleanup can rename the paths.

If you would rather keep the name "Implementation", it is a one-word change.

### Contents, v1 (open-source, ECP5)

Expected files under `AUTODOC_REPORTS_DIR` (existing layout kept):
`yosys/stat.txt`, `yosys/nextpnr.log`, optionally `yosys/yosys.log`.

1. **Build summary** (new): Yosys and nextpnr versions, device and package, seed, and
   the modification time of the reports. Also "documented at" (git describe at docs
   build time), clearly labelled as the *docs* commit, not necessarily the build's.
   Anything not found in a log is omitted, not shown as an error.
2. **Utilization** (extended): the existing Yosys `stat` per-module tables, plus nextpnr's
   device-utilisation summary (resource | used | available | %), e.g. LUTs, slices, block
   RAM, DSP.
3. **Timing** (existing): per-clock achieved fmax against target from the nextpnr log.
4. **Warnings** (new): counts of warnings and the most frequent messages from the Yosys
   and nextpnr logs.

Stretch, only if the sample reports make it cheap: nextpnr's JSON report
(`--report`) for utilization and critical paths.

### Vivado (phase 2)

The existing Vivado utilization and timing parsers already feed the same data model. Phase
2 adds Vivado's build summary, power (`report_power`), warnings and DRC counts. The parsers
sit behind the existing "detect the tool, return a common model" pattern, so phase 2 adds
parsers and tables, not a new architecture.

### Output

`synthesis/index.rst` becomes the Build page: summary, utilization, timing, warnings, in
that order. With `BUILD=1` but no reports directory: **no section** (as today, where no
`make doc-reports` means no Implementation section). **[call]**

## Pipeline

- `doc-extract` runs, after the existing steps and only when the switch is on:
  `extract_testbenches.py <hierarchy.json> <docs_dir> <tb_dir>` and
  `extract_reports.py <hierarchy.json> <docs_dir> <reports_dir>` (existing, extended).
- Both always re-run (cheap, like register extraction); they are not part of the
  per-module extraction cache.
- New parsing code goes in its own modules (`parse_testbenches.py`, `parse_build_info.py`,
  `parse_warnings.py`); `extract_*.py` orchestrate and write RST, matching how
  `extract_reports.py` uses `parse_utilization.py` and `parse_timing.py`.
- Parse failures print a warning and skip that file. They never abort the build.

## Testing and docs

- Unit tests per parser, with small fixture files checked in under the tests directory;
  tests for the switches (generated files appear, and are **deleted** when switched off).
- `example/` gains a small `tb/{vunit,cocotb,directed}` and sample Yosys/nextpnr ECP5
  reports so the demo shows both sections.
- README: a Testbenches section **including the directed-test convention**, an updated
  Build section, four new rows in the Make variables table, release notes. **[decided:
  the convention must be documented]**
- Backwards compatible: no `tb/`, no reports, or both switches off gives byte-identical
  output to today.

## Phasing

1. Switches and plumbing: variables, `--no-*` flags, stale-file removal, clean target.
2. Testbenches: parsers, page, example, docs. Release.
3. Build refresh (open-source): summary, nextpnr utilization, warnings, rename, docs. Release.
4. Later: Vivado additions, optional JUnit results.

Two minor releases (testbenches, then build). **[call]**

## Left to the builder

- Exact regular expressions for the nextpnr-ecp5 and Yosys log lines. These vary by
  version, so write them against real sample files (see below) and keep them tolerant.
- Table styling and column widths, matching the existing Implementation tables.
- The exact RST and file naming inside `testbenches/`.

## Needs input

- **A real sample set from the ECP5 flow**: a `nextpnr-ecp5` log, the Yosys `stat`
  output (and `yosys.log` if kept), and one example testbench from each of VUnit, cocotb
  and directed. The parsers should be written against these, not against assumed formats.
