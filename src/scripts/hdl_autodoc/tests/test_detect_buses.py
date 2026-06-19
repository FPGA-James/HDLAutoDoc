"""
test_detect_buses.py
--------------------
Tests for detect_buses.py.

Covers all 11 cases from the spec:
  1.  AXI4-Full Subordinate detected from s_axi_ prefix
  2.  AXI4-Lite Subordinate detected when burst signals absent
  3.  AXI4-Stream detected from axis_ prefix
  4.  APB Subordinate detected from apb_ prefix
  5.  Wishbone detected from wb_ prefix
  6.  Custom group matched by prefix from TOML
  7.  Prefix with < 3 ports not grouped
  8.  Prefix with < 50% signal match not grouped
  9.  group_ports preserves order of remaining ports
  10. Missing TOML path → no custom groups (no error)
  11. Malformed TOML → no custom groups (no error)
"""

import pytest
from pathlib import Path

from detect_buses import BusGroup, group_ports


def _port(name: str, dir_: str = "in", type_: str = "std_logic") -> dict:
    return {"name": name, "dir": dir_, "type": type_, "range": None, "comment": ""}


# ── Test 1: AXI4-Full Subordinate ────────────────────────────────────────────

def test_axi4_full_subordinate():
    ports = [_port(f"s_axi_{sig}") for sig in [
        "awvalid", "awready", "awaddr", "awlen", "awsize", "awburst",
        "wvalid", "wready", "wdata", "wstrb", "wlast",
        "bvalid", "bready", "bresp",
        "arvalid", "arready", "araddr", "arlen", "arsize", "arburst",
        "rvalid", "rready", "rdata", "rresp", "rlast",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "s_axi"
    assert groups[0].bus_type == "AXI4-Full Subordinate"
    assert remaining == []


# ── Test 2: AXI4-Lite Subordinate (no burst signals) ─────────────────────────

def test_axi4_lite_subordinate():
    ports = [_port(f"s_axi_{sig}") for sig in [
        "awvalid", "awready", "awaddr",
        "wvalid", "wready", "wdata", "wstrb",
        "bvalid", "bready", "bresp",
        "arvalid", "arready", "araddr",
        "rvalid", "rready", "rdata", "rresp",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "s_axi"
    assert groups[0].bus_type == "AXI4-Lite Subordinate"
    assert remaining == []


# ── Test 3: AXI4-Stream ───────────────────────────────────────────────────────

def test_axi4_stream():
    ports = [_port(f"axis_{sig}") for sig in [
        "tvalid", "tready", "tdata", "tlast",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "axis"
    assert groups[0].bus_type == "AXI4-Stream"
    assert remaining == []


def test_axi4_stream_manager():
    ports = [_port(f"m_axis_{sig}") for sig in [
        "tvalid", "tready", "tdata", "tlast",
    ]]
    groups, _ = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].bus_type == "AXI4-Stream Manager"


def test_axi4_stream_subordinate():
    ports = [_port(f"s_axis_{sig}") for sig in [
        "tvalid", "tready", "tdata", "tlast",
    ]]
    groups, _ = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].bus_type == "AXI4-Stream Subordinate"


# ── Test 4: APB Subordinate ───────────────────────────────────────────────────

def test_apb_subordinate():
    ports = [_port(f"apb_{sig}") for sig in [
        "psel", "penable", "paddr", "pwdata", "prdata", "pwrite", "pready",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "apb"
    assert groups[0].bus_type == "APB Subordinate"
    assert remaining == []


# ── Test 5: Wishbone ──────────────────────────────────────────────────────────

def test_wishbone():
    ports = [_port(f"wb_{sig}") for sig in [
        "cyc", "stb", "ack", "adr", "dat_i", "dat_o", "we",
    ]]
    groups, remaining = group_ports(ports)
    assert len(groups) == 1
    assert groups[0].prefix == "wb"
    assert groups[0].bus_type == "Wishbone"
    assert remaining == []


# ── Test 6: Custom group from TOML ────────────────────────────────────────────

def test_custom_group_from_toml(tmp_path):
    toml_file = tmp_path / "bus_groups.toml"
    toml_file.write_text('[[group]]\nprefix = "dma"\nlabel = "DMA Write Master"\n')
    ports = [_port(f"dma_{sig}") for sig in ["addr", "data", "valid"]]
    groups, remaining = group_ports(ports, toml_path=toml_file)
    assert len(groups) == 1
    assert groups[0].prefix == "dma"
    assert groups[0].bus_type == "DMA Write Master"
    assert remaining == []


# ── Test 7: Prefix with < 3 ports not grouped ────────────────────────────────

def test_fewer_than_three_ports_not_grouped():
    ports = [_port("clk"), _port("s_axi_awvalid"), _port("s_axi_awready")]
    groups, remaining = group_ports(ports)
    assert groups == []
    assert len(remaining) == 3


# ── Test 8: < 50% signal match not grouped ───────────────────────────────────

def test_low_signal_match_not_grouped():
    # Only 3 of 17 AXI4-Lite signals — below 50% threshold
    ports = [_port(f"s_axi_{sig}") for sig in ["awvalid", "wdata", "rresp"]]
    groups, remaining = group_ports(ports)
    assert groups == []
    assert len(remaining) == 3


# ── Test 9: Remaining ports preserve original order ──────────────────────────

def test_remaining_ports_preserve_order():
    ports = [_port("clk"), _port("rst"), _port("en")]
    _, remaining = group_ports(ports)
    assert [p["name"] for p in remaining] == ["clk", "rst", "en"]


# ── Test 10: Missing TOML path → no error ────────────────────────────────────

def test_missing_toml_path_no_error():
    ports = [_port("clk"), _port("rst"), _port("en")]
    groups, remaining = group_ports(ports, toml_path=None)
    assert groups == []
    assert len(remaining) == 3


def test_missing_toml_file_no_error(tmp_path):
    absent = tmp_path / "bus_groups.toml"
    ports = [_port("clk"), _port("rst"), _port("en")]
    groups, remaining = group_ports(ports, toml_path=absent)
    assert groups == []


# ── Test 11: Malformed TOML → no error ───────────────────────────────────────

def test_malformed_toml_no_error(tmp_path):
    bad_toml = tmp_path / "bus_groups.toml"
    bad_toml.write_text("[[group\nthis is not valid toml!!!")
    ports = [_port("clk"), _port("rst"), _port("en")]
    groups, remaining = group_ports(ports, toml_path=bad_toml)
    assert groups == []


# ── Test 12: Custom group missing label is silently skipped ──────────────────

def test_custom_group_missing_label_no_error(tmp_path):
    """TOML group entry without a label is silently skipped."""
    toml_file = tmp_path / "bus_groups.toml"
    toml_file.write_text('[[group]]\nprefix = "dma"\n')  # no label field
    ports = [_port(f"dma_{sig}") for sig in ["addr", "data", "valid"]]
    groups, remaining = group_ports(ports, toml_path=toml_file)
    assert groups == []
    assert len(remaining) == 3
