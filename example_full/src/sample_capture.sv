// Sample capture across a clock boundary.
//
// Registers samples from a free-running converter clock (adc_clk) and hands
// them to the system clock (clk) through an asynchronous FIFO. The enable
// and clear requests go the other way through two-flop synchronisers, so
// neither domain samples a signal that changes under its own clock edge.
//
// .. mermaid::
//    :caption: Capture data path
//
//    flowchart LR
//      subgraph sys[clk domain]
//        E[enable] --> C[p_ctrl]
//        O[p_out] --> S[sample_data]
//      end
//      subgraph adc[adc_clk domain]
//        N[p_adc_en] --> R[p_adc_capture]
//        D[adc_data] --> R
//      end
//      C -- capture_en, clear_req --> N
//      R -- samples --> F[(async_fifo)]
//      F --> O
module sample_capture #(
    // Keep overflow set until reset (1), or show it for one cycle per lost
    // sample (0).
    parameter bit STICKY_OVERFLOW = 1'b1
) (
    // System clock.
    input  logic                       clk,
    // System-domain asynchronous active-low reset, released synchronously
    // (from a reset_sync on clk).
    input  logic                       rst_n,
    // Capture while high.
    input  logic                       enable,
    // Clears the overflow flag while high (system clock domain).
    input  logic                       clear_overflow,
    // Converter clock; unrelated to clk.
    input  logic                       adc_clk,
    // Converter-domain synchronous active-high reset, released on adc_clk.
    input  logic                       adc_rst,
    // Sample from the converter.
    input  logic [full_pkg::SAMPLE_W-1:0] adc_data,
    // Oldest unread sample, valid while sample_valid is high.
    output logic [full_pkg::SAMPLE_W-1:0] sample_data,
    // A sample is waiting on sample_data.
    output logic                       sample_valid,
    // Consumer takes the sample this cycle.
    input  logic                       sample_ready,
    // Set when a sample arrived while the FIFO was full (held until
    // clear_overflow when STICKY_OVERFLOW). Changes under adc_clk, so the reader
    // must treat it as asynchronous.
    output logic                       overflow
);
    // Requests registered on clk: capture, and clear the overflow flag.
    logic                       capture_en, clear_req;
    // Two-flop synchronisers for capture_en and clear_req on adc_clk.
    logic                       en_meta, en_sync, clr_meta, clr_sync;
    // Registered sample and its write strobe on adc_clk.
    logic [full_pkg::SAMPLE_W-1:0] wr_data;
    logic                       wr_en;
    // FIFO handshake.
    logic                       fifo_full, fifo_empty;
    logic [full_pkg::SAMPLE_W-1:0] fifo_rd_data;
    wire                        rd_en     = !fifo_empty && (!sample_valid || sample_ready);
    wire                        adc_rst_n = !adc_rst;

    // p_ctrl: Registers the enable and clear requests on the system clock.
    always_ff @(posedge clk or negedge rst_n) begin : p_ctrl
        if (!rst_n) begin
            capture_en <= 1'b0;
            clear_req  <= 1'b0;
        end else begin
            capture_en <= enable;
            clear_req  <= clear_overflow;
        end
    end

    // p_out: Presents the oldest sample to the consumer.
    always_ff @(posedge clk or negedge rst_n) begin : p_out
        if (!rst_n) begin
            sample_valid <= 1'b0;
            sample_data  <= '0;
        end else if (rd_en) begin
            sample_valid <= 1'b1;
            sample_data  <= fifo_rd_data;
        end else if (sample_ready) begin
            sample_valid <= 1'b0;
        end
    end

    // p_adc_en: Brings capture_en and clear_req into the converter domain.
    always_ff @(posedge adc_clk) begin : p_adc_en
        if (adc_rst) begin
            en_meta  <= 1'b0;
            en_sync  <= 1'b0;
            clr_meta <= 1'b0;
            clr_sync <= 1'b0;
        end else begin
            en_meta  <= capture_en;
            en_sync  <= en_meta;
            clr_meta <= clear_req;
            clr_sync <= clr_meta;
        end
    end

    // p_adc_capture: Registers each sample and flags FIFO overflow.
    always_ff @(posedge adc_clk) begin : p_adc_capture
        if (adc_rst) begin
            wr_en    <= 1'b0;
            wr_data  <= '0;
            overflow <= 1'b0;
        end else begin
            wr_en   <= en_sync;
            wr_data <= adc_data;
            if (wr_en && fifo_full) begin
                overflow <= 1'b1;
            end else if (clr_sync || !STICKY_OVERFLOW) begin
                overflow <= 1'b0;
            end
        end
    end

    // Sample FIFO between the two clocks (VHDL; its generics are left at their
    // defaults, which match full_pkg::SAMPLE_W).
    async_fifo u_fifo (
        .wr_clk   (adc_clk),
        .wr_rst_n (adc_rst_n),
        .wr_en    (wr_en),
        .wr_data  (wr_data),
        .wr_full  (fifo_full),
        .rd_clk   (clk),
        .rd_rst_n (rst_n),
        .rd_en    (rd_en),
        .rd_data  (fifo_rd_data),
        .rd_empty (fifo_empty)
    );
endmodule
