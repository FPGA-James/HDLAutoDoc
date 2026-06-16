traffic_light — Timing Diagrams
===============================

All timing diagrams extracted from ``traffic_light.vhd``.
Diagrams are sourced from ``.. wavedrom::`` blocks in the VHDL
source comments above each process.

P Next State
------------

.. wavedrom::

   { "signal": [
   { "name": "clk",       "wave": "P........." },
   { "name": "timer_exp", "wave": "0.1.1.1.1." },
   { "name": "state",     "wave": "=.=.=.=.=.",
   "data": ["RED","RED_AMB","GREEN","AMBER","RED"] },
   { "name": "red_out",   "wave": "1.1.0.0.1." },
   { "name": "amber_out", "wave": "0.1.0.1.0." },
   { "name": "green_out", "wave": "0.0.1.0.0." }
   ]}

P Outputs
---------

.. wavedrom::

   { "signal": [
   { "name": "state",     "wave": "=.=.=.=.",
   "data": ["RED","RED_AMB","GREEN","AMBER"] },
   { "name": "red_out",   "wave": "1.1.0.0." },
   { "name": "amber_out", "wave": "0.1.0.1." },
   { "name": "green_out", "wave": "0.0.1.0." }
   ]}

P State Reg
-----------

.. wavedrom::

   { "signal": [
   { "name": "clk",   "wave": "P......." },
   { "name": "rst",   "wave": "1.0....." },
   { "name": "state", "wave": "=.=.....", "data": ["(any)","RED"] },
   { "name": "red",   "wave": "x.1....." }
   ]}
