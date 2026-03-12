pwm_controller — Reset Domain Analysis
======================================

Auto-extracted from ``pwm_controller.sv``.

.. note::

   All clocked processes use a single reset domain (``rst``, sync). No reset domain crossings detected.

Reset Domain
------------

.. list-table::
   :header-rows: 1

   * - Process
     - Clock
     - Reset
     - Style

   * - ``p_state_reg``
     - ``clk``
     - ``rst``
     - Sync
