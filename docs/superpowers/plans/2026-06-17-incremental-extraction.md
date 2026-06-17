# Incremental Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add content-hash caching to `run_extract.py` so unchanged modules are skipped on re-runs, saving time and preserving output.

**Architecture:** A new `extract_cache.py` module holds all cache logic (hashing, load/save, staleness check). `run_extract.py` is refactored to expose a `main()` function and calls into `extract_cache.py` once per module. A `--force` flag bypasses the cache entirely.

**Tech Stack:** Python 3.11+ stdlib only (`hashlib`, `json`, `dataclasses`, `pathlib`); `unittest.mock` for subprocess mocking in tests.

---

## File Structure

| File | Action | Purpose |
|---|---|---|
| `scripts/hdl_autodoc/extract_cache.py` | **Create** | Cache data model, hash functions, load/save, staleness check |
| `scripts/hdl_autodoc/tests/test_extract_cache.py` | **Create** | 12 tests for extract_cache.py |
| `scripts/hdl_autodoc/run_extract.py` | **Modify** | Expose `main()`, add `--force` flag, integrate cache |
| `scripts/hdl_autodoc/tests/test_run_extract.py` | **Create** | 2 tests for cache integration in run_extract.py |
| `Makefile` | **Modify** | Add `$(if $(FORCE),--force)` to extract target, clean cache file, update help |

---

## Task 1: `extract_cache.py` + tests

**Files:**
- Create: `scripts/hdl_autodoc/extract_cache.py`
- Create: `scripts/hdl_autodoc/tests/test_extract_cache.py`

### Background

The cache file lives at `docs/hdl_autodoc/.extract_cache.json`. It stores a `version` integer, a single `extractor_hash` (SHA-256 over all `extract_*.py` and `generate_schematic.py` scripts concatenated), and a `modules` dict mapping module name → source file SHA-256. Any mismatch in version or extractor hash makes the whole cache stale; a module-level mismatch makes only that module stale.

- [ ] **Step 1: Write failing tests for load/save and hash functions**

```python
# scripts/hdl_autodoc/tests/test_extract_cache.py
"""Tests for extract_cache.py."""

import json
from pathlib import Path

from extract_cache import (
    CACHE_VERSION,
    ExtractCache,
    compute_extractor_hash,
    compute_file_hash,
    is_up_to_date,
    load_cache,
    save_cache,
)


# ── load_cache ────────────────────────────────────────────────────────────────

def test_load_cache_returns_none_when_missing(tmp_path):
    result = load_cache(tmp_path / "nonexistent.json")
    assert result is None


def test_load_cache_returns_none_on_version_mismatch(tmp_path):
    p = tmp_path / "cache.json"
    p.write_text(json.dumps({"version": 999, "extractor_hash": "abc", "modules": {}}))
    assert load_cache(p) is None


def test_load_cache_returns_none_on_parse_error(tmp_path):
    p = tmp_path / "cache.json"
    p.write_text("not valid json{{{")
    assert load_cache(p) is None


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "cache.json"
    cache = ExtractCache(extractor_hash="deadbeef", modules={"blinky": "abc123"})
    save_cache(cache, p)
    loaded = load_cache(p)
    assert loaded is not None
    assert loaded.extractor_hash == "deadbeef"
    assert loaded.modules == {"blinky": "abc123"}


# ── is_up_to_date ─────────────────────────────────────────────────────────────

def test_is_up_to_date_false_when_cache_is_none(tmp_path):
    src = tmp_path / "a.vhd"
    src.write_text("entity a is end;")
    assert is_up_to_date(None, "a", str(src), "hash") is False


def test_is_up_to_date_false_when_extractor_hash_differs(tmp_path):
    src = tmp_path / "a.vhd"
    src.write_text("entity a is end;")
    src_hash = compute_file_hash(src)
    cache = ExtractCache(extractor_hash="old_hash", modules={"a": src_hash})
    assert is_up_to_date(cache, "a", str(src), "new_hash") is False


def test_is_up_to_date_false_when_src_hash_differs(tmp_path):
    src = tmp_path / "a.vhd"
    src.write_text("entity a is end;")
    cache = ExtractCache(extractor_hash="h", modules={"a": "wrong_hash"})
    assert is_up_to_date(cache, "a", str(src), "h") is False


def test_is_up_to_date_false_when_module_not_in_cache(tmp_path):
    src = tmp_path / "a.vhd"
    src.write_text("entity a is end;")
    cache = ExtractCache(extractor_hash="h", modules={})
    assert is_up_to_date(cache, "a", str(src), "h") is False


def test_is_up_to_date_true_when_everything_matches(tmp_path):
    src = tmp_path / "a.vhd"
    src.write_text("entity a is end;")
    src_hash = compute_file_hash(src)
    cache = ExtractCache(extractor_hash="h", modules={"a": src_hash})
    assert is_up_to_date(cache, "a", str(src), "h") is True


# ── compute_extractor_hash ────────────────────────────────────────────────────

def test_compute_extractor_hash_changes_when_script_changes(tmp_path):
    script = tmp_path / "extract_fsm.py"
    script.write_text("# version 1")
    h1 = compute_extractor_hash(tmp_path)
    script.write_text("# version 2")
    h2 = compute_extractor_hash(tmp_path)
    assert h1 != h2


# ── integration: full cache round-trip ───────────────────────────────────────

def test_cache_skips_unchanged_module(tmp_path):
    src = tmp_path / "blinky.vhd"
    src.write_text("entity blinky is end;")
    src_hash = compute_file_hash(src)
    cache = ExtractCache(extractor_hash="h", modules={"blinky": src_hash})
    cache_path = tmp_path / ".extract_cache.json"
    save_cache(cache, cache_path)

    loaded = load_cache(cache_path)
    assert is_up_to_date(loaded, "blinky", str(src), "h") is True


def test_cache_invalidated_after_source_change(tmp_path):
    src = tmp_path / "blinky.vhd"
    src.write_text("entity blinky is end;")
    src_hash = compute_file_hash(src)
    cache = ExtractCache(extractor_hash="h", modules={"blinky": src_hash})
    cache_path = tmp_path / ".extract_cache.json"
    save_cache(cache, cache_path)

    src.write_text("entity blinky is -- changed\nend;")

    loaded = load_cache(cache_path)
    assert is_up_to_date(loaded, "blinky", str(src), "h") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_extract_cache.py -v
```

Expected: 12 errors — `ModuleNotFoundError: No module named 'extract_cache'`

- [ ] **Step 3: Create `extract_cache.py`**

```python
# scripts/hdl_autodoc/extract_cache.py
#!/usr/bin/env python3
"""
extract_cache.py
----------------
Content-hash cache for run_extract.py.  Tracks source file hashes and
extractor script hashes so unchanged modules can be skipped.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

CACHE_VERSION = 1


@dataclass
class ExtractCache:
    extractor_hash: str
    modules: dict[str, str] = field(default_factory=dict)  # name → src_hash


def compute_file_hash(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compute_extractor_hash(scripts_dir: Path) -> str:
    """Return a single SHA-256 over all extractor + schematic scripts (sorted)."""
    paths = sorted(
        list(scripts_dir.glob("extract_*.py"))
        + list(scripts_dir.glob("generate_schematic.py"))
    )
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
    return h.hexdigest()


def load_cache(path: Path) -> ExtractCache | None:
    """Load the cache from disk.  Returns None on any error or version mismatch."""
    try:
        data = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if data.get("version") != CACHE_VERSION:
        return None
    return ExtractCache(
        extractor_hash=data.get("extractor_hash", ""),
        modules=data.get("modules", {}),
    )


def save_cache(cache: ExtractCache, path: Path) -> None:
    """Write the cache to disk."""
    data = {
        "version": CACHE_VERSION,
        "extractor_hash": cache.extractor_hash,
        "modules": cache.modules,
    }
    path.write_text(json.dumps(data, indent=2))


def is_up_to_date(
    cache: ExtractCache | None,
    name: str,
    src_file: str,
    extractor_hash: str,
) -> bool:
    """Return True only if name's source file and extractor scripts are unchanged."""
    if cache is None:
        return False
    if cache.extractor_hash != extractor_hash:
        return False
    cached_src_hash = cache.modules.get(name)
    if cached_src_hash is None:
        return False
    return cached_src_hash == compute_file_hash(Path(src_file))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_extract_cache.py -v
```

Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/hdl_autodoc/extract_cache.py \
        scripts/hdl_autodoc/tests/test_extract_cache.py
git commit -m "feat: add extract_cache module with SHA-256 content hashing"
```

---

## Task 2: Refactor `run_extract.py` + `test_run_extract.py`

**Files:**
- Modify: `scripts/hdl_autodoc/run_extract.py`
- Create: `scripts/hdl_autodoc/tests/test_run_extract.py`

### Background

`run_extract.py` currently puts all logic inside `if __name__ == "__main__":`, making it untestable. This task extracts a `main()` function (same pattern as `generate_coverage.py`) and integrates the cache: load before the loop, check per module, update after each extraction, save after the loop. The `--force` flag bypasses the cache check.

The `subprocess.run` calls inside `run()` are patched in tests using `unittest.mock.patch`.

- [ ] **Step 1: Write failing tests**

```python
# scripts/hdl_autodoc/tests/test_run_extract.py
"""Tests for run_extract.py cache integration."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from extract_cache import (
    ExtractCache,
    compute_extractor_hash,
    compute_file_hash,
    save_cache,
)
from run_extract import main


def _make_hierarchy(tmp_path: Path, src_file: Path) -> Path:
    hierarchy = {
        "modules": {
            "blinky": {"file": str(src_file), "children": [], "parents": []}
        }
    }
    h_json = tmp_path / "hierarchy.json"
    h_json.write_text(json.dumps(hierarchy))
    return h_json


def _warm_cache(tmp_path: Path, src_file: Path, scripts_dir: Path) -> None:
    extractor_hash = compute_extractor_hash(scripts_dir)
    cache = ExtractCache(
        extractor_hash=extractor_hash,
        modules={"blinky": compute_file_hash(src_file)},
    )
    save_cache(cache, tmp_path / ".extract_cache.json")


def test_force_bypasses_warm_cache(tmp_path):
    src = tmp_path / "blinky.vhd"
    src.write_text("entity blinky is end;")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    h_json = _make_hierarchy(tmp_path, src)
    _warm_cache(tmp_path, src, scripts_dir)

    extracted = []

    def fake_run(cmd, **kwargs):
        extracted.append(cmd)
        return MagicMock(returncode=0)

    with patch("run_extract.subprocess.run", side_effect=fake_run):
        main(h_json, tmp_path, scripts_dir, force=True)

    assert len(extracted) > 0


def test_skip_line_printed_for_unchanged_module(tmp_path, capsys):
    src = tmp_path / "blinky.vhd"
    src.write_text("entity blinky is end;")
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    h_json = _make_hierarchy(tmp_path, src)
    _warm_cache(tmp_path, src, scripts_dir)

    extracted = []

    def fake_run(cmd, **kwargs):
        extracted.append(cmd)
        return MagicMock(returncode=0)

    with patch("run_extract.subprocess.run", side_effect=fake_run):
        main(h_json, tmp_path, scripts_dir, force=False)

    captured = capsys.readouterr()
    assert "Skipping:" in captured.out
    assert len(extracted) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest scripts/hdl_autodoc/tests/test_run_extract.py -v
```

Expected: 2 errors — `ImportError: cannot import name 'main' from 'run_extract'`

- [ ] **Step 3: Rewrite `run_extract.py`**

Replace the entire file contents:

```python
#!/usr/bin/env python3
"""
run_extract.py
--------------
Reads hierarchy.json and runs all extractors for every module.
Called by the Makefile extract target.

Usage:
    python scripts/run_extract.py <hierarchy.json> <docs_dir> <scripts_dir> [--schematics] [--force]

Flags:
    --schematics   Run generate_schematic.py (requires yosys) and include the
                   RTL schematic in each module's block diagram page.
    --force        Bypass the extraction cache and re-extract all modules.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from extract_cache import (
    ExtractCache,
    compute_extractor_hash,
    compute_file_hash,
    is_up_to_date,
    load_cache,
    save_cache,
)


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main(
    hierarchy_path: Path,
    docs_dir: Path,
    scripts_dir: Path,
    *,
    schematics: bool = False,
    force: bool = False,
) -> None:
    hierarchy = json.loads(hierarchy_path.read_text())

    cache_path     = docs_dir / ".extract_cache.json"
    extractor_hash = compute_extractor_hash(scripts_dir)
    cache          = None if force else load_cache(cache_path)
    updated_cache  = ExtractCache(extractor_hash=extractor_hash)

    for name, mod in hierarchy["modules"].items():
        src_file   = mod["file"]
        module_dir = docs_dir / "modules" / name
        proc_dir   = module_dir / "processes"

        if is_up_to_date(cache, name, src_file, extractor_hash):
            print(f"Skipping:   {name} (unchanged)")
            updated_cache.modules[name] = cache.modules[name]
            continue

        print(f"Extracting: {name} ({src_file})...")

        run(["python", str(scripts_dir / "extract_fsm.py"),
             src_file, name, str(module_dir)])

        run(["python", str(scripts_dir / "extract_processes.py"),
             src_file, str(proc_dir)])

        run(["python", str(scripts_dir / "extract_cdc.py"),
             src_file, name, str(module_dir)])

        if schematics:
            all_src = [m["file"] for m in hierarchy["modules"].values()]
            run(["python", str(scripts_dir / "generate_schematic.py"),
                 src_file, name, str(module_dir)] + all_src)

        run(["python", str(scripts_dir / "extract_block.py"),
             src_file, name, str(module_dir)])

        run(["python", str(scripts_dir / "extract_reset.py"),
             src_file, name, str(module_dir)])

        updated_cache.modules[name] = compute_file_hash(Path(src_file))

    save_cache(updated_cache, cache_path)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Usage: run_extract.py <hierarchy.json> <docs_dir> <scripts_dir> [--schematics] [--force]")

    main(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3]),
        schematics="--schematics" in sys.argv[4:],
        force="--force" in sys.argv[4:],
    )
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest scripts/hdl_autodoc/tests/test_run_extract.py \
       scripts/hdl_autodoc/tests/test_extract_cache.py -v
```

Expected: 14 passed

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest
```

Expected: all tests pass (count will have increased by 14)

- [ ] **Step 6: Commit**

```bash
git add scripts/hdl_autodoc/run_extract.py \
        scripts/hdl_autodoc/tests/test_run_extract.py
git commit -m "feat: integrate extraction cache into run_extract — skip unchanged modules"
```

---

## Task 3: Makefile updates

**Files:**
- Modify: `Makefile`

### Background

Three changes needed:
1. Add `$(if $(FORCE),--force)` to the `extract` target so `make extract FORCE=1` bypasses the cache.
2. Add `.extract_cache.json` to `clean-generated` so `make clean-generated` removes the cache file.
3. Add a `FORCE=1` line to the `help` target.

No new tests — Makefile changes are verified manually.

- [ ] **Step 1: Update the `extract` target (line 93–96)**

Current:
```makefile
extract: scaffold
	python $(AUTODOC_SCRIPTDIR)/run_extract.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) $(AUTODOC_SCRIPTDIR) \
		$(if $(filter 1,$(SCHEMATICS)),--schematics)
```

Replace with:
```makefile
extract: scaffold
	python $(AUTODOC_SCRIPTDIR)/run_extract.py \
		$(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) $(AUTODOC_SCRIPTDIR) \
		$(if $(filter 1,$(SCHEMATICS)),--schematics) $(if $(FORCE),--force)
```

- [ ] **Step 2: Add cache file to `clean-generated` (after the `coverage.rst` line, around line 145)**

Current:
```makefile
	rm -f  $(AUTODOC_SOURCEDIR)/coverage.rst
```

Replace with:
```makefile
	rm -f  $(AUTODOC_SOURCEDIR)/coverage.rst
	rm -f  $(AUTODOC_SOURCEDIR)/.extract_cache.json
```

- [ ] **Step 3: Update `help` target (after the `make extract` line, around line 60)**

Current:
```makefile
	@echo "  make extract              Extract FSM + process docs (runs scaffold first)"
```

Replace with:
```makefile
	@echo "  make extract              Extract FSM + process docs (runs scaffold first)"
	@echo "  make extract FORCE=1      Force re-extraction of all modules (bypass cache)"
```

- [ ] **Step 4: Verify the full test suite still passes**

```bash
pytest
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add Makefile
git commit -m "feat: add FORCE=1 flag and cache cleanup to Makefile extract target"
```
