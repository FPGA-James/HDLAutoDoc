# Register Map Integration — Design Spec

**Date:** 2026-06-18
**Status:** Approved

---

## Overview

Integrate register map definitions (`registers/regs_<module>.toml`) into the per-module documentation. Replace the existing iframe-based register page with RST-native tables rendered inline on a dedicated `registers.rst` page per module. Runs as part of `make extract` — no new Makefile targets.

---

## Architecture & Data Flow

Four components change:

**`extract_registers.py`** (new) — reads `regs_<module>.toml` and `registers/config.yml`, emits `docs/hdl_autodoc/modules/<module>/registers.rst`. No rendering concern beyond RST generation.

**`generate_rst.py`** (updated) — `module_index_rst` gains `has_registers: bool` parameter; when true, appends `registers` to the module toctree. Removes the existing `is_top → ../../registers` block. New `registers_rst(modules_with_regs)` function writes a top-level registers index page.

**`run_extract.py`** (updated) — for each module, checks for `registers/regs_<name>.toml`; if found, calls `extract_registers.py` as a subprocess. Passes the list of modules-with-registers to a second `generate_rst.py` call for the top-level index.

**`Makefile`** (updated) — removes the `include_registers.py` call from `html` and `pdf` targets. Adds `registers.rst` to the per-module `clean-generated` find command.

The existing `include_registers.py` and `registers/generated/` HTML output are no longer part of the Sphinx pipeline once this feature lands.

---

## `extract_registers.py` Module

### CLI

```
python extract_registers.py <regs_toml> <module_name> <output_dir>
```

Writes `<output_dir>/registers.rst`.

### Config parsing

Reads `registers/config.yml` (sibling of `regs_<module>.toml`) using regex — no YAML library dependency:

```python
m = re.search(r'bus_width:\s*(\d+)', config_text)
bus_width = int(m.group(1)) if m else 32
```

### TOML structure

- **Registers** = top-level TOML tables that have a `mode` key
- **Fields** = nested tables within a register that have a `type` key
- **Enum elements** = nested tables within a field (type = `"enumeration"`)

### Offset calculation

```
offset = register_index × (bus_width ÷ 8)
formatted as f"0x{offset:02X}"
```

Registers are indexed in TOML definition order (0, 1, 2, …).

### RST output structure

```rst
Register Map
============

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Register
     - Offset
     - Access
     - Description
   * - conf
     - 0x00
     - r/w
     - Counter configuration.
   ...

conf (0x00)
-----------

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Field
     - Type
     - Default
     - Description
   * - condition
     - enumeration
     - clock_cycles
     - Set mode for how the counter operates.

       .. list-table::
          :header-rows: 1
          :widths: 30 70

          * - Value
            - Description
          * - clock_cycles
            - Increment counter each clock cycle.
          ...
   ...
```

### Access mode rendering

| TOML `mode` | RST display |
|---|---|
| `r_w` | `r/w` |
| `r` | `r` |
| `wpulse` | `wpulse` |
| `w` | `w` |
| anything else | pass through as-is |

---

## `generate_rst.py` Changes

### `module_index_rst`

Gains `has_registers: bool = False` as a new keyword argument. When `True`, appends `registers` to the toctree:

```python
def module_index_rst(name, ..., has_registers: bool = False) -> str:
    ...
    toctree_entries = ["entity", "block", "fsm", "timing", "processes/index", "cdc", "reset"]
    if has_registers:
        toctree_entries.append("registers")
    ...
```

Remove the existing `is_top` block that added `../../registers` (currently at lines 176-179 of `generate_rst.py`). The top-level registers index is now handled by `registers_rst()`.

### New `registers_rst(modules_with_regs: list[str]) -> str`

Writes `docs/hdl_autodoc/registers.rst` — a top-level index page listing all modules that have register maps:

```rst
Register Maps
=============

.. toctree::
   :maxdepth: 1

   modules/counter/registers
   modules/top/registers
```

If `modules_with_regs` is empty, the function returns an empty string and no file is written.

### Top-level `index.rst` toctree

In `index_rst()`, the `registers` entry in the top-level toctree is added only when `modules_with_regs` is non-empty (replaces the current unconditional include in flat mode; adds it to hierarchy mode which currently omits it).

---

## `run_extract.py` Changes

```python
registers_dir = docs_dir.parent.parent / "registers"

modules_with_regs = []
for module in modules:
    regs_toml = registers_dir / f"regs_{module['name']}.toml"
    if regs_toml.exists():
        modules_with_regs.append(module['name'])
        subprocess.run([
            sys.executable, str(script_dir / "extract_registers.py"),
            str(regs_toml), module['name'],
            str(docs_dir / "modules" / module['name'])
        ], check=True)

# Second generate_rst.py call: top-level registers index + toctrees
subprocess.run([
    sys.executable, str(script_dir / "generate_rst.py"),
    str(src_dir), str(docs_dir), project_name,
    "--registers", *modules_with_regs
], check=True)
```

`generate_rst.py` gains a `--registers <name> [<name> ...]` CLI argument consumed by the second pass.

---

## Makefile Changes

Remove `include_registers.py` from `html` and `pdf` targets:

```makefile
# html target — remove these two lines:
#   @echo "Checking for register map..."
#   python $(AUTODOC_SCRIPTDIR)/include_registers.py . $(AUTODOC_SOURCEDIR)

# pdf target — same removal
```

Add `registers.rst` to the per-module `clean-generated` find command in `clean-generated`:

```makefile
-o -name "registers.rst" \
```

(Insert alongside the existing `-o -name "block.rst"` line.)

---

## Testing

New file: `scripts/hdl_autodoc/tests/test_extract_registers.py`

| # | Test |
|---|---|
| 1 | Summary table has correct offset for each register (index × bus_width÷8) |
| 2 | `r_w` mode renders as `r/w` in summary table |
| 3 | `wpulse` mode renders correctly |
| 4 | `r` (read-only) mode renders correctly |
| 5 | `bit` field type appears in field table |
| 6 | `bit_vector` field type appears with width info |
| 7 | `integer` field type appears with min/max in description |
| 8 | `enumeration` field produces nested `.. list-table::` with all enum values |
| 9 | `config.yml` with `bus_width: 64` produces correct 8-byte-stride offsets |
| 10 | Missing `config.yml` falls back to 32-bit bus width |

---

## What Does Not Change

- `include_registers.py` remains on disk but is no longer called from `html` or `pdf` targets.
- `registers/generated/` HTML output is not deleted — existing users who run `make regs` can still access it, it just won't be embedded in the Sphinx site.
- `entity.rst` (hand-editable) is untouched.
- `extract_block.py`, `extract_fsm.py`, `extract_cdc.py`, `extract_reset.py` are unaffected.
- No changes to Sphinx config (`docs/conf.py`).
