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
import pytest

from run_extract import dependency_files, main, registers_dir_for


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


def test_registers_dir_defaults_to_two_levels_above_docs_dir(tmp_path, monkeypatch):
    """Unset: the old docs/hdl_autodoc layout default is kept."""
    monkeypatch.delenv("AUTODOC_REGISTERS_DIR", raising=False)
    docs_dir = tmp_path / "docs" / "hdl_autodoc"
    assert registers_dir_for(docs_dir) == tmp_path / "registers"


def test_registers_dir_env_override_wins_over_layout_default(tmp_path, monkeypatch):
    """AUTODOC_REGISTERS_DIR is used verbatim, whatever the docs layout."""
    custom = tmp_path / "out" / "regs"
    monkeypatch.setenv("AUTODOC_REGISTERS_DIR", str(custom))
    assert registers_dir_for(tmp_path / "docs" / "hdl_autodoc") == custom
    assert registers_dir_for(tmp_path / "somewhere" / "else") == custom


def test_main_extracts_registers_from_overridden_dir(tmp_path, monkeypatch):
    """regs_<module>.toml is picked up from the override directory, not registers/."""
    src_file = tmp_path / "blinky.vhd"
    src_file.write_text("entity blinky is end entity;")
    h_json = _make_hierarchy(tmp_path, src_file)
    docs_dir = tmp_path / "docs" / "hdl_autodoc"
    (docs_dir / "modules" / "blinky").mkdir(parents=True)

    custom = tmp_path / "out" / "regs"
    custom.mkdir(parents=True)
    (custom / "regs_blinky.toml").write_text("[ctrl]\n")
    # A decoy at the default location must be ignored when the override is set.
    (tmp_path / "registers").mkdir()
    (tmp_path / "registers" / "regs_blinky.toml").write_text("[decoy]\n")
    monkeypatch.setenv("AUTODOC_REGISTERS_DIR", str(custom))

    calls = []
    scripts_dir = Path(__file__).parents[1]
    with patch("run_extract.run", side_effect=lambda cmd: calls.append(cmd)):
        main(h_json, docs_dir, scripts_dir, force=True)

    reg_calls = [c for c in calls if c[1].endswith("extract_registers.py")]
    assert len(reg_calls) == 1
    assert reg_calls[0][2] == str(custom / "regs_blinky.toml")


def _schematic_calls(tmp_path, hierarchy_extra: dict) -> list[list[str]]:
    src_file = tmp_path / "blinky.sv"
    src_file.write_text("module blinky; endmodule")
    hierarchy = {"modules": {"blinky": {"file": str(src_file), "children": [], "parents": []}},
                 **hierarchy_extra}
    h_json = tmp_path / "hierarchy.json"
    h_json.write_text(json.dumps(hierarchy))
    docs_dir = tmp_path / "docs" / "hdl_autodoc"
    (docs_dir / "modules" / "blinky").mkdir(parents=True)
    calls = []
    with patch("run_extract.run", side_effect=lambda cmd: calls.append(cmd)):
        main(h_json, docs_dir, Path(__file__).parents[1], schematics=True, force=True)
    return [c for c in calls if c[1].endswith("generate_schematic.py")]


def test_schematics_get_support_files_in_order_after_dependencies(tmp_path):
    """Each module's schematic call carries every support file, as ordered --support pairs."""
    (call,) = _schematic_calls(tmp_path, {"support_files": ["src/aes_pkg.sv", "src/bus_if.sv"]})
    assert call[-4:] == ["--support", "src/aes_pkg.sv", "--support", "src/bus_if.sv"]


def test_schematics_tolerate_a_hierarchy_without_support_files(tmp_path):
    """Older hierarchy.json files lack the key: no --support arguments, no error."""
    (call,) = _schematic_calls(tmp_path, {})
    assert "--support" not in call
