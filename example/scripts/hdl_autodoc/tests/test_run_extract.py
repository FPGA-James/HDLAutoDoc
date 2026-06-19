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
