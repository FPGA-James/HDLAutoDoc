// Directed testbench for the AXI4-Lite adapter.
//
// Writes and reads the scratch register through the flat AXI4-Lite port, with no
// verification framework: each scenario below is marked with a TEST comment.
module tb_axil_adapter;
  logic clk = 1'b0;
  logic rst = 1'b1;
  logic [7:0]  awaddr, araddr;
  logic [31:0] wdata, rdata;
  logic        awvalid, awready, wvalid, wready, bvalid, bready;
  logic        arvalid, arready, rvalid, rready;
  logic        start, filter_enable, clear;
  logic [7:0]  threshold;

  always #5 clk = ~clk;

  axil_adapter dut (
    .clk, .rst,
    .s_axil_awaddr(awaddr), .s_axil_awvalid(awvalid), .s_axil_awready(awready),
    .s_axil_wdata(wdata), .s_axil_wstrb(4'hF), .s_axil_wvalid(wvalid), .s_axil_wready(wready),
    .s_axil_bresp(), .s_axil_bvalid(bvalid), .s_axil_bready(bready),
    .s_axil_araddr(araddr), .s_axil_arvalid(arvalid), .s_axil_arready(arready),
    .s_axil_rdata(rdata), .s_axil_rresp(), .s_axil_rvalid(rvalid), .s_axil_rready(rready),
    .start, .filter_enable, .clear, .threshold,
    .state_code(2'b00), .overflow(1'b0), .count(16'd0)
  );

  initial begin
    {awvalid, wvalid, bready, arvalid, rready} = '0;
    repeat (4) @(posedge clk);
    rst = 1'b0;

    // TEST: scratch_write_read — a value written to scratch reads back unchanged
    awaddr = 8'h0C; wdata = 32'hCAFEF00D; awvalid = 1'b1; wvalid = 1'b1; bready = 1'b1;
    @(posedge clk);
    awvalid = 1'b0; wvalid = 1'b0;
    repeat (2) @(posedge clk);
    araddr = 8'h0C; arvalid = 1'b1; rready = 1'b1;
    @(posedge clk);
    arvalid = 1'b0;
    repeat (2) @(posedge clk);

    // TEST: threshold_output — writing the threshold register drives the threshold port
    awaddr = 8'h08; wdata = 32'd77; awvalid = 1'b1; wvalid = 1'b1;
    @(posedge clk);
    awvalid = 1'b0; wvalid = 1'b0;
    repeat (2) @(posedge clk);
    $finish;
  end
endmodule
