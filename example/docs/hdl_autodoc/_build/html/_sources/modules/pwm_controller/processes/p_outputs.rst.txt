p_outputs
=========

| **Source file:** ``pwm_controller.sv``
| **Source line:** 114
| **Block type:** ``always_comb``
| **Sensitivity list:** ``*``

Description
-----------

p_outputs\: Combinational Moore output decode.
PWM output is high when counter is below duty_i threshold.
period_done pulses for exactly one cycle when state is DONE.
Output truth table:
.. code-block:: none

     IDLE     -> pwm_o=0 period_done=0
     COUNTING -> pwm_o=(count < duty_i) period_done=0
     DONE     -> pwm_o=0 period_done=1


.. wavedrom::


   { "signal": [
   { "name": "state",       "wave": "=.=.=.",     "data": ["IDLE","COUNTING","DONE"] },
   { "name": "count",       "wave": "=.=.=.",     "data": ["x","0..N","N"] },
   { "name": "duty_i",      "wave": "=.....",     "data": ["D"] },
   { "name": "pwm_o",       "wave": "0.x.0." },
   { "name": "period_done", "wave": "0...01" }
   ]}

Source
------

.. code-block:: systemverilog

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
