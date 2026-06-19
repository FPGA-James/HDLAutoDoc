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
