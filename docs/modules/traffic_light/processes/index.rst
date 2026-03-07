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

   * - Process
     - Type
     - Sensitivity List
     - Source Line
     - WaveDrom

   * - :doc:`p_state_reg`
     - Clocked
     - ``clk``
     - 65
     - ✔

   * - :doc:`p_next_state`
     - Combinational
     - ``state``, ``timer_exp``
     - 99
     - ✔

   * - :doc:`p_outputs`
     - Combinational
     - ``state``
     - 147
     - ✔
