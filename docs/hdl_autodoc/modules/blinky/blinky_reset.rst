blinky — Reset Domain Analysis
==============================

Auto-extracted from ``blinky.vhd``.

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
