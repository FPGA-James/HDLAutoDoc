pwm_controller State Machine
============================

Auto-extracted from ``pwm_controller.sv``.

State Transition Diagram
------------------------

.. graphviz:: pwm_controller.dot

State Output Table
------------------

.. list-table::
   :header-rows: 1

   * - State
     - ``pwm_o``
     - ``period_done``

   * - ``IDLE``
     - 0
     - 0

   * - ``COUNTING``
     - 0
     - 0

   * - ``DONE``
     - 0
     - 1


Transitions
-----------

.. list-table::
   :header-rows: 1

   * - From
     - To
     - Condition

   * - ``IDLE``
     - ``COUNTING``
     - ``en``

   * - ``COUNTING``
     - ``DONE``
     - ``count == 8'hFF``

   * - ``DONE``
     - ``IDLE``
     - (always)
