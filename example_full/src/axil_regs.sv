// AXI4-Lite register file for the sampler.
//
// Five 32-bit registers: control (start, filter enable, clear), a read-only
// status word (controller state, overflow flag), the filter threshold, a
// scratch register and a read-only packet count. Write strobes are ignored:
// every write updates the whole register. See registers/regs_axil_regs.toml.
//
// .. mermaid::
//    :caption: AXI4-Lite register write
//
//    sequenceDiagram
//      participant M as Bus master
//      participant R as axil_regs
//      M->>R: awaddr, awvalid
//      M->>R: wdata, wvalid
//      R-->>M: awready, wready (both together)
//      R-->>M: bvalid (OKAY)
//      M->>R: bready
module axil_regs (
    // System clock.
    input  logic        clk,
    // Synchronous active-high reset.
    input  logic        rst,
    // Register access from the bus master.
    axil_if.slave       s_axil,
    // Starts a capture while high.
    output logic        start,
    // Enables the stream filters.
    output logic        filter_enable,
    // Holds the packet counter at zero while high.
    output logic        clear,
    // Smallest first-byte value the filters let through.
    output logic [7:0]  threshold,
    // Sampler controller state.
    input  logic [1:0]  state_code,
    // A sample was lost because the FIFO was full.
    input  logic        overflow,
    // Packets forwarded since the counter was last cleared.
    input  logic [15:0] count
);
    logic [31:0] ctrl_r, threshold_r, scratch_r, rdata_r;
    logic        bvalid_r, rvalid_r;

    // Interface members are copied to plain signals first: Yosys cannot take a bit-select
    // of an interface member inside a submodule.
    wire [7:0]  awaddr = s_axil.awaddr;
    wire [7:0]  araddr = s_axil.araddr;
    wire [31:0] wdata  = s_axil.wdata;

    // A write is taken when both address and data are present and no response is pending.
    wire wr_fire = s_axil.awvalid && s_axil.wvalid && !bvalid_r;
    wire rd_fire = s_axil.arvalid && !rvalid_r;

    // p_bus: Decodes writes and reads and drives the responses.
    always_ff @(posedge clk) begin : p_bus
        if (rst) begin
            ctrl_r      <= 32'd0;
            threshold_r <= 32'd0;
            scratch_r   <= 32'd0;
            rdata_r     <= 32'd0;
            bvalid_r    <= 1'b0;
            rvalid_r    <= 1'b0;
        end else begin
            if (wr_fire) begin
                bvalid_r <= 1'b1;
                case (awaddr[4:2])
                    3'd0:    ctrl_r      <= wdata;
                    3'd2:    threshold_r <= wdata;
                    3'd3:    scratch_r   <= wdata;
                    default: ;
                endcase
            end else if (s_axil.bready) begin
                bvalid_r <= 1'b0;
            end

            if (rd_fire) begin
                rvalid_r <= 1'b1;
                case (araddr[4:2])
                    3'd0:    rdata_r <= ctrl_r;
                    3'd1:    rdata_r <= {29'd0, overflow, state_code};
                    3'd2:    rdata_r <= threshold_r;
                    3'd3:    rdata_r <= scratch_r;
                    default: rdata_r <= {16'd0, count};
                endcase
            end else if (s_axil.rready) begin
                rvalid_r <= 1'b0;
            end
        end
    end

    assign s_axil.awready = wr_fire;
    assign s_axil.wready  = wr_fire;
    assign s_axil.bresp   = 2'b00;
    assign s_axil.bvalid  = bvalid_r;
    assign s_axil.arready = rd_fire;
    assign s_axil.rdata   = rdata_r;
    assign s_axil.rresp   = 2'b00;
    assign s_axil.rvalid  = rvalid_r;

    assign start         = ctrl_r[0];
    assign filter_enable = ctrl_r[1];
    assign clear         = ctrl_r[2];
    assign threshold     = threshold_r[7:0];
endmodule
