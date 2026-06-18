"""
test_extract_registers.py
-------------------------
Tests for extract_registers.py.

Covers:
  1.  Offset calculation for 32-bit bus width
  2.  r_w mode renders as r/w
  3.  wpulse mode renders correctly
  4.  r (read-only) mode renders correctly
  5.  bit field type appears in field table
  6.  bit_vector field with width renders as bit_vector(N)
  7.  integer field shows Range: min–max in description
  8.  enumeration field produces nested list-table with all enum values
  9.  config.yml with bus_width: 64 produces 8-byte-stride offsets
  10. Missing config.yml falls back to 32-bit bus width
"""

import pytest
from pathlib import Path

from extract_registers import generate_registers_rst


def _two_regs(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[rega]\nmode = "r_w"\ndescription = "First."\n'
        '[regb]\nmode = "r"\ndescription = "Second."\n'
    )
    return toml


# ── Test 1: Offset calculation ────────────────────────────────────────────────

def test_offset_calculation_32bit(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[rega]\nmode = "r_w"\ndescription = "First."\n'
        '[regb]\nmode = "r"\ndescription = "Second."\n'
        '[regc]\nmode = "w"\ndescription = "Third."\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "0x00" in rst
    assert "0x04" in rst
    assert "0x08" in rst


# ── Test 2: r_w mode ──────────────────────────────────────────────────────────

def test_r_w_renders_as_r_slash_w(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text('[reg]\nmode = "r_w"\ndescription = "A register."\n')
    rst = generate_registers_rst(toml, "test")
    assert "r/w" in rst


# ── Test 3: wpulse mode ───────────────────────────────────────────────────────

def test_wpulse_mode(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text('[reg]\nmode = "wpulse"\ndescription = "A register."\n')
    rst = generate_registers_rst(toml, "test")
    assert "wpulse" in rst


# ── Test 4: r mode ────────────────────────────────────────────────────────────

def test_r_mode(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text('[reg]\nmode = "r"\ndescription = "A register."\n')
    rst = generate_registers_rst(toml, "test")
    assert "     - r\n" in rst


# ── Test 5: bit field ─────────────────────────────────────────────────────────

def test_bit_field_type(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.flag]\ntype = "bit"\ndescription = "A flag."\ndefault_value = "0"\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "flag" in rst
    assert "bit" in rst


# ── Test 6: bit_vector field ──────────────────────────────────────────────────

def test_bit_vector_field_with_width(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.data]\ntype = "bit_vector"\nwidth = 16\ndescription = "Data."\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "bit_vector(16)" in rst


# ── Test 7: integer field with range ─────────────────────────────────────────

def test_integer_field_shows_range(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.value]\ntype = "integer"\ndescription = "A value."\n'
        'min_value = 1\nmax_value = 255\ndefault_value = 1\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert "Range" in rst
    assert "255" in rst


# ── Test 8: enumeration with nested list-table ────────────────────────────────

def test_enumeration_field_produces_nested_list_table(tmp_path):
    toml = tmp_path / "regs_test.toml"
    toml.write_text(
        '[reg]\nmode = "r_w"\ndescription = "A register."\n'
        '[reg.mode_sel]\ntype = "enumeration"\ndescription = "Mode."\n'
        'default_value = "fast"\n'
        '[reg.mode_sel.element]\nfast = "Fast mode."\nslow = "Slow mode."\n'
    )
    rst = generate_registers_rst(toml, "test")
    assert rst.count(".. list-table::") >= 2  # summary table + inner enum table
    assert "fast" in rst
    assert "slow" in rst
    assert "Fast mode." in rst


# ── Test 9: 64-bit bus width ──────────────────────────────────────────────────

def test_64bit_bus_width_produces_8_byte_stride(tmp_path):
    (tmp_path / "config.yml").write_text(
        "bus_width: 64\naddress_width: 16\nprotocol: axi4lite\n"
    )
    rst = generate_registers_rst(_two_regs(tmp_path), "test")
    assert "0x00" in rst
    assert "0x08" in rst


# ── Test 10: Missing config.yml defaults to 32-bit ───────────────────────────

def test_missing_config_yml_defaults_to_32bit(tmp_path):
    rst = generate_registers_rst(_two_regs(tmp_path), "test")
    assert "0x00" in rst
    assert "0x04" in rst
