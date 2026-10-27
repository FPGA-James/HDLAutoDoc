"""
test_extract_block.py
---------------------
Tests for extract_block.py.

Covers:
  - VHDL port extraction including std_logic, std_logic_vector (with range),
    and inline vs preceding-line comment styles.
  - VHDL generic extraction with name, type, default, and comment.
  - SystemVerilog port extraction with direction normalisation (input→in).
  - SystemVerilog parameter and localparam extraction.
  - Width label computation for numeric and parametric ranges.
  - Graphviz dot output structure (input nodes left, output nodes right).
  - RST output contains port table and generics table.
"""

import pytest

from extract_block import (
    _width_label,
    interface_side,
    extract_generics_vhdl,
    extract_params_sv,
    extract_ports_sv,
    extract_ports_vhdl,
    extract_signals_sv,
    extract_signals_vhdl,
    write_dot_block,
    write_rst_block,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

VHDL_ENTITY = """\
entity my_mod is
    generic (
        WIDTH : integer := 8;   -- Bus width in bits.
        DEPTH : natural := 16
    );
    port (
        -- System clock.
        clk       : in  std_logic;
        rst       : in  std_logic;  -- Synchronous reset.
        data_i    : in  std_logic_vector(7 downto 0);
        valid_i   : in  std_logic;
        data_o    : out std_logic_vector(7 downto 0);
        valid_o   : out std_logic;
        bus_io    : inout std_logic_vector(3 downto 0)
    );
end entity my_mod;
"""

SV_MODULE = """\
module my_sv_mod #(
    parameter int WIDTH = 8,   // Data width
    parameter int DEPTH = 32,
    localparam int MAX = 255   // Max counter value
)(
    input  logic              clk,       // System clock.
    input  logic              rst,
    input  logic [WIDTH-1:0]  data_i,    // Input data.
    output logic              valid_o,
    output logic [WIDTH-1:0]  data_o
);
endmodule
"""


# ─────────────────────────────────────────────────────────────────────────────
# VHDL port extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_vhdl_port_count():
    """All ports in the entity port list are extracted."""
    ports = extract_ports_vhdl(VHDL_ENTITY)
    assert len(ports) == 7


def test_vhdl_port_directions():
    """Port directions are extracted correctly as 'in', 'out', 'inout'."""
    ports  = extract_ports_vhdl(VHDL_ENTITY)
    by_name = {p["name"]: p for p in ports}
    assert by_name["clk"]["dir"]    == "in"
    assert by_name["data_o"]["dir"] == "out"
    assert by_name["bus_io"]["dir"] == "inout"


def test_vhdl_port_type_std_logic():
    """std_logic ports have the correct type and no range."""
    ports   = extract_ports_vhdl(VHDL_ENTITY)
    by_name = {p["name"]: p for p in ports}
    assert by_name["clk"]["type"]  == "std_logic"
    assert by_name["clk"]["range"] == ""


def test_vhdl_port_type_std_logic_vector():
    """std_logic_vector ports have the type and the downto range captured."""
    ports   = extract_ports_vhdl(VHDL_ENTITY)
    by_name = {p["name"]: p for p in ports}
    assert by_name["data_i"]["type"]  == "std_logic_vector"
    assert "7 downto 0" in by_name["data_i"]["range"]


def test_vhdl_port_preceding_comment():
    """A comment on the line directly above a port is used as the description."""
    ports   = extract_ports_vhdl(VHDL_ENTITY)
    by_name = {p["name"]: p for p in ports}
    assert "System clock" in by_name["clk"]["comment"]


def test_vhdl_port_inline_comment():
    """A comment on the same line as the port declaration is used as the description."""
    ports   = extract_ports_vhdl(VHDL_ENTITY)
    by_name = {p["name"]: p for p in ports}
    assert "Synchronous reset" in by_name["rst"]["comment"]


def test_vhdl_no_port_section_returns_empty():
    """A file with no port(...) section returns an empty list."""
    assert extract_ports_vhdl("entity foo is end entity foo;\n") == []


# ─────────────────────────────────────────────────────────────────────────────
# VHDL generic extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_vhdl_generic_count():
    """Both generics are extracted."""
    generics = extract_generics_vhdl(VHDL_ENTITY)
    assert len(generics) == 2


def test_vhdl_generic_fields():
    """Name, type, and default value are correctly extracted for a generic."""
    generics = extract_generics_vhdl(VHDL_ENTITY)
    by_name  = {g["name"]: g for g in generics}
    assert by_name["WIDTH"]["type"]    == "integer"
    assert by_name["WIDTH"]["default"] == "8"


def test_vhdl_generic_comment():
    """Inline comment is captured for a generic declaration."""
    generics = extract_generics_vhdl(VHDL_ENTITY)
    by_name  = {g["name"]: g for g in generics}
    assert "Bus width" in by_name["WIDTH"]["comment"]


def test_vhdl_no_generic_section_returns_empty():
    """A file with no generic(...) section returns an empty list."""
    vhdl = "entity foo is\n  port (clk : in std_logic);\nend entity foo;\n"
    assert extract_generics_vhdl(vhdl) == []


# ─────────────────────────────────────────────────────────────────────────────
# SystemVerilog port extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_sv_port_count():
    """All ports in the SV module are extracted."""
    ports = extract_ports_sv(SV_MODULE)
    assert len(ports) == 5


def test_sv_port_direction_normalised():
    """SV 'input'/'output' are normalised to 'in'/'out'."""
    ports   = extract_ports_sv(SV_MODULE)
    by_name = {p["name"]: p for p in ports}
    assert by_name["clk"]["dir"]    == "in"
    assert by_name["valid_o"]["dir"] == "out"


def test_sv_port_type():
    """SV port type is captured as 'logic'."""
    ports   = extract_ports_sv(SV_MODULE)
    by_name = {p["name"]: p for p in ports}
    assert by_name["clk"]["type"] == "logic"


def test_sv_port_parametric_range():
    """SV parametric range [WIDTH-1:0] is captured correctly."""
    ports   = extract_ports_sv(SV_MODULE)
    by_name = {p["name"]: p for p in ports}
    assert "WIDTH-1:0" in by_name["data_i"]["range"]


def test_sv_port_comment():
    """Inline comment on a SV port line is captured."""
    ports   = extract_ports_sv(SV_MODULE)
    by_name = {p["name"]: p for p in ports}
    assert "System clock" in by_name["clk"]["comment"]


# ─────────────────────────────────────────────────────────────────────────────
# SystemVerilog parameter extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_sv_param_count():
    """All parameters and localparams are extracted."""
    params = extract_params_sv(SV_MODULE)
    assert len(params) == 3


def test_sv_param_fields():
    """Name, type, and default are correctly extracted for a parameter."""
    params  = extract_params_sv(SV_MODULE)
    by_name = {p["name"]: p for p in params}
    assert by_name["WIDTH"]["type"]    == "int"
    assert by_name["WIDTH"]["default"] == "8"


def test_sv_localparam_kind():
    """localparam declarations are tagged with kind='localparam'."""
    params  = extract_params_sv(SV_MODULE)
    by_name = {p["name"]: p for p in params}
    assert by_name["MAX"]["kind"] == "localparam"


def test_sv_param_comment():
    """Inline comment is captured for a parameter declaration."""
    params  = extract_params_sv(SV_MODULE)
    by_name = {p["name"]: p for p in params}
    assert "Data width" in by_name["WIDTH"]["comment"]


# ─────────────────────────────────────────────────────────────────────────────
# Width label helper
# ─────────────────────────────────────────────────────────────────────────────

def test_width_label_std_logic():
    """std_logic with no range returns '1'."""
    assert _width_label({"type": "std_logic", "range": ""}) == "1"


def test_width_label_vhdl_vector():
    """'7 downto 0' is computed to '8'."""
    assert _width_label({"type": "std_logic_vector", "range": "7 downto 0"}) == "8"


def test_width_label_sv_numeric():
    """'7:0' (SV notation) is computed to '8'."""
    assert _width_label({"type": "logic", "range": "7:0"}) == "8"


def test_width_label_sv_parametric():
    """A parametric range returns the bracketed expression."""
    assert _width_label({"type": "logic", "range": "WIDTH-1:0"}) == "[WIDTH-1:0]"


def test_width_label_integer():
    """Integer type with no range returns the type name."""
    assert _width_label({"type": "integer", "range": ""}) == "integer"


# ─────────────────────────────────────────────────────────────────────────────
# Graphviz dot output
# ─────────────────────────────────────────────────────────────────────────────

def test_dot_block_contains_module_node():
    """The port box and gen box node names contain the module name."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    dot      = write_dot_block("my_mod", ports, generics)
    assert "port_box_my_mod" in dot
    assert "gen_box_my_mod" in dot


def test_dot_block_inputs_on_left():
    """Input ports are in the left column of the port box (ALIGN=LEFT)."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    dot      = write_dot_block("my_mod", ports, generics)
    assert 'PORT="i_clk"' in dot
    assert "ALIGN=\"LEFT\"" in dot


def test_dot_block_outputs_on_right():
    """Output ports are in the right column of the port box (ALIGN=RIGHT)."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    dot      = write_dot_block("my_mod", ports, generics)
    assert 'PORT="o_data_o"' in dot
    assert "ALIGN=\"RIGHT\"" in dot


def test_dot_block_bus_width_label():
    """An 8-bit port has [8] shown as its width annotation."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    dot      = write_dot_block("my_mod", ports, generics)
    assert "[8]" in dot


def test_dot_block_inout_bidirectional():
    """Inout ports use the ◂► HTML entity pair as a direction indicator."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    dot      = write_dot_block("my_mod", ports, generics)
    # ◂► is encoded as &#x25C2;&#x25B8; in the HTML label
    assert "&#x25C2;&#x25B8;" in dot


def test_dot_block_generics_box_present():
    """When generics are present a separate green gen_box is emitted."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    dot      = write_dot_block("my_mod", ports, generics)
    assert "c8f5c4" in dot          # green background colour
    assert "gen_box_my_mod" in dot  # generics node present


def test_dot_block_no_generics_box_when_empty():
    """When there are no generics no gen_box or generic stubs are emitted."""
    ports = extract_ports_vhdl(VHDL_ENTITY)
    dot   = write_dot_block("my_mod", ports, [])
    assert "gen_box" not in dot
    assert "c8f5c4" not in dot


# ─────────────────────────────────────────────────────────────────────────────
# RST output
# ─────────────────────────────────────────────────────────────────────────────

def test_rst_block_contains_graphviz_directive():
    """The RST page contains a '.. graphviz::' directive referencing the dot file."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    rst      = write_rst_block("my_mod", "my_mod.vhd", ports, generics, [])
    assert ".. graphviz::" in rst
    assert "my_mod_block.dot" in rst


def test_rst_block_contains_port_table():
    """The RST page includes a port list-table with all port names."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    rst      = write_rst_block("my_mod", "my_mod.vhd", ports, generics, [])
    assert "``clk``" in rst
    assert "``data_i``" in rst
    assert "``data_o``" in rst


def test_rst_block_contains_generics_table():
    """The RST page includes a generics table when generics are present."""
    ports    = extract_ports_vhdl(VHDL_ENTITY)
    generics = extract_generics_vhdl(VHDL_ENTITY)
    rst      = write_rst_block("my_mod", "my_mod.vhd", ports, generics, [])
    assert "Generics" in rst
    assert "``WIDTH``" in rst


def test_rst_block_no_generics_table_when_empty():
    """No generics section appears when there are no generics."""
    ports = extract_ports_vhdl(VHDL_ENTITY)
    rst   = write_rst_block("my_mod", "my_mod.vhd", ports, [], [])
    assert "Generics" not in rst
    assert "Parameters" not in rst


# ─────────────────────────────────────────────────────────────────────────────
# Signal extraction — VHDL
# ─────────────────────────────────────────────────────────────────────────────

VHDL_WITH_SIGNALS = """\
entity sig_mod is
    port (clk : in std_logic);
end entity sig_mod;

architecture rtl of sig_mod is
    -- Current FSM state.
    signal state      : t_state;
    signal next_state : t_state;
    signal count      : std_logic_vector(7 downto 0);
    signal flag       : std_logic := '0';  -- Default low.
begin
    -- architecture body here
end architecture rtl;
"""

SV_WITH_SIGNALS = """\
module sig_sv (input logic clk);
    // Cycle counter.
    logic [7:0] count;
    logic       valid;
    // Input staging register.
    logic [3:0] data_reg;
endmodule
"""


def test_vhdl_signal_count():
    """All signal declarations in the architecture are extracted."""
    signals = extract_signals_vhdl(VHDL_WITH_SIGNALS)
    assert len(signals) == 4


def test_vhdl_signal_names():
    """Signal names are extracted correctly."""
    signals = extract_signals_vhdl(VHDL_WITH_SIGNALS)
    names = [s["name"] for s in signals]
    assert "state" in names
    assert "count" in names
    assert "flag" in names


def test_vhdl_signal_type_vector():
    """std_logic_vector signal has the correct type and range."""
    signals = extract_signals_vhdl(VHDL_WITH_SIGNALS)
    by_name = {s["name"]: s for s in signals}
    assert by_name["count"]["type"]  == "std_logic_vector"
    assert "7 downto 0" in by_name["count"]["range"]


def test_vhdl_signal_preceding_comment():
    """Comment on the line above a signal declaration is captured."""
    signals = extract_signals_vhdl(VHDL_WITH_SIGNALS)
    by_name = {s["name"]: s for s in signals}
    assert "Current FSM state" in by_name["state"]["comment"]


def test_vhdl_signal_inline_comment():
    """Inline comment on the same line as a signal declaration is captured."""
    signals = extract_signals_vhdl(VHDL_WITH_SIGNALS)
    by_name = {s["name"]: s for s in signals}
    assert "Default low" in by_name["flag"]["comment"]


def test_vhdl_no_signals_outside_architecture():
    """Signals are not extracted from outside the architecture declaration area."""
    text = "entity foo is port (clk : in std_logic); end entity foo;\n"
    assert extract_signals_vhdl(text) == []


# ─────────────────────────────────────────────────────────────────────────────
# Signal extraction — SystemVerilog
# ─────────────────────────────────────────────────────────────────────────────

def test_sv_signal_count():
    """All internal logic declarations are extracted."""
    signals = extract_signals_sv(SV_WITH_SIGNALS)
    assert len(signals) == 3


def test_sv_signal_names():
    """Signal names are extracted correctly from SV source."""
    signals = extract_signals_sv(SV_WITH_SIGNALS)
    names = [s["name"] for s in signals]
    assert "count" in names
    assert "valid" in names
    assert "data_reg" in names


def test_sv_signal_range():
    """Bit range is captured for a vector signal."""
    signals = extract_signals_sv(SV_WITH_SIGNALS)
    by_name = {s["name"]: s for s in signals}
    assert by_name["count"]["range"] == "7:0"


def test_sv_signal_comment():
    """Preceding-line comment is captured for an SV signal."""
    signals = extract_signals_sv(SV_WITH_SIGNALS)
    by_name = {s["name"]: s for s in signals}
    assert "Cycle counter" in by_name["count"]["comment"]


def test_sv_ports_not_extracted_as_signals():
    """Port declarations (input/output/inout) are not included in the signals list."""
    signals = extract_signals_sv(SV_WITH_SIGNALS)
    names = [s["name"] for s in signals]
    assert "clk" not in names


# ─────────────────────────────────────────────────────────────────────────────
# Signals table in RST output
# ─────────────────────────────────────────────────────────────────────────────

def test_rst_block_contains_signals_table():
    """The RST page includes a Signals table when signals are present."""
    ports   = extract_ports_vhdl(VHDL_WITH_SIGNALS)
    signals = extract_signals_vhdl(VHDL_WITH_SIGNALS)
    rst     = write_rst_block("sig_mod", "sig_mod.vhd", ports, [], signals)
    assert "Signals" in rst
    assert "``state``" in rst
    assert "``count``" in rst


def test_rst_block_no_signals_table_when_empty():
    """No Signals section appears when there are no internal signals."""
    ports = extract_ports_vhdl(VHDL_ENTITY)
    rst   = write_rst_block("my_mod", "my_mod.vhd", ports, [], [])
    assert "Signals" not in rst


# ── Bus interface tests ───────────────────────────────────────────────────────

def test_bus_group_produces_details_html():
    """Bus-detected ports render as .. raw:: html with <details> rows."""
    ports = [
        {"name": f"s_axi_{sig}", "dir": "in", "type": "std_logic",
         "range": None, "comment": f"{sig} signal"}
        for sig in [
            "awvalid", "awready", "awaddr",
            "wvalid",  "wready",  "wdata",  "wstrb",
            "bvalid",  "bready",  "bresp",
            "arvalid", "arready", "araddr",
            "rvalid",  "rready",  "rdata",  "rresp",
        ]
    ]
    rst = write_rst_block("mymod", "mymod.vhd", ports, [], [])
    assert ".. raw:: html" in rst
    assert "<details>" in rst
    assert "s_axi" in rst
    assert "AXI4-Lite Subordinate" in rst
    assert ".. list-table::" not in rst


def test_no_bus_groups_uses_list_table():
    """Without bus groups the port section stays as .. list-table::."""
    ports = [
        {"name": "clk",  "dir": "in",  "type": "std_logic", "range": None, "comment": "Clock"},
        {"name": "rst",  "dir": "in",  "type": "std_logic", "range": None, "comment": "Reset"},
        {"name": "data", "dir": "out", "type": "std_logic", "range": None, "comment": "Data"},
    ]
    rst = write_rst_block("mymod", "mymod.vhd", ports, [], [])
    assert ".. list-table::" in rst
    assert ".. raw:: html" not in rst
    assert "<details>" not in rst


def test_bus_group_with_remaining_ports():
    """Remaining (non-bus) ports appear as plain rows alongside bus group details."""
    ports = [
        {"name": f"s_axi_{sig}", "dir": "in", "type": "std_logic",
         "range": None, "comment": ""}
        for sig in [
            "awvalid", "awready", "awaddr",
            "wvalid",  "wready",  "wdata",  "wstrb",
            "bvalid",  "bready",  "bresp",
            "arvalid", "arready", "araddr",
            "rvalid",  "rready",  "rdata",  "rresp",
        ]
    ] + [
        {"name": "clk", "dir": "in", "type": "std_logic", "range": None, "comment": "Clock"},
        {"name": "rst", "dir": "in", "type": "std_logic", "range": None, "comment": "Reset"},
    ]
    rst = write_rst_block("mymod", "mymod.vhd", ports, [], [])
    assert "<details>" in rst          # bus group is collapsed
    assert "AXI4-Lite Subordinate" in rst
    # remaining ports appear as plain rows (outside <details>)
    assert "<code>clk</code>" in rst
    assert "<code>rst</code>" in rst


def test_rtl_schematic_is_a_collapsed_detail_section():
    """The schematic sits in a collapsed <details> block (HTML) under 'RTL Detail'."""
    rst = write_rst_block("m", "m.vhd", [], [], [], include_schematic=True)
    assert "RTL Detail" in rst
    assert "<details" in rst and "</details>" in rst
    assert rst.index("<details") < rst.index(".. image:: m_schematic.*") < rst.index("</details>")


def test_no_rtl_detail_section_without_schematic():
    rst = write_rst_block("m", "m.vhd", [], [], [], include_schematic=False)
    assert "RTL Detail" not in rst and "<details" not in rst


def test_rtl_schematic_gets_a_landscape_page_in_latex():
    """PDF output rotates the schematic onto its own page and fits it to that page."""
    rst = write_rst_block("m", "m.vhd", [], [], [], include_schematic=True)
    latex = rst[rst.index(".. only:: latex"):]
    assert "\\begin{landscape}" in latex and "\\end{landscape}" in latex
    # Sphinx's image height cap is portrait-sized; it must be reset inside the block.
    assert "\\spx@image@maxheight" in latex
    assert latex.index("\\begin{landscape}") < latex.index(".. image:: m_schematic.*") \
        < latex.index("\\end{landscape}")


# ─────────────────────────────────────────────────────────────────────────────
# SystemVerilog interface-typed ports
# ─────────────────────────────────────────────────────────────────────────────

_IFACES = {"axil_if", "axis_if"}

_BRIDGE_SV = """\
module bridge #(
    parameter int DEPTH = 4
)(
    // System clock.
    input  logic       clk,
    // Register write interface.
    axil_if.slave      s_axil,
    // Outgoing byte stream.
    axis_if.master     m_axis,
    axis_if            s_dbg       // Debug tap.
);
    axis_if inner (.clk(clk));
endmodule
"""


def test_interface_ports_are_extracted_in_declaration_order():
    ports = extract_ports_sv(_BRIDGE_SV, _IFACES)
    assert [p["name"] for p in ports] == ["clk", "s_axil", "m_axis", "s_dbg"]


def test_interface_port_fields():
    ports = {p["name"]: p for p in extract_ports_sv(_BRIDGE_SV, _IFACES)}
    s_axil = ports["s_axil"]
    assert s_axil["kind"] == "interface"
    assert s_axil["interface"] == "axil_if" and s_axil["modport"] == "slave"
    assert s_axil["dir"] == "slave" and s_axil["type"] == "axil_if" and s_axil["range"] == ""
    assert s_axil["comment"] == "Register write interface."
    assert ports["m_axis"]["modport"] == "master"
    assert ports["s_dbg"]["modport"] == "" and ports["s_dbg"]["dir"] == "\u2014"
    assert ports["s_dbg"]["comment"] == "Debug tap."          # inline comment
    assert "kind" not in ports["clk"]                         # ordinary ports unchanged


def test_interface_instance_in_the_module_body_is_not_a_port():
    names = [p["name"] for p in extract_ports_sv(_BRIDGE_SV, _IFACES)]
    assert "inner" not in names


def test_interface_ports_need_a_known_interface_name():
    """A plain type name, or an unknown interface, is not listed."""
    text = "module m (\n    input logic clk,\n    foo_t data,\n    other_if.slave o\n);\nendmodule\n"
    assert [p["name"] for p in extract_ports_sv(text, _IFACES)] == ["clk"]


def test_without_interface_names_behaviour_is_unchanged():
    assert [p["name"] for p in extract_ports_sv(_BRIDGE_SV)] == ["clk"]
    assert [p["name"] for p in extract_ports_sv(_BRIDGE_SV, set())] == ["clk"]


def test_interface_ports_after_a_parameter_list_are_found():
    text = "module m #(parameter int W = (4 + 4)) (\n    axis_if.master out_s\n);\nendmodule\n"
    assert [p["name"] for p in extract_ports_sv(text, _IFACES)] == ["out_s"]


def test_interface_side_rule():
    assert interface_side({"modport": "master"}) == "right"
    assert interface_side({"modport": "src"}) == "right"
    assert interface_side({"modport": "mp_manager"}) == "right"
    assert interface_side({"modport": "slave"}) == "left"
    assert interface_side({"modport": "snk"}) == "left"
    assert interface_side({"modport": ""}) == "left"
    assert interface_side({"modport": "weird"}) == "left"


def test_diagram_places_interface_ports_by_modport_and_labels_them():
    ports = extract_ports_sv(_BRIDGE_SV, _IFACES)
    dot = write_dot_block("bridge", ports, [])
    assert 'PORT="i_s_axil"' in dot and "s_axil (interface)" in dot    # slave: left
    assert 'PORT="i_s_dbg"' in dot                                     # no modport: left
    assert 'PORT="o_m_axis"' in dot and "m_axis (interface)" in dot    # master: right
    assert 'PORT="i_m_axis"' not in dot


def test_diagram_modport_named_in_or_out_is_not_mistaken_for_a_plain_port():
    ports = [
        {"name": "clk", "dir": "in", "type": "logic", "range": "", "comment": ""},
        {"name": "bus", "dir": "out", "type": "x_if", "range": "", "comment": "",
         "kind": "interface", "interface": "x_if", "modport": "out"},
    ]
    dot = write_dot_block("m", ports, [])
    assert "bus (interface)" in dot
    assert dot.count('PORT="o_bus"') == 1 and 'PORT="i_bus"' not in dot


def test_port_table_has_one_row_per_interface_port():
    ports = extract_ports_sv(_BRIDGE_SV, _IFACES)
    rst = write_rst_block("bridge", "bridge.sv", ports, [], [])
    assert "   * - ``s_axil``\n     - ``slave``\n     - ``axil_if``\n     - Register write interface." in rst
    assert "   * - ``m_axis``\n     - ``master``\n     - ``axis_if``" in rst
    assert "   * - ``s_dbg``\n     - \u2014\n     - ``axis_if``" in rst


def test_interface_ports_are_not_swallowed_by_bus_grouping():
    """Several ports sharing a prefix form a bus group; an interface port never does."""
    ports = [
        {"name": f"s_axi_{n}", "dir": "in", "type": "logic", "range": "", "comment": ""}
        for n in ("awvalid", "awready", "awaddr", "wvalid", "wready", "wdata",
                  "bvalid", "bready", "bresp", "arvalid")
    ] + [
        {"name": "s_axi", "dir": "slave", "type": "axil_if", "range": "", "comment": "",
         "kind": "interface", "interface": "axil_if", "modport": "slave"},
    ]
    rst = write_rst_block("m", "m.sv", ports, [], [])
    assert "port-table" in rst and "bus-group-row" in rst          # the flat ports did group
    assert "AXI4-Lite" in rst
    # ...and the interface port is its own plain row, not inside the group.
    assert "<td><code>s_axi</code></td>" in rst
    assert "<td><code>axil_if</code></td>" in rst
    group_html = rst[rst.index("<details>"):rst.index("</details>")]
    assert "<code>s_axi</code>" not in group_html


_AXIS_DEF = {"name": "axis_if", "members": [
    {"name": "tdata", "type": "logic", "range": "7:0", "comment": "Payload."},
    {"name": "tready", "type": "logic", "range": "", "comment": ""},
], "modports": {"master": {"tdata": "out", "tready": "in"}, "slave": {"tdata": "in"}}}


def test_interfaces_section_lists_members_with_widths_and_modport_directions():
    ports = [{"name": "m_axis", "dir": "master", "type": "axis_if", "range": "", "comment": "",
              "kind": "interface", "interface": "axis_if", "modport": "master"}]
    rst = write_rst_block("m", "m.sv", ports, [], [], interfaces={"axis_if": _AXIS_DEF})
    assert "Interfaces\n----------" in rst
    assert "``axis_if`` \u2014 used by ``m_axis``." in rst
    assert "``tdata``\n     - ``logic[7:0]``\n     - out\n     - Payload." in rst
    assert "``tready``\n     - ``logic``\n     - in\n" in rst
    # Only the modport this module uses gets a column.
    assert "     - master" in rst and "     - slave" not in rst


def test_no_interfaces_section_without_interface_ports():
    ports = [{"name": "clk", "dir": "in", "type": "logic", "range": "", "comment": ""}]
    rst = write_rst_block("m", "m.sv", ports, [], [], interfaces={"axis_if": _AXIS_DEF})
    assert "Interfaces" not in rst
