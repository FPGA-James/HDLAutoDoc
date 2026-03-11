pwm_controller — Timing Diagrams
================================

All timing diagrams extracted from ``pwm_controller.sv``.
Diagrams are sourced from ``.. wavedrom::`` blocks in the VHDL
source comments above each process.

P Next State
------------

.. wavedrom::

   { "signal": [
   { "name": "clk",         "wave": "P............." },
   { "name": "en",          "wave": "01...........0" },
   { "name": "state",       "wave": "=.=........=..", "data": ["IDLE","COUNTING","DONE"] },
   { "name": "count",       "wave": "=.=........=..", "data": ["0","1..255","0"] },
   { "name": "period_done", "wave": "0..........1.0" }
   ]}

P Outputs
---------

.. wavedrom::

   { "signal": [
   { "name": "state",       "wave": "=.=.=.",     "data": ["IDLE","COUNTING","DONE"] },
   { "name": "count",       "wave": "=.=.=.",     "data": ["x","0..N","N"] },
   { "name": "duty_i",      "wave": "=.....",     "data": ["D"] },
   { "name": "pwm_o",       "wave": "0.x.0." },
   { "name": "period_done", "wave": "0...01" }
   ]}

P State Reg
-----------

.. wavedrom::

   { "signal": [
   { "name": "clk",   "wave": "P......." },
   { "name": "rst",   "wave": "1.0....." },
   { "name": "en",    "wave": "0......." },
   { "name": "state", "wave": "=.=.....", "data": ["(any)","IDLE"] },
   { "name": "pwm_o", "wave": "x.0....." }
   ]}
