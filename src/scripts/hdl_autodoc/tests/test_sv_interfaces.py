"""Tests for sv_interfaces.py: interface names, members, modports, interface ports."""

from pathlib import Path

from sv_interfaces import (
    collect_interfaces,
    find_interface_names,
    find_interface_port,
    parse_interface,
)

AXIS = """\
// AXI4-Stream bundle.
interface axis_if #(parameter W = 8) (input logic clk);
    // Payload.
    logic [W-1:0] tdata;
    logic         tvalid, tready;   // Handshake.
    types_pkg::byte_t user;
    parameter int X = 1;

    modport master (output tdata, tvalid, input tready);
    modport slave  (input  tdata, tvalid, output tready);
endinterface
"""


# ── find_interface_names ─────────────────────────────────────────────────────

def test_find_interface_names_finds_definitions_only():
    text = AXIS + "interface bus_if; endinterface\nmodule m; endmodule\n"
    assert find_interface_names(text) == {"axis_if", "bus_if"}


def test_find_interface_names_ignores_comments_and_interface_class():
    text = "// interface fake_if;\n/* interface other_if; */\ninterface class base_c;\nendclass\n"
    assert find_interface_names(text) == set()


# ── parse_interface ──────────────────────────────────────────────────────────

def test_parse_interface_members_types_widths_and_comments():
    iface = parse_interface(AXIS, "axis_if")
    by_name = {m["name"]: m for m in iface["members"]}
    assert list(by_name) == ["tdata", "tvalid", "tready", "user"]
    assert by_name["tdata"]["range"] == "W-1:0"
    assert by_name["tdata"]["comment"] == "Payload."          # preceding comment
    assert by_name["tvalid"]["comment"] == "Handshake."       # inline, shared by the line
    assert by_name["tready"]["comment"] == "Handshake."
    assert by_name["user"]["type"] == "types_pkg::byte_t"


def test_parse_interface_skips_header_ports_modports_and_parameters():
    names = [m["name"] for m in parse_interface(AXIS, "axis_if")["members"]]
    assert "clk" not in names and "master" not in names and "X" not in names


def test_parse_interface_modport_directions_carry_over_until_changed():
    iface = parse_interface(AXIS, "axis_if")
    assert iface["modports"]["master"] == {"tdata": "out", "tvalid": "out", "tready": "in"}
    assert iface["modports"]["slave"] == {"tdata": "in", "tvalid": "in", "tready": "out"}


def test_parse_interface_returns_none_for_an_unknown_name():
    assert parse_interface(AXIS, "nope_if") is None


# ── collect_interfaces ───────────────────────────────────────────────────────

def test_collect_interfaces_across_files_first_definition_wins(tmp_path):
    a = tmp_path / "a.sv"
    a.write_text("interface x_if;\n    logic a;\nendinterface\n")
    b = tmp_path / "b.sv"
    b.write_text("interface x_if;\n    logic b;\nendinterface\n"
                 "interface y_if;\n    logic c;\nendinterface\n")
    found = collect_interfaces([a, b, tmp_path / "missing.sv"])
    assert set(found) == {"x_if", "y_if"}
    assert [m["name"] for m in found["x_if"]["members"]] == ["a"]


# ── find_interface_port ──────────────────────────────────────────────────────

def test_find_interface_port_forms():
    names = {"axil_if", "axis_if"}
    assert find_interface_port("    axil_if.slave s_axil,", names) == ("axil_if", "slave", "s_axil")
    assert find_interface_port("    axis_if m_axis", names) == ("axis_if", "", "m_axis")
    assert find_interface_port("    axis_if.master m_axis  // Out.", names) == ("axis_if", "master", "m_axis")
    assert find_interface_port("    axis_if.master m_axis);", names) == ("axis_if", "master", "m_axis")


def test_find_interface_port_requires_a_known_interface_name():
    """A plain type name is never mistaken for an interface."""
    assert find_interface_port("    byte_t data,", {"axis_if"}) is None
    assert find_interface_port("    axis_if m_axis,", set()) is None


def test_find_interface_port_rejects_non_ports():
    names = {"axis_if"}
    assert find_interface_port("    input logic clk,", names) is None
    assert find_interface_port("    axis_if s (.clk(clk));", names) is None   # instance
