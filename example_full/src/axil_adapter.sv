// Flat AXI4-Lite to register file adapter.
//
// Presents the register bus as flat AXI4-Lite subordinate ports (so a VHDL
// bridge can drive it) and wraps them in an axil_if instance for axil_regs.
module axil_adapter (
    // System clock.
    input  logic        clk,
    // Synchronous active-high reset.
    input  logic        rst,
    // AXI4-Lite subordinate port.
    input  logic [7:0]    s_axil_awaddr,
    input  logic          s_axil_awvalid,
    output logic          s_axil_awready,
    input  logic [31:0]   s_axil_wdata,
    input  logic [3:0]    s_axil_wstrb,
    input  logic          s_axil_wvalid,
    output logic          s_axil_wready,
    output logic [1:0]    s_axil_bresp,
    output logic          s_axil_bvalid,
    input  logic          s_axil_bready,
    input  logic [7:0]    s_axil_araddr,
    input  logic          s_axil_arvalid,
    output logic          s_axil_arready,
    output logic [31:0]   s_axil_rdata,
    output logic [1:0]    s_axil_rresp,
    output logic          s_axil_rvalid,
    input  logic          s_axil_rready,
    // Starts a capture while high.
    output logic        start,
    // Enables the stream filters.
    output logic        filter_enable,
    // Holds the packet counter at zero while high.
    output logic        clear,
    // Clears the sampler's overflow flag while high.
    output logic        clear_overflow,
    // Smallest first-byte value the filters let through.
    output logic [7:0]  threshold,
    // Sampler controller state.
    input  logic [1:0]  state_code,
    // A sample was lost because the FIFO was full.
    input  logic        overflow,
    // Packets forwarded since the counter was last cleared.
    input  logic [15:0] count
);
    axil_if bus ();

    assign bus.awaddr = s_axil_awaddr;
    assign bus.awvalid = s_axil_awvalid;
    assign s_axil_awready = bus.awready;
    assign bus.wdata = s_axil_wdata;
    assign bus.wstrb = s_axil_wstrb;
    assign bus.wvalid = s_axil_wvalid;
    assign s_axil_wready = bus.wready;
    assign s_axil_bresp = bus.bresp;
    assign s_axil_bvalid = bus.bvalid;
    assign bus.bready = s_axil_bready;
    assign bus.araddr = s_axil_araddr;
    assign bus.arvalid = s_axil_arvalid;
    assign s_axil_arready = bus.arready;
    assign s_axil_rdata = bus.rdata;
    assign s_axil_rresp = bus.rresp;
    assign s_axil_rvalid = bus.rvalid;
    assign bus.rready = s_axil_rready;

    axil_regs u_regs (
        .clk(clk), .rst(rst), .s_axil(bus),
        .start(start), .filter_enable(filter_enable), .clear(clear), .clear_overflow(clear_overflow),
        .threshold(threshold), .state_code(state_code), .overflow(overflow), .count(count)
    );
endmodule
