Design Hierarchy
================

Top-level module: ``top``
Total modules: 4

Instantiation Tree
-------------------

.. graphviz:: hierarchy.dot

Module List
-----------

.. list-table::
   :header-rows: 1

   * - Module
     - Source File
     - Parents
     - Children

   * - :doc:`modules/blinky/index`
     - ``src/blinky.vhd``
     - ``top``
     - —

   * - :doc:`modules/pwm_controller/index`
     - ``src/pwm_controller.sv``
     - ``top``
     - —

   * - :doc:`modules/top/index`
     - ``src/top.vhd``
     - *(top)*
     - ``blinky``, ``pwm_controller``, ``traffic_light``

   * - :doc:`modules/traffic_light/index`
     - ``src/traffic_light.vhd``
     - ``top``
     - —
