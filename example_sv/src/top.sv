// Top level.
module top (
    input  logic clk,
    input  logic rst
);
    axil_if s_axil (.clk(clk));
    axis_if m_axis (.clk(clk));
    axis_if dbg    (.clk(clk));
    bridge u_bridge (.clk(clk), .rst(rst), .s_axil(s_axil), .m_axis(m_axis), .s_dbg(dbg));
endmodule
