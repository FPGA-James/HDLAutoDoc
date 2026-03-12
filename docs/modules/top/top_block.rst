top — Block Diagram
===================

Auto-extracted from ``top.vhd``.

.. graphviz:: top_block.dot

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
     - System clock 50 MHz.

   * - ``rst``
     - ``in``
     - ``std_logic``
     - Synchronous active-high reset (sys_clk domain).

   * - ``cfg_clk``
     - ``in``
     - ``std_logic``
     - Config bus clock (slow, e.g. 10 MHz from external MCU).

   * - ``cfg_rst``
     - ``in``
     - ``std_logic``
     - Synchronous active-high reset (cfg_clk domain).

   * - ``mode_sel``
     - ``in``
     - ``std_logic``
     - Config inputs (cfg_clk domain).

   * - ``duty_cycle``
     - ``in``
     - ``std_logic_vector(7 downto 0)``
     - —

   * - ``red_out``
     - ``out``
     - ``std_logic``
     - Traffic light outputs.

   * - ``amber_out``
     - ``out``
     - ``std_logic``
     - —

   * - ``green_out``
     - ``out``
     - ``std_logic``
     - —

   * - ``led_on``
     - ``out``
     - ``std_logic``
     - Blinky LED outputs.

   * - ``led_fade``
     - ``out``
     - ``std_logic``
     - —

   * - ``led_off``
     - ``out``
     - ``std_logic``
     - —

   * - ``pwm_out``
     - ``out``
     - ``std_logic``
     - PWM output for LED fading (shared).
