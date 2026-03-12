cfg_sync — Block Diagram
========================

Auto-extracted from ``cfg_sync.vhd``.

.. graphviz:: cfg_sync_block.dot

Ports
-----

.. list-table::
   :header-rows: 1

   * - Port
     - Direction
     - Type
     - Description

   * - ``sys_clk``
     - ``in``
     - ``std_logic``
     - System clock domain (50 MHz).

   * - ``sys_rst``
     - ``in``
     - ``std_logic``
     - Synchronous active-high reset (sys_clk domain).

   * - ``cfg_clk``
     - ``in``
     - ``std_logic``
     - Config clock domain (slow bus clock).

   * - ``cfg_rst``
     - ``in``
     - ``std_logic``
     - Synchronous active-high reset (cfg_clk domain).

   * - ``mode_sel``
     - ``in``
     - ``std_logic``
     - Blinky enable: 1 = blinky LED active.

   * - ``duty_cycle``
     - ``in``
     - ``std_logic_vector(7 downto 0)``
     - PWM duty cycle: 0x00 = 0 %, 0xFF = 100 %.

   * - ``blinky_en``
     - ``out``
     - ``std_logic``
     - Synchronised blinky enable (two-flop).

   * - ``pwm_duty``
     - ``out``
     - ``std_logic_vector(7 downto 0)``
     - PWM duty cycle (unsynchronised crossing).


Signals
-------

.. list-table::
   :header-rows: 1

   * - Signal
     - Type
     - Description

   * - ``mode_sel_r``
     - ``std_logic``
     - cfg_clk domain registers

   * - ``duty_cycle_r``
     - ``std_logic_vector(7 downto 0)``
     - —

   * - ``mode_meta``
     - ``std_logic``
     - sys_clk domain: two-flop synchroniser pipeline for mode_sel_r

   * - ``mode_sync_r``
     - ``std_logic``
     - —
