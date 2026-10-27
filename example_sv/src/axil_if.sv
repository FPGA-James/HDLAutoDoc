// AXI4-Lite write channel (reduced).
interface axil_if (input logic clk);
    logic [31:0] awaddr;
    logic        awvalid;
    logic        awready;
    logic [31:0] wdata;

    modport slave  (input awaddr, awvalid, wdata, output awready);
    modport master (output awaddr, awvalid, wdata, input awready);
endinterface
