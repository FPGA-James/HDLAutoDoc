traffic_light State Machine
===========================

Auto-extracted from ``traffic_light.vhd``.

State Transition Diagram
------------------------

.. graphviz:: traffic_light.dot

State Output Table
------------------

.. list-table::
   :header-rows: 1

   * - State
     - ``red_out``
     - ``amber_out``
     - ``green_out``

   * - ``RED``
     - 1
     - 0
     - 0

   * - ``RED_AMBER``
     - 1
     - 1
     - 0

   * - ``GREEN``
     - 0
     - 0
     - 1

   * - ``AMBER``
     - 0
     - 1
     - 0


Transitions
-----------

.. list-table::
   :header-rows: 1

   * - From
     - To
     - Condition

   * - ``RED``
     - ``RED_AMBER``
     - ``timer_exp = '1'``

   * - ``RED_AMBER``
     - ``GREEN``
     - ``timer_exp = '1'``

   * - ``GREEN``
     - ``AMBER``
     - ``timer_exp = '1'``

   * - ``AMBER``
     - ``RED``
     - ``timer_exp = '1'``
