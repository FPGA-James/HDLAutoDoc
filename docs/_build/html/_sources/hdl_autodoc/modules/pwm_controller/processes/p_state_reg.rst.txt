p_state_reg
===========

| **Source file:** ``pwm_controller.sv``
| **Source line:** 53
| **Block type:** ``always_ff``
| **Sensitivity list:** ``posedge clk``

Description
-----------

p_state_reg\: Clocked state and counter register.
Captures next_state on each rising edge of clk.
Synchronous reset drives state to IDLE and clears counter.
Counter increments each cycle in COUNTING state.

.. wavedrom::


   { "signal": [
   { "name": "clk",   "wave": "P......." },
   { "name": "rst",   "wave": "1.0....." },
   { "name": "en",    "wave": "0......." },
   { "name": "state", "wave": "=.=.....", "data": ["(any)","IDLE"] },
   { "name": "pwm_o", "wave": "x.0....." }
   ]}

Source
------

.. code-block:: systemverilog

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
