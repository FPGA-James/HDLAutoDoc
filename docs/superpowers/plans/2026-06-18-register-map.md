# Register Map Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `registers/regs_<module>.toml` definitions into per-module Sphinx docs as RST-native tables on a dedicated `registers.rst` page per module.

**Architecture:** New `extract_registers.py` parses TOML and emits RST. `generate_rst.py` auto-detects `registers.rst` on disk and adds it to module toctrees + a top-level index. `run_extract.py` calls the extractor after all HDL extraction. Makefile removes the old `include_registers.py` call.

**Tech Stack:** Python 3.11+ `tomllib` (stdlib), `re`, `pathlib`. No new dependencies.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/hdl_autodoc/extract_registers.py` | **Create** | Parse TOML → emit `registers.rst` |
| `scripts/hdl_autodoc/tests/test_extract_registers.py` | **Create** | 10 tests for extractor |
| `scripts/hdl_autodoc/generate_rst.py` | **Modify** | Auto-detect registers, write top-level index |
| `scripts/hdl_autodoc/tests/test_generate_rst.py` | **Modify** | 4 new tests for register-aware toctrees |
| `scripts/hdl_autodoc/run_extract.py` | **Modify** | Call extractor for each module with a TOML |
| `Makefile` | **Modify** | Remove `include_registers.py` from html/pdf; clean registers.rst |

---

## Task 1: `extract_registers.py` — core extractor + tests

**Files:**
- Create: `scripts/hdl_autodoc/extract_registers.py`
- Create: `scripts/hdl_autodoc/tests/test_extract_registers.py`

### Context

`registers/regs_counter.toml` (the project's only register TOML) has this structure when parsed by `tomllib`:

```python
{
    "conf": {
        "mode": "r_w",                      # ← "mode" key = this is a register
        "description": "Counter configuration.",
        "condition": {                       # ← "type" key = this is a field
            "type": "enumeration",
            "description": "Set mode...",
            "default_value": "clock_cycles",
            "element": {                    # ← enum values live here
                "clock_cycles": "Increment counter each clock cycle.",
                ...
            }
        },
        "increment": {
            "type": "integer",
            "description": "Step size...",
            "min_value": 1,
            "max_value": 255,
            "default_value": 1
        }
    },
    "command": { "mode": "wpulse", ... },
    "status":  { "mode": "r", ... },
}
```

`registers/config.yml` content (note leading spaces — regex handles it):
```
# config.yml
  bus_width:  32
  address_width: 8
  protocol: axi4lite
```

Offset formula: `index × (bus_width ÷ 8)` — so 32-bit = 4 bytes per register.

- [ ] **Step 1: Write the failing tests**

Create `scripts/hdl_autodoc/tests/test_extract_registers.py`:

```python
"""
test_extract_registers.py
-------------------------
Tests for extract_registers.py.

Covers:
  1.  Offset calculation for 32-bit bus width
  2.  r_w mode renders as r/w
  3.  wpulse mode renders correctly
  4.  r (read-only) mode renders correctly
  5.  bit field type appears in field table
  6.  bit_vector field with width renders as bit_vector(N)
  7.  integer field shows Range: min–max in description
  8.  enumeration field produces nested list-table with all enum values
  9.  config.yml with bus_width: 64 produces 8-byte-stride offsets
  10. Missing config.yml falls back to 32-bit bus width
"""

import pytest
from pathlib import Path

from extract_registers import generate_registers_rst


def _two_regs(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[rega]\nmode = "r_w"\ndescription = "First."\n'
        '[regb]\nmode = "r"\ndescription = "Second."\n'
    )
    return toml


# ── Test 1: Offset calculation ────────────────────────────────────────────────

def test_offset_calculation_32bit(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[rega]\nmode = "r_w"\ndescription = "First."\n'
        '[regb]\nmode = "r"\ndescription = "Second."\n'
        '[regc]\nmode = "w"\ndescription = "Third."\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "0x00" in rst
    assert "0x04" in rst
    assert "0x08" in rst


# ── Test 2: r_w mode ──────────────────────────────────────────────────────────

def test_r_w_renders_as_r_slash_w(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text('[reg]\nmode = "r_w"\ndescription = "A register."\n')
    rst = generate_registers_rst(toml, "test")
    assert "r/w" in rst


# ── Test 3: wpulse mode ───────────────────────────────────────────────────────

def test_wpulse_mode(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text('[reg]\nmode = "wpulse"\ndescription = "A register."\n')
    rst = generate_registers_rst(toml, "test")
    assert "wpulse" in rst


# ── Test 4: r mode ────────────────────────────────────────────────────────────

def test_r_mode(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text('[reg]\nmode = "r"\ndescription = "A register."\n')
    rst = generate_registers_rst(toml, "test")
    assert "     - r\n" in rst


# ── Test 5: bit field ─────────────────────────────────────────────────────────

def test_bit_field_type(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.flag]\ntype = "bit"\ndescription = "A flag."\ndefault_value = "0"\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "flag" in rst
    assert "bit" in rst


# ── Test 6: bit_vector field ──────────────────────────────────────────────────

def test_bit_vector_field_with_width(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.data]\ntype = "bit_vector"\nwidth = 16\ndescription = "Data."\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "bit_vector(16)" in rst


# ── Test 7: integer field with range ─────────────────────────────────────────

def test_integer_field_shows_range(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.value]\ntype = "integer"\ndescription = "A value."\n'
        'min_value = 1\nmax_value = 255\ndefault_value = 1\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "Range" in rst
    assert "255" in rst


# ── Test 8: enumeration with nested list-table ────────────────────────────────

def test_enumeration_field_produces_nested_list_table(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.mode_sel]\ntype = "enumeration"\ndescription = "Mode."\n'
        'default_value = "fast"\n'
        '[reg.mode_sel.element]\nfast = "Fast mode."\nslow = "Slow mode."\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert rst.count(".. list-table::") >= 2  # summary table + inner enum table
    assert "fast" in rst
    assert "slow" in rst
    assert "Fast mode." in rst


# ── Test 9: 64-bit bus width ──────────────────────────────────────────────────

def test_64bit_bus_width_produces_8_byte_stride(tmp_path):
    (tmp_path / "config.yml").write_text(
        "bus_width: 64\naddress_width: 16\nprotocol: axi4lite\n"
    )
    rst = generate_registers_rst(_two_regs(tmp_path), "test")
    assert "0x00" in rst
    assert "0x08" in rst


# ── Test 10: Missing config.yml defaults to 32-bit ───────────────────────────

def test_missing_config_yml_defaults_to_32bit(tmp_path):
    rst = generate_registers_rst(_two_regs(tmp_path), "test")
    assert "0x00" in rst
    assert "0x04" in rst
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd scripts/hdl_autodoc && pytest tests/test_extract_registers.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'extract_registers'`

- [ ] **Step 3: Implement `extract_registers.py`**

Create `scripts/hdl_autodoc/extract_registers.py`:

```python
#!/usr/bin/env python3
"""
extract_registers.py
--------------------
Reads registers/regs_<module>.toml and writes registers.rst
to the module's doc directory.

Usage:
    python extract_registers.py <regs_toml> <module_name> <output_dir>
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


ACCESS_MAP = {"r_w": "r/w", "r": "r", "w": "w", "wpulse": "wpulse"}


def _access(mode: str) -> str:
    return ACCESS_MAP.get(mode, mode)


def _read_bus_width(regs_toml: Path) -> int:
    config = regs_toml.parent / "config.yml"
    if config.exists():
        m = re.search(r'bus_width:\s*(\d+)', config.read_text())
        if m:
            return int(m.group(1))
    return 32


def _render_field_type(fdata: dict) -> str:
    ftype = fdata.get("type", "")
    if ftype == "bit_vector":
        width = fdata.get("width", "")
        return f"bit_vector({width})" if width else "bit_vector"
    return ftype


def _render_enum_subtable(elements: dict[str, str]) -> list[str]:
    lines = [
        "",
        "      .. list-table::",
        "         :header-rows: 1",
        "         :widths: 30 70",
        "",
        "         * - Value",
        "           - Description",
    ]
    for val, desc in elements.items():
        lines.append(f"         * - ``{val}``")
        lines.append(f"           - {desc}")
    lines.append("")
    return lines


def _render_field_row(fname: str, fdata: dict) -> list[str]:
    ftype   = fdata.get("type", "")
    desc    = fdata.get("description", "")
    default = fdata.get("default_value", "")
    lines = [
        f"   * - ``{fname}``",
        f"     - {_render_field_type(fdata)}",
        f"     - {default}",
        f"     - {desc}",
    ]
    if ftype == "integer":
        mn = fdata.get("min_value")
        mx = fdata.get("max_value")
        if mn is not None and mx is not None:
            lines.append(f"       Range: {mn}–{mx}.")
    if ftype == "enumeration":
        elements = fdata.get("element", {})
        if elements:
            lines.extend(_render_enum_subtable(elements))
    return lines


def generate_registers_rst(regs_toml: Path, module_name: str) -> str:
    data      = tomllib.loads(regs_toml.read_text())
    bus_width = _read_bus_width(regs_toml)
    stride    = bus_width // 8

    registers = [(k, v) for k, v in data.items()
                 if isinstance(v, dict) and "mode" in v]

    title = "Register Map"
    lines: list[str] = [title, "=" * len(title), ""]

    # Summary table
    lines += [
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: 20 15 15 50",
        "",
        "   * - Register",
        "     - Offset",
        "     - Access",
        "     - Description",
    ]
    for i, (rname, rdata) in enumerate(registers):
        offset = f"0x{i * stride:02X}"
        lines += [
            f"   * - {rname}",
            f"     - {offset}",
            f"     - {_access(rdata.get('mode', ''))}",
            f"     - {rdata.get('description', '')}",
        ]
    lines.append("")

    # Per-register detail sections
    for i, (rname, rdata) in enumerate(registers):
        offset  = f"0x{i * stride:02X}"
        heading = f"{rname} ({offset})"
        lines += [heading, "-" * len(heading), ""]

        fields = [(k, v) for k, v in rdata.items()
                  if isinstance(v, dict) and "type" in v]
        if fields:
            lines += [
                ".. list-table::",
                "   :header-rows: 1",
                "   :widths: 20 20 20 40",
                "",
                "   * - Field",
                "     - Type",
                "     - Default",
                "     - Description",
            ]
            for fname, fdata in fields:
                lines.extend(_render_field_row(fname, fdata))
            lines.append("")
        else:
            lines += [f"No fields defined for ``{rname}``.", ""]

    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("Usage: extract_registers.py <regs_toml> <module_name> <output_dir>")

    regs_toml   = Path(sys.argv[1])
    module_name = sys.argv[2]
    output_dir  = Path(sys.argv[3])

    rst = generate_registers_rst(regs_toml, module_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "registers.rst").write_text(rst)
    print(f"  → {output_dir / 'registers.rst'}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd scripts/hdl_autodoc && pytest tests/test_extract_registers.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/extract_registers.py \
        scripts/hdl_autodoc/tests/test_extract_registers.py
git commit -m "feat: add extract_registers.py — TOML → RST register map extractor"
```

---

## Task 2: `generate_rst.py` — register-aware toctrees + top-level index

**Files:**
- Modify: `scripts/hdl_autodoc/generate_rst.py:155-179` (module_index_rst)
- Modify: `scripts/hdl_autodoc/generate_rst.py:434-467` (index_rst)
- Modify: `scripts/hdl_autodoc/generate_rst.py:556-570` (main loop)
- Modify: `scripts/hdl_autodoc/generate_rst.py:603-608` (post-loop writes)
- Test: `scripts/hdl_autodoc/tests/test_generate_rst.py`

### Context

Current `module_index_rst` signature (line 155):
```python
def module_index_rst(entity: dict, children: list[str],
                     shared_children: set[str],
                     has_processes: bool = True,
                     is_top: bool = False) -> str:
```

The `is_top` parameter exists only to add `   ../../registers` (lines 178-179). It's being replaced by `has_registers` which auto-detects from disk.

Current `index_rst` (line 434) adds `registers` unconditionally in flat mode (line 455) but never in hierarchy mode (lines 445-451).

- [ ] **Step 1: Write the failing tests**

Add to the end of `scripts/hdl_autodoc/tests/test_generate_rst.py`:

```python
# ── Register-aware toctree tests ──────────────────────────────────────────────

from generate_rst import registers_rst, index_rst


def test_module_index_rst_with_registers_includes_registers_entry():
    """has_registers=True adds registers to the module toctree."""
    rst = module_index_rst(
        _make_entity(), children=[], shared_children=set(),
        has_registers=True
    )
    assert "   registers" in rst


def test_module_index_rst_without_registers_excludes_registers_entry():
    """has_registers=False (default) does not add registers to the toctree."""
    rst = module_index_rst(
        _make_entity(), children=[], shared_children=set()
    )
    assert "registers" not in rst


def test_registers_rst_generates_toctree():
    """registers_rst writes a toctree with module paths."""
    rst = registers_rst(["counter", "top"])
    assert "modules/counter/registers" in rst
    assert "modules/top/registers" in rst
    assert ".. toctree::" in rst


def test_index_rst_includes_registers_when_modules_present():
    """index_rst adds a registers entry when modules_with_regs is non-empty."""
    entity = {"name": "top", "brief": "Top.", "file": "top.vhd", "ports": []}
    rst = index_rst([entity], "MyProject", modules_with_regs=["top"])
    assert "registers" in rst
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd scripts/hdl_autodoc && pytest tests/test_generate_rst.py -v -k "registers" 2>&1 | tail -20
```

Expected: 4 failures — `ImportError` on `registers_rst` and `TypeError` on `has_registers` kwarg.

- [ ] **Step 3: Update `module_index_rst` — replace `is_top` with `has_registers`**

In `scripts/hdl_autodoc/generate_rst.py`, replace:

```python
def module_index_rst(entity: dict, children: list[str],
                     shared_children: set[str],
                     has_processes: bool = True,
                     is_top: bool = False) -> str:
    """Always-regenerated toctree for one module."""
    name  = entity["name"]
    title = name
    lines = [
        title, "=" * len(title), "",
        ".. toctree::",
        "   :maxdepth: 3",
        "",
        "   entity",
        "   block",
        "   fsm",
        "   timing",
    ]
    if has_processes:
        lines.append("   processes/index")
    lines.append("   cdc")
    lines.append("   reset")
    lines.append("")

    if is_top:
        lines += ["   ../../registers", ""]
```

with:

```python
def module_index_rst(entity: dict, children: list[str],
                     shared_children: set[str],
                     has_processes: bool = True,
                     has_registers: bool = False) -> str:
    """Always-regenerated toctree for one module."""
    name  = entity["name"]
    title = name
    lines = [
        title, "=" * len(title), "",
        ".. toctree::",
        "   :maxdepth: 3",
        "",
        "   entity",
        "   block",
        "   fsm",
        "   timing",
    ]
    if has_processes:
        lines.append("   processes/index")
    lines.append("   cdc")
    lines.append("   reset")
    if has_registers:
        lines.append("   registers")
    lines.append("")
```

- [ ] **Step 4: Add `registers_rst` function**

Add this function after `hierarchy_rst` (around line 431, before `index_rst`):

```python
def registers_rst(modules_with_regs: list[str]) -> str:
    """Top-level registers index page listing all modules with register maps."""
    title = "Register Maps"
    lines = [
        title, "=" * len(title), "",
        ".. toctree::",
        "   :maxdepth: 1",
        "",
    ]
    for name in modules_with_regs:
        lines.append(f"   modules/{name}/registers")
    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 5: Update `index_rst` — conditional registers entry**

In `index_rst`, replace the current signature and hierarchy/flat branches:

Old signature:
```python
def index_rst(entities: list[dict], project_name: str,
              hierarchy: dict = None, has_coverage: bool = False) -> str:
```

New signature:
```python
def index_rst(entities: list[dict], project_name: str,
              hierarchy: dict = None, has_coverage: bool = False,
              modules_with_regs: list[str] | None = None) -> str:
```

Old branches (lines 445-455):
```python
    if hierarchy:
        # Only list the top-level module — it contains submodule toctrees
        top = hierarchy["top"]
        lines += [
            f"   modules/{top}/index",
            "   hierarchy",
        ]
    else:
        for e in entities:
            lines.append(f"   modules/{e['name']}/index")
        lines.append("   registers")
```

New branches:
```python
    if hierarchy:
        top = hierarchy["top"]
        lines += [
            f"   modules/{top}/index",
            "   hierarchy",
        ]
        if modules_with_regs:
            lines.append("   registers")
    else:
        for e in entities:
            lines.append(f"   modules/{e['name']}/index")
        if modules_with_regs:
            lines.append("   registers")
```

- [ ] **Step 6: Update the main loop to detect registers and collect names**

In the `__main__` block, before the entity loop (around line 554), add:

```python
    modules_with_regs: list[str] = []
```

Inside the entity loop (around line 564), add `has_registers` detection and collection before the `write_always` call for `index.rst`:

```python
        # Always regenerated
        has_processes = (mod_dir / "processes" / "index.rst").exists()
        has_registers = (mod_dir / "registers.rst").exists()
        if has_registers:
            modules_with_regs.append(name)
```

Change the `module_index_rst` call from:
```python
        results.append(write_always(
            mod_dir / "index.rst",
            module_index_rst(entity, children, shared_names,
                             has_processes=has_processes,
                             is_top=(hierarchy and name == hierarchy["top"]))
        ))
```
to:
```python
        results.append(write_always(
            mod_dir / "index.rst",
            module_index_rst(entity, children, shared_names,
                             has_processes=has_processes,
                             has_registers=has_registers)
        ))
```

- [ ] **Step 7: Write top-level `registers.rst` and update `index_rst` call**

In the post-loop section (around line 603), after the existing `has_coverage` line, add the registers.rst write:

```python
    has_coverage = (docs_dir / "coverage.rst").exists()
    if modules_with_regs:
        results.append(write_always(
            docs_dir / "registers.rst",
            registers_rst(modules_with_regs)
        ))
```

Update the `index_rst` call to pass `modules_with_regs`:

```python
    results.append(write_always(
        docs_dir / "index.rst",
        index_rst(entities, project_name, hierarchy, has_coverage=has_coverage,
                  modules_with_regs=modules_with_regs or None)
    ))
```

- [ ] **Step 8: Run all generate_rst tests**

```bash
cd scripts/hdl_autodoc && pytest tests/test_generate_rst.py -v
```

Expected: all pass (existing tests + 4 new register tests).

- [ ] **Step 9: Run the full test suite**

```bash
cd scripts/hdl_autodoc && pytest -v
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add scripts/hdl_autodoc/generate_rst.py \
        scripts/hdl_autodoc/tests/test_generate_rst.py
git commit -m "feat: generate_rst.py — register-aware toctrees and top-level register index"
```

---

## Task 3: `run_extract.py` — call register extractor per module

**Files:**
- Modify: `scripts/hdl_autodoc/run_extract.py:93-95` (after `save_cache`)

### Context

`run_extract.py` currently ends its main function with `save_cache(...)`.

Register extraction must run AFTER all HDL extraction (because it's independent of the HDL cache). `registers_dir` is at the repo root's `registers/` folder:
- `docs_dir` = `docs/hdl_autodoc`
- `docs_dir.parent.parent` = repo root
- `registers_dir` = `<repo_root>/registers`

Register extraction always re-runs (no caching) — the TOML files are small and parsing is fast. This means `regs_*.toml` changes always take effect without `--force`.

- [ ] **Step 1: Add register extraction after `save_cache`**

In `scripts/hdl_autodoc/run_extract.py`, after `save_cache(updated_cache, cache_path)` (line 95), add:

```python
    # Register map extraction — always re-run (independent of HDL cache)
    registers_dir = docs_dir.parent.parent / "registers"
    for name in hierarchy["modules"]:
        regs_toml = registers_dir / f"regs_{name}.toml"
        if regs_toml.exists():
            module_dir = docs_dir / "modules" / name
            print(f"Registers:  {name} ({regs_toml.name})...")
            run(["python", str(scripts_dir / "extract_registers.py"),
                 str(regs_toml), name, str(module_dir)])
```

- [ ] **Step 2: Smoke-test by running `make extract`**

```bash
make extract FORCE=1
```

Expected output includes `Registers:  counter (regs_counter.toml)...` and `docs/hdl_autodoc/modules/counter/registers.rst` is created.

Verify the file was created:
```bash
test -f docs/hdl_autodoc/modules/counter/registers.rst && echo "OK"
```

- [ ] **Step 3: Verify `registers.rst` content is valid RST**

```bash
grep -c "Register Map" docs/hdl_autodoc/modules/counter/registers.rst
```

Expected: `1`

```bash
grep "0x00\|0x04\|0x08" docs/hdl_autodoc/modules/counter/registers.rst
```

Expected: three lines with offsets 0x00, 0x04, 0x08 (conf, command, status at 4-byte stride).

- [ ] **Step 4: Commit**

```bash
git add scripts/hdl_autodoc/run_extract.py
git commit -m "feat: run_extract.py — call extract_registers.py for each module with a regs TOML"
```

---

## Task 4: Makefile cleanup + full build verification

**Files:**
- Modify: `Makefile:109-111` (html target — remove include_registers.py)
- Modify: `Makefile:117-119` (pdf target — remove include_registers.py)
- Modify: `Makefile:150-157` (clean-generated find command — add registers.rst)

### Context

Current `html` target (line 107):
```makefile
html: extract
	mkdir -p $(AUTODOC_SOURCEDIR)/_static $(AUTODOC_SOURCEDIR)/_templates
	@echo "Checking for register map..."
	python $(AUTODOC_SCRIPTDIR)/include_registers.py . $(AUTODOC_SOURCEDIR)
	$(AUTODOC_SPHINXBUILD) -M html ...
```

Current `pdf` target (line 116):
```makefile
pdf: extract
	@echo "Checking for register map..."
	python $(AUTODOC_SCRIPTDIR)/include_registers.py . $(AUTODOC_SOURCEDIR)
	$(AUTODOC_SPHINXBUILD) -M latexpdf ...
```

Current `clean-generated` per-module find (lines 151-157) includes `-name "block.rst"` but not `-name "registers.rst"`.

- [ ] **Step 1: Remove `include_registers.py` from `html` target**

In `Makefile`, change the `html` target from:
```makefile
html: extract
	mkdir -p $(AUTODOC_SOURCEDIR)/_static $(AUTODOC_SOURCEDIR)/_templates
	@echo "Checking for register map..."
	python $(AUTODOC_SCRIPTDIR)/include_registers.py . $(AUTODOC_SOURCEDIR)
	$(AUTODOC_SPHINXBUILD) -M html $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) $(AUTODOC_SPHINXOPTS)
	@echo ""
	@echo "Documentation built: $(AUTODOC_BUILDDIR)/html/index.html"
```

to:
```makefile
html: extract
	mkdir -p $(AUTODOC_SOURCEDIR)/_static $(AUTODOC_SOURCEDIR)/_templates
	$(AUTODOC_SPHINXBUILD) -M html $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) $(AUTODOC_SPHINXOPTS)
	@echo ""
	@echo "Documentation built: $(AUTODOC_BUILDDIR)/html/index.html"
```

- [ ] **Step 2: Remove `include_registers.py` from `pdf` target**

Change:
```makefile
pdf: extract
	@echo "Checking for register map..."
	python $(AUTODOC_SCRIPTDIR)/include_registers.py . $(AUTODOC_SOURCEDIR)
	$(AUTODOC_SPHINXBUILD) -M latexpdf $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) $(AUTODOC_SPHINXOPTS)
```

to:
```makefile
pdf: extract
	$(AUTODOC_SPHINXBUILD) -M latexpdf $(AUTODOC_SOURCEDIR) $(AUTODOC_BUILDDIR) $(AUTODOC_SPHINXOPTS)
```

- [ ] **Step 3: Add `registers.rst` to `clean-generated` find command**

In `clean-generated`, find the block:
```makefile
	     -name "block.rst" -o -name "*_block.rst" -o -name "*_block.dot" \
```

Add `-o -name "registers.rst"` on the same line or the next:
```makefile
	     -name "block.rst" -o -name "*_block.rst" -o -name "*_block.dot" \
	     -o -name "registers.rst" \
```

- [ ] **Step 4: Run full build and verify registers page appears**

```bash
make html 2>&1 | tail -5
```

Expected: `Documentation built: docs/hdl_autodoc/_build/html/index.html` with no errors.

Verify the counter registers page exists in the HTML output:
```bash
test -f docs/hdl_autodoc/_build/html/modules/counter/registers.html && echo "OK"
```

Verify the top-level registers index:
```bash
test -f docs/hdl_autodoc/_build/html/registers.html && echo "OK"
```

- [ ] **Step 5: Run the full test suite one final time**

```bash
cd scripts/hdl_autodoc && pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add Makefile
git commit -m "chore: remove include_registers.py from html/pdf targets; registers now built by extract_registers.py"
```
