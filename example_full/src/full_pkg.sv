// Shared types for example_full.
//
// Gathers the constants and types that more than one module agrees on, so the
// widths and encodings are written down once.
package full_pkg;
    // Width of one captured sample in bits.
    localparam int SAMPLE_W = 12;

    // Width of a register-bus address in bits.
    localparam int ADDR_W = 8;

    // Sampler state, shared by the controller and the capture path.
    typedef enum logic [1:0] {
        SAMPLE_IDLE,
        SAMPLE_ARMED,
        SAMPLE_RUN,
        SAMPLE_DONE
    } sample_state_t;
endpackage
