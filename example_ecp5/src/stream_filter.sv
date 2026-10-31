// Threshold filter for a byte stream.
//
// Forwards each byte that is at or above the threshold and drops the rest.
// One register stage; counts the bytes it forwards.
module stream_filter (
    // System clock.
    input  logic        clk,
    // Synchronous active-high reset.
    input  logic        rst,
    // Filtering is on while high; while low every byte is dropped.
    input  logic        enable,
    // Holds the counter at zero while high.
    input  logic        clear,
    // Smallest byte value that is forwarded.
    input  logic [7:0]  threshold,
    // Incoming bytes.
    axis_if.slave       s_axis,
    // Forwarded bytes.
    axis_if.master      m_axis,
    // Bytes forwarded since the counter was last cleared.
    output logic [15:0] count
);
    logic [7:0] tdata_r;
    logic       tvalid_r, tlast_r;

    // The output register is free when empty or being read this cycle.
    wire  can_load = !tvalid_r || m_axis.tready;
    wire  pass     = s_axis.tvalid && enable && (s_axis.tdata >= threshold);

    always_ff @(posedge clk) begin
        if (rst || clear) begin
            count <= 16'd0;
        end else if (can_load && pass) begin
            count <= count + 16'd1;
        end

        if (rst) begin
            tvalid_r <= 1'b0;
        end else if (can_load) begin
            tvalid_r <= pass;
            tdata_r  <= s_axis.tdata;
            tlast_r  <= s_axis.tlast;
        end
    end

    assign s_axis.tready = can_load;
    assign m_axis.tdata  = tdata_r;
    assign m_axis.tvalid = tvalid_r;
    assign m_axis.tlast  = tlast_r;
endmodule
