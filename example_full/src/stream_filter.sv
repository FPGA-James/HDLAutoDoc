// Packet filter for a byte stream.
//
// Looks at the first byte of each packet: if it is at or above the threshold
// (and the filter is enabled) the whole packet is forwarded, otherwise the
// whole packet is dropped. Counts the packets it forwards.
module stream_filter #(
    // Width of the forwarded-packet counter in bits.
    parameter int COUNT_W = 16
) (
    // System clock.
    input  logic               clk,
    // Synchronous active-high reset.
    input  logic               rst,
    // Filtering is on while high; while low every packet is dropped.
    input  logic               enable,
    // Holds the counter at zero while high.
    input  logic               clear,
    // Smallest first-byte value that lets a packet through.
    input  logic [7:0]         threshold,
    // Incoming bytes.
    axis_if.slave              s_axis,
    // Forwarded bytes.
    axis_if.master             m_axis,
    // Packets forwarded since the counter was last cleared.
    output logic [COUNT_W-1:0] count
);
    typedef enum logic [1:0] {
        // Waiting for the first byte of a packet.
        FIRST,
        // Forwarding the rest of an accepted packet.
        FORWARD,
        // Dropping the rest of a rejected packet.
        DISCARD
    } state_t;

    state_t state, next_state;

    wire [7:0] tdata  = s_axis.tdata;
    wire       tvalid = s_axis.tvalid;
    wire       tlast  = s_axis.tlast;
    wire       first_ok   = enable && (tdata >= threshold);
    wire       in_first   = (state == FIRST);
    wire       forwarding = (state == FORWARD) || (in_first && first_ok);
    wire       beat       = tvalid && (m_axis.tready || !forwarding);
    wire       start_fwd  = in_first && beat && first_ok && !tlast;
    wire       start_drop = in_first && beat && !first_ok && !tlast;
    wire       last_beat  = beat && tlast;

    // p_state: Clocked state register and forwarded-packet counter.
    //
    // .. wavedrom::
    //
    //    { "signal": [
    //      { "name": "clk",    "wave": "P......." },
    //      { "name": "tvalid", "wave": "01.....0" },
    //      { "name": "tlast",  "wave": "0....10." },
    //      { "name": "state",  "wave": "=.=...=.", "data": ["FIRST","FORWARD","FIRST"] }
    //    ]}
    always_ff @(posedge clk) begin : p_state
        if (rst) begin
            state <= FIRST;
            count <= '0;
        end else begin
            state <= next_state;
            if (clear) begin
                count <= '0;
            end else if (forwarding && last_beat) begin
                count <= count + 1'b1;
            end
        end
    end

    // p_next_state: Packet-level next-state logic.
    //
    // The first byte of a packet decides whether the rest is forwarded or
    // dropped; the last byte returns to FIRST.
    always_comb begin : p_next_state
        next_state = state;
        case (state)
            FIRST:   if (start_fwd) next_state = FORWARD;
                     else if (start_drop) next_state = DISCARD;
            FORWARD: if (last_beat) next_state = FIRST;
            DISCARD: if (last_beat) next_state = FIRST;
            default: next_state = FIRST;
        endcase
    end

    assign m_axis.tdata  = tdata;
    assign m_axis.tvalid = tvalid && forwarding;
    assign m_axis.tlast  = tlast;
    assign s_axis.tready = forwarding ? m_axis.tready : 1'b1;
endmodule
