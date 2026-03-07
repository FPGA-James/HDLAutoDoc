Processes
=========

Auto-extracted from ``blinky.vhd``.

.. toctree::
   :maxdepth: 1

   p_state_reg
   p_next_state
   p_outputs

Summary
-------

.. list-table::
   :header-rows: 1

   * - Process
     - Type
     - Sensitivity List
     - Source Line
     - WaveDrom

   * - :doc:`p_state_reg`
     - Clocked
     - ``clk``
     - 67
     - ✔

   * - :doc:`p_next_state`
     - Combinational
     - ``state``, ``en``, ``timer_exp``
     - 100
     - ✔

   * - :doc:`p_outputs`
     - Combinational
     - ``state``
     - 133
     - ✔
