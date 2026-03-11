p_next_state
============

| **Source file:** ``traffic_light.vhd``
| **Source line:** 99
| **Block type:** ``process``
| **Sensitivity list:** ``state``, ``timer_exp``

Description
-----------

p_next_state\: Combinational next-state logic.
Evaluates the FSM transition function. Default assignment
next_state <= state implements hold when timer_exp is low.
All four transitions are guarded solely by timer_exp = 1.
Transitions:
.. code-block:: none

     RED       + timer_exp -> RED_AMBER
     RED_AMBER + timer_exp -> GREEN
     GREEN     + timer_exp -> AMBER
     AMBER     + timer_exp -> RED


.. wavedrom::


   { "signal": [
   { "name": "clk",       "wave": "P........." },
   { "name": "timer_exp", "wave": "0.1.1.1.1." },
   { "name": "state",     "wave": "=.=.=.=.=.",
   "data": ["RED","RED_AMB","GREEN","AMBER","RED"] },
   { "name": "red_out",   "wave": "1.1.0.0.1." },
   { "name": "amber_out", "wave": "0.1.0.1.0." },
   { "name": "green_out", "wave": "0.0.1.0.0." }
   ]}

Signal Assignments
------------------

.. list-table::
   :header-rows: 1

   * - State
     - ``next_state``

   * - ``RED``
     - RED_AMBER

   * - ``RED_AMBER``
     - GREEN

   * - ``GREEN``
     - AMBER

   * - ``AMBER``
     - RED


Source
------

.. code-block:: vhdl

       p_next_state : process(state, timer_exp)
       begin
           next_state <= state;
   
           case state is
               when RED =>
                   if timer_exp = '1' then
                       next_state <= RED_AMBER;
                   end if;
   
               when RED_AMBER =>
                   if timer_exp = '1' then
                       next_state <= GREEN;
                   end if;
   
               when GREEN =>
                   if timer_exp = '1' then
                       next_state <= AMBER;
                   end if;
   
               when AMBER =>
                   if timer_exp = '1' then
                       next_state <= RED;
                   end if;
           end case;
       end process p_next_state;
