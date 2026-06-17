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
            assert cache is not None  # proven by is_up_to_date
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

        # Generate RTL schematic before extract_block so the SVG is available
        # for inclusion in the block diagram RST.  All source files are passed
        # so that ghdl can resolve cross-unit references (e.g. top-level entities
        # that instantiate submodules).
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
