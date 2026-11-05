"""Tests for extract_cache.py."""

import json

from extract_cache import (
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


# ── what the cache key covers (audit: stale pages after a dependency changed) ─

def test_extractor_hash_covers_the_helper_modules_the_extractors_import(tmp_path):
    (tmp_path / "extract_fsm.py").write_text("# fsm")
    helper = tmp_path / "hdl_scan.py"
    helper.write_text("# v1")
    h1 = compute_extractor_hash(tmp_path)
    helper.write_text("# v2")
    assert compute_extractor_hash(tmp_path) != h1


def test_extractor_hash_ignores_subdirectories_such_as_tests(tmp_path):
    (tmp_path / "extract_fsm.py").write_text("# fsm")
    (tmp_path / "tests").mkdir()
    h1 = compute_extractor_hash(tmp_path)
    (tmp_path / "tests" / "test_x.py").write_text("# a test")
    assert compute_extractor_hash(tmp_path) == h1


def test_extractor_hash_covers_extra_input_files_and_skips_missing_ones(tmp_path):
    (tmp_path / "extract_fsm.py").write_text("# fsm")
    extra = tmp_path / "axis_if.sv"
    extra.write_text("interface a; endinterface")
    h1 = compute_extractor_hash(tmp_path, [extra, tmp_path / "missing.toml"])
    extra.write_text("interface a; logic x; endinterface")
    assert compute_extractor_hash(tmp_path, [extra, tmp_path / "missing.toml"]) != h1
    assert compute_extractor_hash(tmp_path, [tmp_path / "missing.toml"]) == compute_extractor_hash(tmp_path)


def test_module_hash_without_dependencies_is_the_file_hash(tmp_path):
    from extract_cache import compute_module_hash
    src = tmp_path / "a.vhd"
    src.write_text("entity a is end;")
    assert compute_module_hash(src, []) == compute_file_hash(src)


def test_module_hash_changes_when_a_dependency_changes(tmp_path):
    from extract_cache import compute_module_hash
    src, child = tmp_path / "a.vhd", tmp_path / "child.vhd"
    src.write_text("entity a is end;")
    child.write_text("entity child is end;")
    h1 = compute_module_hash(src, [str(child)])
    child.write_text("entity child is port (x : in bit); end;")
    assert compute_module_hash(src, [str(child)]) != h1


def test_is_up_to_date_follows_the_dependencies(tmp_path):
    from extract_cache import compute_module_hash
    src, child = tmp_path / "a.vhd", tmp_path / "child.vhd"
    src.write_text("entity a is end;")
    child.write_text("entity child is end;")
    cache = ExtractCache("h", {"a": compute_module_hash(src, [str(child)])})
    assert is_up_to_date(cache, "a", str(src), "h", [str(child)]) is True
    child.write_text("changed")
    assert is_up_to_date(cache, "a", str(src), "h", [str(child)]) is False
