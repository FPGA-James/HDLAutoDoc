// ECP5 design: an AXI4-Stream threshold filter with an AXI4-Lite register file.
//
// Bytes arriving on s_axis are forwarded to m_axis if they are at or above a
// threshold the bus master sets through the registers.
module top (
    // System clock.
    input  logic   clk,
    // Synchronous active-high reset.
    input  logic   rst,
    // Register bus: control, status, threshold and scratch registers.
    axil_if.slave  s_axil,
    // Incoming byte stream.
    axis_if.slave  s_axis,
    // Filtered byte stream.
    axis_if.master m_axis
);
    logic        enable, clear;
    logic [7:0]  threshold;
    logic [15:0] count;

    axil_regs u_regs (
        .clk(clk), .rst(rst), .s_axil(s_axil),
        .enable(enable), .clear(clear), .threshold(threshold), .count(count)
    );

    stream_filter u_filter (
        .clk(clk), .rst(rst), .enable(enable), .clear(clear), .threshold(threshold),
        .s_axis(s_axis), .m_axis(m_axis), .count(count)
    );
endmodule
