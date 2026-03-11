p_mode_sync
===========

| **Source file:** ``cfg_sync.vhd``
| **Source line:** 80
| **Block type:** ``process``
| **Sensitivity list:** ``sys_clk``

Description
-----------

p_mode_sync\: Two-flop synchroniser for mode_sel_r (cfg_clk → sys_clk).
mode_sel_r is sampled twice in the sys_clk domain to resolve
metastability before the signal is used by downstream logic.

.. wavedrom::


   { "signal": [
   { "name": "cfg_clk",    "wave": "p........" },
   { "name": "sys_clk",    "wave": "P........" },
   { "name": "mode_sel_r", "wave": "0...1...." },
   { "name": "mode_meta",  "wave": "0....1..." },
   { "name": "mode_sync_r","wave": "0.....1.." }
   ]}

Source
------

.. code-block:: vhdl

       p_mode_sync : process(sys_clk) is
       begin
           if rising_edge(sys_clk) then
               if sys_rst = '1' then
                   mode_meta   <= '0';
                   mode_sync_r <= '0';
               else
                   mode_meta   <= mode_sel_r;
                   mode_sync_r <= mode_meta;
               end if;
           end if;
       end process p_mode_sync;
