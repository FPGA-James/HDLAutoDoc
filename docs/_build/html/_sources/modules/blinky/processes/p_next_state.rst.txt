p_next_state
============

| **Source file:** ``blinky.vhd``
| **Source line:** 100
| **Sensitivity list:** ``state``, ``en``, ``timer_exp``

Description
-----------

p_next_state\: Combinational next-state logic.
FSM only advances when both en and timer_exp are asserted.
If en is deasserted the state holds regardless of timer_exp.
Transitions:
.. code-block:: none

     OFF_STATE  + en + timer_exp -> ON_STATE
     ON_STATE   + en + timer_exp -> FADE_STATE
     FADE_STATE + en + timer_exp -> OFF_STATE


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

Source
------

.. code-block:: vhdl

       begin
           next_state <= state;
   
           if en = '1' and timer_exp = '1' then
               case state is
                   when OFF_STATE  => next_state <= ON_STATE;
                   when ON_STATE   => next_state <= FADE_STATE;
                   when FADE_STATE => next_state <= OFF_STATE;
               end case;
           end if;
       end process p_next_state;
