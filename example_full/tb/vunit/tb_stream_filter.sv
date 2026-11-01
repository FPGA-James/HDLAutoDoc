// Testbench for stream_filter.
//
// Sends single-byte and multi-byte packets and checks that a packet is forwarded
// or dropped as a whole according to its first byte.
`include "vunit_defines.svh"

module tb_stream_filter;
  logic        clk = 1'b0;
  logic        rst = 1'b1;
  logic        enable = 1'b1;
  logic        clear  = 1'b0;
  logic [7:0]  threshold = 8'd100;
  logic [15:0] count;

  axis_if s_axis ();
  axis_if m_axis ();

  always #5 clk = ~clk;

  stream_filter dut (.clk, .rst, .enable, .clear, .threshold, .s_axis, .m_axis, .count);

  // Sends one byte and waits one cycle.
  task automatic send(input logic [7:0] value, input logic last);
    s_axis.tdata  = value;
    s_axis.tvalid = 1'b1;
    s_axis.tlast  = last;
    m_axis.tready = 1'b1;
    @(posedge clk);
    s_axis.tvalid = 1'b0;
    @(posedge clk);
  endtask

  `TEST_SUITE begin
    `TEST_SETUP begin
      rst = 1'b1;
      repeat (2) @(posedge clk);
      rst = 1'b0;
    end

    // A packet whose first byte reaches the threshold is forwarded.
    `TEST_CASE("forwards_packet_at_threshold") begin
      send(8'd100, 1'b1);
      `CHECK_EQUAL(count, 16'd1);
    end

    // A packet whose first byte is below the threshold is dropped whole.
    `TEST_CASE("drops_packet_below_threshold") begin
      send(8'd99, 1'b0);
      send(8'd200, 1'b1);
      `CHECK_EQUAL(count, 16'd0);
    end

    // Only forwarded packets are counted.
    `TEST_CASE("counts_forwarded_packets") begin
      send(8'd50, 1'b1);
      send(8'd150, 1'b1);
      send(8'd200, 1'b1);
      `CHECK_EQUAL(count, 16'd2);
    end
  end
endmodule
