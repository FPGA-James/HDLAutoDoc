blinky — Timing Diagrams
========================

All timing diagrams extracted from ``blinky.vhd``.
Diagrams are sourced from ``.. wavedrom::`` blocks in the VHDL
source comments above each process.

P Next State
------------

.. wavedrom::

   { "signal": [
   { "name": "clk",       "wave": "P............." },
   { "name": "en",        "wave": "01...........0" },
   { "name": "timer_exp", "wave": "0..1..1..1..0." },
   { "name": "state",     "wave": "=..=..=..=..=.",
   "data": ["OFF","ON","FADE","OFF","OFF"] },
   { "name": "led_on",    "wave": "0..1..0..0..0." },
   { "name": "led_fade",  "wave": "0..0..1..0..0." },
   { "name": "led_off",   "wave": "1..0..0..1..1." }
   ]}

P Outputs
---------

.. wavedrom::

   { "signal": [
   { "name": "state",    "wave": "=.=.=.=.",
   "data": ["OFF","ON","FADE","OFF"] },
   { "name": "led_on",   "wave": "0.1.0.0." },
   { "name": "led_fade", "wave": "0.0.1.0." },
   { "name": "led_off",  "wave": "1.0.0.1." }
   ]}

P State Reg
-----------

.. wavedrom::

   { "signal": [
   { "name": "clk",       "wave": "P......." },
   { "name": "rst",       "wave": "1.0....." },
   { "name": "en",        "wave": "0......." },
   { "name": "state",     "wave": "=.=.....", "data": ["(any)","OFF"] },
   { "name": "led_on",    "wave": "x.0....." },
   { "name": "led_fade",  "wave": "x.0....." },
   { "name": "led_off",   "wave": "x.1....." }
   ]}
