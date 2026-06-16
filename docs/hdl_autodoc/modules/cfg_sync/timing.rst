cfg_sync — Timing Diagrams
==========================

All timing diagrams extracted from ``cfg_sync.vhd``.
Diagrams are sourced from ``.. wavedrom::`` blocks in the VHDL
source comments above each process.

P Mode Sync
-----------

.. wavedrom::

   { "signal": [
   { "name": "cfg_clk",    "wave": "p........" },
   { "name": "sys_clk",    "wave": "P........" },
   { "name": "mode_sel_r", "wave": "0...1...." },
   { "name": "mode_meta",  "wave": "0....1..." },
   { "name": "mode_sync_r","wave": "0.....1.." }
   ]}
