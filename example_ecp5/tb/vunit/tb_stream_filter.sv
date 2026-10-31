// Testbench for stream_filter.
//
// Drives bytes into s_axis and checks which ones come out of m_axis: the filter
// forwards bytes at or above the threshold and drops the rest.
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
  task automatic send(input logic [7:0] value);
    s_axis.tdata  = value;
    s_axis.tvalid = 1'b1;
    s_axis.tlast  = 1'b0;
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

    // A byte equal to or above the threshold appears on m_axis.
    `TEST_CASE("passes_at_or_above_threshold") begin
      send(8'd100);
      `CHECK_EQUAL(m_axis.tvalid, 1'b1);
      `CHECK_EQUAL(m_axis.tdata, 8'd100);
    end

    // A byte below the threshold is dropped.
    `TEST_CASE("drops_below_threshold") begin
      send(8'd99);
      `CHECK_EQUAL(m_axis.tvalid, 1'b0);
    end

    // The counter counts only the bytes that were forwarded.
    `TEST_CASE("counts_forwarded_bytes") begin
      send(8'd50);
      send(8'd150);
      send(8'd200);
      `CHECK_EQUAL(count, 16'd2);
    end
  end
endmodule
