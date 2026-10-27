"""Tests for the registers directory resolution in scripts/registers/generate.py."""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("hdl_registers")  # generate.py imports it at module level

GENERATE = Path(__file__).parents[2] / "registers" / "generate.py"


def _load():
    spec = importlib.util.spec_from_file_location("registers_generate", GENERATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)   # defines functions only; generation is under __main__
    return module


def test_registers_dir_defaults_to_cwd_registers(tmp_path, monkeypatch):
    """Unset: registers/ in the working directory (unchanged behaviour)."""
    monkeypatch.delenv("AUTODOC_REGISTERS_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    assert _load().registers_dir() == tmp_path / "registers"


def test_registers_dir_honours_env_override(tmp_path, monkeypatch):
    """AUTODOC_REGISTERS_DIR relocates both the input TOML and the generated/ output."""
    custom = tmp_path / "out" / "regs"
    monkeypatch.setenv("AUTODOC_REGISTERS_DIR", str(custom))
    monkeypatch.chdir(tmp_path)
    module = _load()
    assert module.registers_dir() == custom
    assert module.THIS_DIR == custom
    assert module.OUTPUT_DIR == custom / "generated"
