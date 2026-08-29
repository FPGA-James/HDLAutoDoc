p_next_state
============

| **Source file:** ``pwm_controller.sv``
| **Source line:** 85
| **Block type:** ``always_comb``
| **Sensitivity list:** ``*``

Description
-----------

p_next_state\: Combinational next-state logic.
FSM advances only when en is asserted.
COUNTING state runs for a full 256-cycle period then moves to DONE.
Transitions:
.. code-block:: none

     IDLE     + en           -> COUNTING
     COUNTING + count==255   -> DONE
     DONE                    -> IDLE


.. wavedrom::


   { "signal": [
   { "name": "clk",         "wave": "P............." },
   { "name": "en",          "wave": "01...........0" },
   { "name": "state",       "wave": "=.=........=..", "data": ["IDLE","COUNTING","DONE"] },
   { "name": "count",       "wave": "=.=........=..", "data": ["0","1..255","0"] },
   { "name": "period_done", "wave": "0..........1.0" }
   ]}

Source
------

.. code-block:: systemverilog

       always_comb begin : p_next_state
           next_state = state;
           case (state)
               IDLE:     if (en)              next_state = COUNTING;
               COUNTING: if (count == 8'hFF)  next_state = DONE;
               DONE:                          next_state = IDLE;
               default:                       next_state = IDLE;
           endcase
       end
