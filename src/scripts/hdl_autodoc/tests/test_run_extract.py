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
from run_extract import dependency_files, main


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


def test_dependency_files_are_transitive_leaves_first_and_exclude_unrelated():
    """Only a module's own (indirect) children are passed on, deepest first."""
    h = {"top": "top", "modules": {
        "top":  {"file": "src/top.vhd",  "children": ["mid", "ext"]},
        "mid":  {"file": "src/mid.vhd",  "children": ["leaf"]},
        "leaf": {"file": "src/leaf.vhd", "children": []},
        "sv":   {"file": "src/sv.sv",    "children": []},   # unrelated to top's VHDL chain
    }}
    assert dependency_files(h, "top") == ["src/leaf.vhd", "src/mid.vhd"]
    assert dependency_files(h, "leaf") == []
    assert "src/sv.sv" not in dependency_files(h, "mid")
