# Coverage Report — Design Spec

**Date:** 2026-06-16
**Status:** Approved

---

## Overview

A `make coverage` target that inspects the extraction output for each module and produces two things: a compact terminal table printed at the end of the script, and a `coverage.rst` page in the Sphinx docs with a coloured HTML table linking each module to its documentation.

---

## Architecture & Data Flow

A single new script `scripts/hdl_autodoc/generate_coverage.py`:

1. Reads `hierarchy.json` to get the module list and ordering
2. For each module, inspects its `modules/<name>/` directory to compute 5 coverage signals
3. Prints the compact terminal table (stdout)
4. Writes `coverage.rst` into `docs/hdl_autodoc/`

`generate_rst.py` is updated to include `coverage` in the generated `index.rst` toctree (alongside `overview`, `hierarchy`).

New Makefile target:
```makefile
coverage: hierarchy
    python $(AUTODOC_SCRIPTDIR)/generate_coverage.py \
        $(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR)
```

- Runs independently — requires only `hierarchy.json` + a completed `make extract`
- `make html` does **not** depend on `coverage` (opt-in)
- `clean-generated` gets: `rm -f $(AUTODOC_SOURCEDIR)/coverage.rst`

---

## Coverage Signals

Each signal is detected by inspecting `docs/hdl_autodoc/modules/<name>/`:

| Signal | Detection method |
|---|---|
| **FSM** | `<name>.dot` exists |
| **Processes** | Count of `processes/p_*.rst` files |
| **CDC crossings** | `<name>_cdc.rst` exists AND contains `→` |
| **Reset crossings** | `<name>_reset.rst` exists AND contains `crossing` (case-insensitive) |
| **Ports** | `<name>_block.rst` exists AND count of `list-table` data rows (beyond header) |

### Data Model

```python
@dataclass
class CoverageResult:
    name: str
    fsm: bool
    process_count: int   # 0 = none found
    cdc: bool
    reset: bool
    port_count: int      # 0 = none found
```

`process_count` and `port_count` surface as numbers in both outputs rather than a plain tick.

---

## Terminal Output

Printed to stdout after all modules are scanned:

```
Coverage Report
───────────────────────────────────────────────────────
Module            FSM   Processes   CDC   Reset   Ports
───────────────────────────────────────────────────────
blinky             ✓     3 procs     –      ✓     6 ports
cfg_sync           –     3 procs     ✓      ✓     8 ports
pwm_controller     ✓     3 procs     –      –     6 ports
top                –      –          –      –     4 ports
traffic_light      ✓     4 procs     –      ✓     7 ports
───────────────────────────────────────────────────────
Totals           3/5      4/5       1/5    3/5     5/5
```

- `✓` = detected, `–` = not detected
- Process and port counts shown as `N procs` / `N ports` where N > 0, `–` where 0
- Totals: boolean signals count modules where true; count signals count modules where > 0
- Modules listed in hierarchy depth-first order; alphabetical in flat mode

---

## Sphinx Coverage Page

`coverage.rst` uses `.. raw:: html` to render a styled table (consistent with `registers.rst` approach). Module names link to their docs pages.

```rst
Documentation Coverage
======================

.. raw:: html

   <table class="coverage-table">
     <thead>
       <tr>
         <th>Module</th><th>FSM</th><th>Processes</th>
         <th>CDC</th><th>Reset</th><th>Ports</th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td><a href="modules/blinky/index.html">blinky</a></td>
         <td class="cov-yes">✓</td>
         <td class="cov-count">3</td>
         <td class="cov-no">–</td>
         <td class="cov-yes">✓</td>
         <td class="cov-count">6</td>
       </tr>
       ...
     </tbody>
     <tfoot>
       <tr><td>Totals</td><td>3/5</td>...</tr>
     </tfoot>
   </table>
```

### CSS additions to `custom.css`

Three classes added, with values for both Catppuccin Latte (light) and Mocha (dark) tokens:

- `.cov-yes` — green background (success)
- `.cov-no` — muted/grey background (gap)
- `.cov-count` — neutral background, displays numeric value
- `.coverage-table` — table layout/spacing styles
- `tfoot` row — slightly bolder weight

---

## `generate_rst.py` change

`index_rst()` gains a `coverage` entry in the toctree, guarded so it only appears when `coverage.rst` exists at build time (avoids broken toctree if `make coverage` hasn't been run):

```python
if (docs_dir / "coverage.rst").exists():
    lines.append("   coverage")
```

---

## Testing

New file: `scripts/hdl_autodoc/tests/test_generate_coverage.py`

Tests cover (all use `tmp_path` fixtures):

1. **FSM signal** — `.dot` present → `fsm=True`; absent → `fsm=False`
2. **Process count** — N `p_*.rst` files → `process_count=N`; none → 0
3. **CDC signal** — `_cdc.rst` with `→` → `cdc=True`; missing or no arrow → `False`
4. **Reset signal** — `_reset.rst` with `crossing` → `reset=True`; missing or no match → `False`
5. **Port count** — `_block.rst` with N data rows → `port_count=N`; missing → 0
6. **Terminal formatter** — correct column alignment, `✓`/`–`, counts, totals row
7. **RST generator** — `cov-yes`/`cov-no`/`cov-count` classes, module href links, `<tfoot>`
8. **Hierarchy ordering** — depth-first order preserved from `hierarchy.json`
