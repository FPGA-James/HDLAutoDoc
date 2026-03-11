p_duty_capture
==============

| **Source file:** ``cfg_sync.vhd``
| **Source line:** 100
| **Block type:** ``process``
| **Sensitivity list:** ``sys_clk``

Description
-----------

p_duty_capture\: Capture duty_cycle_r directly in the sys_clk domain.
WARNING: This is an unsynchronised multi-bit crossing. duty_cycle_r is
driven in the cfg_clk domain and sampled here without a handshake or
grey-code scheme. Glitches are possible if both bits change together
near a sys_clk edge. A proper implementation should use a handshake
protocol or an async FIFO.

Source
------

.. code-block:: vhdl

       p_duty_capture : process(sys_clk) is
       begin
           if rising_edge(sys_clk) then
               if sys_rst = '1' then
                   pwm_duty <= (others => '0');
               else
                   pwm_duty <= duty_cycle_r;
               end if;
           end if;
       end process p_duty_capture;
