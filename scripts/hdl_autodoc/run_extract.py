#!/usr/bin/env python3
"""
run_extract.py
--------------
Reads hierarchy.json and runs extract_fsm.py + extract_processes.py
for every module. Called by the Makefile extract target.

Usage:
    python scripts/run_extract.py <hierarchy.json> <docs_dir> <scripts_dir>
"""

import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]):
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit("Usage: run_extract.py <hierarchy.json> <docs_dir> <scripts_dir>")

    hierarchy_path = Path(sys.argv[1])
    docs_dir       = Path(sys.argv[2])
    scripts_dir    = Path(sys.argv[3])

    hierarchy = json.loads(hierarchy_path.read_text())

    for name, mod in hierarchy["modules"].items():
        src_file   = mod["file"]
        module_dir = docs_dir / "modules" / name
        proc_dir   = module_dir / "processes"

        print(f"Extracting: {name} ({src_file})...")

        run(["python", str(scripts_dir / "extract_fsm.py"),
             src_file, name, str(module_dir)])

        run(["python", str(scripts_dir / "extract_processes.py"),
             src_file, str(proc_dir)])

        run(["python", str(scripts_dir / "extract_cdc.py"),
             src_file, name, str(module_dir)])

        run(["python", str(scripts_dir / "extract_block.py"),
             src_file, name, str(module_dir)])