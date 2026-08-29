traffic_light — Reset Domain Analysis
=====================================

Auto-extracted from ``traffic_light.vhd``.

.. graphviz:: traffic_light_reset.dot

Reset Domains
-------------

.. list-table::
   :header-rows: 1

   * - Process
     - Clock
     - Reset
     - Style

   * - ``p_watchdog``
     - ``clk``
     - ``por_n``
     - Async

   * - ``p_state_reg``
     - ``clk``
     - ``rst``
     - Sync


.. warning::

   The following signals cross between different reset domains. Logic driven under one reset may not be in a consistent state when the other reset releases.


Signal Crossings
----------------

.. list-table::
   :header-rows: 1

   * - Signal
     - Source Reset
     - Destination Reset

   * - ``state``
     - ``rst``
     - ``por_n``
