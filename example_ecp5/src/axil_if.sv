// AXI4-Lite register bus: 8-bit byte address, 32-bit data.
interface axil_if;
    logic [7:0]  awaddr;    // Write address.
    logic        awvalid;   // Write address valid.
    logic        awready;   // Write address accepted.
    logic [31:0] wdata;     // Write data.
    logic [3:0]  wstrb;     // Write byte strobes.
    logic        wvalid;    // Write data valid.
    logic        wready;    // Write data accepted.
    logic [1:0]  bresp;     // Write response (OKAY = 0).
    logic        bvalid;    // Write response valid.
    logic        bready;    // Write response accepted.
    logic [7:0]  araddr;    // Read address.
    logic        arvalid;   // Read address valid.
    logic        arready;   // Read address accepted.
    logic [31:0] rdata;     // Read data.
    logic [1:0]  rresp;     // Read response (OKAY = 0).
    logic        rvalid;    // Read data valid.
    logic        rready;    // Read data accepted.

    modport master (
        output awaddr, awvalid, wdata, wstrb, wvalid, bready, araddr, arvalid, rready,
        input  awready, wready, bresp, bvalid, arready, rdata, rresp, rvalid
    );
    modport slave (
        input  awaddr, awvalid, wdata, wstrb, wvalid, bready, araddr, arvalid, rready,
        output awready, wready, bresp, bvalid, arready, rdata, rresp, rvalid
    );
endinterface
