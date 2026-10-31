# ECP5 example

A small ECP5 design that exercises every section of the generated documentation: an
**AXI4-Stream** threshold filter, controlled through an **AXI4-Lite** register file,
with testbenches in all three supported frameworks and **real** Yosys / nextpnr reports.

| Path | What it is |
|---|---|
| `src/axis_if.sv`, `src/axil_if.sv` | Interfaces with `master` / `slave` modports (support files: no module) |
| `src/axil_regs.sv` | AXI4-Lite register file (`axil_if.slave`), four registers |
| `src/stream_filter.sv` | Forwards bytes at or above a threshold (`axis_if.slave` in, `axis_if.master` out) |
| `src/top.sv` | Wires the two together; the interfaces are its ports |
| `registers/regs_axil_regs.toml` | Register map for `axil_regs` (`ctrl`, `status`, `threshold`, `scratch`) |
| `tb/vunit/`, `tb/cocotb/`, `tb/directed/` | One testbench per framework: 3 + 3 + 2 tests |
| `reports/yosys/` | `yosys.log`, `stat.txt`, `nextpnr.log` from a real run |

```bash
make doc-venv && make doc-html      # → docs/hdl_autodoc/_build/html/index.html
```

In the generated site:

- **Verification** lists the three testbenches and their eight tests (one skipped), each
  linked to the module it tests.
- **Build** shows the Yosys and nextpnr versions, device utilisation, the achieved fmax
  against the 100 MHz target, and the warnings.
- **Top → Block Diagram** shows the three interface ports; **axil_regs → Registers** lists
  the four registers.

## Testbenches

The testbenches show the layout and the comment conventions; they are *not* run by the
documentation build, and VUnit and cocotb are not dependencies of this example.
Directed tests are marked with a comment before each scenario:

```systemverilog
// TEST: register_write_read — a value written to scratch reads back unchanged
```

## Regenerating the reports

```bash
make ecp5-reports      # needs yosys and nextpnr-ecp5 on PATH (the OSS CAD Suite has both)
```

This runs `synth_ecp5` and `nextpnr-ecp5 --25k --package CABGA256` and rewrites
`reports/yosys/`. The committed logs contain the tool paths of the machine that produced
them. Where the reports live is set by `AUTODOC_REPORTS_DIR` (default `reports`) and the
testbenches by `AUTODOC_TB_DIR` (default `tb`); `make doc-html TESTBENCHES=0 BUILD=0`
removes both sections.
