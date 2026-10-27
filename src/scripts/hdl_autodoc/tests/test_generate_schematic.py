"""Tests for generate_schematic.py's netlistsvg -> yosys-show renderer fallback."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import generate_schematic

from generate_schematic import render_schematic


def _sv_src(tmp_path: Path) -> Path:
    src = tmp_path / "pwm_controller.sv"
    src.write_text("module pwm_controller; endmodule")
    return src


def test_uses_netlistsvg_when_available(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", side_effect=lambda t: t in ("netlistsvg", "dot")), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_netlistsvg", return_value=True) as netlistsvg, \
         patch("generate_schematic._run_yosys_show") as yosys_show:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    netlistsvg.assert_called_once()
    yosys_show.assert_not_called()


def test_falls_back_to_yosys_show_when_netlistsvg_missing(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", side_effect=lambda t: t == "dot"), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_netlistsvg") as netlistsvg, \
         patch("generate_schematic._run_yosys_show", return_value=True) as yosys_show:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    netlistsvg.assert_not_called()
    yosys_show.assert_called_once()


def test_yosys_show_fallback_cleans_up_dot_intermediate(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"
    dot_path = tmp_path / "pwm_controller_schematic.dot"

    def fake_yosys_show(script_prefix, yosys_args, module_name, svg_prefix):
        dot_path.write_text("digraph {}")
        return True

    with patch("generate_schematic._have", side_effect=lambda t: t == "dot"), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_yosys_show", side_effect=fake_yosys_show):
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    assert not dot_path.exists()


def test_falls_back_to_yosys_show_when_netlistsvg_render_fails(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", side_effect=lambda t: t in ("netlistsvg", "dot")), \
         patch("generate_schematic._run_yosys", return_value=(True, "")), \
         patch("generate_schematic._run_netlistsvg", return_value=False), \
         patch("generate_schematic._run_yosys_show", return_value=True) as yosys_show:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is True
    yosys_show.assert_called_once()


def test_returns_false_when_no_renderer_available(tmp_path):
    src = _sv_src(tmp_path)
    json_path = tmp_path / "pwm_controller_schematic.json"
    svg_path = tmp_path / "pwm_controller_schematic.svg"

    with patch("generate_schematic._have", return_value=False), \
         patch("generate_schematic._run_yosys") as run_yosys:
        ok = render_schematic(src, "pwm_controller", [], json_path, svg_path)

    assert ok is False
    run_yosys.assert_not_called()


def test_returns_false_for_unsupported_extension(tmp_path):
    src = tmp_path / "thing.txt"
    src.write_text("not hdl")
    json_path = tmp_path / "thing_schematic.json"
    svg_path = tmp_path / "thing_schematic.svg"

    with patch("generate_schematic._have", return_value=True), \
         patch("generate_schematic._run_yosys") as run_yosys:
        ok = render_schematic(src, "thing", [], json_path, svg_path)

    assert ok is False
    run_yosys.assert_not_called()


def test_netlistsvg_is_given_the_custom_skin(tmp_path):
    """The bundled skin is passed to netlistsvg, and dropped if the file is absent."""
    ok = MagicMock(returncode=0, stderr="")
    with patch("generate_schematic.subprocess.run", return_value=ok) as run:
        assert generate_schematic._run_netlistsvg(tmp_path / "a.json", tmp_path / "a.svg", "m")
    cmd = run.call_args[0][0]
    assert cmd[cmd.index("--skin") + 1] == str(generate_schematic.NETLISTSVG_SKIN)
    assert generate_schematic.NETLISTSVG_SKIN.is_file()

    with patch("generate_schematic.NETLISTSVG_SKIN", tmp_path / "missing.svg"), \
         patch("generate_schematic.subprocess.run", return_value=ok) as run:
        generate_schematic._run_netlistsvg(tmp_path / "a.json", tmp_path / "a.svg", "m")
    assert "--skin" not in run.call_args[0][0]


def test_sv_stub_mirrors_generics_and_ports_and_ties_outputs_low(tmp_path):
    """A SV child becomes a VHDL entity with matching ports, outputs driven to 0."""
    sv = tmp_path / "pwm.sv"
    sv.write_text(
        "module pwm #(\n    parameter int WIDTH = 8\n)(\n"
        "    input  logic              clk,\n"
        "    input  logic [WIDTH-1:0]  duty_i,\n"
        "    output logic              pwm_o,\n"
        "    output logic [3:0]        cnt_o\n);\nendmodule\n"
    )
    vhdl = generate_schematic.sv_module_stub_vhdl(sv)
    assert "entity pwm is" in vhdl
    assert "WIDTH : integer := 8" in vhdl
    assert "duty_i : in std_logic_vector(WIDTH-1 downto 0)" in vhdl
    assert "pwm_o <= '0';" in vhdl
    assert "cnt_o <= (others => '0');" in vhdl


def test_sv_stub_is_none_when_there_are_no_ports(tmp_path):
    sv = tmp_path / "x.sv"
    sv.write_text("module x; endmodule\n")
    assert generate_schematic.sv_module_stub_vhdl(sv) is None


def test_prepare_netlist_puts_module_first_and_strips_generic_suffixes(tmp_path):
    """The requested module leads, and ghdl's `<entity>_<generics>` names are tidied."""
    import json
    j = tmp_path / "n.json"
    j.write_text(json.dumps({"modules": {
        "child_8": {"cells": {}},
        "top": {"cells": {"u": {"type": "child_8"}}},
        "my_fifo_2": {"cells": {}},          # base not a known entity: left alone
    }}))
    generate_schematic._prepare_netlist(j, "top", {"top", "child"})
    data = json.loads(j.read_text())
    assert list(data["modules"]) == ["top", "child", "my_fifo_2"]
    assert data["modules"]["top"]["cells"]["u"]["type"] == "child"


# ─────────────────────────────────────────────────────────────────────────────
# SystemVerilog support files (packages / interfaces) and hierarchy -top
# ─────────────────────────────────────────────────────────────────────────────

def _read_order(prefix: str) -> list[str]:
    """File names in the order the prefix reads them."""
    import re
    return [Path(f).name for f in re.findall(r"read_verilog -sv (\S+?);", prefix)]


def test_sv_prefix_reads_support_then_deps_then_module_then_hierarchy_top():
    """Package-before-use: support files, then dependencies, then the module itself."""
    prefix, args = generate_schematic._build_prefix_sv(
        Path("src/top.sv"),
        [Path("src/child.sv")],
        [Path("src/aes_pkg.sv"), Path("src/bus_if.sv")],
        "top",
    )
    assert _read_order(prefix) == ["aes_pkg.sv", "bus_if.sv", "child.sv", "top.sv"]
    assert prefix.endswith("hierarchy -top top; proc; opt;")
    assert prefix.index("hierarchy -top") > prefix.rindex("read_verilog")
    assert args == []


def test_sv_prefix_without_support_files_keeps_the_old_read_order():
    prefix, _ = generate_schematic._build_prefix_sv(
        Path("src/top.sv"), [Path("src/child.sv")], module_name="top")
    assert _read_order(prefix) == ["child.sv", "top.sv"]
    assert "hierarchy -top top; proc; opt;" in prefix


def test_sv_prefix_dedupes_and_ignores_non_sv_support_files():
    prefix, _ = generate_schematic._build_prefix_sv(
        Path("src/top.sv"),
        [Path("src/pkg.sv")],                      # also a support file
        [Path("src/pkg.sv"), Path("src/other.vhd")],
        "top",
    )
    assert _read_order(prefix) == ["pkg.sv", "top.sv"]


def test_sv_top_uses_the_modules_real_spelling(tmp_path):
    """hierarchy.json lower-cases names but `hierarchy -top` is case-sensitive."""
    src = tmp_path / "mymod.sv"
    src.write_text("module MyMod (input logic clk);\nendmodule\n")
    prefix, _ = generate_schematic._build_prefix_sv(src, [], [], "mymod")
    assert "hierarchy -top MyMod;" in prefix


def test_render_passes_support_files_to_the_sv_prefix(tmp_path):
    """render_schematic hands the support files to the SV prefix builder."""
    src = _sv_src(tmp_path)
    with patch("generate_schematic._build_prefix_sv", return_value=None) as build:
        render_schematic(src, "pwm_controller", [Path("dep.sv")],
                         tmp_path / "a.json", tmp_path / "a.svg",
                         [Path("pkg.sv")])
    build.assert_called_once_with(src, [Path("dep.sv")], [Path("pkg.sv")], "pwm_controller")


def test_vhdl_prefix_ignores_support_files(tmp_path):
    """VHDL behaviour is unchanged: support files never reach the ghdl prefix."""
    src = tmp_path / "blinky.vhd"
    src.write_text("entity blinky is end entity;")
    with patch("generate_schematic._build_prefix_vhdl", return_value=None) as build, \
         patch("generate_schematic._build_prefix_sv") as build_sv:
        render_schematic(src, "blinky", [Path("dep.vhd")],
                         tmp_path / "a.json", tmp_path / "a.svg",
                         [Path("pkg.sv")])
    build_sv.assert_not_called()
    args = build.call_args[0]
    assert args[:3] == (src, "blinky", [Path("dep.vhd")])
    assert Path("pkg.sv") not in args[2]


def test_parse_source_args_splits_dependencies_from_support_files():
    extras, support = generate_schematic.parse_source_args(
        ["dep1.sv", "--support", "pkg.sv", "dep2.sv", "--support", "if.sv"])
    assert extras == [Path("dep1.sv"), Path("dep2.sv")]
    assert support == [Path("pkg.sv"), Path("if.sv")]
    assert generate_schematic.parse_source_args([]) == ([], [])


def test_prepare_netlist_labels_interface_copies_and_undots_port_names(tmp_path):
    """`mod$interfaces$if` boxes get the module name; dotted interface ports lose the dot."""
    import json
    j = tmp_path / "n.json"
    j.write_text(json.dumps({"modules": {
        "producer$interfaces$stream_if": {"ports": {}, "cells": {}},
        "producer": {"ports": {"out_if.data": {"bits": [2]}, "clk": {"bits": [3]}},
                     "cells": {}},
        "top": {"ports": {"q": {"bits": [4]}},
                "cells": {"p": {"type": "producer$interfaces$stream_if"}}},
    }}))
    generate_schematic._prepare_netlist(j, "producer", {"producer", "top"})
    data = json.loads(j.read_text())
    assert next(iter(data["modules"])) == "producer"
    assert set(data["modules"]["producer"]["ports"]) == {"out_if_data", "clk"}
    # `producer` already exists, so the derived copy keeps its distinct name.
    assert "producer$interfaces$stream_if" in data["modules"]
    assert data["modules"]["top"]["cells"]["p"]["type"] == "producer$interfaces$stream_if"


def test_prepare_netlist_strips_interface_suffix_when_the_name_is_free(tmp_path):
    import json
    j = tmp_path / "n.json"
    j.write_text(json.dumps({"modules": {
        "consumer$interfaces$stream_if": {"ports": {}, "cells": {}},
        "top": {"ports": {}, "cells": {"c": {"type": "consumer$interfaces$stream_if"}}},
    }}))
    generate_schematic._prepare_netlist(j, "top", {"top"})
    data = json.loads(j.read_text())
    assert "consumer" in data["modules"]
    assert data["modules"]["top"]["cells"]["c"]["type"] == "consumer"
