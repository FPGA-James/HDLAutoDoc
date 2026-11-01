# Full-feature example

A mixed VHDL / SystemVerilog design for a Lattice ECP5 that exercises **every feature** of
HDL AutoDoc, so there is one place to see all of the generated output.

## The design

A sampler: a converter clock (`adc_clk`) feeds samples through an asynchronous FIFO into the
system clock (`clk`); a capture window is started over an APB port that is bridged to AXI4-Lite;
captured samples and an external byte stream both go through packet filters.

| Module | Language | What it shows |
|---|---|---|
| `top` | VHDL | generics, header flow diagram, SystemVerilog children as components |
| `reset_sync` | VHDL | asynchronous-assert / synchronous-release reset, header sequence diagram |
| `sample_capture` | SV | two clock domains, two-flop synchroniser, dual-clock FIFO instance, parameter, header flow diagram |
| `async_fifo` | VHDL | generics, Gray-coded pointer synchronisers (CDC) |
| `sample_ctrl` | VHDL | FSM, WaveDrom, process-level Mermaid state diagram |
| `apb_bridge` | VHDL | flat APB and AXI4-Lite manager port groups |
| `axil_adapter` | SV | flat AXI4-Lite port group, an interface instantiated inside the module |
| `axil_regs` | SV | `axil_if.slave` interface port, register map, header sequence diagram |
| `stream_filter` | SV | FSM, `axis_if` ports, parameter, **two parents** (shared module) |
| `axis_pipeline`, `sample_stream` | SV | flat AXI4-Stream port groups, interface instances |
| `full_pkg.sv`, `axis_if.sv`, `axil_if.sv` | SV | package and interfaces (module-less support files) |

Also: `docs/hdl_autodoc/bus_groups.toml` (a custom port group), `registers/` (register map),
`tb/` (VUnit, cocotb and directed benches, one skipped test and one unlinked bench),
`reports/` (real Yosys/nextpnr output plus sample Vivado reports), and RTL schematics.
`test_example_full.py` checks, from the source files and the extractors' output, that the design still demonstrates the features above (it does not render the site, the schematics or the PDF).

## Try it

```bash
make doc-venv && make doc-html     # HTML: docs/hdl_autodoc/_build/html/index.html
make doc-pdf                       # PDF; Mermaid diagrams need mermaid-cli (mmdc), see the main README
make ecp5-reports                  # regenerate reports/yosys (needs yosys with ghdl, nextpnr-ecp5)
```

Interfaces here have no clock port: Yosys cannot pass a clocked interface instance to a
submodule.

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
