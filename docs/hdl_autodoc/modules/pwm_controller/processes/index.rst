Processes
=========

Auto-extracted from ``pwm_controller.sv``.

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
     - ``always_ff``
     - ``posedge clk``
     - 53
     - ✔

   * - :doc:`p_next_state`
     - ``always_comb``
     - ``*``
     - 85
     - ✔

   * - :doc:`p_outputs`
     - ``always_comb``
     - ``*``
     - 114
     - ✔
