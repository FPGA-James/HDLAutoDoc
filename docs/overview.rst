test123 — Overview
==================

This project contains 5 VHDL/SV modules.

Top-level module: :doc:`modules/top/index`

Modules
-------

.. list-table::
   :header-rows: 1

   * - Module
     - Source File
     - Description

   * - :doc:`modules/traffic_light/index`
     - ``traffic_light.vhd``
     - Traffic light controller. Implements a standard UK traffic light sequencer with four states:

   * - :doc:`modules/pwm_controller/index`
     - ``pwm_controller.sv``
     - PWM controller module. Generates a variable duty-cycle PWM signal using a 3-state FSM:

   * - :doc:`modules/cfg_sync/index`
     - ``cfg_sync.vhd``
     - cfg_sync entity.

   * - :doc:`modules/top/index`
     - ``top.vhd``
     - top entity.

   * - :doc:`modules/blinky/index`
     - ``blinky.vhd``
     - Blinky LED controller. Implements a 3-state FSM that drives an LED through a repeating
