// PWM controller module.
//
// Generates a variable duty-cycle PWM signal using a 3-state FSM:
// IDLE -> COUNTING -> DONE. The duty cycle is set via the duty_i port.
// The period is fixed at 256 clock cycles.
module pwm_controller #(
    parameter int WIDTH = 8
)(
    // System clock, rising-edge triggered.
    input  logic              clk,
    // Synchronous active-high reset.
    input  logic              rst,
    // Enable signal. FSM runs when asserted.
    input  logic              en,
    // Duty cycle: 0=0%, 255=100%.
    input  logic [WIDTH-1:0]  duty_i,
    // PWM output signal.
    output logic              pwm_o,
    // Active high when one full PWM period has completed.
    output logic              period_done
);

    // FSM state encoding
    typedef enum logic [1:0] {
        // Waiting for enable.
        IDLE,
        // Counting through the PWM period.
        COUNTING,
        // Period complete, pulse period_done for one cycle.
        DONE
    } t_state;

    t_state state, next_state;

    // Period counter register.
    logic [WIDTH-1:0] count;

    // p_state_reg: Clocked state and counter register.
    //
    // Captures next_state on each rising edge of clk.
    // Synchronous reset drives state to IDLE and clears counter.
    // Counter increments each cycle in COUNTING state.
    //
    // // wavedrom::
    //
    //    { "signal": [
    //      { "name": "clk",   "wave": "P......." },
    //      { "name": "rst",   "wave": "1.0....." },
    //      { "name": "en",    "wave": "0......." },
    //      { "name": "state", "wave": "=.=.....", "data": ["(any)","IDLE"] },
    //      { "name": "pwm_o", "wave": "x.0....." }
    //    ]}
    always_ff @(posedge clk) begin : p_state_reg
        if (rst) begin
            state <= IDLE;
            count <= '0;
        end else begin
            state <= next_state;
            if (state == COUNTING)
                count <= count + 1'b1;
            else
                count <= '0;
        end
    end

    // p_next_state: Combinational next-state logic.
    //
    // FSM advances only when en is asserted.
    // COUNTING state runs for a full 256-cycle period then moves to DONE.
    //
    // Transitions:
    //   IDLE     + en           -> COUNTING
    //   COUNTING + count==255   -> DONE
    //   DONE                    -> IDLE
    //
    // // wavedrom::
    //
    //    { "signal": [
    //      { "name": "clk",         "wave": "P............." },
    //      { "name": "en",          "wave": "01...........0" },
    //      { "name": "state",       "wave": "=.=........=..", "data": ["IDLE","COUNTING","DONE"] },
    //      { "name": "count",       "wave": "=.=........=..", "data": ["0","1..255","0"] },
    //      { "name": "period_done", "wave": "0..........1.0" }
    //    ]}
    always_comb begin : p_next_state
        next_state = state;
        case (state)
            IDLE:     if (en)              next_state = COUNTING;
            COUNTING: if (count == 8'hFF)  next_state = DONE;
            DONE:                          next_state = IDLE;
            default:                       next_state = IDLE;
        endcase
    end

    // p_outputs: Combinational Moore output decode.
    //
    // PWM output is high when counter is below duty_i threshold.
    // period_done pulses for exactly one cycle when state is DONE.
    //
    // Output truth table:
    //   IDLE     -> pwm_o=0 period_done=0
    //   COUNTING -> pwm_o=(count < duty_i) period_done=0
    //   DONE     -> pwm_o=0 period_done=1
    //
    // // wavedrom::
    //
    //    { "signal": [
    //      { "name": "state",       "wave": "=.=.=.",     "data": ["IDLE","COUNTING","DONE"] },
    //      { "name": "count",       "wave": "=.=.=.",     "data": ["x","0..N","N"] },
    //      { "name": "duty_i",      "wave": "=.....",     "data": ["D"] },
    //      { "name": "pwm_o",       "wave": "0.x.0." },
    //      { "name": "period_done", "wave": "0...01" }
    //    ]}
    always_comb begin : p_outputs
        pwm_o       = 1'b0;
        period_done = 1'b0;
        case (state)
            IDLE:     begin pwm_o = 1'b0;           period_done = 1'b0; end
            COUNTING: begin pwm_o = (count < duty_i); period_done = 1'b0; end
            DONE:     begin pwm_o = 1'b0;           period_done = 1'b1; end
            default:  begin pwm_o = 1'b0;           period_done = 1'b0; end
        endcase
    end

endmodule
