# Incremental Extraction — Design Spec

**Date:** 2026-06-17
**Status:** Approved

---

## Overview

Add content-hash-based caching to `run_extract.py` so that modules whose source files have not changed since the last run are skipped. This reduces wall-clock time on large designs and prevents extraction from clobbering output for unchanged modules.

---

## Architecture & Data Flow

A new helper module `scripts/hdl_autodoc/extract_cache.py` holds all cache logic. `run_extract.py` stays as the thin orchestrator it is today and calls into it.

Flow on `make extract`:

1. `run_extract.py` loads `.extract_cache.json` from `docs_dir` (or treats cache as empty on any error)
2. Computes a single **extractor hash** — SHA-256 of the sorted contents of all `extract_*.py` + `generate_schematic.py` scripts concatenated. If this hash differs from the cached value, all modules are treated as stale.
3. For each module: if the module's source file hash matches the cached hash **and** the extractor hash is current, print a skip line and continue. Otherwise run all extractors, then update the module's cache entry.
4. Saves the updated cache after the loop.

`--force` bypasses all cache checks and re-extracts every module.

---

## Cache File

**Path:** `docs/hdl_autodoc/.extract_cache.json`

```json
{
  "version": 1,
  "extractor_hash": "a3f9c2...",
  "modules": {
    "blinky":         {"src_hash": "d4e1b7..."},
    "cfg_sync":       {"src_hash": "9a2c55..."},
    "pwm_controller": {"src_hash": "1f83de..."}
  }
}
```

| Field | Purpose |
|---|---|
| `version` | Integer bumped in code when extraction output format changes; mismatch → treat cache as empty |
| `extractor_hash` | SHA-256 of all extractor script contents concatenated; mismatch → all modules stale |
| `modules[name].src_hash` | SHA-256 of that module's source file contents |

---

## `extract_cache.py` Module

```python
CACHE_VERSION = 1

@dataclass
class ExtractCache:
    extractor_hash: str
    modules: dict[str, str]   # name → src_hash

def load_cache(path: Path) -> ExtractCache | None
    # Returns None on: missing file, version mismatch, JSON parse error

def save_cache(cache: ExtractCache, path: Path) -> None

def compute_file_hash(path: Path) -> str
    # SHA-256 of file contents

def compute_extractor_hash(scripts_dir: Path) -> str
    # SHA-256 of sorted(extract_*.py + generate_schematic.py) contents concatenated

def is_up_to_date(cache: ExtractCache | None, name: str, src_file: str, extractor_hash: str) -> bool
    # Returns False if: cache is None, extractor_hash differs, module src_hash missing or differs
```

---

## `run_extract.py` Changes

- Accept `--force` flag (follows existing `--schematics` pattern)
- Load cache and compute extractor hash once before the module loop
- Per module:
  - If `--force` or `not is_up_to_date(...)`: run extractors, update `cache.modules[name]`
  - Otherwise: print skip line and continue
- Save cache after the loop

### Terminal Output

```
Extracting: blinky (src/blinky.vhd)...
Skipping:   cfg_sync (unchanged)
Extracting: pwm_controller (src/pwm_controller.vhd)...
```

---

## Makefile Changes

```makefile
extract: scaffold
    python $(AUTODOC_SCRIPTDIR)/run_extract.py \
        $(AUTODOC_HIERARCHY_JSON) $(AUTODOC_SOURCEDIR) $(AUTODOC_SCRIPTDIR) \
        $(if $(FORCE),--force) $(if $(SCHEMATICS),--schematics)
```

- `make extract FORCE=1` — bypass cache, re-extract all modules
- `clean-generated` gains: `rm -f $(AUTODOC_SOURCEDIR)/.extract_cache.json`
- `help` target updated with `FORCE=1` note

---

## Testing

New file: `scripts/hdl_autodoc/tests/test_extract_cache.py`

All tests use `tmp_path` fixtures.

| # | Test |
|---|---|
| 1 | `load_cache` returns `None` when file is missing |
| 2 | `load_cache` returns `None` on version mismatch |
| 3 | `load_cache` returns `None` on JSON parse error |
| 4 | Save/load roundtrip preserves all fields |
| 5 | `is_up_to_date` returns `False` when cache is `None` |
| 6 | `is_up_to_date` returns `False` when extractor hash differs |
| 7 | `is_up_to_date` returns `False` when module src hash differs |
| 8 | `is_up_to_date` returns `False` when module name not in cache |
| 9 | `is_up_to_date` returns `True` when everything matches |
| 10 | `compute_extractor_hash` changes when a script file changes |
| 11 | Integration: module skipped on second run when source unchanged |
| 12 | Integration: module re-extracted after source file changes |

`run_extract.py` tests (added to existing test file):

| # | Test |
|---|---|
| 13 | `--force` re-extracts all modules even with a warm cache |
| 14 | Skip line printed for unchanged module; extract line for changed module |
