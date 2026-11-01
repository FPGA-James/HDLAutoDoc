"""hdl_scan: balanced-delimiter helpers and instance scanning (no regex can count nesting)."""

import pytest

from hdl_scan import matching_paren, named_connections, scan_sv_instances, scan_vhdl_instances


def test_matching_paren_skips_nested_pairs():
    text = "x(a(b)(c(d)), e) tail"
    assert text[matching_paren(text, 1)] == ")" and matching_paren(text, 1) == text.index(", e)") + 3


def test_matching_paren_of_an_unclosed_paren_is_none():
    assert matching_paren("f(a(b)", 1) is None


def test_matching_paren_must_start_on_an_open_paren():
    with pytest.raises(ValueError):
        matching_paren("abc", 1)


def test_named_connections_read_nested_expressions():
    text = ".clk(sys_clk), .data({a, b[3:0]}), .en(f(x, g(y))), .rst ( rst_n )"
    assert named_connections(text) == {
        "clk": "sys_clk", "data": "{a, b[3:0]}", "en": "f(x, g(y))", "rst": "rst_n"}


SV = """
module top;
  async_fifo #(.WIDTH(8), .DEPTH(clog2(16))) u_fifo (
      .wr_clk(clk_a), .rd_clk(clk_b), .din(d));
  async_fifo #(8, 4) u_pos (.wr_clk(clk_a), .rd_clk(clk_b));
  plain u_plain (.a(x));
  banked u_arr [3:0] (.a(y));
  always_ff @(posedge clk) begin end
  if (x) begin end
endmodule
"""


def test_sv_instances_with_nested_parameter_overrides_are_found():
    found = {i["instance"]: i for i in scan_sv_instances(SV)}
    assert set(found) == {"u_fifo", "u_pos", "u_plain", "u_arr"}
    assert found["u_fifo"]["component"] == "async_fifo"
    assert "clog2(16)" in found["u_fifo"]["params"]
    assert named_connections(found["u_fifo"]["ports"])["rd_clk"] == "clk_b"
    assert found["u_pos"]["params"] == "8, 4"
    assert found["u_plain"]["params"] == ""


def test_sv_statements_that_look_like_instances_are_not():
    names = {i["component"] for i in scan_sv_instances(SV)}
    assert not names & {"always_ff", "if", "module", "endmodule"}


VHDL = """
u_f : entity work.async_fifo
    generic map (WIDTH => f(8), D => 4)
    port map (wr_clk => clk_a, rd_clk => clk_b, din => std_logic_vector(d));
u_g : async_fifo port map (wr_clk => clk_a, rd_clk => clk_b);
u_h : component fifo2 generic map (W => 8) port map (a => b);
p_x : process (clk) is begin end process;
"""


def test_vhdl_instances_with_nested_generic_and_port_maps_are_found():
    found = {i["instance"]: i for i in scan_vhdl_instances(VHDL)}
    assert set(found) == {"u_f", "u_g", "u_h"}
    assert found["u_f"]["component"] == "async_fifo"
    assert "f(8)" in found["u_f"]["generics"]
    assert found["u_f"]["ports"].count("=>") == 3
    assert found["u_g"]["generics"] == ""
    assert found["u_h"]["component"] == "fifo2"
