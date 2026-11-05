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


def compute_extractor_hash(scripts_dir: Path, extra_files=()) -> str:
    """
    Return one SHA-256 over every top-level script in `scripts_dir` (the extractors and the
    helper modules they import, so a fix in any of them invalidates the cache) and over
    `extra_files`, the project inputs every module's pages depend on (SystemVerilog support
    files, bus_groups.toml).  Files that do not exist are skipped.
    """
    h = hashlib.sha256()
    for p in sorted(Path(scripts_dir).glob("*.py")):
        h.update(p.read_bytes())
    for f in sorted(Path(f) for f in extra_files):
        if f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()


def compute_module_hash(src_file, extra_files=()) -> str:
    """
    Fingerprint of everything one module's pages are built from: its own source file and
    `extra_files` (the child modules its schematic is synthesised from).  With no extra
    files it is the file hash.
    """
    if not extra_files:
        return compute_file_hash(Path(src_file))
    h = hashlib.sha256(Path(src_file).read_bytes())
    for f in map(Path, extra_files):
        if f.is_file():
            h.update(f.read_bytes())
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
    extra_files=(),
) -> bool:
    """Return True only if name's source (and `extra_files`) and the extractor scripts are unchanged."""
    if cache is None:
        return False
    if cache.extractor_hash != extractor_hash:
        return False
    cached_src_hash = cache.modules.get(name)
    if cached_src_hash is None:
        return False
    return cached_src_hash == compute_module_hash(src_file, extra_files)
