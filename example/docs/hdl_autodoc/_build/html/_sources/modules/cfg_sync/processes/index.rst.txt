Processes
=========

Auto-extracted from ``cfg_sync.vhd``.

.. toctree::
   :maxdepth: 2

   p_cfg_reg
   p_mode_sync
   p_duty_capture

Summary
-------

.. list-table::
   :header-rows: 1

   * - Block
     - Type
     - Sensitivity
     - Source Line
     - WaveDrom

   * - :doc:`p_cfg_reg`
     - ``process``
     - ``cfg_clk``
     - 53
     - —

   * - :doc:`p_mode_sync`
     - ``process``
     - ``sys_clk``
     - 80
     - ✔

   * - :doc:`p_duty_capture`
     - ``process``
     - ``sys_clk``
     - 100
     - —
