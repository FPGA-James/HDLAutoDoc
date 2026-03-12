p_watchdog
==========

| **Source file:** ``traffic_light.vhd``
| **Source line:** 187
| **Block type:** ``process``
| **Sensitivity list:** ``clk``, ``por_n``

Description
-----------

p_watchdog\: Phase watchdog counter.
Increments each clock cycle to track how long the FSM has been in the
current phase. Resets to zero whenever the FSM returns to RED.
Uses por_n (async active-low) rather than rst so the counter is
guaranteed zero at power-on before rst has been asserted by the system.
This creates a deliberate reset domain crossing: state is driven under
rst (synchronous) but read here under por_n (asynchronous).

Source
------

.. code-block:: vhdl

       p_watchdog : process(clk, por_n) is
       begin
           if por_n = '0' then
               phase_cnt <= (others => '0');
           elsif rising_edge(clk) then
               if state = RED then
                   phase_cnt <= (others => '0');
               else
                   phase_cnt <= std_logic_vector(unsigned(phase_cnt) + 1);
               end if;
           end if;
       end process p_watchdog;
