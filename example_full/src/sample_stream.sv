// Captured samples as a filtered byte stream.
//
// Sends the low byte of each sample as a one-byte packet and runs it through a
// stream_filter, so only samples whose low byte reaches the threshold leave on
// the flat AXI4-Stream master port.
module sample_stream (
    // System clock.
    input  logic                       clk,
    // Synchronous active-high reset.
    input  logic                       rst,
    // Filtering is on while high.
    input  logic                       enable,
    // Smallest low-byte value that lets a sample through.
    input  logic [7:0]                 threshold,
    // Sample and its handshake from the capture path.
    input  logic [full_pkg::SAMPLE_W-1:0] sample_data,
    input  logic                       sample_valid,
    output logic                       sample_ready,
    // Forwarded bytes.
    output logic [7:0]                 m_axis_tdata,
    output logic                       m_axis_tvalid,
    input  logic                       m_axis_tready,
    output logic                       m_axis_tlast
);
    axis_if s_if ();
    axis_if m_if ();
    logic [15:0] unused_count;

    assign s_if.tdata  = sample_data[7:0];
    assign s_if.tvalid = sample_valid;
    assign s_if.tlast  = 1'b1;
    assign sample_ready = s_if.tready;
    assign m_axis_tdata  = m_if.tdata;
    assign m_axis_tvalid = m_if.tvalid;
    assign m_axis_tlast  = m_if.tlast;
    assign m_if.tready   = m_axis_tready;

    stream_filter u_filter (
        .clk(clk), .rst(rst), .enable(enable), .clear(1'b0), .threshold(threshold),
        .s_axis(s_if), .m_axis(m_if), .count(unused_count)
    );
endmodule
