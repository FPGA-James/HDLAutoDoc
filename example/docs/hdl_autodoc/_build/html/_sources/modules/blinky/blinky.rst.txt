blinky State Machine
====================

Auto-extracted from ``blinky.vhd``.

State Transition Diagram
------------------------

.. graphviz:: blinky.dot

State Output Table
------------------

.. list-table::
   :header-rows: 1

   * - State
     - ``led_on``
     - ``led_fade``
     - ``led_off``

   * - ``OFF_STATE``
     - 0
     - 0
     - 1

   * - ``ON_STATE``
     - 1
     - 0
     - 0

   * - ``FADE_STATE``
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

   * - ``OFF_STATE``
     - ``ON_STATE``
     - (always)

   * - ``ON_STATE``
     - ``FADE_STATE``
     - (always)

   * - ``FADE_STATE``
     - ``OFF_STATE``
     - (always)
