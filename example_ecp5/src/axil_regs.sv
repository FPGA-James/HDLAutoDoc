// AXI4-Lite register file for the stream filter.
//
// Four 32-bit registers: control (enable, clear), a read-only forwarded-byte
// count, the filter threshold, and a scratch register. Write strobes are
// ignored: every write updates the whole register. See registers/regs_axil_regs.toml.
module axil_regs (
    // System clock.
    input  logic        clk,
    // Synchronous active-high reset.
    input  logic        rst,
    // Register access from the bus master.
    axil_if.slave       s_axil,
    // Enables the stream filter.
    output logic        enable,
    // Holds the forwarded-byte counter at zero while high.
    output logic        clear,
    // Smallest byte value the filter forwards.
    output logic [7:0]  threshold,
    // Bytes forwarded since the counter was last cleared.
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

    always_ff @(posedge clk) begin
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
                case (awaddr[3:2])
                    2'd0:    ctrl_r      <= wdata;
                    2'd2:    threshold_r <= wdata;
                    2'd3:    scratch_r   <= wdata;
                    default: ;
                endcase
            end else if (s_axil.bready) begin
                bvalid_r <= 1'b0;
            end

            if (rd_fire) begin
                rvalid_r <= 1'b1;
                case (araddr[3:2])
                    2'd0:    rdata_r <= ctrl_r;
                    2'd1:    rdata_r <= {16'd0, count};
                    2'd2:    rdata_r <= threshold_r;
                    default: rdata_r <= scratch_r;
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

    assign enable    = ctrl_r[0];
    assign clear     = ctrl_r[1];
    assign threshold = threshold_r[7:0];
endmodule
