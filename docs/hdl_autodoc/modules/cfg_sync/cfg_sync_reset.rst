cfg_sync — Reset Domain Analysis
================================

Auto-extracted from ``cfg_sync.vhd``.

.. graphviz:: cfg_sync_reset.dot

Reset Domains
-------------

.. list-table::
   :header-rows: 1

   * - Process
     - Clock
     - Reset
     - Style

   * - ``p_cfg_reg``
     - ``cfg_clk``
     - ``cfg_rst``
     - Sync

   * - ``p_mode_sync``
     - ``sys_clk``
     - ``sys_rst``
     - Sync

   * - ``p_duty_capture``
     - ``sys_clk``
     - ``sys_rst``
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

   * - ``duty_cycle_r``
     - ``cfg_rst``
     - ``sys_rst``

   * - ``mode_sel_r``
     - ``cfg_rst``
     - ``sys_rst``
