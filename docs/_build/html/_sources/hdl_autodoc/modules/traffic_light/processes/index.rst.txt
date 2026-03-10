Processes
=========

Auto-extracted from ``traffic_light.vhd``.

.. toctree::
   :maxdepth: 1

   p_state_reg
   p_next_state
   p_outputs

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
     - 65
     - ✔

   * - :doc:`p_next_state`
     - ``process``
     - ``state``, ``timer_exp``
     - 99
     - ✔

   * - :doc:`p_outputs`
     - ``process``
     - ``state``
     - 147
     - ✔
