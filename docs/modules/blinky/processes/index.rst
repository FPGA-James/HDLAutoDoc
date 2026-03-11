Processes
=========

Auto-extracted from ``blinky.vhd``.

.. toctree::
   :maxdepth: 2

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
     - 67
     - ✔

   * - :doc:`p_next_state`
     - ``process``
     - ``state``, ``en``, ``timer_exp``
     - 100
     - ✔

   * - :doc:`p_outputs`
     - ``process``
     - ``state``
     - 133
     - ✔
