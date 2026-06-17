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
