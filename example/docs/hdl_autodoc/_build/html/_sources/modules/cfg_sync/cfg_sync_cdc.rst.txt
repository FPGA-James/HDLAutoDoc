cfg_sync — Clock Domain Analysis
================================

Auto-extracted from ``cfg_sync.vhd``.

.. graphviz:: cfg_sync_cdc.dot

Clock Domains
-------------

.. list-table::
   :header-rows: 1

   * - Clock
     - Clocked Processes

   * - ``cfg_clk``
     - ``p_cfg_reg``

   * - ``sys_clk``
     - ``p_mode_sync``, ``p_duty_capture``


.. warning::

   The following signal(s) cross clock domains without a detected synchronizer: ``duty_cycle_r``.


Signal Crossings
----------------

.. list-table::
   :header-rows: 1

   * - Signal
     - Source Domain
     - Destination Domain
     - Synchronized

   * - ``duty_cycle_r``
     - ``cfg_clk``
     - ``sys_clk``
     - **No**

   * - ``mode_sel_r``
     - ``cfg_clk``
     - ``sys_clk``
     - Yes *(two-flop)*
