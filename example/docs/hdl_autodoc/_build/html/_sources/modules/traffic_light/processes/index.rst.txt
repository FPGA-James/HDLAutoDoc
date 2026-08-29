Processes
=========

Auto-extracted from ``traffic_light.vhd``.

.. toctree::
   :maxdepth: 2

   p_state_reg
   p_next_state
   p_outputs
   p_watchdog

Summary
-------

.. list-table::
   :header-rows: 1

   * - Block
     - Type
     - Sensitivity
     - Source Line
     - WaveDrom

   * - :doc:`p_state_reg`
     - ``process``
     - ``clk``
     - 81
     - ✔

   * - :doc:`p_next_state`
     - ``process``
     - ``state``, ``timer_exp``
     - 115
     - ✔

   * - :doc:`p_outputs`
     - ``process``
     - ``state``
     - 163
     - ✔

   * - :doc:`p_watchdog`
     - ``process``
     - ``clk``, ``por_n``
     - 187
     - —
