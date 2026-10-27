// Bridges a register write port to a stream.
//
// Takes AXI4-Lite writes and forwards the data as an AXI4-Stream.
module bridge #(
    parameter int DEPTH = 4
)(
    // System clock.
    input  logic       clk,
    // Synchronous reset.
    input  logic       rst,
    // Register write interface.
    axil_if.slave      s_axil,
    // Outgoing byte stream.
    axis_if.master     m_axis,
    axis_if            s_dbg       // Debug tap, no modport.
);
    assign s_axil.awready = 1'b1;
    assign m_axis.tdata   = s_axil.wdata[7:0];
    assign m_axis.tvalid  = s_axil.awvalid;
    assign m_axis.tlast   = 1'b0;
endmodule
