"""Generate the register artifacts for axil_regs (VHDL packages, C header, HTML)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src" / "scripts" / "registers"))

from generate import OUTPUT_DIR, THIS_DIR, generate  # noqa: E402
from hdl_registers.parser.toml import from_toml  # noqa: E402

generate(from_toml(name="axil_regs", toml_file=THIS_DIR / "regs_axil_regs.toml"), OUTPUT_DIR)
