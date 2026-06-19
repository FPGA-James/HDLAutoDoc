from pathlib import Path

from hdl_registers.parser.toml import from_toml
from hdl_registers.parser.yaml import from_yaml

from hdl_registers.generator.vhdl.register_package import VhdlRegisterPackageGenerator
from hdl_registers.generator.vhdl.record_package import VhdlRecordPackageGenerator
from hdl_registers.generator.vhdl.axi_lite.wrapper import VhdlAxiLiteWrapperGenerator
from hdl_registers.generator.c.header import CHeaderGenerator
from hdl_registers.generator.html.page import HtmlPageGenerator

THIS_DIR = Path(__file__).parents[2] / "registers"
OUTPUT_DIR = THIS_DIR / "generated"


def generate(register_list, output_folder):
    output_folder.mkdir(parents=True, exist_ok=True)

    # VHDL: register address/field constants package
    VhdlRegisterPackageGenerator(
        register_list=register_list, output_folder=output_folder
    ).create()

    # VHDL: natively-typed record package (use this in RTL)
    VhdlRecordPackageGenerator(
        register_list=register_list, output_folder=output_folder
    ).create()

    # VHDL: AXI-Lite register file wrapper (instantiate in your design)
    VhdlAxiLiteWrapperGenerator(
        register_list=register_list, output_folder=output_folder
    ).create()

    # C header (for embedded drivers)
    CHeaderGenerator(
        register_list=register_list, output_folder=output_folder
    ).create()

    # HTML documentation
    HtmlPageGenerator(
        register_list=register_list, output_folder=output_folder
    ).create()


# --- Parse from TOML ---
regs_toml = from_toml(name="counter", toml_file=THIS_DIR / "regs_counter.toml")
generate(regs_toml, OUTPUT_DIR )

# --- Parse from YAML (produces identical output) ---
# regs_yaml = from_yaml(name="counter", yaml_file=THIS_DIR / "regs_counter.yaml")
# generate(regs_yaml, OUTPUT_DIR / "from_yaml")