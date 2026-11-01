// Filtered pass-through for an external byte stream.
//
// Presents flat AXI4-Stream ports, wraps them in interface instances and runs
// them through a stream_filter.
module axis_pipeline (
    // System clock.
    input  logic       clk,
    // Synchronous active-high reset.
    input  logic       rst,
    // Filtering is on while high.
    input  logic       enable,
    // Holds the packet counter at zero while high.
    input  logic       clear,
    // Smallest first-byte value that lets a packet through.
    input  logic [7:0] threshold,
    // Incoming bytes.
    input  logic [7:0] s_axis_tdata,
    input  logic       s_axis_tvalid,
    output logic       s_axis_tready,
    input  logic       s_axis_tlast,
    // Forwarded bytes.
    output logic [7:0] m_axis_tdata,
    output logic       m_axis_tvalid,
    input  logic       m_axis_tready,
    output logic       m_axis_tlast,
    // Packets forwarded since the counter was last cleared.
    output logic [15:0] count
);
    axis_if s_if ();
    axis_if m_if ();

    assign s_if.tdata  = s_axis_tdata;
    assign s_if.tvalid = s_axis_tvalid;
    assign s_if.tlast  = s_axis_tlast;
    assign s_axis_tready = s_if.tready;
    assign m_axis_tdata  = m_if.tdata;
    assign m_axis_tvalid = m_if.tvalid;
    assign m_axis_tlast  = m_if.tlast;
    assign m_if.tready   = m_axis_tready;

    stream_filter u_filter (
        .clk(clk), .rst(rst), .enable(enable), .clear(clear), .threshold(threshold),
        .s_axis(s_if), .m_axis(m_if), .count(count)
    );
endmodule
