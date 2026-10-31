# Full-feature example

A mixed VHDL / SystemVerilog design for a Lattice ECP5 that exercises **every feature** of
HDL AutoDoc, so there is one place to see all of the generated output.

> Work in progress: the design is being added module by module. This README is completed
> with the module list and the feature map when the design is finished.

## Synthesis strategy

The Yosys and ghdl front ends can share one design, in both directions (verified before the
design was written), so the build reports cover the **whole** mixed design:

- every SystemVerilog file is read with `read_verilog -sv`;
- every VHDL unit that no other VHDL unit instantiates is elaborated with
  `ghdl --std=08 <vhdl files> -e <unit>`; `ghdl` pulls in the VHDL that unit instantiates, so
  SystemVerilog can instantiate VHDL and VHDL can instantiate SystemVerilog components;
- a SystemVerilog parent cannot override a VHDL child's generics with `#(.NAME(value))`
  (Yosys sees a ghdl-elaborated module as non-parametric); generics are set on the ghdl side
  with `-g<name>=<value>`.

`make ecp5-reports` runs this flow (see the `Makefile`).
