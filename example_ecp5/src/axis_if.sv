// AXI4-Stream bundle: one byte per beat, with a packet boundary marker.
interface axis_if;
    logic [7:0] tdata;    // Payload byte.
    logic       tvalid;   // The source has a byte this cycle.
    logic       tready;   // The sink accepts a byte this cycle.
    logic       tlast;    // Last byte of a packet.

    modport master (output tdata, tvalid, tlast, input  tready);
    modport slave  (input  tdata, tvalid, tlast, output tready);
endinterface
