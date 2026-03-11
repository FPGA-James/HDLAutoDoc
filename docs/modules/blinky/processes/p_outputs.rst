p_outputs
=========

| **Source file:** ``blinky.vhd``
| **Source line:** 133
| **Block type:** ``process``
| **Sensitivity list:** ``state``

Description
-----------

p_outputs\: Combinational Moore output decode.
Drives LED outputs based solely on current state.
All outputs default to 0 before the case statement to
prevent latches during synthesis.
Output truth table:
.. code-block:: none

     OFF_STATE  -> led_on=0 led_fade=0 led_off=1
     ON_STATE   -> led_on=1 led_fade=0 led_off=0
     FADE_STATE -> led_on=0 led_fade=1 led_off=0


.. wavedrom::


   { "signal": [
   { "name": "state",    "wave": "=.=.=.=.",
   "data": ["OFF","ON","FADE","OFF"] },
   { "name": "led_on",   "wave": "0.1.0.0." },
   { "name": "led_fade", "wave": "0.0.1.0." },
   { "name": "led_off",  "wave": "1.0.0.1." }
   ]}

Source
------

.. code-block:: vhdl

       p_outputs : process(state)
       begin
           led_on   <= '0';
           led_fade <= '0';
           led_off  <= '0';
   
           case state is
               when OFF_STATE  => led_off  <= '1';
               when ON_STATE   => led_on   <= '1';
               when FADE_STATE => led_fade <= '1';
           end case;
       end process p_outputs;
