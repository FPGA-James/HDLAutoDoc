p_state_reg
===========

| **Source file:** ``blinky.vhd``
| **Source line:** 67
| **Sensitivity list:** ``clk``

Description
-----------

p_state_reg\: Clocked state register.
Captures next_state on each rising edge of clk.
Synchronous reset drives state back to OFF_STATE.

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

Source
------

.. code-block:: vhdl

       begin
           if rising_edge(clk) then
               if rst = '1' then
                   state <= OFF_STATE;
               else
                   state <= next_state;
               end if;
           end if;
       end process p_state_reg;
