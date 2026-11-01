// Clock and reset smoke test.
//
// Checks only that a free-running clock toggles; it does not instantiate any
// design module, so it is not linked to one.
module tb_smoke;
  logic clk = 1'b0;
  always #5 clk = ~clk;

  initial begin
    // TEST: clock_toggles — the clock changes level
    @(posedge clk);
    @(negedge clk);
    $finish;
  end
endmodule
