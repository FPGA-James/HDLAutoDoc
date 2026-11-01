// AXI4-Stream bundle.
//
// Carries bytes from a master to a slave with valid/ready flow control. It has
// no clock port: Yosys cannot pass a clocked interface instance to a submodule.
interface axis_if;
    // Payload byte.
    logic [7:0] tdata;
    // Master has a byte; slave takes it when tready is also high.
    logic       tvalid;
    // Slave can take a byte this cycle.
    logic       tready;
    // Last byte of a packet.
    logic       tlast;

    modport master (output tdata, tvalid, tlast, input  tready);
    modport slave  (input  tdata, tvalid, tlast, output tready);
endinterface
