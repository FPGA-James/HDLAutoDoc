# SystemVerilog interface example

A small SystemVerilog design that shows how packages and interfaces are documented:

| File | Role |
|---|---|
| `src/bus_pkg.sv` | Package — recorded as a *support file* (no module) |
| `src/axis_if.sv`, `src/axil_if.sv` | Interfaces with modports — also support files |
| `src/bridge.sv` | Module with `axil_if.slave`, `axis_if.master` and a modport-less `axis_if` port |
| `src/top.sv` | Top level, instantiates `bridge` |

```bash
make doc-venv && make doc-html     # → docs/hdl_autodoc/_build/html/index.html
```

Open **Top → bridge → Block Diagram** to see the interface ports in the port table (Direction = modport, Type = interface), the `name (interface)` ports on the diagram, and the **Interfaces** section listing each interface's members. **Top → Block Diagram** has no interface ports (only `clk` and `rst`), but a blue **interfaces** box on the diagram lists the interfaces it instantiates, and its **Interfaces** section documents them ("instantiated here as ...").

`filelist.f` is dependency-ordered, so the package and interfaces come before the modules that use them. Support files are read first when generating RTL schematics.

The modport-less `s_dbg` port is deliberate: it shows the interface port in the block page, but netlistsvg rejects the `inout` members yosys gives it, so `bridge` falls back to yosys's own (plainer) schematic renderer and `top` gets no RTL schematic. Give the port a modport (`axis_if.slave s_dbg`) for clean schematics.
