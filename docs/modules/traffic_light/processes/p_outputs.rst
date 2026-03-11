p_outputs
=========

| **Source file:** ``traffic_light.vhd``
| **Source line:** 147
| **Block type:** ``process``
| **Sensitivity list:** ``state``

Description
-----------

p_outputs\: Combinational Moore output decode.
Drives lamp outputs based solely on current state.
All outputs default to 0 before the case statement to
prevent latches during synthesis.
Output truth table:
.. code-block:: none

     RED       -> red=1 amber=0 green=0
     RED_AMBER -> red=1 amber=1 green=0
     GREEN     -> red=0 amber=0 green=1
     AMBER     -> red=0 amber=1 green=0


.. wavedrom::


   { "signal": [
   { "name": "state",     "wave": "=.=.=.=.",
   "data": ["RED","RED_AMB","GREEN","AMBER"] },
   { "name": "red_out",   "wave": "1.1.0.0." },
   { "name": "amber_out", "wave": "0.1.0.1." },
   { "name": "green_out", "wave": "0.0.1.0." }
   ]}

Source
------

.. code-block:: vhdl

       p_outputs : process(state)
       begin
           red_out   <= '0';
           amber_out <= '0';
           green_out <= '0';
   
           case state is
               -- define red
               when RED       => red_out <= '1';
               when RED_AMBER => red_out <= '1'; amber_out <= '1';
               when GREEN     => green_out <= '1';
               when AMBER     => amber_out <= '1';
           end case;
       end process p_outputs;
