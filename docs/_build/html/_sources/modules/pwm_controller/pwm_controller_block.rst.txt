pwm_controller — Block Diagram
==============================

Auto-extracted from ``pwm_controller.sv``.

.. graphviz:: pwm_controller_block.dot

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
     - ``logic``
     - System clock, rising-edge triggered.

   * - ``rst``
     - ``in``
     - ``logic``
     - Synchronous active-high reset.

   * - ``en``
     - ``in``
     - ``logic``
     - Enable signal. FSM runs when asserted.

   * - ``duty_i``
     - ``in``
     - ``logic[WIDTH-1:0]``
     - Duty cycle: 0=0%, 255=100%.

   * - ``pwm_o``
     - ``out``
     - ``logic``
     - PWM output signal.

   * - ``period_done``
     - ``out``
     - ``logic``
     - Active high when one full PWM period has completed.


Parameters
----------

.. list-table::
   :header-rows: 1

   * - Name
     - Type
     - Default
     - Description

   * - ``WIDTH``
     - ``int``
     - ``8``
     - —


Signals
-------

.. list-table::
   :header-rows: 1

   * - Signal
     - Type
     - Description

   * - ``count``
     - ``logic[WIDTH-1:0]``
     - Period counter register.
