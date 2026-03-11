p_state_reg
===========

| **Source file:** ``traffic_light.vhd``
| **Source line:** 65
| **Block type:** ``process``
| **Sensitivity list:** ``clk``

Description
-----------

p_state_reg\: Clocked state register.
Captures next_state on each rising edge of clk.
When rst is asserted the state returns to RED synchronously,
regardless of timer_exp or next_state.

.. wavedrom::


   { "signal": [
   { "name": "clk",   "wave": "P......." },
   { "name": "rst",   "wave": "1.0....." },
   { "name": "state", "wave": "=.=.....", "data": ["(any)","RED"] },
   { "name": "red",   "wave": "x.1....." }
   ]}

Source
------

.. code-block:: vhdl

       p_state_reg : process(clk)
       begin
           if rising_edge(clk) then
               if rst = '1' then
                   state <= RED;
               else
                   state <= next_state;
               end if;
           end if;
       end process p_state_reg;
