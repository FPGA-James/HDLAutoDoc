// AXI4-Lite register bus bundle.
//
// All five channels of the single-beat register bus. The clock is a port so each
// instance is tied to one domain.
interface axil_if (input logic clk);
    // Write address channel.
    logic [7:0]  awaddr;
    logic        awvalid;
    logic        awready;
    // Write data channel.
    logic [31:0] wdata;
    logic [3:0]  wstrb;
    logic        wvalid;
    logic        wready;
    // Write response channel.
    logic [1:0]  bresp;
    logic        bvalid;
    logic        bready;
    // Read address channel.
    logic [7:0]  araddr;
    logic        arvalid;
    logic        arready;
    // Read data channel.
    logic [31:0] rdata;
    logic [1:0]  rresp;
    logic        rvalid;
    logic        rready;

    modport slave (
        input  awaddr, awvalid, wdata, wstrb, wvalid, bready, araddr, arvalid, rready,
        output awready, wready, bresp, bvalid, arready, rdata, rresp, rvalid
    );
    modport master (
        output awaddr, awvalid, wdata, wstrb, wvalid, bready, araddr, arvalid, rready,
        input  awready, wready, bresp, bvalid, arready, rdata, rresp, rvalid
    );
endinterface
