blinky — Block Diagram
======================

Auto-extracted from ``blinky.vhd``.

.. graphviz:: blinky_block.dot

Ports
-----

.. list-table::
   :header-rows: 1

   * - Port
     - Direction
     - Type
     - Description

   * - ``clk``
     - ``in``
     - ``std_logic``
     - System clock, rising-edge triggered.

   * - ``rst``
     - ``in``
     - ``std_logic``
     - Synchronous active-high reset. Returns FSM to OFF state.

   * - ``en``
     - ``in``
     - ``std_logic``
     - Enable signal. FSM only advances when en is asserted.

   * - ``timer_exp``
     - ``in``
     - ``std_logic``
     - Phase timer expiry pulse. Must be high for exactly one cycle.

   * - ``led_on``
     - ``out``
     - ``std_logic``
     - LED full-brightness drive.

   * - ``led_fade``
     - ``out``
     - ``std_logic``
     - LED half-brightness PWM drive (fade effect).

   * - ``led_off``
     - ``out``
     - ``std_logic``
     - LED off indicator (all drives deasserted).


Signals
-------

.. list-table::
   :header-rows: 1

   * - Signal
     - Type
     - Description

   * - ``state``
     - ``t_state``
     - Current state register, initialised to OFF at power-on.

   * - ``next_state``
     - ``t_state``
     - Next state combinational signal.
