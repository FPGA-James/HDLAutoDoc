traffic_light — Block Diagram
=============================

Auto-extracted from ``traffic_light.vhd``.

.. graphviz:: traffic_light_block.dot

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
     - Synchronous active-high reset. Returns FSM to RED state.

   * - ``timer_exp``
     - ``in``
     - ``std_logic``
     - Phase timer expiry pulse. Must be high for exactly one cycle.

   * - ``red_out``
     - ``out``
     - ``std_logic``
     - Red lamp drive. Asserted in RED and RED_AMBER states.

   * - ``amber_out``
     - ``out``
     - ``std_logic``
     - Amber lamp drive. Asserted in RED_AMBER and AMBER states.

   * - ``green_out``
     - ``out``
     - ``std_logic``
     - Green lamp drive. Asserted in GREEN state only.


Generics
--------

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Default
     - Description

   * - ``CLK_FREQ_HZ``
     - ``natural``
     - ``50_000_000``
     - System clock frequency in Hz. Used to derive phase timer counts.

   * - ``PHASE_MS``
     - ``natural``
     - ``5_000``
     - Duration of the RED and GREEN phases in milliseconds.

   * - ``TRANS_MS``
     - ``natural``
     - ``2_000``
     - Duration of the RED_AMBER and AMBER transition phases in milliseconds.
