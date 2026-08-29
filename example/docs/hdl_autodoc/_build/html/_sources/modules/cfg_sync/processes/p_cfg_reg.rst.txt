p_cfg_reg
=========

| **Source file:** ``cfg_sync.vhd``
| **Source line:** 53
| **Block type:** ``process``
| **Sensitivity list:** ``cfg_clk``

Description
-----------

p_cfg_reg\: Register config inputs in the cfg_clk domain.
Provides a stable registered version of mode_sel and duty_cycle
before they cross into the sys_clk domain.

Source
------

.. code-block:: vhdl

       p_cfg_reg : process(cfg_clk) is
       begin
           if rising_edge(cfg_clk) then
               if cfg_rst = '1' then
                   mode_sel_r   <= '0';
                   duty_cycle_r <= (others => '0');
               else
                   mode_sel_r   <= mode_sel;
                   duty_cycle_r <= duty_cycle;
               end if;
           end if;
       end process p_cfg_reg;
