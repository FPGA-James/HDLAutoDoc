// AXI4-Stream bundle.
interface axis_if (input logic clk);
    // Payload byte.
    logic [7:0] tdata;
    logic       tvalid, tready;   // Handshake.
    logic       tlast;

    modport master (output tdata, tvalid, tlast, input  tready);
    modport slave  (input  tdata, tvalid, tlast, output tready);
endinterface
