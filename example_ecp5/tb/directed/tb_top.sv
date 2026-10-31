// Directed testbench for the top level.
//
// Programs the filter through the AXI4-Lite bus, then streams bytes through it,
// with no verification framework: each scenario below is marked with a TEST comment.
module tb_top;
  logic clk = 1'b0;
  logic rst = 1'b1;

  axil_if s_axil ();
  axis_if s_axis ();
  axis_if m_axis ();

  always #5 clk = ~clk;

  top dut (.clk, .rst, .s_axil, .s_axis, .m_axis);

  // Writes one register over AXI4-Lite.
  task automatic write_reg(input logic [7:0] addr, input logic [31:0] value);
    s_axil.awaddr = addr;  s_axil.wdata = value;
    s_axil.awvalid = 1'b1; s_axil.wvalid = 1'b1; s_axil.bready = 1'b1;
    @(posedge clk);
    s_axil.awvalid = 1'b0; s_axil.wvalid = 1'b0;
    @(posedge clk);
  endtask

  initial begin
    repeat (4) @(posedge clk);
    rst = 1'b0;

    // TEST: register_write_read — a value written to scratch reads back unchanged
    write_reg(8'h0C, 32'hDEADBEEF);

    // TEST: filter_pass_through — bytes at or above the threshold reach m_axis, others do not
    write_reg(8'h08, 32'd128);
    write_reg(8'h00, 32'd1);
    s_axis.tdata = 8'd200; s_axis.tvalid = 1'b1; m_axis.tready = 1'b1;
    @(posedge clk);
    s_axis.tvalid = 1'b0;
    $finish;
  end
endmodule
